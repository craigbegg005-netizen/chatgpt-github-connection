"""SQLite-backed canonical shared state, durable job queue, and audit log.

This is the piece that makes the connector worth having: Oddfellow owns the shared
project state, so work can move between providers without any provider having to
share its private memory with another. A provider reads state, claims a job,
submits a result, and is forgotten. The state outlives all of them.

Three tables, one file, no server:

  * ``state``  -- canonical project state, one row per (project, key), JSON value.
  * ``jobs``   -- the durable queue. ``job_id`` is the primary key, so creating the
                  same job twice is a no-op that returns the existing row.
  * ``audit``  -- append-only event log. It records *that* something happened,
                  never the payload or the result. A connector that logs job
                  contents would become the single richest place to steal from.

Plus a ``flags`` table for the emergency pause, which has to survive a restart --
a stop button that forgets it was pressed is not a stop button.

Idempotency is enforced in two places on purpose: the primary key stops duplicate
*creation*, and (job_id, result_hash) stops duplicate *submission* when a job is
retried, including across a provider failover.
"""

from __future__ import annotations

import json
import secrets
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from .schema import (
    APPROVAL_REQUIRED,
    Job,
    Risk,
    Status,
    canonical_json,
    canonical_provider,
    result_hash,
)


class ClaimRefused(Exception):
    """A claim was refused. Distinct from an error: refusal is a normal outcome."""


class SubmitRefused(Exception):
    """A result submission was refused."""


SCHEMA = """
CREATE TABLE IF NOT EXISTS state (
    project     TEXT NOT NULL,
    key         TEXT NOT NULL,
    value       TEXT NOT NULL,
    updated_at  TEXT NOT NULL,
    updated_by  TEXT NOT NULL,
    PRIMARY KEY (project, key)
);

CREATE TABLE IF NOT EXISTS jobs (
    job_id        TEXT PRIMARY KEY,
    kind          TEXT NOT NULL,
    title         TEXT NOT NULL,
    payload       TEXT NOT NULL,
    risk          TEXT NOT NULL,
    status        TEXT NOT NULL,
    provider      TEXT,
    transport     TEXT,
    depends_on    TEXT NOT NULL DEFAULT '[]',
    attempts      INTEGER NOT NULL DEFAULT 0,
    max_attempts  INTEGER NOT NULL DEFAULT 3,
    result        TEXT,
    result_hash   TEXT,
    error         TEXT,
    verified      INTEGER NOT NULL DEFAULT 0,
    verified_by   TEXT,
    verification_evidence TEXT,
    created_at    TEXT NOT NULL,
    updated_at    TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS jobs_status ON jobs(status);
CREATE INDEX IF NOT EXISTS jobs_provider ON jobs(provider);

CREATE TABLE IF NOT EXISTS audit (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    at          TEXT NOT NULL,
    actor       TEXT NOT NULL,
    event       TEXT NOT NULL,
    job_id      TEXT,
    detail      TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS approvals (
    approval_id  TEXT PRIMARY KEY,
    job_id       TEXT NOT NULL,
    risk         TEXT NOT NULL,
    state        TEXT NOT NULL,
    requested_by TEXT NOT NULL,
    requested_at TEXT NOT NULL,
    decided_by   TEXT,
    decided_at   TEXT,
    note         TEXT NOT NULL DEFAULT '',
    evidence     TEXT NOT NULL DEFAULT ''
);

CREATE INDEX IF NOT EXISTS approvals_job ON approvals(job_id);

CREATE TABLE IF NOT EXISTS flags (
    key    TEXT PRIMARY KEY,
    value  TEXT NOT NULL,
    at     TEXT NOT NULL
);
"""

#: Columns added after the first release. Applied idempotently so an existing
#: connector database upgrades in place rather than needing to be deleted -- a
#: queue that must be discarded to be upgraded is a queue that loses work.
_ADDED_COLUMNS = (
    ("jobs", "verified", "INTEGER NOT NULL DEFAULT 0"),
    ("jobs", "verified_by", "TEXT"),
    ("jobs", "verification_evidence", "TEXT"),
)

#: Detail keys the audit log refuses to store verbatim. A payload that reaches the
#: log has escaped the approval gate and the scoping rules, so this is enforced
#: centrally rather than trusted to each caller.
_REDACTED_KEYS = frozenset(
    {
        "payload", "result", "token", "secret", "password", "key", "credential",
        "authorization", "value", "body", "content", "detail", "text",
    }
)

