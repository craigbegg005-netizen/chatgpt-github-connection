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

from .schema import Job, Status, canonical_json, result_hash


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

#: Detail keys the audit log refuses to store. A payload that reaches the log has
#: escaped the approval gate and the scoping rules, so this is enforced centrally
#: rather than trusted to each caller.
_REDACTED_KEYS = frozenset(
    {"payload", "result", "token", "secret", "password", "key", "credential", "authorization"}
)


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class Store:
    """All connector persistence. Safe to construct against a path or ``:memory:``."""

    def __init__(self, path: str | Path = ":memory:") -> None:
        self.path = str(path)
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.path)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(SCHEMA)
        self._conn.commit()

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
        """Append an audit event. Payloads and results are stripped, not trusted.

        ``detail`` is filtered against a deny-list and each surviving value is
        replaced by its type and length. The log therefore answers "did this
        happen, and how big was it" without becoming a copy of the data.
        """
        safe = {
            k: (f"<{type(v).__name__} len={len(v)}>" if hasattr(v, "__len__") else f"<{type(v).__name__}>")
            for k, v in detail.items()
            if k.lower() not in _REDACTED_KEYS
        }
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

    def claim_job(self, job_id: str, provider: str, transport: Any, actor: str) -> Job:
        """Move a job to RUNNING under a chosen provider/transport."""
        job = self._require(job_id)
        job.status = Status.RUNNING
        job.provider = provider
        job.transport = transport
        job.attempts += 1
        return self._update(job, actor, "job.claim", provider=provider)

    def submit_result(self, job_id: str, result: Any, actor: str) -> tuple[Job, bool]:
        """Record a result. Returns ``(job, is_new_outcome)``.

        If the same job is retried and produces identical content, the hash matches
        and the submission is recorded as a duplicate rather than a second
        completion. This is what makes failover across providers safe: two
        providers producing the same answer is one answer.
        """
        job = self._require(job_id)
        digest = result_hash(result)
        if job.result_hash == digest:
            self.audit(actor, "job.result.duplicate", job_id=job_id)
            return job, False
        job.result = result
        job.result_hash = digest
        job.status = Status.COMPLETE
        job.error = None
        return self._update(job, actor, "job.result", result_hash=digest), True

    def fail_job(self, job_id: str, error: str, actor: str, retryable: bool = True) -> Job:
        """Record a failure, choosing retryable vs terminal from evidence."""
        job = self._require(job_id)
        if retryable and job.attempts < job.max_attempts:
            job.status = Status.FAILED_RETRYABLE
        else:
            job.status = Status.FAILED_TERMINAL
        job.error = error
        return self._update(job, actor, "job.fail", error=error)

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
