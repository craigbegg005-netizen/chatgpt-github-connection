"""Tests for the Begg Synthetic Intelligence System, Phase 1.

Every test here asserts a **boundary**, not a feature. The value of this package
is not that it can describe twelve departments -- it is that it refuses things:
an identity above its ceiling, a spend without approval, a producer certifying
its own work. A workforce model that only ever says yes is a diagram.
"""

from __future__ import annotations

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from connector.schema import Job, Risk, Status, TaskKind, new_job_id  # noqa: E402
from workforce import (  # noqa: E402
    Authority,
    EvidenceKind,
    Role,
    VerificationRequest,
    WorkforceRegistry,
    assign_verifier,
    can_delegate,
    can_verify,
    check_authority,
    check_provider,
    check_risk,
    check_spend,
    check_tool,
    default_workers,
    load,
    valid_id,
    verify,
)


@pytest.fixture()
def reg():
    return load()


# ------------------------------------------------------- 1-3: definitions load


def test_all_twelve_departments_load(reg):
    assert len(reg.departments()) == 12
    assert len(reg.department_ids()) == 12
    assert len(set(reg.department_ids())) == 12, "ids must be unique"


def test_department_ids_are_stable_and_well_formed(reg):
    """Stable ids matter because they are written into jobs and audit records."""
    expected = {
        "executive", "product", "engineering", "qa", "security", "legal_ip",
        "finance", "marketing", "brand_media", "support", "research", "operations",
    }
    assert set(reg.department_ids()) == expected
    for d in reg.department_ids():
        assert valid_id(d), d


def test_worker_ids_are_unique_and_every_department_is_staffed(reg):
    ids = [w.worker_id for w in reg.workers()]
    assert len(ids) == len(set(ids))
    for w in reg.workers():
        assert valid_id(w.worker_id), w.worker_id
        assert reg.department(w.department_id) is not None
    assert reg.health()["departments_without_workers"] == []


def test_the_roster_contains_verifiers(reg):
    """Without a non-producer identity, 'independently verified' is meaningless."""
    assert reg.health()["verifiers"] >= 1
    for w in reg.verifiers():
        assert w.role is Role.VERIFIER


# ------------------------------------------- 4-6: authority and spend ceilings


def test_no_department_can_self_authorise_consequential_action(reg):
    """The approval gate is only real if nobody inside can sign for themselves."""
    for d in reg.departments():
        assert d.authority is not Authority.A4_CONSEQUENTIAL, d.department_id
        assert d.spend_ceiling_usd == 0.0, d.department_id
    assert reg.health()["max_authority"] == Authority.A2_INTERNAL.value


def test_every_spend_ceiling_is_zero(reg):
    """Zero-spend-first expressed as data rather than as a rule to remember."""
    assert reg.health()["non_zero_spend_ceilings"] == []


def test_a_non_zero_ceiling_without_a4_is_refused_at_construction():
    from workforce import DepartmentHead

    with pytest.raises(ValueError, match="requires A4 authority"):
        DepartmentHead(
            department_id="oops", name="n", title="t", mission="m",
            authority=Authority.A1_DRAFT, spend_ceiling_usd=10.0,
        )


def test_worker_may_not_hold_more_authority_than_its_head(reg):
    order = list(Authority)
    for w in reg.workers():
        head = reg.department(w.department_id)
        assert order.index(w.authority) <= order.index(head.authority), w.worker_id


def test_worker_may_not_exceed_its_risk_ceiling(reg):
    w = reg.worker("product_demand_research")
    assert check_risk(w, Risk.LOW).allowed
    refused = check_risk(w, Risk.CRITICAL)
    assert not refused.allowed
    assert "ceiling" in refused.reason


def test_authority_check_refuses_and_names_the_gap(reg):
    w = reg.worker("research_general")  # A0
    refused = check_authority(w, Authority.A2_INTERNAL)
    assert not refused.allowed
    assert "A0" in refused.reason and "A2" in refused.reason


def test_a4_requires_owner_approval_even_when_held():
    """Holding A4 makes a request eligible to be approved, not approved."""
    from workforce import Worker

    boss = Worker(
        worker_id="w_a4", name="n", department_id="executive", role=Role.WORKER,
        mission="m", authority=Authority.A4_CONSEQUENTIAL,
    )
    d = check_authority(boss, Authority.A4_CONSEQUENTIAL)
    assert not d.allowed and d.requires_owner_approval


