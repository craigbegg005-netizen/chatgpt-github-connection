"""Default worker roster, derived from the department definitions.

Workers inherit the department's tool and provider permissions and are given
authority **at or below** their head's. That direction is enforced, not assumed:
a worker with more authority than its head would be an escalation path that
bypasses the head entirely.

Authority is deliberately lower for workers than heads in most cases. A head is
accountable for a decision; a worker produces an artifact. Giving both the same
permissions means the distinction exists only in a name.

The verifier workers in `qa` are the reason `verification.py` can enforce
producer/verifier separation at all: there has to be an identity that is *not*
the producer before "someone else checked it" can mean anything.
"""

from __future__ import annotations

from connector.schema import Risk
from .departments import (
    CAP_BRAND_REVIEW,
    CAP_CODE,
    CAP_CONTENT,
    CAP_COORDINATE,
    CAP_COST_TRACK,
    CAP_DRAFT,
    CAP_DRAFT_POLICY,
    CAP_IP_RESEARCH,
    CAP_MARKET_RESEARCH,
    CAP_MONITOR,
    CAP_REGISTRY,
    CAP_RESEARCH,
    CAP_REVIEW_SECURITY,
    CAP_SCAN_SECRETS,
    CAP_SUPPORT_DRAFT,
    CAP_TEST,
    CAP_VERIFY,
    CAP_ZERO_SPEND,
    DEPARTMENTS,
)
from .schema import Authority, Role, Worker


def _w(
    worker_id: str,
    name: str,
    department_id: str,
    role: Role,
    mission: str,
    capabilities: tuple[str, ...],
    authority: Authority,
    risk_ceiling: Risk = Risk.LOW,
) -> Worker:
    return Worker(
        worker_id=worker_id,
        name=name,
        department_id=department_id,
        role=role,
        mission=mission,
        capabilities=capabilities,
        authority=authority,
        risk_ceiling=risk_ceiling,
    )


