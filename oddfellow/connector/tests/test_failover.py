"""Tests for the automatic failover trigger (``Store.failover_to_next``).

The directive's requirement is precise: when a provider fails, the job moves
to another *capable, authorized* provider and resumes -- and a failure must
never become a route around an approval. These tests assert the doctrine,
not the mechanics: only failures fail over, approvals survive, paid providers
stay excluded by default, and exhaustion parks the job instead of dropping it.
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from connector import (  # noqa: E402
    Job,
    Risk,
    Status,
    Store,
    TaskKind,
    Transport,
    new_job_id,
)
from connector.providers import Capability, Provider  # noqa: E402


def capable(name, *, paid=False, polling=False, transport=Transport.HANDOFF):
    """A provider whose capability is VERIFIED, as detection would leave it."""
    return Provider(
        name=name,
        label=name,
        declared=(Capability(transport, frozenset(TaskKind), "docs"),),
        verified={transport: "probed in test"},
        paid=paid,
        polling=polling,
    )


def registry(*providers):
    return {p.name: p for p in providers}


def job(title, risk=Risk.LOW):
    payload = {"spec": title}
    return Job(
        job_id=new_job_id(TaskKind.RESEARCH, title, payload),
        kind=TaskKind.RESEARCH,
        title=title,
        payload=payload,
        risk=risk,
        max_attempts=2,
    )


def failed_job(store, title="t", provider="grok", risk=Risk.LOW):
    j, _ = store.create_job(job(title, risk=risk), actor="oddfellow")
    approval_id = None
    if risk in (Risk.HIGH, Risk.CRITICAL):
        req = store.request_approval(j.job_id, actor=provider)
        store.decide_approval(req["approval_id"], "approve", actor="oddfellow", evidence="owner instruction")
        approval_id = req["approval_id"]
    store.claim_job(j.job_id, provider=provider, transport=Transport.HANDOFF, actor=provider, approval_id=approval_id)
    store.fail_job(j.job_id, "cannot complete", actor=provider, retryable=True)
    return j.job_id


def test_retryable_failure_moves_to_next_capable_provider():
    with Store() as store:
        reg = registry(capable("grok"), capable("claude"))
        jid = failed_job(store)
        job2, chosen = store.failover_to_next(jid, actor="oddfellow", registry=reg)
        assert chosen == "claude"
        assert job2.status is Status.READY
        assert job2.provider is None  # provider is set by a claim, not a recommendation


def test_the_just_failed_provider_is_never_reselected():
    with Store() as store:
        reg = registry(capable("grok"), capable("claude"), capable("gemini"))
        jid = failed_job(store, provider="grok")
        _, chosen = store.failover_to_next(jid, actor="oddfellow", registry=reg)
        assert chosen != "grok"


def test_only_failed_retryable_jobs_fail_over():
    """A non-failure must refuse: re-routing a READY/WAITING job is not failover."""
    with Store() as store:
        reg = registry(capable("grok"), capable("claude"))
        j, _ = store.create_job(job("ready job"), actor="oddfellow")
        with pytest.raises(ValueError, match="not failover"):
            store.failover_to_next(j.job_id, actor="oddfellow", registry=reg)


def test_exhaustion_preserves_the_job_and_audits_it():
    with Store() as store:
        reg = registry(capable("grok"))  # only the failed provider exists
        jid = failed_job(store, provider="grok")
        job2, chosen = store.failover_to_next(jid, actor="oddfellow", registry=reg)
        assert chosen is None
        assert job2.status is Status.FAILED_RETRYABLE  # parked, not dropped
        events = [e["event"] for e in store.audit_trail()]
        assert "job.failover.exhausted" in events


def test_paid_providers_are_excluded_by_default():
    with Store() as store:
        reg = registry(capable("grok"), capable("openai", paid=True))
        jid = failed_job(store, provider="grok")
        _, chosen = store.failover_to_next(jid, actor="oddfellow", registry=reg)
        assert chosen is None  # paid candidate excluded -> exhausted
        _, chosen2 = store.failover_to_next(jid, actor="oddfellow", registry=reg, allow_paid=True)
        # allow_paid only reaches candidates when the owner opted in
        assert chosen2 == "openai"


def test_approval_survives_failover():
    """HIGH-risk job fails over; the receiver still cannot claim without approval."""
    with Store() as store:
        reg = registry(capable("grok"), capable("claude"))
        jid = failed_job(store, provider="grok", risk=Risk.HIGH)
        store.failover_to_next(jid, actor="oddfellow", registry=reg)
        with pytest.raises(Exception):
            store.claim_job(jid, provider="claude", transport=Transport.HANDOFF, actor="claude")
        # With a fresh approval bound to the job, the claim succeeds.
        req = store.request_approval(jid, actor="claude")
        store.decide_approval(req["approval_id"], "approve", actor="oddfellow", evidence="owner instruction in chat 2026-10-14")
        store.claim_job(jid, provider="claude", transport=Transport.HANDOFF, actor="claude", approval_id=req["approval_id"])
        assert store.get_job(jid).provider == "claude"


def test_checkpoint_trail_and_payload_survive_failover():
    with Store() as store:
        reg = registry(capable("grok"), capable("claude"))
        jid = failed_job(store, provider="grok")
        store.record_checkpoint(jid, "demand researched", actor="grok", note="3 competitors")
        store.fail_job(jid, "second failure", actor="grok", retryable=True)
        # note: fail again after checkpoint to keep status FAILED_RETRYABLE
        store.failover_to_next(jid, actor="oddfellow", registry=reg)
        store.claim_job(jid, provider="claude", transport=Transport.HANDOFF, actor="claude")
        resumed = store.get_job(jid)
        assert [e["step"] for e in resumed.checkpoints] == ["demand researched"]
        assert resumed.payload == {"spec": "t"}


def test_every_failover_is_audited_with_from_and_to():
    with Store() as store:
        reg = registry(capable("grok"), capable("claude"))
        jid = failed_job(store, provider="grok")
        store.failover_to_next(jid, actor="oddfellow", registry=reg)
        events = [e for e in store.audit_trail() if e["event"] == "job.failover"]
        assert len(events) == 1
        detail = events[0]["detail"]
        assert "claude" in str(detail) and "grok" in str(detail)


def test_receiver_resumes_and_completes_end_to_end():
    """The directive's whole flow: fail, fail over, claim, resume, submit."""
    with Store() as store:
        reg = registry(capable("grok"), capable("claude"))
        jid = failed_job(store, provider="grok")
        store.record_checkpoint(jid, "half done", actor="grok")
        store.fail_job(jid, "still failed", actor="grok", retryable=True)
        _, chosen = store.failover_to_next(jid, actor="oddfellow", registry=reg)
        store.claim_job(jid, provider=chosen, transport=Transport.HANDOFF, actor=chosen)
        submitted = store.submit_result(jid, result={"ok": True}, provider=chosen, actor=chosen)
        done = submitted[0] if isinstance(submitted, tuple) else submitted
        assert done.status is Status.COMPLETE
        assert [e["step"] for e in done.checkpoints] == ["half done"]
