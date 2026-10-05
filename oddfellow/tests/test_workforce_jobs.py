"""Phase 2 tests: workforce identities linked to jobs.

The rule this file exists to defend is that **a synthetic head cannot create
work without saying what caused it**. Everything else here is linkage, and
linkage that is wrong is usually linkage that silently does nothing -- a
worker assigned under a near-miss identity, a verifier recorded for a job it
could not actually verify.
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from connector.schema import Job, Risk, Status, TaskKind, new_job_id  # noqa: E402
from connector.store import Store  # noqa: E402
from workforce import (  # noqa: E402
    OriginRequired,
    assign_job,
    create_generated_job,
    load,
    record_verification_worker,
    traceability,
    untraced_jobs,
)


@pytest.fixture()
def store():
    s = Store(":memory:")
    yield s
    s.close()


@pytest.fixture()
def reg():
    return load()


def human_job(title="filed by hand"):
    payload = {"spec": title}
    return Job(
        job_id=new_job_id(TaskKind.CODE, title, payload),
        kind=TaskKind.CODE, title=title, payload=payload, risk=Risk.LOW,
    )


# ------------------------------------------------ the origin rule, enforced


def test_a_generated_job_must_state_an_origin(store, reg):
    """The rule Phase 1 could not express, and the reason for this module."""
    with pytest.raises(OriginRequired):
        create_generated_job(
            store, reg, department_id="engineering", requested_by="eng_backend",
            kind=TaskKind.CODE, title="no reason given",
        )


def test_a_generated_job_with_an_objective_is_accepted(store, reg):
    job = create_generated_job(
        store, reg, department_id="engineering", requested_by="eng_backend",
        kind=TaskKind.CODE, title="bounded work", origin_objective="obj-1",
    )
    assert job.origin_objective == "obj-1"
    assert job.assigned_department == "engineering"
    assert traceability(job)["state"] == "traced"


def test_a_generated_job_with_a_parent_is_accepted(store, reg):
    parent = create_generated_job(
        store, reg, department_id="engineering", requested_by="eng_backend",
        kind=TaskKind.CODE, title="parent", origin_objective="obj-1",
    )
    child = create_generated_job(
        store, reg, department_id="engineering", requested_by="eng_backend",
        kind=TaskKind.CODE, title="child", origin_job_id=parent.job_id,
    )
    assert traceability(child)["state"] == "traced"


def test_a_parent_that_does_not_exist_is_refused(store, reg):
    """A dangling parent still *looks* traced, which is worse than untraced."""
    with pytest.raises(ValueError, match="does not exist"):
        create_generated_job(
            store, reg, department_id="engineering", requested_by="eng_backend",
            kind=TaskKind.CODE, title="orphan", origin_job_id="job-nope",
        )


def test_the_store_provably_holds_no_untraced_generated_jobs(store, reg):
    create_generated_job(
        store, reg, department_id="engineering", requested_by="eng_backend",
        kind=TaskKind.CODE, title="a", origin_objective="obj-1",
    )
    assert untraced_jobs(store) == []


# ------------------------------------------- identity validated, not compared


@pytest.mark.parametrize("near_miss", [
    "ENG_BACKEND",        # case
    "eng_backend ",       # trailing space
    " eng_backend",       # leading space
    "eng-backend",        # hyphen for underscore
])
def test_a_near_miss_identity_is_rejected_not_accepted(store, reg, near_miss):
    """Phase 1's central rule was bypassable by a case change.

    The fix there was to validate ids rather than compare raw strings, and this
    module applies the same rule: a near-miss must fail as an *invalid id*, not
    become a second identity that silently matches nothing.
    """
    with pytest.raises(ValueError, match="not a valid id|not a known worker"):
        create_generated_job(
            store, reg, department_id="engineering", requested_by=near_miss,
            kind=TaskKind.CODE, title="near miss", origin_objective="obj-1",
        )


def test_an_unknown_worker_is_refused(store, reg):
    with pytest.raises(ValueError, match="not a known worker"):
        create_generated_job(
            store, reg, department_id="engineering", requested_by="nobody_here",
            kind=TaskKind.CODE, title="x", origin_objective="obj-1",
        )


def test_a_worker_cannot_file_work_for_another_department(store, reg):
    with pytest.raises(ValueError, match="belongs to"):
        create_generated_job(
            store, reg, department_id="security", requested_by="eng_backend",
            kind=TaskKind.CODE, title="x", origin_objective="obj-1",
        )


def test_an_unknown_department_is_refused(store, reg):
    with pytest.raises(ValueError, match="not a known department"):
        create_generated_job(
            store, reg, department_id="ghost", requested_by="eng_backend",
            kind=TaskKind.CODE, title="x", origin_objective="obj-1",
        )


# ------------------------------------------------------------- job assignment


def test_a_job_can_be_assigned_to_an_eligible_worker(store, reg):
    j = human_job()
    store.create_job(j, actor="owner")
    assigned = assign_job(store, reg, j.job_id, "eng_backend", actor="exec_program_coordinator")
    assert assigned.assigned_worker == "eng_backend"
    assert assigned.assigned_department == "engineering"


def test_assignment_honours_the_emergency_pause(store, reg):
    j = human_job()
    store.create_job(j, actor="owner")
    with pytest.raises(ValueError, match="pause"):
        assign_job(store, reg, j.job_id, "eng_backend", actor="x", paused=True)


def test_assignment_honours_the_risk_ceiling(store, reg):
    payload = {"spec": "critical"}
    j = Job(
        job_id=new_job_id(TaskKind.CODE, "critical", payload), kind=TaskKind.CODE,
        title="critical", payload=payload, risk=Risk.CRITICAL,
    )
    store.create_job(j, actor="owner")
    with pytest.raises(ValueError, match="approval"):
        assign_job(store, reg, j.job_id, "eng_backend", actor="x")


def test_assignment_is_audited(store, reg):
    j = human_job()
    store.create_job(j, actor="owner")
    assign_job(store, reg, j.job_id, "eng_backend", actor="exec_program_coordinator")
    events = {e["event"] for e in store.audit_trail(limit=20)}
    assert "job.assigned" in events


# --------------------------------------------------- verification assignment


def test_a_verifier_is_recorded_for_a_job(store, reg):
    j = human_job()
    store.create_job(j, actor="owner")
    assign_job(store, reg, j.job_id, "eng_backend", actor="x")
    updated = record_verification_worker(
        store, reg, j.job_id, "qa_claim_verifier", actor="ops_monitor"
    )
    assert updated.verification_worker == "qa_claim_verifier"


def test_the_producer_cannot_be_recorded_as_its_own_verifier(store, reg):
    j = human_job()
    store.create_job(j, actor="owner")
    assign_job(store, reg, j.job_id, "qa_claim_verifier", actor="x")
    with pytest.raises(ValueError, match="own work"):
        record_verification_worker(
            store, reg, j.job_id, "qa_claim_verifier", actor="x"
        )


def test_a_non_verifier_role_cannot_be_recorded_as_verifier(store, reg):
    j = human_job()
    store.create_job(j, actor="owner")
    assign_job(store, reg, j.job_id, "eng_backend", actor="x")
    with pytest.raises(ValueError, match="verify_claims"):
        record_verification_worker(store, reg, j.job_id, "brand_copy", actor="x")


# ------------------------------------------------------ backward compatibility


def test_a_job_with_no_workforce_fields_is_untraced_not_invalid(store, reg):
    """Human-filed and legacy jobs are not defects, and must not be reported as
    such -- collapsing the two states would make the rule unusable."""
    j = human_job()
    store.create_job(j, actor="owner")
    report = traceability(store.get_job(j.job_id))
    assert report["state"] == "not-synthetic"
    assert untraced_jobs(store) == [], "a human job is not an untraced defect"


def test_existing_job_round_trips_through_the_store_unchanged(store, reg):
    """The Phase 2 columns must not disturb a job that predates them."""
    j = human_job()
    store.create_job(j, actor="owner")
    back = store.get_job(j.job_id)
    assert back.status is Status.READY
    assert back.assigned_department is None
    assert back.assigned_worker is None
    assert back.requested_by is None
    assert back.origin_objective is None
    assert back.origin_job_id is None
    assert back.verification_worker is None


def test_workforce_fields_survive_a_store_round_trip(store, reg):
    job = create_generated_job(
        store, reg, department_id="engineering", requested_by="eng_backend",
        kind=TaskKind.CODE, title="persisted", origin_objective="obj-9",
        assigned_worker="eng_backend",
    )
    back = store.get_job(job.job_id)
    assert back.assigned_department == "engineering"
    assert back.assigned_worker == "eng_backend"
    assert back.requested_by == "eng_backend"
    assert back.origin_objective == "obj-9"
