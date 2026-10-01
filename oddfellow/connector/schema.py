"""Provider-independent job schema, status vocabulary, and risk levels.

Everything in the Universal Connector speaks these types. A job is created once,
carries its own idempotency key, and moves through the status vocabulary below.
No provider's private format is allowed to leak into the shared state -- that is
the whole point of the connector: Oddfellow owns the canonical project state, and
the providers are interchangeable workers reading and writing it.

Stdlib only, deliberately. This module has to be importable in the deploy image
and in a bare test runner with nothing installed.

Design rules carried over from the operating doctrine:

  * A status is only ever set from evidence. ``COMPLETE`` is not reachable
    without a result, and ``VERIFIED`` is not a status this schema can invent.
  * Idempotency is keyed on (job_id, result_hash), so a retried job that produces
    the same bytes is recognised as the same outcome rather than a second one.
  * Risk is declared at creation, not inferred at execution, because the approval
    gate has to decide *before* anything runs.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any


class Status(str, Enum):
    """The only statuses a job may hold.

    Deliberately mirrors the operating protocol's task states. ``COMPLETE`` means
    the result was submitted; it does NOT mean the result was verified -- that is a
    separate judgement made by whoever consumes it, and conflating the two is how
    "implemented" silently becomes "working".
    """

    READY = "READY"
    RUNNING = "RUNNING"
    WAITING_DEPENDENCY = "WAITING_DEPENDENCY"
    WAITING_AUTHORIZATION = "WAITING_AUTHORIZATION"
    BLOCKED = "BLOCKED"
    FAILED_RETRYABLE = "FAILED_RETRYABLE"
    FAILED_TERMINAL = "FAILED_TERMINAL"
    COMPLETE = "COMPLETE"


class Risk(str, Enum):
    """Risk is declared by the caller and gates execution, not the other way round."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


#: Risk levels that may never execute without an explicit owner approval.
APPROVAL_REQUIRED = frozenset({Risk.HIGH, Risk.CRITICAL})


class TaskKind(str, Enum):
    """Task categories, used for capability matching rather than for display."""

    DRAFTING = "drafting"
    CODE = "code"
    RESEARCH = "research"
    ANALYSIS = "analysis"
    DESIGN = "design"
    STRATEGY = "strategy"
    SECURITY = "security"
    EXTERNAL_ACTION = "external_action"


class Transport(str, Enum):
    """The fallback ladder, best first.

    A provider is reached by the highest rung it actually supports. Rungs are
    never skipped silently: choosing a lower rung is recorded, because "we fell
    back to a queued handoff" is a materially different fact from "we called the
    provider's API", and a reader has to be able to tell them apart.
    """

    MCP = "mcp"                      # native / remote MCP
    API = "api"                      # official API or tool calling
    HANDOFF = "handoff"              # approved import/export or structured handoff
    QUEUE = "queue"                  # durable queued handoff, no direct execution


#: Ladder order, best first. Used by the router.
TRANSPORT_LADDER = (Transport.MCP, Transport.API, Transport.HANDOFF, Transport.QUEUE)


def canonical_json(value: Any) -> str:
    """Deterministic JSON, so a result hash depends on content and not on key order."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def result_hash(result: Any) -> str:
    """Stable content hash of a job result.

    Keyed on content alone. Two providers returning the same bytes produce the
    same hash, which is what makes (job_id, result_hash) a usable idempotency key
    when a job is retried across providers.
    """
    return hashlib.sha256(canonical_json(result).encode("utf-8")).hexdigest()


@dataclass
class Job:
    """A provider-independent unit of work.

    ``payload`` is the input; ``result`` is filled in on submission. Both are
    treated as sensitive by the audit log, which records *that* they changed and
    how large they are, never what they contain.
    """

    job_id: str
    kind: TaskKind
    title: str
    payload: dict = field(default_factory=dict)
    risk: Risk = Risk.LOW
    status: Status = Status.READY
    provider: str | None = None
    transport: Transport | None = None
    depends_on: tuple[str, ...] = ()
    attempts: int = 0
    max_attempts: int = 3
    result: Any = None
    result_hash: str | None = None
    error: str | None = None
    created_at: str | None = None
    updated_at: str | None = None

    def to_row(self) -> dict:
        """Flat, JSON-safe representation for storage."""
        data = asdict(self)
        data["kind"] = self.kind.value
        data["risk"] = self.risk.value
        data["status"] = self.status.value
        data["transport"] = self.transport.value if self.transport else None
        # Stored as a JSON string: sqlite binds only scalars, and a bare list
        # raises "type 'list' is not supported" at execute time.
        data["depends_on"] = canonical_json(list(self.depends_on))
        data["payload"] = canonical_json(self.payload)
        data["result"] = canonical_json(self.result) if self.result is not None else None
        return data

    @classmethod
    def from_row(cls, row: dict) -> "Job":
        return cls(
            job_id=row["job_id"],
            kind=TaskKind(row["kind"]),
            title=row["title"],
            payload=json.loads(row["payload"] or "{}"),
            risk=Risk(row["risk"]),
            status=Status(row["status"]),
            provider=row["provider"],
            transport=Transport(row["transport"]) if row["transport"] else None,
            depends_on=tuple(json.loads(row["depends_on"] or "[]")),
            attempts=row["attempts"],
            max_attempts=row["max_attempts"],
            result=json.loads(row["result"]) if row["result"] is not None else None,
            result_hash=row["result_hash"],
            error=row["error"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )


def new_job_id(kind: TaskKind, title: str, payload: dict) -> str:
    """Deterministic job id.

    Derived from the job's identity rather than random, so creating the same job
    twice from two different AIs yields *the same id* and the queue collapses the
    duplicate instead of running the work twice. That is the mechanism behind the
    "do not redo completed work unnecessarily" rule.
    """
    seed = canonical_json({"kind": kind.value, "title": title, "payload": payload})
    return "job-" + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:32]
