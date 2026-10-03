"""Whether a job may be given to a worker.

Delegation is the point where an organisational chart becomes an authority
boundary, so every refusal here names the specific constraint that stopped it.

The checks run in a fixed order, cheapest and most fundamental first, and the
**emergency pause is checked first of all**. If the organisation is paused,
nothing else about the job matters -- a pause that only stops some kinds of work
is not a pause.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from connector.schema import Risk, Status
from .permissions import Decision, check_authority, check_risk
from .registry import WorkforceRegistry
from .schema import Authority, Worker

#: Job states a worker may be given. A job that is already RUNNING or COMPLETE
#: is not available to delegate, and re-delegating it is how two workers end up
#: producing the same artifact.
DELEGATABLE = frozenset({Status.READY})


@dataclass(frozen=True)
class Delegation:
    allowed: bool
    worker_id: str
    reason: str = ""
    requires_owner_approval: bool = False

    def __bool__(self) -> bool:
        return self.allowed


def can_delegate(
    registry: WorkforceRegistry,
    worker_id: str,
    *,
    job_risk: Risk = Risk.LOW,
    job_status: Status = Status.READY,
    required_capability: str | None = None,
    paused: bool = False,
    approved: bool = False,
    required_authority: Authority | None = None,
) -> Delegation:
    """Decide whether `worker_id` may take this job."""
    if paused:
        return Delegation(
            False, worker_id, "the emergency pause is set; no delegation while paused"
        )

    worker = registry.worker(worker_id)
    if worker is None:
        return Delegation(False, worker_id, f"unknown worker {worker_id!r}")

    if job_status not in DELEGATABLE:
        return Delegation(
            False, worker_id, f"job is {job_status.value}, not READY"
        )

    if required_capability is not None and required_capability not in worker.capabilities:
        return Delegation(
            False, worker_id,
            f"worker does not declare capability {required_capability!r}",
        )

    # Approval is checked before risk so that an unapproved high-risk job is
    # refused for the reason that actually matters.
    if job_risk in (Risk.HIGH, Risk.CRITICAL) and not approved:
        return Delegation(
            False, worker_id,
            f"{job_risk.value}-risk work requires owner approval before delegation",
            requires_owner_approval=True,
        )

    d = check_risk(worker, job_risk)
    if not d.allowed:
        return Delegation(False, worker_id, d.reason)

    if required_authority is not None:
        a = check_authority(worker, required_authority)
        if not a.allowed:
            return Delegation(False, worker_id, a.reason, a.requires_owner_approval)

    return Delegation(True, worker_id, "delegable")


def eligible_workers(
    registry: WorkforceRegistry,
    *,
    department_id: str | None = None,
    capability: str | None = None,
    job_risk: Risk = Risk.LOW,
    paused: bool = False,
) -> tuple[Worker, ...]:
    """Every worker that could take this job, for routing and diagnostics.

    Returns an empty tuple when nothing is eligible, including when the
    organisation is paused. An empty result is a real answer -- callers must not
    read it as "no constraint" and pick a worker anyway.
    """
    pool = (
        registry.workers_in(department_id) if department_id else registry.workers()
    )
    out = []
    for w in pool:
        d = can_delegate(
            registry, w.worker_id, job_risk=job_risk,
            required_capability=capability, paused=paused,
        )
        if d.allowed:
            out.append(w)
    return tuple(out)


def delegation_plan(
    registry: WorkforceRegistry,
    job: Any,
    *,
    capability: str | None = None,
    paused: bool = False,
) -> dict[str, Any]:
    """A read-only explanation of who could take a job, and why not.

    Exists so a blocked job can be explained to the owner in one step instead of
    a manual walk through the roster.
    """
    risk = getattr(job, "risk", Risk.LOW)
    status = getattr(job, "status", Status.READY)
    eligible = eligible_workers(
        registry, capability=capability, job_risk=risk, paused=paused
    )
    refusals = []
    if not eligible:
        for w in registry.workers():
            d = can_delegate(
                registry, w.worker_id, job_risk=risk, job_status=status,
                required_capability=capability, paused=paused,
            )
            if not d.allowed:
                refusals.append({"worker_id": w.worker_id, "reason": d.reason})
    return {
        "job_id": getattr(job, "job_id", None),
        "risk": risk.value,
        "status": status.value,
        "paused": paused,
        "eligible": [w.worker_id for w in eligible],
        "refusals": refusals[:12],
    }