#: Scalars longer than this are truncated. Long enough for a reason or an error
#: message, short enough that a mis-typed key cannot dump a document into the log.
_MAX_SCALAR = 200


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _evidence_is_checkable(evidence: str) -> bool:
    """A heuristic floor on evidence: does the string *look like* a reference?

    **This is a heuristic, not a property, and the distinction is the point.**
    Whether a string "names something another party could check" is not
    decidable by inspecting the string -- `"see src/foo.py"` and
    `"looks fine/ok"` are the same shape, and only one of them points anywhere.
    No rule here can tell them apart, so this function does not claim to. It
    raises the floor from "non-empty" to "shaped like a reference" and leaves
    the real judgment to the verifier, which is where it belongs.

    **What it does catch:** a bare assertion with no reference-shaped token --
    "looks fine", "ok", "verified it myself", "trust me", "done", "n/a".

    **What it does not catch, stated plainly because the previous version of
    this function claimed otherwise:** a filler phrase with a reference-shaped
    token bolted on. `"looks fine/ok"` passes. So does `"done#1"` and
    `"deadbeef"`. An earlier revision tested only `"/" in evidence`, so the
    exact string this docstring names -- `"looks fine"` plus a single trailing
    slash -- was accepted, and the regression test shipped alongside it checked
    only the four strings the author had in mind. That is a proxy recorded as a
    property, the same mistake this project has now made eight times.

    If the floor needs to be a real property rather than a heuristic, the fix is
    not a better regex -- it is structured evidence (a typed kind plus a value,
    as `workforce.EvidenceKind` already models) so the *shape* is enforced
    instead of guessed from prose.
    """
    import re as _re

    lowered = evidence.lower().strip()
    # A handful of pure-filler tokens that are reference-shaped by accident --
    # `n/a` matches a path pattern because it has a slash and word characters on
    # both sides. This list is illustrative, not exhaustive, and is not a claim
    # that everything outside it is real evidence.
    if lowered.rstrip("./! ") in {"n/a", "na", "none", "nil", "tbd", "n.a"}:
        return False
    # A URL may be embedded in a sentence ("see https://..."), not only leading.
    if _re.search(r"https?://\S", evidence):
        return True
    # A path needs a word character on both sides of the slash. `"looks fine/"`
    # and `"done/"` have nothing after it, so they no longer pass.
    if _re.search(r"(?:^|[\s(])\.{0,2}/?\w[\w.\-]*/\w", evidence):
        return True
    if lowered.startswith(("commit ", "apr-", "job-")):
        return True  # an identifier reference
    if _re.search(r"\b[0-9a-f]{7,40}\b", lowered):
        return True  # a commit-like hash named in prose
    return False


def _summarise(key: str, value: Any) -> Any:
    """Decide what an audit entry may keep for one detail value.

    Returns the value itself for short, non-payload scalars; a type-and-length
    placeholder for everything else.
    """
    if key.lower() in _REDACTED_KEYS:
        return f"<{type(value).__name__} len={len(value)}>" if hasattr(value, "__len__") else f"<{type(value).__name__}>"
    if isinstance(value, (list, tuple, set, dict)):
        return f"<{type(value).__name__} len={len(value)}>"
    if isinstance(value, str):
        if len(value) > _MAX_SCALAR:
            return value[:_MAX_SCALAR] + f"...<truncated, {len(value)} chars>"
        return value
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    return f"<{type(value).__name__}>"


