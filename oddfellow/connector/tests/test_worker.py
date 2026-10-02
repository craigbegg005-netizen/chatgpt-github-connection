"""Tests for the queue tick.

The tick exists so the queue can be drained on a schedule, which means every test
here is really about **what happens when it runs repeatedly** -- because that is the
only thing a scheduled job does differently from a manual one. An idempotency bug in
a one-off command is invisible; in an hourly command it is a flood.
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from connector import Job, Risk, Status, Store, TaskKind, new_job_id  # noqa: E402
from connector.worker import FINGERPRINT_KEY, reset_fingerprint, tick  # noqa: E402


def job(title, risk=Risk.LOW, max_attempts=3):
    payload = {"spec": title}
    return Job(
        job_id=new_job_id(TaskKind.CODE, title, payload),
        kind=TaskKind.CODE, title=title, payload=payload, risk=risk,
        max_attempts=max_attempts,
    )


@pytest.fixture()
def store():
    s = Store(":memory:")
    yield s
    s.close()


def test_tick_renders_a_handoff_when_there_is_work(store, tmp_path):
    store.create_job(job("do a thing"), actor="x")
    report = tick(store, "claude", tmp_path)
    assert report["ready"] == 1
    assert report["rendered"] is not None
    written = tmp_path / "handoff-claude.md"
    assert written.exists()
    assert "do a thing" in written.read_text()


def test_second_tick_is_idempotent(store, tmp_path):
    """The property that makes this safe to schedule."""
    store.create_job(job("do a thing"), actor="x")
    first = tick(store, "claude", tmp_path)
    assert first["rendered"] is not None

    before = (tmp_path / "handoff-claude.md").read_text()
    second = tick(store, "claude", tmp_path)
    assert second["rendered"] is None
    assert "identical" in second["skipped"]
    assert (tmp_path / "handoff-claude.md").read_text() == before


def test_tick_with_no_ready_jobs_does_nothing_and_says_so(store, tmp_path):
    report = tick(store, "claude", tmp_path)
    assert report["ready"] == 0
    assert report["rendered"] is None
    assert report["skipped"] == "no ready jobs"
    assert not (tmp_path / "handoff-claude.md").exists(), "no empty document"


def test_tick_refuses_to_prepare_work_while_paused(store, tmp_path):
    """The emergency stop applies to preparation, not only to execution."""
    store.create_job(job("do a thing"), actor="x")
    store.set_paused(True, actor="owner", reason="stop")
    report = tick(store, "claude", tmp_path)
    assert report["paused"] is True
    assert report["rendered"] is None
    assert "pause" in report["skipped"]
    assert not (tmp_path / "handoff-claude.md").exists()


def test_a_changed_ready_set_renders_again(store, tmp_path):
    store.create_job(job("first"), actor="x")
    assert tick(store, "claude", tmp_path)["rendered"] is not None
    store.create_job(job("second"), actor="x")
    assert tick(store, "claude", tmp_path)["rendered"] is not None


def test_reset_fingerprint_forces_a_re_render(store, tmp_path):
    """Needed when a job's CONTENT changes but the id set does not."""
    store.create_job(job("do a thing"), actor="x")
    tick(store, "claude", tmp_path)
    assert tick(store, "claude", tmp_path)["rendered"] is None
    reset_fingerprint(store)
    assert tick(store, "claude", tmp_path)["rendered"] is not None


def test_tick_records_what_it_did_in_the_audit_trail(store, tmp_path):
    store.create_job(job("do a thing"), actor="x")
    report = tick(store, "claude", tmp_path)
    events = {e["event"] for e in store.audit_trail(limit=20)}
    assert "worker.handoff_rendered" in events
    assert report["fingerprint"] in store.flag_get(FINGERPRINT_KEY, "")


def test_tick_does_not_change_job_state(store, tmp_path):
    """It prepares work. It must not claim, approve, or complete anything."""
    j = job("do a thing")
    store.create_job(j, actor="x")
    tick(store, "claude", tmp_path)
    after = store.get_job(j.job_id)
    assert after.status is Status.READY
    assert after.provider is None
    assert after.attempts == 0
    assert after.verified is False


def test_a_high_risk_job_is_rendered_but_stays_unclaimable(store, tmp_path):
    """Rendering is not approval: the gate still holds at claim time."""
    from connector import ClaimRefused

    j = job("dangerous", risk=Risk.CRITICAL)
    store.create_job(j, actor="x")
    report = tick(store, "claude", tmp_path)
    assert report["rendered"] is not None, "the work is prepared"
    with pytest.raises(ClaimRefused):
        store.claim_job(j.job_id, "claude", None, actor="claude")


def test_tick_reports_dead_letters(store, tmp_path):
    # max_attempts=1 so the first failure is terminal rather than retryable --
    # fail_job defaults to retryable, and with attempts < max it would be.
    j = job("will fail", max_attempts=1)
    store.create_job(j, actor="x")
    store.claim_job(j.job_id, "letta", None, actor="letta")
    store.fail_job(j.job_id, "permanent", actor="letta")
    report = tick(store, "claude", tmp_path)
    assert report["dead_letters"] == 1
