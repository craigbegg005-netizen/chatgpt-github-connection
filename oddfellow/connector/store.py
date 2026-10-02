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
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from .schema import APPROVAL_REQUIRED, Job, Risk, Status, canonical_json, result_hash


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
        """
        existing = self.get_job(job.job_id)
        if existing:
            self.audit(actor, "job.duplicate", job_id=job.job_id)
            return existing, False

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

    def claim_job(
        self,
        job_id: str,
        provider: str,
        transport: Any,
        actor: str,
        *,
        paused: bool = False,
        approved: bool = False,
    ) -> Job:
        """Claim a READY job for a provider, or refuse with a reason.

        Refusals, each preventing a specific failure:

          * **paused** -- the emergency stop blocks claims, not merely new work.
          * **not READY** -- a RUNNING job must not be claimed twice, and a
            COMPLETE one must not be quietly reopened by a second claim.
          * **unapproved high/critical** -- approval is checked before the claim,
            so gated work cannot be picked up and run first.

        The state change is a *conditional* UPDATE, so two providers racing produce
        one winner and one refusal rather than two RUNNING rows.
        """
        job = self._require(job_id)
        if paused:
            self.audit(actor, "job.claim.refused", job_id=job_id, reason="paused")
            raise ClaimRefused("emergency pause is set")
        if job.status is not Status.READY:
            self.audit(actor, "job.claim.refused", job_id=job_id, reason=job.status.value)
            raise ClaimRefused(f"job is {job.status.value}, not READY")
        if job.risk in APPROVAL_REQUIRED and not approved:
            self.audit(actor, "job.claim.refused", job_id=job_id, reason="unapproved")
            raise ClaimRefused(
                f"{job.risk.value}-risk work cannot be claimed before it is approved"
            )

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
        job = self._require(job_id)
        if job.status is not Status.COMPLETE:
            raise ValueError(f"cannot verify a job that is {job.status.value}")
        if not (evidence or "").strip():
            raise ValueError("verification requires evidence")
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