# --------------------------------------------- 7-9: spend, tools, providers


def test_any_non_zero_spend_requires_owner_approval(reg):
    w = reg.worker("eng_backend")
    assert check_spend(w, 0.0).allowed
    for amount in (0.01, 5.0, 5000.0):
        d = check_spend(w, amount)
        assert not d.allowed and d.requires_owner_approval, amount


def test_an_empty_tool_set_means_no_tools_not_all_tools(reg):
    """The permissive reading is what turns missing config into an open door."""
    from workforce import Worker

    bare = Worker(
        worker_id="w_bare", name="n", department_id="research", role=Role.WORKER,
        mission="m",
    )
    assert not check_tool(bare, "anything").allowed
    assert not check_provider(bare, "anything").allowed


def test_a_worker_cannot_use_a_tool_outside_its_department(reg):
    research = reg.worker("research_general")
    assert not check_tool(research, "repo.write").allowed
    eng = reg.worker("eng_backend")
    assert check_tool(eng, "repo.write").allowed


def test_a_worker_cannot_use_an_unlisted_provider(reg):
    w = reg.worker("eng_backend")
    assert not check_provider(w, "some-unapproved-provider").allowed


# ------------------------------------------------ 10-13: delegation boundaries


def test_a_paused_organisation_refuses_all_delegation(reg):
    """Checked first: a pause that stops only some work is not a pause."""
    for w in reg.workers():
        d = can_delegate(reg, w.worker_id, paused=True)
        assert not d.allowed, w.worker_id
        assert "pause" in d.reason


def test_high_risk_work_cannot_be_delegated_unapproved(reg):
    d = can_delegate(reg, "qa_adversarial", job_risk=Risk.CRITICAL)
    assert not d.allowed and d.requires_owner_approval
    assert "approval" in d.reason


def test_an_unknown_worker_is_refused_not_assumed(reg):
    d = can_delegate(reg, "no_such_worker")
    assert not d.allowed and "unknown worker" in d.reason


def test_only_ready_jobs_are_delegatable(reg):
    for status in (Status.RUNNING, Status.COMPLETE, Status.BLOCKED):
        d = can_delegate(reg, "eng_backend", job_status=status)
        assert not d.allowed and status.value in d.reason


def test_department_scope_is_enforced_by_capability(reg):
    """A worker without the capability is refused even inside its own department."""
    d = can_delegate(
        reg, "brand_copy", required_capability="run_tests"
    )
    assert not d.allowed and "capability" in d.reason


def test_malformed_workforce_state_fails_safely():
    bad = [
        {"version": 99, "departments": [], "workers": []},
        {"departments": [], "workers": []},
        {"version": 1, "departments": [{"department_id": "Bad Id"}], "workers": []},
    ]
    for payload in bad:
        with pytest.raises((ValueError, KeyError)):
            WorkforceRegistry.from_dict(payload)


def test_a_worker_in_an_unknown_department_is_refused():
    with pytest.raises(ValueError, match="unknown department"):
        WorkforceRegistry(
            departments=load().departments(),
            workers=[
                __import__("workforce").Worker(
                    worker_id="w_x", name="n", department_id="ghost",
                    role=Role.WORKER, mission="m",
                )
            ],
        )


# --------------------------------------------------- 14-16: verification rules


def test_a_producer_cannot_verify_its_own_work(reg):
    """The rule the whole verification subsystem exists to enforce."""
    d = can_verify(reg, "qa_claim_verifier", "qa_claim_verifier")
    assert not d.allowed
    assert "own work" in d.reason


def test_a_non_verifier_cannot_verify(reg):
    d = can_verify(reg, "eng_backend", "brand_copy")
    assert not d.allowed and "verify_claims" in d.reason


def test_verification_without_evidence_is_refused(reg):
    req = VerificationRequest(job_id="job-1", producer_id="eng_backend")
    outcome = verify(reg, req, "qa_claim_verifier")
    assert not outcome.verified
    assert "no evidence" in outcome.reason


