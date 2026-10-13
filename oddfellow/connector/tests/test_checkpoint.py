"""Tests for the Phase 3 failover fields: ``priority`` and the checkpoint trail.

Both exist for one directive requirement: a job handed from one provider to
another must carry its partial progress with it, so the receiver resumes
instead of repeating verified work. The failure mode they guard against is
specific: without a durable, audited trail, "resume from checkpoint" is a
phrase, and the receiving provider either redoes completed steps (wasted work)
or trusts the previous provider's word for what was done (unverifiable).
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from connector import (  # noqa: E402
    Job,
    Priority,
    Risk,
    Status,
    Store,
    TaskKind,
    Transport,
    new_job_id,
)


def job(title, risk=Risk.LOW, priority=Priority.NORMAL):
    payload = {"spec": title}
    return Job(
        job_id=new_job_id(TaskKind.RESEARCH, title, payload),
        kind=TaskKind.RESEARCH,
        title=title,
        payload=payload,
        risk=risk,
        priority=priority,
        max_attempts=2,
    )


# ------------------------------------------------------------------ priority


def test_priority_defaults_to_normal():
    assert job("a").priority is Priority.NORMAL


def test_priority_round_trips_through_storage(tmp_path):
    db = str(tmp_path / "c.db")
    with Store(db) as store:
        j, _ = store.create_job(job("urgent storefront fix", priority=Priority.URGENT), actor="oddfellow")
    with Store(db) as store:
        reloaded = store.get_job(j.job_id)
    assert reloaded.priority is Priority.URGENT


# --------------------------------------------------------------- checkpoints


def test_checkpoint_appends_in_order_with_actor_and_timestamp():
    with Store() as store:
        j, _ = store.create_job(job("gumroad audit"), actor="oddfellow")
        store.record_checkpoint(j.job_id, "listed products", actor="grok", note="2 listings")
        store.record_checkpoint(j.job_id, "checked delivery files", actor="grok")
        trail = store.checkpoint_trail(j.job_id)
    assert [e["step"] for e in trail] == ["listed products", "checked delivery files"]
    assert all(e["actor"] == "grok" for e in trail)
    assert all(e["at"] for e in trail)


def test_checkpoints_survive_store_reload(tmp_path):
    """Durability: a trail that lives only in memory is not a failover record.

    This is also the negative control for the INSERT statement: if the column
    list omits ``checkpoints``, the write succeeds silently and the reload
    below sees an empty trail.
    """
    db = str(tmp_path / "c.db")
    with Store(db) as store:
        j, _ = store.create_job(job("durable trail"), actor="oddfellow")
        store.record_checkpoint(j.job_id, "step one", actor="claude", evidence="out/one.md")
    with Store(db) as store:
        trail = store.checkpoint_trail(j.job_id)
    assert len(trail) == 1
    assert trail[0]["evidence"] == "out/one.md"


def test_checkpoint_requires_a_step_label():
    with Store() as store:
        j, _ = store.create_job(job("no label"), actor="oddfellow")
        with pytest.raises(ValueError, match="step label"):
            store.record_checkpoint(j.job_id, "  ", actor="grok")


def test_checkpoint_on_unknown_job_is_refused():
    with Store() as store:
        with pytest.raises(KeyError, match="no such job"):
            store.record_checkpoint("job-does-not-exist", "x", actor="grok")


def test_every_checkpoint_lands_in_the_audit_log():
    with Store() as store:
        j, _ = store.create_job(job("audited trail"), actor="oddfellow")
        store.record_checkpoint(j.job_id, "step a", actor="grok")
        store.record_checkpoint(j.job_id, "step b", actor="claude")
        events = [e for e in store.audit_trail() if e["event"] == "job.checkpoint"]
    assert len(events) == 2
    assert all(e["job_id"] == j.job_id for e in events)


def test_failover_resume_scenario_keeps_the_trail():
    """The directive's core flow: provider A claims, makes progress, releases;
    provider B claims and reads the trail -- and the trail is intact.

    If release/re-claim cleared or reset the checkpoints, B would redo A's
    completed steps, which is exactly the duplication the directive forbids.
    """
    with Store() as store:
        j, _ = store.create_job(job("handoff job"), actor="oddfellow")
        store.claim_job(j.job_id, provider="grok", transport=Transport.HANDOFF, actor="grok")
        store.record_checkpoint(j.job_id, "demand researched", actor="grok", note="3 competitors")
        store.release_claim(j.job_id, actor="grok", reason="cannot reach storefront")
        store.claim_job(j.job_id, provider="claude", transport=Transport.QUEUE, actor="claude")
        resumed = store.get_job(j.job_id)
    assert resumed.provider == "claude"
    assert resumed.status is Status.RUNNING
    assert [e["step"] for e in resumed.checkpoints] == ["demand researched"]
    assert resumed.checkpoints[0]["note"] == "3 competitors"


def test_to_row_from_row_round_trip_with_checkpoints():
    j = job("round trip")
    j.checkpoints = ({"at": "2026-10-13T00:00:00Z", "actor": "grok", "step": "s", "note": "", "evidence": ""},)
    restored = Job.from_row(j.to_row())
    assert restored.priority is j.priority
    assert restored.checkpoints == j.checkpoints
