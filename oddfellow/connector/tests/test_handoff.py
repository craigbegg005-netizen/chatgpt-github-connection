"""Tests for Tier 3/4 of the fallback ladder: structured handoff and the queue.

These rungs need no credentials, which makes them the only part of the connector
that is usable with a real provider today. Two properties matter most and are
asserted directly: a handoff must be safe to paste into a third-party chat (no
secrets), and a returned result must not be a way around the claim/approval gate.
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from connector import Job, Risk, Status, Store, TaskKind, new_job_id  # noqa: E402
from connector.handoff import (  # noqa: E402
    apply_handoff,
    parse_handoff,
    render_handoff,
)

SECRET = "OWNER-TOKEN-DO-NOT-PASTE-THIS"


def job(title, risk=Risk.LOW, payload=None):
    payload = payload if payload is not None else {"spec": title}
    return Job(
        job_id=new_job_id(TaskKind.CODE, title, payload),
        kind=TaskKind.CODE,
        title=title,
        payload=payload,
        risk=risk,
    )


@pytest.fixture()
def store():
    s = Store(":memory:")
    yield s
    s.close()


# ------------------------------------------------------------------ rendering


def test_render_includes_only_ready_jobs(store):
    ready = job("do the thing")
    running = job("already taken")
    store.create_job(ready, actor="x")
    store.create_job(running, actor="x")
    store.claim_job(running.job_id, "letta", None, actor="letta")

    doc = render_handoff(store, "claude")
    assert ready.job_id in doc
    assert running.job_id not in doc, "work already claimed must not be handed over"


def test_render_says_so_when_there_is_nothing_to_do(store):
    doc = render_handoff(store, "claude")
    assert "No jobs are ready" in doc


def test_render_carries_no_secret(store):
    """A document meant to be pasted into a chat has to be safe to paste."""
    j = job("handle it", payload={"spec": "x", "note": SECRET})
    store.create_job(j, actor="x")
    doc = render_handoff(store, "claude")
    # The job's own payload is included by design -- that IS the work. What must
    # never appear is a credential the connector holds.
    assert "odf_" not in doc
    assert "connector_tokens" not in doc
    assert "owner-master" not in doc


def test_render_requires_evidence_in_its_instructions(store):
    store.create_job(job("t"), actor="x")
    doc = render_handoff(store, "claude")
    assert "evidence" in doc.lower()


# -------------------------------------------------------------------- parsing


def test_parse_a_well_formed_block():
    text = 'Here you go:\n```json\n{"job_id": "job-1", "result": {"a": 1}, "evidence": "ran it"}\n```'
    results, problems = parse_handoff(text)
    assert problems == []
    assert results[0].job_id == "job-1"
    assert results[0].result == {"a": 1}
    assert results[0].evidence == "ran it"


def test_parse_reports_bad_json_rather_than_skipping_it():
    results, problems = parse_handoff("```json\n{not json}\n```")
    assert results == []
    assert problems and "not valid JSON" in problems[0]


def test_parse_reports_a_missing_job_id():
    results, problems = parse_handoff('```json\n{"result": 1}\n```')
    assert results == []
    assert any("job_id" in p for p in problems)


def test_parse_reports_a_missing_result():
    results, problems = parse_handoff('```json\n{"job_id": "job-1"}\n```')
    assert results == []
    assert any("result" in p for p in problems)


def test_parse_reports_prose_with_no_block():
    results, problems = parse_handoff("I looked at the jobs and they seem fine.")
    assert results == []
    assert any("no fenced JSON block" in p for p in problems)


def test_parse_accepts_a_bare_fence():
    results, _ = parse_handoff('```\n{"job_id": "j", "result": 1}\n```')
    assert results[0].job_id == "j"


def test_parse_handles_empty_input():
    results, problems = parse_handoff("")
    assert results == [] and problems == []


# ------------------------------------------------------------------- applying


def test_apply_claims_and_submits(store):
    j = job("do it")
    store.create_job(j, actor="x")
    report = apply_handoff(
        store,
        f'```json\n{{"job_id": "{j.job_id}", "result": {{"ok": true}}, "evidence": "ran the suite"}}\n```',
        provider="claude",
        actor="claude",
    )
    assert len(report["accepted"]) == 1
    got = store.get_job(j.job_id)
    assert got.status is Status.COMPLETE
    assert got.provider == "claude"


def test_accepted_results_are_complete_never_verified(store):
    j = job("do it")
    store.create_job(j, actor="x")
    report = apply_handoff(
        store,
        f'```json\n{{"job_id": "{j.job_id}", "result": 1, "evidence": "checked"}}\n```',
        provider="claude", actor="claude",
    )
    assert report["accepted"][0]["verified"] is False
    assert store.get_job(j.job_id).verified is False
    assert "not VERIFIED" in report["note"]


def test_apply_refuses_an_unknown_job(store):
    report = apply_handoff(
        store, '```json\n{"job_id": "job-nope", "result": 1}\n```',
        provider="claude", actor="claude",
    )
    assert report["accepted"] == []
    assert report["refused"][0]["reason"] == "unknown job"


def test_handoff_cannot_steal_a_job_another_provider_claimed(store):
    """A handoff is an untrusted channel; it must not be a way around the gate."""
    j = job("contested")
    store.create_job(j, actor="x")
    store.claim_job(j.job_id, "letta", None, actor="letta")
    report = apply_handoff(
        store,
        f'```json\n{{"job_id": "{j.job_id}", "result": "mine now"}}\n```',
        provider="claude", actor="claude",
    )
    assert report["accepted"] == []
    assert "claimed by" in report["refused"][0]["reason"]
    assert store.get_job(j.job_id).provider == "letta"


def test_handoff_cannot_run_high_risk_work_unapproved(store):
    j = job("dangerous", risk=Risk.CRITICAL)
    store.create_job(j, actor="x")
    report = apply_handoff(
        store,
        f'```json\n{{"job_id": "{j.job_id}", "result": "done"}}\n```',
        provider="claude", actor="claude",
    )
    assert report["accepted"] == []
    assert "approv" in report["refused"][0]["reason"].lower()
    assert store.get_job(j.job_id).status is Status.READY


def test_handoff_reports_problems_alongside_accepted_results(store):
    j = job("good one")
    store.create_job(j, actor="x")
    text = (
        f'```json\n{{"job_id": "{j.job_id}", "result": 1}}\n```\n'
        "and also\n```json\n{oops}\n```"
    )
    report = apply_handoff(store, text, provider="claude", actor="claude")
    assert len(report["accepted"]) == 1
    assert report["problems"], "a bad block must be reported, not swallowed"


def test_handoff_is_idempotent_on_replay(store):
    j = job("replayable")
    store.create_job(j, actor="x")
    text = f'```json\n{{"job_id": "{j.job_id}", "result": {{"n": 1}}}}\n```'
    first = apply_handoff(store, text, provider="claude", actor="claude")
    assert len(first["accepted"]) == 1

    # Same result replayed: the job is COMPLETE, so a second claim is refused --
    # and the refusal is reported rather than silently swallowed.
    second = apply_handoff(store, text, provider="claude", actor="claude")
    assert second["accepted"] == []
    assert second["refused"], "a replayed handoff must be visibly refused"