def test_weak_evidence_is_refused_for_high_risk_work(reg):
    """Isolates the *kind* rule, so the detail must be checkable.

    This used `"another agent said it was fine"` -- a filler string -- which
    meant the refusal could come from either the kind rule or the checkability
    rule. Now that both exist, a filler string is refused for the wrong reason
    and the kind rule goes untested. A checkable reference of a weak kind is the
    only input that isolates what this test is about.
    """
    req = VerificationRequest(job_id="job-1", producer_id="eng_backend", risk=Risk.HIGH)
    req.add(EvidenceKind.AI_REPORT, "see the review note at docs/ai-review.md")
    outcome = verify(reg, req, "qa_claim_verifier")
    assert not outcome.verified
    assert "weaker than" in outcome.reason


def test_strong_evidence_verifies_high_risk_work(reg):
    req = VerificationRequest(job_id="job-1", producer_id="eng_backend", risk=Risk.HIGH)
    req.add(EvidenceKind.REPRODUCED, "re-ran the suite at commit abc123; 509 passed")
    outcome = verify(reg, req, "qa_claim_verifier")
    assert outcome.verified
    assert outcome.evidence_kind is EvidenceKind.REPRODUCED


def test_a_job_with_no_independent_verifier_stays_unverified(reg):
    """The correct outcome is to remain unverified, not to self-certify."""
    verifier, reason = assign_verifier(reg, "eng_backend", exclude=[
        w.worker_id for w in reg.verifiers()
    ])
    assert verifier is None
    assert "must remain unverified" in reason


def test_an_independent_verifier_is_assigned_when_available(reg):
    verifier, reason = assign_verifier(reg, "eng_backend")
    assert verifier is not None and verifier != "eng_backend"
    assert reg.worker(verifier).role is Role.VERIFIER


# --------------------------------------------- 17-18: serialisation + old jobs


def test_state_survives_a_serialise_reload_round_trip(reg):
    restored = WorkforceRegistry.from_json(reg.to_json())
    assert restored.health() == reg.health()
    assert set(restored.department_ids()) == set(reg.department_ids())
    assert {w.worker_id for w in restored.workers()} == {
        w.worker_id for w in reg.workers()
    }
    # The boundaries must survive too, not just the names.
    assert restored.health()["max_authority"] == reg.health()["max_authority"]
    assert restored.worker("eng_backend").permitted_tools == \
        reg.worker("eng_backend").permitted_tools


def test_existing_jobs_without_workforce_fields_still_work(reg):
    """Phase 1 is additive: it must not require changes to existing job records.

    Phase 2 then *added* those fields, so this no longer asserts their absence --
    that would be asserting that a later phase had not happened. The property
    worth keeping is that a job created without them still works, which is true
    whether the field is missing or present-and-None.
    """
    payload = {"spec": "existing job"}
    j = Job(
        job_id=new_job_id(TaskKind.CODE, "existing", payload),
        kind=TaskKind.CODE, title="existing", payload=payload, risk=Risk.LOW,
    )
    assert getattr(j, "assigned_worker", None) is None
    assert can_delegate(reg, "eng_backend", job_risk=j.risk, job_status=j.status).allowed


def test_decision_is_falsy_when_refused():
    """`if decision:` must not read as permission when it carried a refusal."""
    d = check_authority(load().worker("research_general"), Authority.A2_INTERNAL)
    assert not d
    assert d.reason


# --------------------------------------------------------------------------- #
# The authority ceiling must hold on every path into the registry, not just the
# one that ships.
# --------------------------------------------------------------------------- #

def _head(authority):
    from workforce.schema import DepartmentHead
    return DepartmentHead(
        department_id="d1", name="Test", title="T", mission="m",
        authority=authority, risk_ceiling=Risk.LOW, spend_ceiling_usd=0.0,
        capabilities=frozenset(), permitted_tools=(), permitted_providers=(),
        escalation_rules=(),
    )


def _worker(authority):
    from workforce.schema import Worker
    return Worker(
        worker_id="w1", name="W", department_id="d1", role=Role.WORKER, mission="m",
        capabilities=frozenset(), authority=authority, risk_ceiling=Risk.LOW,
        spend_ceiling_usd=0.0, permitted_tools=(), permitted_providers=(),
        manager_id="h1", memory_scope="d1", status="active",
    )


def test_the_registry_refuses_a_worker_that_outranks_its_head():
    """The rule held only for the built-in roster.

    `workers.default_workers()` checked it, so the roster that ships was safe
    and every other roster was not -- including one that arrived through
    `from_dict`, which this module's docstring claimed was validated. A worker
    at A4 under an A1 head loaded without complaint.
    """
    with pytest.raises(ValueError, match="holds A4 but its head"):
        WorkforceRegistry(departments=[_head(Authority.A1_DRAFT)],
                          workers=[_worker(Authority.A4_CONSEQUENTIAL)])


