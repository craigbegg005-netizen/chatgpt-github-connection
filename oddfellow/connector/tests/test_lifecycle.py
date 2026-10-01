"""Tests for provider connect/disconnect and dead-letter behaviour.

Both features exist because of a specific way this system fails quietly:

  * a "disconnect" that leaves tokens working and jobs stranded is a label, not a
    change;
  * a terminal failure nobody can see or revive is a job that has silently ceased
    to exist.

So these tests assert the consequences, not the calls.
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from connector import (  # noqa: E402
    AuthError,
    ClaimRefused,
    Job,
    Risk,
    Scope,
    Status,
    Store,
    TaskKind,
    TokenStore,
    Transport,
    connect_provider,
    disconnect_provider,
    new_job_id,
)

MASTER = "owner-master-token-value"


def job(title, risk=Risk.LOW):
    payload = {"spec": title}
    return Job(
        job_id=new_job_id(TaskKind.CODE, title, payload),
        kind=TaskKind.CODE,
        title=title,
        payload=payload,
        risk=risk,
        max_attempts=1,
    )


@pytest.fixture()
def store():
    s = Store(":memory:")
    yield s
    s.close()


@pytest.fixture()
def tokens(store):
    return TokenStore(store._conn, owner_token=MASTER)


# ------------------------------------------------------------------ connecting


def test_connect_returns_a_token_once_and_a_safe_summary(tokens):
    plaintext, summary = connect_provider(tokens, "claude", {Scope.READ}, note="phase B")
    assert plaintext.startswith("odf_")
    assert summary["provider"] == "claude"
    assert summary["scopes"] == ["read"]
    assert plaintext not in str(summary), "the summary must be safe to log"


# ---------------------------------------------------------------- disconnecting


def test_disconnect_revokes_every_token_for_that_provider(store, tokens):
    a, _ = connect_provider(tokens, "claude", {Scope.READ})
    b, _ = connect_provider(tokens, "claude", {Scope.CLAIM, Scope.SUBMIT})
    other, _ = connect_provider(tokens, "gemini", {Scope.READ})

    report = disconnect_provider(store, tokens, "claude", actor="owner", reason="rotating")
    assert len(report.tokens_revoked) == 2
    assert report.clean

    for dead in (a, b):
        with pytest.raises(AuthError) as exc:
            tokens.verify(dead, Scope.READ)
        assert exc.value.code == "token_revoked"

    # A different provider is untouched.
    assert tokens.verify(other, Scope.READ).provider == "gemini"


def test_disconnect_releases_claims_so_the_work_is_reachable_again(store, tokens):
    connect_provider(tokens, "claude", {Scope.READ})
    j = job("half-done work")
    store.create_job(j, actor="x")
    store.claim_job(j.job_id, "claude", Transport.HANDOFF, actor="claude")
    assert store.get_job(j.job_id).status is Status.RUNNING

    report = disconnect_provider(store, tokens, "claude", actor="owner", reason="gone")
    assert report.claims_released == [j.job_id]
    after = store.get_job(j.job_id)
    assert after.status is Status.READY
    assert after.provider is None
    # And another provider can now take it.
    store.claim_job(j.job_id, "letta", Transport.API, actor="letta")
    assert store.get_job(j.job_id).provider == "letta"


def test_disconnect_does_not_touch_another_providers_claims(store, tokens):
    connect_provider(tokens, "claude", {Scope.READ})
    mine = job("claude's job")
    theirs = job("letta's job")
    store.create_job(mine, actor="x")
    store.create_job(theirs, actor="x")
    store.claim_job(mine.job_id, "claude", Transport.HANDOFF, actor="claude")
    store.claim_job(theirs.job_id, "letta", Transport.API, actor="letta")

    report = disconnect_provider(store, tokens, "claude", actor="owner")
    assert report.claims_released == [mine.job_id]
    assert store.get_job(theirs.job_id).provider == "letta"


def test_disconnect_is_audited(store, tokens):
    connect_provider(tokens, "claude", {Scope.READ})
    disconnect_provider(store, tokens, "claude", actor="owner", reason="owner revoked access")
    trail = store.audit_trail(limit=20)
    entry = next(e for e in trail if e["event"] == "provider.disconnected")
    assert "owner revoked access" in entry["detail"]


def test_disconnect_is_idempotent(store, tokens):
    connect_provider(tokens, "claude", {Scope.READ})
    first = disconnect_provider(store, tokens, "claude", actor="owner")
    second = disconnect_provider(store, tokens, "claude", actor="owner")
    assert len(first.tokens_revoked) == 1
    assert second.tokens_revoked == []
    assert second.clean


def test_disconnect_of_an_unknown_provider_is_harmless(store, tokens):
    report = disconnect_provider(store, tokens, "nobody", actor="owner")
    assert report.clean and report.tokens_revoked == [] and report.claims_released == []


# ---------------------------------------------------------------- dead letters


def test_a_terminal_failure_becomes_visible_as_a_dead_letter(store):
    j = job("will fail")
    store.create_job(j, actor="x")
    store.claim_job(j.job_id, "letta", Transport.API, actor="letta")
    store.fail_job(j.job_id, "permanent fault", actor="letta")
    assert store.get_job(j.job_id).status is Status.FAILED_TERMINAL

    report = store.dead_letter_report()
    assert report["count"] == 1
    assert report["jobs"][0]["job_id"] == j.job_id
    assert report["jobs"][0]["error"] == "permanent fault"


def test_dead_letters_are_not_claimable(store):
    j = job("dead")
    store.create_job(j, actor="x")
    store.claim_job(j.job_id, "letta", Transport.API, actor="letta")
    store.fail_job(j.job_id, "boom", actor="letta")
    with pytest.raises(ClaimRefused):
        store.claim_job(j.job_id, "letta", Transport.API, actor="letta")


def test_requeue_revives_a_dead_letter_with_a_reason(store):
    j = job("revivable")
    store.create_job(j, actor="x")
    store.claim_job(j.job_id, "letta", Transport.API, actor="letta")
    store.fail_job(j.job_id, "transient-looking", actor="letta")

    revived = store.requeue(j.job_id, actor="owner", reason="the upstream fault was fixed")
    assert revived.status is Status.READY
    assert revived.attempts == 0
    assert revived.provider is None
    assert store.dead_letter_report()["count"] == 0
    assert [x.job_id for x in store.ready_jobs()] == [j.job_id]


def test_requeue_requires_a_reason(store):
    j = job("needs a reason")
    store.create_job(j, actor="x")
    store.claim_job(j.job_id, "letta", Transport.API, actor="letta")
    store.fail_job(j.job_id, "boom", actor="letta")
    for empty in ("", "   ", None):
        with pytest.raises(ValueError):
            store.requeue(j.job_id, actor="owner", reason=empty)
    assert store.get_job(j.job_id).status is Status.FAILED_TERMINAL


def test_cannot_requeue_a_job_that_has_not_failed_terminally(store):
    j = job("still fine")
    store.create_job(j, actor="x")
    with pytest.raises(ValueError):
        store.requeue(j.job_id, actor="owner", reason="because")


def test_release_claim_requires_a_running_job(store):
    j = job("not running")
    store.create_job(j, actor="x")
    with pytest.raises(ValueError):
        store.release_claim(j.job_id, actor="owner", reason="nope")
