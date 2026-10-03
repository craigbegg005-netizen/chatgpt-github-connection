"""The Begg Synthetic Intelligence System -- Phase 1.

Persistent organisational identity, not persistent compute. A department or
worker exists as durable state; model compute is invoked only when there is work.
That is what keeps a roster of this size affordable at zero spend.

This package is deliberately a *library*, not a service. Phase 1 establishes the
definitions, the authority boundaries and the verification rule; nothing here
claims a job, spends money, or touches the network. Wiring it to the queue is
Phase 2, and it is separated so the boundaries can be tested before anything
depends on them.

Terminology note: "synthetic department head" is an engineering term for a
durable identity plus a permission set. Nothing in this system is conscious,
sentient or self-aware, and the design depends on that being true rather than
being a disclaimer -- a component that claimed judgement would be trusted where
it should be checked.
"""

from .delegation import (
    DELEGATABLE,
    Delegation,
    can_delegate,
    delegation_plan,
    eligible_workers,
)
from .departments import DEPARTMENTS, department_ids
from .permissions import (
    Decision,
    check_all,
    check_authority,
    check_provider,
    check_risk,
    check_spend,
    check_tool,
)
from .registry import WorkforceRegistry, load
from .schema import (
    Authority,
    Capability,
    DepartmentHead,
    OWNER_APPROVAL_REQUIRED,
    Role,
    Worker,
    allows,
    authority_rank,
    risk_at_most,
    valid_id,
)
from .verification import (
    EvidenceKind,
    MINIMUM_EVIDENCE,
    VerificationOutcome,
    VerificationRequest,
    assign_verifier,
    can_verify,
    verify,
)
from .workers import default_workers

__all__ = [
    "DELEGATABLE",
    "DEPARTMENTS",
    "Delegation",
    "Decision",
    "EvidenceKind",
    "MINIMUM_EVIDENCE",
    "OWNER_APPROVAL_REQUIRED",
    "Authority",
    "Capability",
    "DepartmentHead",
    "Role",
    "VerificationOutcome",
    "VerificationRequest",
    "Worker",
    "WorkforceRegistry",
    "allows",
    "assign_verifier",
    "authority_rank",
    "can_delegate",
    "can_verify",
    "check_all",
    "check_authority",
    "check_provider",
    "check_risk",
    "check_spend",
    "check_tool",
    "default_workers",
    "delegation_plan",
    "department_ids",
    "eligible_workers",
    "load",
    "risk_at_most",
    "valid_id",
    "verify",
]