#: The roster. Keys are worker IDs; IDs are stable and never reused for a
#: different role, because a reused ID silently inherits the old history.
_ROSTER: tuple[Worker, ...] = (
    # -- executive -----------------------------------------------------------
    _w("exec_program_coordinator", "Program Coordinator", "executive", Role.WORKER,
       "Turn owner objectives into concrete, traceable programs of work.",
       (CAP_COORDINATE, CAP_RESEARCH), Authority.A1_DRAFT),
    _w("exec_dependency_analyst", "Dependency Analyst", "executive", Role.WORKER,
       "Find which blocked work is blocking other work, and say so early.",
       (CAP_MONITOR, CAP_RESEARCH), Authority.A0_OBSERVE),

    # -- product -------------------------------------------------------------
    _w("product_demand_research", "Demand Research Worker", "product", Role.WORKER,
       "Look for evidence that a problem is real and that someone would pay to solve it.",
       (CAP_MARKET_RESEARCH, CAP_RESEARCH), Authority.A0_OBSERVE),
    _w("product_requirements", "Requirements Worker", "product", Role.WORKER,
       "Turn an agreed problem into requirements precise enough to build against.",
       (CAP_DRAFT,), Authority.A1_DRAFT),

    # -- engineering ---------------------------------------------------------
    _w("eng_backend", "Backend Developer", "engineering", Role.WORKER,
       "Implement and maintain server-side code.",
       (CAP_CODE, CAP_TEST), Authority.A2_INTERNAL, Risk.MEDIUM),
    _w("eng_frontend", "Frontend Developer", "engineering", Role.WORKER,
       "Implement and maintain the user-facing layer.",
       (CAP_CODE, CAP_TEST), Authority.A2_INTERNAL, Risk.MEDIUM),
    _w("eng_integration", "Integration Developer", "engineering", Role.WORKER,
       "Connect components and keep the seams honest.",
       (CAP_CODE, CAP_TEST), Authority.A2_INTERNAL, Risk.MEDIUM),

    # -- qa / verification ---------------------------------------------------
    # These identities exist so that producer/verifier separation is enforceable
    # rather than aspirational.
    _w("qa_claim_verifier", "Claim Verification Worker", "qa", Role.VERIFIER,
       "Check whether a claim is supported by evidence, and say no when it is not.",
       (CAP_VERIFY, CAP_TEST), Authority.A2_INTERNAL, Risk.MEDIUM),
    _w("qa_evidence_reviewer", "Evidence Reviewer", "qa", Role.VERIFIER,
       "Judge the quality and provenance of the evidence itself, not just its presence.",
       (CAP_VERIFY,), Authority.A2_INTERNAL, Risk.MEDIUM),
    _w("qa_adversarial", "Adversarial QA Worker", "qa", Role.VERIFIER,
       "Try to break what has been declared finished.",
       (CAP_TEST, CAP_VERIFY), Authority.A2_INTERNAL, Risk.MEDIUM),
    _w("qa_regression", "Regression Worker", "qa", Role.WORKER,
       "Confirm that a change did not break something that previously worked.",
       (CAP_TEST,), Authority.A1_DRAFT),

    # -- security ------------------------------------------------------------
    _w("sec_secret_scanner", "Secret Scanner", "security", Role.WORKER,
       "Find credentials where they should not be, without printing them.",
       (CAP_SCAN_SECRETS,), Authority.A0_OBSERVE),
    _w("sec_auth_reviewer", "Auth Reviewer", "security", Role.WORKER,
       "Review authentication and authorisation paths for fail-open behaviour.",
       (CAP_REVIEW_SECURITY,), Authority.A1_DRAFT),

    # -- legal / ip ----------------------------------------------------------
    _w("legal_ip_inventory", "IP Inventory Worker", "legal_ip", Role.WORKER,
       "Maintain the inventory of what exists and who made it.",
       (CAP_IP_RESEARCH,), Authority.A0_OBSERVE),
    _w("legal_policy_drafter", "Policy Drafting Assistant", "legal_ip", Role.WORKER,
       "Draft policy and terms for professional review; never represent them as reviewed.",
       (CAP_DRAFT_POLICY,), Authority.A1_DRAFT),

    # -- finance -------------------------------------------------------------
    _w("fin_cost_analyst", "Cost Analyst", "finance", Role.WORKER,
       "Track what is actually being spent, and flag anything that is not zero.",
       (CAP_COST_TRACK,), Authority.A1_DRAFT),
    _w("fin_zero_spend", "Zero-Spend Enforcer", "finance", Role.WORKER,
       "Refuse unapproved spend. Has no authority to approve it.",
       (CAP_ZERO_SPEND,), Authority.A2_INTERNAL),

    # -- marketing -----------------------------------------------------------
    _w("mkt_market_research", "Market Research Worker", "marketing", Role.WORKER,
       "Research demand, competitors and channels from current sources.",
       (CAP_MARKET_RESEARCH, CAP_RESEARCH), Authority.A0_OBSERVE),
    _w("mkt_content", "Content Marketing Worker", "marketing", Role.WORKER,
       "Draft organic content that a human can review before it goes anywhere.",
       (CAP_CONTENT, CAP_DRAFT), Authority.A1_DRAFT),

    # -- brand / media -------------------------------------------------------
    _w("brand_copy", "Copy Worker", "brand_media", Role.WORKER,
       "Write copy that fits the brand it belongs to and no other.",
       (CAP_CONTENT, CAP_DRAFT), Authority.A1_DRAFT),
    _w("brand_consistency", "Brand Consistency Worker", "brand_media", Role.WORKER,
       "Check that public material keeps separate brands separate.",
       (CAP_BRAND_REVIEW,), Authority.A0_OBSERVE),

    # -- support -------------------------------------------------------------
    _w("support_triage", "Support Triage Worker", "support", Role.WORKER,
       "Classify incoming problems so recurring ones become product work.",
       (CAP_SUPPORT_DRAFT, CAP_RESEARCH), Authority.A1_DRAFT),
    _w("support_faq", "FAQ Worker", "support", Role.WORKER,
       "Answer the questions that keep being asked, once, in writing.",
       (CAP_SUPPORT_DRAFT, CAP_DRAFT), Authority.A1_DRAFT),

    # -- research ------------------------------------------------------------
    _w("research_general", "General Research Worker", "research", Role.WORKER,
       "Find current evidence and attach its source.",
       (CAP_RESEARCH,), Authority.A0_OBSERVE),
    _w("research_grants", "Grants Research Worker", "research", Role.WORKER,
       "Check funding opportunities against primary sources before anyone relies on them.",
       (CAP_RESEARCH, CAP_DRAFT), Authority.A1_DRAFT),

    # -- operations ----------------------------------------------------------
    _w("ops_scheduler", "Scheduler Worker", "operations", Role.WORKER,
       "Maintain recurring work and keep it from duplicating itself.",
       (CAP_REGISTRY, CAP_MONITOR), Authority.A2_INTERNAL, Risk.MEDIUM),
    _w("ops_registry", "Resource Registry Worker", "operations", Role.WORKER,
       "Keep the mapping from human names to real resources current and honest.",
       (CAP_REGISTRY,), Authority.A2_INTERNAL, Risk.MEDIUM),
    _w("ops_monitor", "Monitoring Worker", "operations", Role.WORKER,
       "Watch for things that have stopped working, including quietly.",
       (CAP_MONITOR,), Authority.A0_OBSERVE),
)


def default_workers() -> tuple[Worker, ...]:
    """The roster with department permissions inherited.

    Inheritance happens here rather than in each definition so a department's
    permissions can change in one place. A worker may never hold *more*
    authority than its head -- that is checked, and a violation raises rather
    than being quietly clamped.
    """
    by_id = {d.department_id: d for d in DEPARTMENTS}
    out: list[Worker] = []
    for w in _ROSTER:
        head = by_id.get(w.department_id)
        if head is None:
            raise ValueError(f"{w.worker_id}: unknown department {w.department_id!r}")
        if not _authority_within(w.authority, head.authority):
            raise ValueError(
                f"{w.worker_id} holds {w.authority.value} but its head "
                f"{head.department_id} holds only {head.authority.value}"
            )
        w.permitted_tools = head.permitted_tools
        w.permitted_providers = head.permitted_providers
        w.risk_ceiling = min(w.risk_ceiling, head.risk_ceiling, key=_risk_rank)
        out.append(w)
    return tuple(out)


def _risk_rank(risk: Risk) -> int:
    return (Risk.LOW, Risk.MEDIUM, Risk.HIGH, Risk.CRITICAL).index(risk)


def _authority_within(worker: Authority, head: Authority) -> bool:
    order = (Authority.A0_OBSERVE, Authority.A1_DRAFT, Authority.A2_INTERNAL,
             Authority.A3_EXTERNAL, Authority.A4_CONSEQUENTIAL)
    return order.index(worker) <= order.index(head)
