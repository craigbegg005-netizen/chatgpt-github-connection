"""Tests for the claim lease (``renew_lease`` / ``expire_stale_claims``).

A claim used to be indefinite: a dead worker left its job RUNNING forever,
which is abandonment that nothing could see. The lease makes silence
measurable. These tests assert the doctrine: expiry releases dead claims,
never live ones; a NULL clock is never punished; the checkpoint trail
survives; and expiry is always an audited act.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from connector import Job, Status, Store, TaskKind, Transport, new_job_id  # noqa: E402


def job(title, lease_seconds=3600):
    payload = {"spec": title}
    return Job(
        job_id=new_job_id(TaskKind.RESEARCH, title, payload),
        kind=TaskKind.RESEARCH,
        title=title,
        payload=payload,
        lease_seconds=lease_seconds,
    )


def claimed(store, title="t", provider="grok", lease_seconds=3600):
    j, _ = store.create_job(job(title, lease_seconds=lease_seconds), actor="oddfellow")
    store.claim_job(j.job_id, provider=provider, transport=Transport.HANDOFF, actor=provider)
    return j.job_id


def later(**kwargs):
    return datetime.now(timezone.utc) + timedelta(**kwargs)


def test_claim_starts_the_clock():
    with Store() as store:
        jid = claimed(store)
        j = store.get_job(jid)
        assert j.claimed_at is not None
        assert j.lease_seconds == 3600


def test_expired_claim_is_released_and_audited():
    with Store() as store:
        jid = claimed(store)
        expired = store.expire_stale_claims(now=later(hours=2))
        assert [e.job_id for e in expired] == [jid]
        j = store.get_job(jid)
        assert j.status is Status.READY
        assert j.provider is None
        assert j.claimed_at is None
        events = [e for e in store.audit_trail() if e["event"] == "job.lease.expired"]
        assert len(events) == 1 and "grok" in str(events[0]["detail"])


def test_fresh_claim_is_not_expired():
    with Store() as store:
        claimed(store)
        assert store.expire_stale_claims(now=later(minutes=30)) == []


def test_renewal_resets_the_clock():
    with Store() as store:
        jid = claimed(store)
        store.renew_lease(jid, actor="grok")
        assert store.expire_stale_claims(now=later(minutes=30)) == []
        events = [e["event"] for e in store.audit_trail()]
        assert "job.lease.renewed" in events


def test_renewing_a_non_running_job_is_refused():
    with Store() as store:
        j, _ = store.create_job(job("ready"), actor="oddfellow")
        with pytest.raises(ValueError, match="no claim to renew"):
            store.renew_lease(j.job_id, actor="grok")


def test_null_clock_never_expires():
    """A pre-lease row (claimed_at NULL) must not be killed by a clock it never started."""
    with Store() as store:
        jid = claimed(store)
        store._conn.execute("UPDATE jobs SET claimed_at=NULL WHERE job_id=?", (jid,))
        store._conn.commit()
        assert store.expire_stale_claims(now=later(days=30)) == []
        assert store.get_job(jid).status is Status.RUNNING


def test_only_running_jobs_are_touched():
    with Store() as store:
        j, _ = store.create_job(job("ready"), actor="oddfellow")
        assert store.expire_stale_claims(now=later(days=30)) == []
        assert store.get_job(j.job_id).status is Status.READY


def test_expiry_is_idempotent():
    with Store() as store:
        claimed(store)
        first = store.expire_stale_claims(now=later(hours=2))
        second = store.expire_stale_claims(now=later(hours=3))
        assert len(first) == 1 and second == []


def test_checkpoint_trail_and_payload_survive_expiry():
    with Store() as store:
        jid = claimed(store)
        store.record_checkpoint(jid, "half done", actor="grok")
        store.expire_stale_claims(now=later(hours=2))
        store.claim_job(jid, provider="claude", transport=Transport.HANDOFF, actor="claude")
        resumed = store.get_job(jid)
        assert [e["step"] for e in resumed.checkpoints] == ["half done"]
        assert resumed.payload == {"spec": "t"}


def test_claim_ending_paths_clear_the_clock():
    """Complete, fail, release, and failover all end the claim clock."""
    with Store() as store:
        jid = claimed(store)
        store.submit_result(jid, {"ok": True}, actor="grok", provider="grok")
        assert store.get_job(jid).claimed_at is None

        jid2 = claimed(store, title="u")
        store.fail_job(jid2, "boom", actor="grok", retryable=True)
        assert store.get_job(jid2).claimed_at is None

        jid3 = claimed(store, title="v")
        store.release_claim(jid3, actor="oddfellow", reason="disconnect")
        assert store.get_job(jid3).claimed_at is None


def test_dead_worker_resume_end_to_end():
    """The directive's scenario: claim, die silently, expire, re-claim, complete."""
    with Store() as store:
        jid = claimed(store, lease_seconds=600)
        store.record_checkpoint(jid, "progress A", actor="grok")
        # grok dies: no renewal, no fail, no release.
        store.expire_stale_claims(now=later(minutes=11))
        store.claim_job(jid, provider="claude", transport=Transport.HANDOFF, actor="claude")
        done, is_new = store.submit_result(jid, {"ok": True}, actor="claude", provider="claude")
        assert is_new and done.status is Status.COMPLETE
        assert [e["step"] for e in done.checkpoints] == ["progress A"]
