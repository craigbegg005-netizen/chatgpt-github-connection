"""Independent verification, as a rule rather than a convention.

The single most important function here is `can_verify`, and it enforces one
thing: **the identity that produced a result may not be the identity that
verifies it.** Everything else in this module supports that.

This mirrors the rule already enforced in `connector.store.verify_result`, and
the duplication is intentional rather than accidental -- the connector enforces
it for provider submissions, this enforces it for synthetic workers, and the two
paths must not be able to disagree about whether self-certification is allowed.
The wording borrowed from a peer AI, which puts it better than I had: *builder
never verifies its own work.*

Verification also requires **evidence**. A verification with no evidence is
indistinguishable from no verification at all, and it is worse than nothing
because it produces a `VERIFIED` label that a later reader will trust.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable

from connector.schema import Risk
from .permissions import Decision, check_authority
from .registry import WorkforceRegistry
from .schema import Authority, Worker


class EvidenceKind(str, Enum):
    """Ranked best-to-worst. Higher wins; a claim backed only by another claim
    does not become true by repetition."""

    REPRODUCED = "reproduced"          # directly re-run and observed
    TOOL = "tool"                      # a connector or tool reported it
    REPOSITORY = "repository"          # present in version control
    DEPLOYMENT_LOG = "deployment_log"  # the deployment system's own output
    ARTIFACT = "artifact"              # screenshot, file, capture
    AI_REPORT = "ai_report"            # another synthetic identity said so
    UNSUPPORTED = "unsupported"        # narrative only


#: Weakest evidence that can support a VERIFIED verdict, by risk.
#:
#: Low risk may be verified from the repository; high risk requires
#: reproduction or a tool observation. This is stricter for higher risk on
#: purpose: the cost of a wrong "verified" scales with what was verified.
MINIMUM_EVIDENCE: dict[Risk, EvidenceKind] = {
    Risk.LOW: EvidenceKind.REPOSITORY,
    Risk.MEDIUM: EvidenceKind.TOOL,
    Risk.HIGH: EvidenceKind.REPRODUCED,
    Risk.CRITICAL: EvidenceKind.REPRODUCED,
}


@dataclass
class VerificationRequest:
    job_id: str
    producer_id: str
    risk: Risk = Risk.LOW
    evidence: list[tuple[EvidenceKind, str]] = field(default_factory=list)

    def add(self, kind: EvidenceKind, detail: str) -> "VerificationRequest":
        self.evidence.append((kind, detail))
        return self

    @property
    def best_evidence(self) -> EvidenceKind | None:
        if not self.evidence:
            return None
        order = list(EvidenceKind)
        return min((k for k, _ in self.evidence), key=order.index)


@dataclass(frozen=True)
class VerificationOutcome:
    verified: bool
    reason: str
    verifier_id: str | None = None
    evidence_kind: EvidenceKind | None = None
    requires_owner_approval: bool = False

    def __bool__(self) -> bool:
        return self.verified


def can_verify(
    registry: WorkforceRegistry, producer_id: str, verifier_id: str
) -> Decision:
    """Whether `verifier_id` is permitted to verify `producer_id`'s work."""
    if producer_id == verifier_id:
        return Decision.no(
            "a producer may not verify its own work; verification must be independent"
        )
    verifier = registry.worker(verifier_id)
    if verifier is None:
        return Decision.no(f"unknown verifier {verifier_id!r}")
    if "verify_claims" not in verifier.capabilities:
        return Decision.no(
            f"{verifier_id} does not declare the verify_claims capability"
        )
    a = check_authority(verifier, Authority.A1_DRAFT)
    if not a.allowed:
        return Decision.no(f"{verifier_id} may not verify: {a.reason}")
    return Decision.yes()


def verify(
    registry: WorkforceRegistry,
    request: VerificationRequest,
    verifier_id: str,
) -> VerificationOutcome:
    """Evaluate a verification request. Refuses rather than guessing."""
    permission = can_verify(registry, request.producer_id, verifier_id)
    if not permission.allowed:
        return VerificationOutcome(False, permission.reason, verifier_id)

    best = request.best_evidence
    if best is None:
        return VerificationOutcome(
            False,
            "no evidence supplied; an unevidenced verification is not a verification",
            verifier_id,
        )

    minimum = MINIMUM_EVIDENCE.get(request.risk)
    if minimum is None:
        return VerificationOutcome(
            False, f"unrecognised risk {request.risk!r}; refusing to verify",
            verifier_id, best,
        )

    order = list(EvidenceKind)
    if order.index(best) > order.index(minimum):
        return VerificationOutcome(
            False,
            f"evidence {best.value!r} is weaker than the {minimum.value!r} "
            f"minimum for {request.risk.value}-risk work",
            verifier_id, best,
        )

    return VerificationOutcome(
        True, f"verified from {best.value} evidence", verifier_id, best
    )


def assign_verifier(
    registry: WorkforceRegistry,
    producer_id: str,
    *,
    risk: Risk = Risk.LOW,
    exclude: Iterable[str] = (),
) -> tuple[str | None, str]:
    """Choose a verifier that is not the producer. Returns `(verifier_id, reason)`.

    Returns `None` with a reason when no independent verifier exists. That is a
    real and important outcome: the correct response is to leave the job
    unverified, not to fall back to the producer.
    """
    blocked = set(exclude)
    for w in registry.verifiers():
        if w.worker_id == producer_id or w.worker_id in blocked:
            continue
        if not can_verify(registry, producer_id, w.worker_id).allowed:
            continue
        return w.worker_id, "independent verifier available"
    return (
        None,
        "no independent verifier is available for this result; it must remain "
        "unverified rather than being self-certified",
    )