class Store:
    """All connector persistence. Safe to construct against a path or ``:memory:``."""

    def __init__(self, path: str | Path = ":memory:") -> None:
        self.path = str(path)
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.path)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(SCHEMA)
        self._migrate()
        self._conn.commit()

    def _migrate(self) -> None:
        """Add columns introduced after the first release, if they are missing."""
        for table, column, decl in _ADDED_COLUMNS:
            existing = {
                r["name"] for r in self._conn.execute(f"PRAGMA table_info({table})")
            }
            if column not in existing:
                self._conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {decl}")

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> "Store":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    # ---------------------------------------------------------------- audit

    def audit(
        self,
        actor: str,
        event: str,
        job_id: str | None = None,
        **detail: Any,
    ) -> None:
        """Append an audit event. Payload-class values are stripped, not trusted.

        Two rules, and the split between them matters:

          * a key naming payload-class data (``payload``, ``result``, ``token``,
            ``value``, ...) is replaced by its type and length, whatever it holds;
          * anything else that is a short scalar is kept verbatim, because an audit
            log that cannot say *why* something happened is not an audit log --
            it is a counter. ``reason``, ``error`` and ``provider`` are the entries
            someone reads when reconstructing an incident.

        Containers are always summarised, and long scalars are truncated, so a
        mis-typed key cannot dump a document into the log.
        """
        safe = {k: _summarise(k, v) for k, v in detail.items()}
        self._conn.execute(
            "INSERT INTO audit (at, actor, event, job_id, detail) VALUES (?,?,?,?,?)",
            (_now(), actor, event, job_id, canonical_json(safe)),
        )
        self._conn.commit()

    def audit_trail(self, limit: int = 50) -> list[dict]:
        rows = self._conn.execute(
            "SELECT * FROM audit ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]

    # ---------------------------------------------------------------- pause

    def set_paused(self, paused: bool, actor: str, reason: str = "") -> None:
        self._conn.execute(
            "INSERT INTO flags (key, value, at) VALUES ('paused', ?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value, at=excluded.at",
            (canonical_json({"paused": paused, "reason": reason}), _now()),
        )
        self._conn.commit()
        self.audit(actor, "pause.set" if paused else "pause.clear", reason=reason)

    def is_paused(self) -> bool:
        row = self._conn.execute("SELECT value FROM flags WHERE key='paused'").fetchone()
        if not row:
            return False
        return bool(json.loads(row["value"]).get("paused"))

    def pause_reason(self) -> str:
        row = self._conn.execute("SELECT value FROM flags WHERE key='paused'").fetchone()
        if not row:
            return ""
        return str(json.loads(row["value"]).get("reason", ""))

    # ---------------------------------------------------------------- flags

    def flag_get(self, key: str, default: str | None = None) -> str | None:
        """Read a durable key/value flag. Survives a restart, like the pause flag.

        Generic because a worker needs to remember what it last did: without a
        place to record "I already rendered a handoff for this exact set of jobs",
        every tick either repeats identical work forever or does nothing at all.
        """
        row = self._conn.execute(
            "SELECT value FROM flags WHERE key=?", (key,)
        ).fetchone()
        return row["value"] if row else default

    def flag_set(self, key: str, value: str) -> None:
        self._conn.execute(
            "INSERT INTO flags (key, value, at) VALUES (?, ?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value, at=excluded.at",
            (key, value, _now()),
        )
        self._conn.commit()

    # ---------------------------------------------------------------- state

    def set_state(self, project: str, key: str, value: Any, actor: str) -> None:
        self._conn.execute(
            "INSERT INTO state (project, key, value, updated_at, updated_by) VALUES (?,?,?,?,?) "
            "ON CONFLICT(project, key) DO UPDATE SET value=excluded.value, "
            "updated_at=excluded.updated_at, updated_by=excluded.updated_by",
            (project, key, canonical_json(value), _now(), actor),
        )
        self._conn.commit()
        self.audit(actor, "state.set", project=project, key=key, value=value)

    def get_state(self, project: str, key: str | None = None) -> Any:
        if key is None:
            rows = self._conn.execute(
                "SELECT key, value FROM state WHERE project=? ORDER BY key", (project,)
            ).fetchall()
            return {r["key"]: json.loads(r["value"]) for r in rows}
        row = self._conn.execute(
            "SELECT value FROM state WHERE project=? AND key=?", (project, key)
        ).fetchone()
        return json.loads(row["value"]) if row else None

    # ---------------------------------------------------------------- jobs

    def create_job(self, job: Job, actor: str) -> tuple[Job, bool]:
        """Insert a job, or return the existing one.

        Returns ``(job, created)``. ``created=False`` means the id already existed,
        which is the intended behaviour when two AIs independently derive the same
        job from the same instruction -- the second one is told so, and no
        duplicate work is queued.

        A job may be created already claimed (``provider`` set). That is the one
        write path that stored the provider verbatim, which made it the one place
        a provider id could escape canonicalisation -- a job created under
        ``Anthropic`` was invisible to ``disconnect_provider("anthropic")``, so
        the disconnect reported itself clean while the claim stayed stranded. No
        shipped caller sets ``provider`` here, so it was not reachable from the
        CLI; it was still the gap in "canonicalised at every write", and QA found
        it by reading rather than by exploiting.
        """
        existing = self.get_job(job.job_id)
        if existing:
            self.audit(actor, "job.duplicate", job_id=job.job_id)
            return existing, False

        if job.provider is not None:
            job.provider = canonical_provider(job.provider)
        job.created_at = job.created_at or _now()
        job.updated_at = job.created_at
        row = job.to_row()
        self._conn.execute(
            "INSERT INTO jobs (job_id, kind, title, payload, risk, status, provider, "
            "transport, depends_on, attempts, max_attempts, result, result_hash, error, "
            "created_at, updated_at) VALUES (:job_id,:kind,:title,:payload,:risk,:status,"
            ":provider,:transport,:depends_on,:attempts,:max_attempts,:result,:result_hash,"
            ":error,:created_at,:updated_at)",
            row,
        )
        self._conn.commit()
        self.audit(actor, "job.create", job_id=job.job_id, risk=job.risk.value, title=job.title)
        return job, True

    def get_job(self, job_id: str) -> Job | None:
        row = self._conn.execute("SELECT * FROM jobs WHERE job_id=?", (job_id,)).fetchone()
        return Job.from_row(dict(row)) if row else None

    def jobs(self, status: Status | None = None) -> list[Job]:
        if status:
            rows = self._conn.execute(
                "SELECT * FROM jobs WHERE status=? ORDER BY created_at, job_id",
                (status.value,),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM jobs ORDER BY created_at, job_id"
            ).fetchall()
        return [Job.from_row(dict(r)) for r in rows]

    def _update(self, job: Job, actor: str, event: str, **detail: Any) -> Job:
        job.updated_at = _now()
        row = job.to_row()
        self._conn.execute(
            "UPDATE jobs SET kind=:kind, title=:title, payload=:payload, risk=:risk, "
            "status=:status, provider=:provider, transport=:transport, "
            "depends_on=:depends_on, attempts=:attempts, max_attempts=:max_attempts, "
            "result=:result, result_hash=:result_hash, error=:error, "
            "verified=:verified, verified_by=:verified_by, "
            "verification_evidence=:verification_evidence, "
            "updated_at=:updated_at WHERE job_id=:job_id",
            row,
        )
        self._conn.commit()
        self.audit(actor, event, job_id=job.job_id, status=job.status.value, **detail)
        return job

    def set_status(self, job: Job, status: Status, actor: str, error: str | None = None) -> Job:
        job.status = status
        if error is not None:
            job.error = error
        return self._update(job, actor, "job.status")

    # ------------------------------------------------------------ approvals

    def request_approval(self, job_id: str, actor: str, note: str = "") -> dict:
        """Open a pending approval for one job. Asks; it never grants.

        Bound to a job id at creation, so an approval can never be re-pointed at
        different work later. That binding is the whole difference between this
        and the boolean it replaces.
        """
        job = self._require(job_id)
        record = {
            "approval_id": "apr-" + secrets.token_hex(8),
            "job_id": job.job_id,
            "risk": job.risk.value,
            "state": "WAITING_AUTHORIZATION",
            "requested_by": actor,
            "requested_at": _now(),
            "decided_by": None,
            "decided_at": None,
            "note": (note or "").strip(),
            "evidence": "",
        }
        self._conn.execute(
            "INSERT INTO approvals (approval_id, job_id, risk, state, requested_by, "
            "requested_at, decided_by, decided_at, note, evidence) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (
                record["approval_id"], record["job_id"], record["risk"], record["state"],
                record["requested_by"], record["requested_at"], None, None,
                record["note"], "",
            ),
        )
        self._conn.commit()
        self.audit(actor, "job.approval.requested", job_id=job_id,
                   approval_id=record["approval_id"], risk=record["risk"])
        return record

    def decide_approval(
        self,
        approval_id: str,
        decision: str,
        actor: str,
        note: str = "",
        evidence: str = "",
    ) -> dict:
        """Grant or refuse a pending approval. Once decided, it is decided.

        Re-deciding is refused rather than overwritten: an approval whose outcome
        can be edited after the fact is not a record of a decision, and the audit
        trail would show two different truths for one id.
        """
        if decision not in ("approve", "reject"):
            raise ValueError("decision must be approve or reject")
        row = self._conn.execute(
            "SELECT * FROM approvals WHERE approval_id=?", (approval_id,)
        ).fetchone()
        if row is None:
            raise KeyError(approval_id)
        if row["state"] != "WAITING_AUTHORIZATION":
            raise ValueError(f"approval is already {row['state']}")

        state = "APPROVED" if decision == "approve" else "REJECTED"
        self._conn.execute(
            "UPDATE approvals SET state=?, decided_by=?, decided_at=?, note=?, evidence=? "
            "WHERE approval_id=? AND state='WAITING_AUTHORIZATION'",
            (state, actor, _now(), (note or "").strip(), (evidence or "").strip(), approval_id),
        )
        self._conn.commit()
        self.audit(actor, "job.approval.decided", job_id=row["job_id"],
                   approval_id=approval_id, decision=decision)
        return self.get_approval(approval_id)

    def get_approval(self, approval_id: str) -> dict | None:
        row = self._conn.execute(
            "SELECT * FROM approvals WHERE approval_id=?", (approval_id,)
        ).fetchone()
        return dict(row) if row is not None else None

    def approvals_for_job(self, job_id: str) -> list[dict]:
        rows = self._conn.execute(
            "SELECT * FROM approvals WHERE job_id=? ORDER BY requested_at", (job_id,)
        ).fetchall()
        return [dict(r) for r in rows]

    def approval_state_for_job(self, job_id: str) -> str:
        """``APPROVED`` if any live approval for this job is granted, else the latest state.

        This is the value a *planner* should route on. It is not enforcement --
        `claim_job` re-checks the record itself, because a decision read now and
        acted on later is a decision that can change in between.
        """
        rows = self.approvals_for_job(job_id)
        if any(r["state"] == "APPROVED" for r in rows):
            return "APPROVED"
        return rows[-1]["state"] if rows else "NONE"

    def _require_approval(self, job: Job, approval_id: str | None, actor: str) -> None:
        """Refuse a gated claim unless a live approval covers *this* job.

        Until 2026-10-02 this was `if job.risk in APPROVAL_REQUIRED and not
        approved:` -- a boolean the caller passed in. The refusal was real, but
        the enforcement was nominal: `claim_job(..., approved=True)` claimed any
        gated job, and `handoff.apply_handoff` and the CLI passed the flag
        straight through from an argument. Nothing recorded who approved what.

        Four conditions, all required:

        1. an ``approval_id`` was supplied;
        2. it names a record that exists;
        3. it is ``APPROVED``;
        4. it is bound to this job, at this risk level.

        Condition 4 is what a boolean cannot express. An approval is for one
        piece of work, and re-pointing it at different work is the failure this
        exists to prevent.
        """
        def refuse(reason: str, message: str) -> None:
            self.audit(actor, "job.claim.refused", job_id=job.job_id, reason=reason)
            raise ClaimRefused(message)

        if not approval_id:
            refuse(
                "unapproved",
                f"{job.risk.value}-risk work cannot be claimed without an approval id; "
                "request one with Store.request_approval and have the owner decide it",
            )

        record = self.get_approval(approval_id)
        if record is None:
            refuse("unknown_approval", f"no approval {approval_id!r} exists")

        if record["state"] != "APPROVED":
            refuse(
                "not_approved",
                f"approval {approval_id!r} is {record['state']}, not APPROVED",
            )

        if record["job_id"] != job.job_id:
            refuse(
                "approval_for_other_job",
                f"approval {approval_id!r} authorises {record['job_id']!r}, not {job.job_id!r}",
            )

        if record["risk"] != job.risk.value:
            refuse(
                "approval_risk_mismatch",
                f"approval {approval_id!r} was granted for {record['risk']} risk, "
                f"but this job is {job.risk.value}",
            )

    def claim_job(
        self,
        job_id: str,
        provider: str,
        transport: Any,
        actor: str,
        *,
        paused: bool = False,
        approval_id: str | None = None,
    ) -> Job:
        """Claim a READY job for a provider, or refuse with a reason.

        Refusals, each preventing a specific failure:

          * **paused** -- the emergency stop blocks claims, not merely new work.
          * **not READY** -- a RUNNING job must not be claimed twice, and a
            COMPLETE one must not be quietly reopened by a second claim.
          * **unapproved high/critical** -- approval is checked before the claim,
            so gated work cannot be picked up and run first. The check reads a
            persisted approval record bound to *this* job; it does not trust a
            boolean the caller supplied. See `_require_approval`.

        The state change is a *conditional* UPDATE, so two providers racing produce
        one winner and one refusal rather than two RUNNING rows.

        The provider id is canonicalised here as well as at token issue. Storing
        it verbatim was the second half of the disconnect bug: a job claimed by
        ``Anthropic`` was invisible to ``disconnect_provider("anthropic")``, so
        the disconnect revoked the token, released no claims, and reported itself
        clean -- leaving the work stranded in RUNNING under a provider that no
        longer exists. Canonicalising at the *write* is what makes every later
        comparison correct, rather than patching each comparison in turn.
        """
        provider = canonical_provider(provider)
        job = self._require(job_id)
        if paused:
            self.audit(actor, "job.claim.refused", job_id=job_id, reason="paused")
            raise ClaimRefused("emergency pause is set")
        if job.status is not Status.READY:
            self.audit(actor, "job.claim.refused", job_id=job_id, reason=job.status.value)
            raise ClaimRefused(f"job is {job.status.value}, not READY")
        if job.risk in APPROVAL_REQUIRED:
            self._require_approval(job, approval_id, actor)

        cur = self._conn.execute(
            "UPDATE jobs SET status=?, provider=?, transport=?, attempts=attempts+1, "
            "updated_at=? WHERE job_id=? AND status=?",
            (
                Status.RUNNING.value,
                provider,
                transport.value if transport else None,
                _now(),
                job_id,
                Status.READY.value,
            ),
        )
        self._conn.commit()
        if cur.rowcount != 1:
            # Lost the race between the read above and this update.
            self.audit(actor, "job.claim.refused", job_id=job_id, reason="race")
            raise ClaimRefused("job was claimed concurrently")

        self.audit(actor, "job.claim", job_id=job_id, provider=provider)
        return self._require(job_id)

    def submit_result(
        self,
        job_id: str,
        result: Any,
        actor: str,
        *,
        provider: str | None = None,
    ) -> tuple[Job, bool]:
        """Record a result. Returns ``(job, is_new_outcome)``.

        Refusals:

          * **not RUNNING** -- a result may only be submitted against work that was
            actually claimed. Otherwise a provider could answer a job it never took.
          * **wrong provider** -- only the provider holding the claim may submit.
            This is what stops a second provider replaying a result into a job it
            does not own, and it is checked *before* the idempotency comparison so
            an unauthorised replay is refused rather than silently deduplicated.

        If the same job is retried and produces identical content, the hash matches
        and the submission is recorded as a duplicate rather than a second
        completion. This is what makes failover across providers safe: two
        providers producing the same answer is one answer.
        """
        # Canonicalise the caller's id before comparing it to the stored one, so
        # a case difference refuses nothing it should allow. This is a false
        # *refusal* rather than a hole, but a provider that cannot submit under
        # its own name is a provider that silently loses work.
        if provider is not None:
            provider = canonical_provider(provider)
        job = self._require(job_id)
        if job.status is not Status.RUNNING:
            self.audit(actor, "job.result.refused", job_id=job_id, reason=job.status.value)
            raise SubmitRefused(f"job is {job.status.value}, not RUNNING")
        if provider is not None and job.provider != provider:
            self.audit(actor, "job.result.refused", job_id=job_id, reason="not_claim_owner")
            raise SubmitRefused(
                f"job is claimed by {job.provider!r}; {provider!r} may not submit a result"
            )
        digest = result_hash(result)
        if job.result_hash == digest:
            self.audit(actor, "job.result.duplicate", job_id=job_id)
            return job, False
        job.result = result
        job.result_hash = digest
        job.status = Status.COMPLETE
        job.error = None
        return self._update(job, actor, "job.result", result_hash=digest), True

    def verify_result(
        self, job_id: str, verified_by: str, evidence: str
    ) -> Job:
        """Mark a COMPLETE result as VERIFIED. Separate from COMPLETE, on purpose.

        COMPLETE means a result was submitted. It does not mean the result is true,
        and a system that treats the two as the same will eventually act on an
        unverified claim as though it were company state. So verification is its own
        act, performed by someone other than the submitter, and it **requires
        evidence** -- a bare "looks fine" is refused, because an unevidenced
        verification is indistinguishable from no verification at all.
        """
        verified_by = canonical_provider(verified_by)
        job = self._require(job_id)
        if job.status is not Status.COMPLETE:
            raise ValueError(f"cannot verify a job that is {job.status.value}")
        evidence = (evidence or "").strip()
        if not evidence:
            raise ValueError("verification requires evidence")
        # The docstring promises a bare "looks fine" is refused. Until
        # 2026-10-03 the code only refused *empty* evidence, so any
        # filler string passed -- the seventh false control in this
        # project's ledger, caught by live-checking the claim instead
        # of trusting the docstring. Evidence must now name something
        # checkable: a URL, a path, or a reference. A phrase is not
        # evidence; it is a restatement of the claim.
        if not _evidence_is_checkable(evidence):
            raise ValueError(
                "verification evidence must be checkable (a URL, path, or "
                "identifier), not a bare assertion"
            )
        if verified_by == job.provider:
            raise ValueError("a result cannot be verified by the provider that submitted it")
        job.verified = True
        job.verified_by = verified_by
        job.verification_evidence = evidence.strip()
        return self._update(job, verified_by, "job.verified", evidence=evidence)

    def fail_job(self, job_id: str, error: str, actor: str, retryable: bool = True) -> Job:
        """Record a failure, choosing retryable vs terminal from evidence."""
        job = self._require(job_id)
        if retryable and job.attempts < job.max_attempts:
            job.status = Status.FAILED_RETRYABLE
        else:
            job.status = Status.FAILED_TERMINAL
        job.error = error
        return self._update(job, actor, "job.fail", error=error)

    def release_claim(self, job_id: str, actor: str, reason: str) -> Job:
        """Return a RUNNING job to READY, so another provider can take it.

        This is what makes a provider disconnect clean rather than destructive.
        Without it, disconnecting a provider strands every job it held in RUNNING
        forever -- the work is not lost, but nothing can reach it either, which is
        the same outcome from the owner's side.
        """
        job = self._require(job_id)
        if job.status is not Status.RUNNING:
            raise ValueError(f"job is {job.status.value}, not RUNNING")
        job.status = Status.READY
        job.provider = None
        job.transport = None
        return self._update(job, actor, "job.claim.released", reason=reason)

    def _require(self, job_id: str) -> Job:
        job = self.get_job(job_id)
        if job is None:
            raise KeyError(f"no such job: {job_id}")
        return job

    def ready_jobs(self) -> Iterator[Job]:
        """Jobs that can run now: READY, not paused, dependencies COMPLETE."""
        for job in self.jobs(Status.READY):
            deps_satisfied = True
            for dep_id in job.depends_on:
                dep = self.get_job(dep_id)
                if dep is None or dep.status is not Status.COMPLETE:
                    deps_satisfied = False
                    break
            if deps_satisfied:
                yield job

    # ---------------------------------------------------------- dead letters

    def terminal_failures(self) -> list[Job]:
        """Jobs that have exhausted their retries.

        A terminal failure that is merely a status is a job nobody will ever look
        at again. Exposing them as a set is what makes "dead letter" a behaviour
        rather than a label: they can be counted, shown to the owner, and
        deliberately revived.
        """
        return self.jobs(Status.FAILED_TERMINAL)

    def dead_letter_report(self) -> dict:
        """A summary suitable for the Command Center or a handoff."""
        dead = self.terminal_failures()
        return {
            "count": len(dead),
            "jobs": [
                {
                    "job_id": j.job_id,
                    "title": j.title,
                    "risk": j.risk.value,
                    "attempts": j.attempts,
                    "max_attempts": j.max_attempts,
                    "provider": j.provider,
                    "error": j.error,
                }
                for j in dead
            ],
        }

    def requeue(self, job_id: str, actor: str, reason: str) -> Job:
        """Deliberately revive a terminal failure. Requires a stated reason.

        Explicit and audited on purpose: silently retrying a job that has already
        failed terminally is how a queue turns a permanent fault into an infinite
        loop. Reviving is a decision someone makes and signs.
        """
        job = self._require(job_id)
        if job.status is not Status.FAILED_TERMINAL:
            raise ValueError(f"job is {job.status.value}, not FAILED_TERMINAL")
        if not (reason or "").strip():
            raise ValueError("requeue requires a reason")
        job.status = Status.READY
        job.attempts = 0
        job.provider = None
        job.transport = None
        job.error = None
        return self._update(job, actor, "job.requeued", reason=reason)