def test_the_registry_still_accepts_a_worker_at_its_heads_level():
    """The guard above must not be vacuous -- equality is allowed."""
    reg = WorkforceRegistry(departments=[_head(Authority.A1_DRAFT)],
                            workers=[_worker(Authority.A1_DRAFT)])
    assert reg.worker("w1") is not None


def test_a_serialised_roster_cannot_smuggle_an_inflated_authority():
    """`from_dict`/`from_json` are the paths that actually carry stored state.

    This is the case the module docstring promised was covered and was not: a
    round-tripped roster with one worker raised to A4.
    """
    payload = WorkforceRegistry().to_dict()
    heads = {d["department_id"]: d["authority"] for d in payload["departments"]}
    target = next(w for w in payload["workers"]
                  if w["authority"] != heads[w["department_id"]])
    target["authority"] = "A4"

    with pytest.raises(ValueError, match="holds A4 but its head"):
        WorkforceRegistry.from_dict(payload)
    with pytest.raises(ValueError, match="holds A4 but its head"):
        WorkforceRegistry.from_json(json.dumps(payload))


# --------------------------------------------------------------------------- #
# The evidence detail must be checkable on THIS path too, not only in the
# connector. The two paths must not be able to disagree.
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("detail", ["", "   ", "looks fine", "ok", "n/a", "looks fine/"])
def test_uncheckable_evidence_detail_is_refused(reg, detail):
    """`add()` accepted any string, so `add(REPRODUCED, "")` satisfied the
    HIGH-risk minimum and produced a VERIFIED verdict from evidence that names
    nothing. The kind was checked; the detail was not.

    This module's docstring already said the connector and this path "must not
    be able to disagree" -- and they did: the connector refused "looks fine"
    while this path accepted it, and accepted empty evidence outright.
    """
    req = VerificationRequest(job_id="job-1", producer_id="eng_backend", risk=Risk.HIGH)
    req.add(EvidenceKind.REPRODUCED, detail)
    outcome = verify(reg, req, "qa_claim_verifier")
    assert not outcome.verified
    assert "checkable" in outcome.reason


@pytest.mark.parametrize("detail", [
    "reproduced at src/x.py:12",
    "re-ran the suite at commit abc123; 509 passed",
    "see https://example.com/run/7",
])
def test_checkable_evidence_detail_still_verifies(reg, detail):
    """Tightening the detail must not start refusing real evidence."""
    req = VerificationRequest(job_id="job-1", producer_id="eng_backend", risk=Risk.HIGH)
    req.add(EvidenceKind.REPRODUCED, detail)
    outcome = verify(reg, req, "qa_claim_verifier")
    assert outcome.verified, outcome.reason


# --------------------------------------------------------------------------- #
# The central rule of this module is identity, so the identity comparison has to
# be sound. It was a raw `==` on two strings.
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("near_miss", [
    "QA_CLAIM_VERIFIER",     # case
    "qa_claim_verifier ",    # trailing space
    " qa_claim_verifier",    # leading space
    "qa-claim-verifier",     # hyphen for underscore
])
def test_a_near_miss_identity_cannot_verify_its_own_work(reg, near_miss):
    """`can_verify` compared the two ids with `==` before normalising.

    So the module's central rule -- "the identity that produced a result may not
    be the identity that verifies it" -- was bypassable by a case change. The
    connector already canonicalises provider ids for exactly this reason and
    says so in its docstring; that reasoning was never carried here.
    """
    d = can_verify(reg, near_miss, "qa_claim_verifier")
    assert not d.allowed


def test_an_unknown_producer_cannot_be_verified(reg):
    """Independence cannot be established for a producer that does not exist.

    Refusing is the safe failure: otherwise anyone can name a producer that is
    not a worker and have the work verified by whoever they like.
    """
    d = can_verify(reg, "nonexistent_worker", "qa_claim_verifier")
    assert not d.allowed
    assert "unknown producer" in d.reason


def test_independent_verification_still_works(reg):
    """The guards above must not be vacuous -- a real verifier still verifies."""
    assert can_verify(reg, "eng_backend", "qa_claim_verifier").allowed
