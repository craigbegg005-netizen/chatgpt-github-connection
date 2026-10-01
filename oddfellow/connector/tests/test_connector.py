"""Connector tests.

These test the properties that make the connector safe to trust, not merely the
properties that make it work. In particular they assert the *refusals*: that
unapproved high-risk work does not run, that a paid provider is ineligible under
zero-spend, that a declared-but-unverified capability is not routed on, and that
the audit log does not retain payloads. A connector that only ever says yes is
the failure mode, so "it refused correctly" is the assertion that matters most.

Fully offline and deterministic: in-memory SQLite, no network, no keys, no clock
dependence beyond ISO strings.
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from connector import (  # noqa: E402
    Scope,
    Gateway,
    Job,
    Risk,
    Status,
    Store,
    TaskKind,
    TokenStore,
    Transport,
    build_registry,
    choose_transport,
    failover_order,
    new_job_id,
    route,
)


# --------------------------------------------------------------------- helpers


def job(kind=TaskKind.CODE, title="t", risk=Risk.LOW, payload=None, depends_on=()):
    payload = payload if payload is not None else {"spec": title}
    return Job(
        job_id=new_job_id(kind, title, payload),
        kind=kind,
        title=title,
        payload=payload,
        risk=risk,
        depends_on=tuple(depends_on),
    )


def verified_registry(*names, transport=Transport.API):
    """Registry with the named providers marked VERIFIED for `transport`."""
    reg = build_registry()
    for n in names:
        reg[n].verified[transport] = "probe: 200 in 0.01s (test fixture)"
    return reg


@pytest.fixture()
def store():
    s = Store(":memory:")
    yield s
    s.close()


# --------------------------------------------------------------- idempotency


def test_same_job_derived_twice_collapses_to_one(store):
    """Two AIs deriving the same job from one instruction must not double the work."""
    a = job(title="write the handoff")
    b = job(title="write the handoff")
    assert a.job_id == b.job_id

    _, created_first = store.create_job(a, actor="letta")
    existing, created_second = store.create_job(b, actor="chatgpt")

    assert created_first is True
    assert created_second is False
    assert len(store.jobs()) == 1
    assert existing.job_id == a.job_id


def test_different_payload_is_a_different_job(store):
    a = job(title="same title", payload={"x": 1})
    b = job(title="same title", payload={"x": 2})
    assert a.job_id != b.job_id


def test_identical_result_is_recognised_not_duplicated(store):
    """Failover safety: two providers returning the same bytes is ONE outcome."""
    j = job()
    store.create_job(j, actor="letta")
    store.claim_job(j.job_id, "letta", Transport.API, actor="letta")
    _, first_new = store.submit_result(j.job_id, {"answer": 42}, actor="letta")
    assert first_new is True
    assert store.get_job(j.job_id).status is Status.COMPLETE

    # A retry: the job goes back to READY, is claimed again, and produces the same
    # content. That must be recognised as the SAME outcome, not a second one.
    store.set_status(store.get_job(j.job_id), Status.READY, actor="letta")
    store.claim_job(j.job_id, "letta", Transport.API, actor="letta")
    _, second_new = store.submit_result(j.job_id, {"answer": 42}, actor="letta")
    assert second_new is False


def test_key_order_does_not_change_the_result_hash(store):
    j = job()
    store.create_job(j, actor="letta")
    store.claim_job(j.job_id, "letta", Transport.API, actor="letta")
    _, a = store.submit_result(j.job_id, {"a": 1, "b": 2}, actor="x")
    store.set_status(store.get_job(j.job_id), Status.READY, actor="x")
    store.claim_job(j.job_id, "letta", Transport.API, actor="x")
    _, b = store.submit_result(j.job_id, {"b": 2, "a": 1}, actor="y")
    assert a is True and b is False, "key order must not create a second outcome"


# ------------------------------------------------------------- approval gates


@pytest.mark.parametrize("risk", [Risk.HIGH, Risk.CRITICAL])
def test_high_risk_does_not_route_without_approval(risk):
    reg = verified_registry("letta")
    d = route(job(risk=risk), reg)
    assert not d.runnable
    assert d.status is Status.WAITING_AUTHORIZATION


@pytest.mark.parametrize("risk", [Risk.HIGH, Risk.CRITICAL])
def test_high_risk_routes_once_approved(risk):
    reg = verified_registry("letta")
    d = route(job(risk=risk), reg, approved=True)
    assert d.runnable
    assert d.provider == "letta"


def test_low_risk_routes_without_approval():
    reg = verified_registry("letta")
    assert route(job(risk=Risk.LOW), reg).runnable


# --------------------------------------------------------------- emergency stop


def test_pause_blocks_even_safe_work():
    """A stop button with exceptions is not a stop button."""
    reg = verified_registry("letta")
    d = route(job(risk=Risk.LOW), reg, paused=True, pause_reason="owner stopped everything")
    assert not d.runnable
    assert d.status is Status.BLOCKED
    assert "owner stopped everything" in d.reason


def test_pause_survives_a_reopen(tmp_path):
    """A stop button that forgets it was pressed is not a stop button."""
    path = tmp_path / "connector.db"
    s1 = Store(path)
    s1.set_paused(True, actor="owner", reason="incident")
    s1.close()

    s2 = Store(path)
    assert s2.is_paused() is True
    assert s2.pause_reason() == "incident"
    s2.close()


# ------------------------------------------------------------------ zero spend


def test_paid_provider_is_ineligible_under_zero_spend():
    reg = verified_registry("openai")  # openai is declared paid
    d = route(job(), reg)
    assert not d.runnable
    assert "paid" in d.reason


def test_paid_provider_eligible_once_spend_is_approved():
    reg = verified_registry("openai")
    d = route(job(), reg, allow_paid=True)
    assert d.runnable and d.provider == "openai"


def test_free_provider_preferred_over_paid_by_default():
    reg = verified_registry("letta", "openai")
    d = route(job(), reg, preferred=("letta", "openai"))
    assert d.provider == "letta"


# ------------------------------------------------- capability detection honesty


def test_declared_but_unverified_capability_is_not_routed():
    """The central rule: documentation is not observation."""
    reg = build_registry()  # nothing verified
    d = route(job(), reg)
    assert not d.runnable
    assert "no verified transport" in d.reason


def test_verification_makes_a_capability_routable():
    reg = build_registry()
    assert choose_transport(reg["letta"], TaskKind.CODE) is None
    reg["letta"].verified[Transport.API] = "probe: 200"
    assert choose_transport(reg["letta"], TaskKind.CODE) is Transport.API


def test_ladder_prefers_mcp_over_api_when_both_verified():
    reg = build_registry()
    reg["letta"].verified[Transport.API] = "probe"
    reg["letta"].verified[Transport.MCP] = "probe"
    assert choose_transport(reg["letta"], TaskKind.CODE) is Transport.MCP


def test_ladder_falls_through_to_queue_when_only_queue_verified():
    reg = build_registry()
    reg["anthropic"].verified[Transport.QUEUE] = "probe"
    assert choose_transport(reg["anthropic"], TaskKind.CODE) is Transport.QUEUE


# ------------------------------------------------------------------- failover


def test_failover_excludes_the_provider_that_just_failed():
    # allow_paid=True here on purpose: anthropic is a paid provider, so under
    # zero-spend it would be excluded for THAT reason and this test would pass
    # for the wrong one. Isolating the `failed` exclusion is the point.
    reg = verified_registry("letta", "anthropic")
    order = failover_order(job(), reg, failed=("letta",), allow_paid=True)
    assert [p for p, _ in order] == ["anthropic"]


def test_failover_prefers_a_provider_that_can_act_without_a_human():
    reg = verified_registry("letta", "anthropic")
    order = failover_order(job(), reg)
    assert order[0][0] == "letta", "letta polls; anthropic waits for the owner to open a chat"


def test_failover_respects_zero_spend():
    reg = verified_registry("openai", "anthropic")  # both paid
    assert failover_order(job(), reg) == []
    assert [p for p, _ in failover_order(job(), reg, allow_paid=True)]


# ------------------------------------------------------------- dependencies


def test_job_with_unfinished_dependency_is_not_ready(store):
    first = job(title="first")
    second = job(title="second", depends_on=(first.job_id,))
    store.create_job(first, actor="x")
    store.create_job(second, actor="x")
    assert [j.job_id for j in store.ready_jobs()] == [first.job_id]

    store.claim_job(first.job_id, "letta", Transport.API, actor="x")
    store.submit_result(first.job_id, {"done": True}, actor="x")
    assert {j.job_id for j in store.ready_jobs()} == {first.job_id, second.job_id} or (
        second.job_id in {j.job_id for j in store.ready_jobs()}
    )


def test_job_with_missing_dependency_never_becomes_ready(store):
    orphan = job(title="orphan", depends_on=("job-does-not-exist",))
    store.create_job(orphan, actor="x")
    assert list(store.ready_jobs()) == []


# ------------------------------------------------------------------ failures


def test_failure_is_retryable_while_attempts_remain(store):
    j = job()
    store.create_job(j, actor="x")
    store.claim_job(j.job_id, "letta", Transport.API, actor="x")
    assert store.fail_job(j.job_id, "timeout", actor="x").status is Status.FAILED_RETRYABLE


def test_failure_is_terminal_once_attempts_are_exhausted(store):
    j = job()
    j.max_attempts = 1
    store.create_job(j, actor="x")
    store.claim_job(j.job_id, "letta", Transport.API, actor="x")
    assert store.fail_job(j.job_id, "boom", actor="x").status is Status.FAILED_TERMINAL


# ------------------------------------------------------------------ audit log


def test_audit_never_records_payload_or_result(store):
    secret = "OWNER-SECRET-VALUE"
    j = job(title="handle the thing", payload={"token": secret})
    store.create_job(j, actor="x")
    store.claim_job(j.job_id, "letta", Transport.API, actor="x")
    store.submit_result(j.job_id, {"answer": secret}, actor="x")

    trail = store.audit_trail(limit=100)
    blob = repr(trail)
    assert secret not in blob, "the audit log must never retain job content"
    assert "job.create" in blob and "job.result" in blob, "but it must record that they happened"


def test_audit_records_size_not_content(store):
    store.audit("x", "state.set", project="oddfellow", key="k", value="a" * 50)
    detail = store.audit_trail(limit=1)[0]["detail"]
    assert "len=50" in detail
    assert "aaaa" not in detail


# --------------------------------------------------------------- shared state


def test_state_round_trips_and_is_scoped_by_project(store):
    store.set_state("oddfellow", "deploy", {"ready": False}, actor="x")
    store.set_state("peace", "deploy", {"separate": True}, actor="x")
    assert store.get_state("oddfellow", "deploy") == {"ready": False}
    assert store.get_state("peace", "deploy") == {"separate": True}
    assert store.get_state("oddfellow") == {"deploy": {"ready": False}}


def test_state_upsert_keeps_one_row_per_key(store):
    store.set_state("p", "k", 1, actor="x")
    store.set_state("p", "k", 2, actor="y")
    assert store.get_state("p", "k") == 2
    assert store.get_state("p") == {"k": 2}


# --------------------------------------------------------------- MCP gateway


def test_gateway_refuses_by_default(store):
    g = Gateway(store)
    assert g.may_serve() is False
    result = g.call("get_project_state", credential="anything", project="oddfellow")
    assert result["serving"] is False
    assert result["unmet_preconditions"], "it must name what is missing"


def test_gateway_still_refuses_when_enabled_without_preconditions(store):
    g = Gateway(store, enabled=True)
    assert g.may_serve() is False
    assert any("connector token" in u for u in g.unmet_preconditions())


def test_gateway_requires_a_credential_even_when_ready(store):
    tokens = TokenStore(store._conn)
    tokens.issue("anthropic", {Scope.READ})
    g = Gateway(
        store,
        tokens=tokens,
        enabled=True,
        host_origin_allowlisted=True,
        approval_gate_configured=True,
    )
    assert g.may_serve() is True
    refused = g.call("get_project_state", credential=None)
    assert refused["ok"] is False
    assert refused["status"] == 401


def test_gateway_never_accepts_the_owner_master_token_as_a_connector_credential(store):
    """Documented here as an executable fact, not a comment."""
    g = Gateway(store)
    doc = (g.refusal()["note"] + " " + " ".join(g.unmet_preconditions())).lower()
    assert "connector token" in doc

    # The scaffold must have no code path that READS any environment secret. The
    # name is allowed to appear (the precondition text names it, to say it must be
    # distinct); what is forbidden is reading it.
    import inspect

    import connector.gateway as gw

    source = inspect.getsource(gw)
    assert "getenv" not in source
    assert "environ" not in source


def test_mutating_tool_requires_an_approval_gate(store):
    tokens = TokenStore(store._conn)
    tokens.issue("anthropic", {Scope.READ})
    g = Gateway(store, tokens=tokens, enabled=True, host_origin_allowlisted=True)
    assert g.may_serve() is False  # no approval gate yet


def test_tool_surface_is_the_agreed_minimum(store):
    names = {t.name for t in Gateway(store).tools}
    assert names == {
        "get_project_state",
        "list_jobs",
        "claim_job",
        "submit_result",
        "append_audit",
        "request_approval",
    }
