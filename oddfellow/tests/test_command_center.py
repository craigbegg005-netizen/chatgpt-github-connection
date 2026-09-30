"""
Tests for the Begg AI Command Center (command_center.py, mounted by the backend).

Offline and free: no network, no API key. The point of these tests is the
*security and fail-closed* behaviour, not the shape of the JSON — a private
owner-only surface is only private if every route enforces that, including the
ones added later, which is why the auth test enumerates the routes from the
OpenAPI document rather than listing them by hand.

    python -m pytest oddfellow/tests -q
"""

import importlib
import os
import sys

import pytest
from fastapi.testclient import TestClient

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, APP_DIR)
MODULE = "oddfellow_letta_backend"

OWNER_TOKEN = "test-owner-token"
AGENT_ID = "agent-00000000-0000-0000-0000-000000000001"

BASE_ENV = {
    "LETTA_API_KEY": "test-key-not-real",
    "ODDFELLOW_OWNER_TOKEN": OWNER_TOKEN,
    "LETTA_MODEL": "letta/auto",
    "ODDFELLOW_AGENT_ID": AGENT_ID,
}

ALL_ENV = [
    "LETTA_API_KEY", "ODDFELLOW_OWNER_TOKEN", "LETTA_MODEL", "ODDFELLOW_AGENT_ID",
    "ALLOWED_ORIGIN", "LETTA_BASE_URL", "ODDFELLOW_ALLOW_PAID_MODEL",
    "ODDFELLOW_RATE_PER_MIN", "ODDFELLOW_FRONTEND_DIR", "ODDFELLOW_AUDIT_LOG",
    "ODDFELLOW_MAX_BODY_BYTES",
]

AUTH = {"X-Owner-Token": OWNER_TOKEN}


def load_app(monkeypatch, **overrides):
    for key in ALL_ENV:
        monkeypatch.delenv(key, raising=False)
    for key, value in {**BASE_ENV, **overrides}.items():
        if value is not None:
            monkeypatch.setenv(key, value)
    if MODULE in sys.modules:
        return importlib.reload(sys.modules[MODULE])
    return importlib.import_module(MODULE)


@pytest.fixture()
def app(monkeypatch):
    return load_app(monkeypatch)


@pytest.fixture()
def client(app):
    # `app` is the reloaded *module*; the ASGI application is its `app` attribute.
    return TestClient(app.app)


def command_routes(client):
    """Every /api/command path and the methods it actually accepts, from OpenAPI.

    Enumerated rather than hard-coded so a route added later is covered by the
    auth test automatically. A hand-written list silently stops covering the
    surface it was written to protect. The methods come from the spec too: calling
    GET on a POST-only route returns 405, which is not an auth failure and would
    make this test lie in the other direction.
    """
    spec = client.get("/openapi.json").json()
    return sorted(
        (path, sorted(m.upper() for m in ops))
        for path, ops in spec["paths"].items()
        if path.startswith("/api/command")
    )


# --------------------------------------------------------------------------- #
# It is private
# --------------------------------------------------------------------------- #

def test_command_routes_exist(client):
    routes = dict(command_routes(client))
    assert "/api/command/status" in routes
    assert "/api/command/pause" in routes
    assert len(routes) >= 5


def test_every_command_route_requires_the_owner_token(client):
    """No anonymous read path, and no weaker token for 'just looking'."""
    for path, methods in command_routes(client):
        concrete = path.replace("{approval_id}", "apr-does-not-exist")
        for method in methods:
            call = getattr(client, method.lower())
            kwargs = {"json": {}} if method in ("POST", "PUT", "PATCH") else {}
            assert call(concrete, **kwargs).status_code == 401, (method, path, "no token")
            assert call(concrete, headers={"X-Owner-Token": "wrong"}, **kwargs).status_code == 401, \
                (method, path, "wrong token")


def test_status_reports_the_company(client):
    body = client.get("/api/command/status", headers=AUTH).json()
    assert body["service"] == "begg_ai_command_center"
    assert body["paused"] is False
    assert len(body["departments"]) == 12
    assert len(body["lanes"]) >= 8
    assert body["approvals_pending"] == 0
    # The state trade is stated, not hidden.
    assert "does not survive a restart" in body["state_persistence"]


def test_peace_lane_is_marked_separate(client):
    lanes = client.get("/api/command/status", headers=AUTH).json()["lanes"]
    peace = [l for l in lanes if "Peace" in l["name"]]
    assert peace, "the Peace Framework lane should be visible"
    assert "SEPARATE PROJECT" in peace[0]["note"]


# --------------------------------------------------------------------------- #
# Approvals
# --------------------------------------------------------------------------- #

def test_approval_lifecycle(client):
    created = client.post(
        "/api/command/approvals",
        headers=AUTH,
        json={"title": "Deploy Oddfellow", "detail": "Render", "risk": "high"},
    )
    assert created.status_code == 200
    record = created.json()
    assert record["state"] == "WAITING_AUTHORIZATION"
    assert record["id"].startswith("apr-")

    listed = client.get("/api/command/approvals", headers=AUTH).json()["approvals"]
    assert [r["id"] for r in listed] == [record["id"]]

    pending = client.get("/api/command/status", headers=AUTH).json()["approvals_pending"]
    assert pending == 1

    decided = client.post(
        f"/api/command/approvals/{record['id']}/decide",
        headers=AUTH,
        json={"decision": "approve", "note": "go"},
    )
    assert decided.status_code == 200
    assert decided.json()["state"] == "APPROVED"
    assert decided.json()["note"] == "go"

    assert client.get("/api/command/status", headers=AUTH).json()["approvals_pending"] == 0


def test_approval_cannot_be_decided_twice(client):
    record = client.post(
        "/api/command/approvals", headers=AUTH, json={"title": "x", "risk": "high"}
    ).json()
    url = f"/api/command/approvals/{record['id']}/decide"
    assert client.post(url, headers=AUTH, json={"decision": "approve"}).status_code == 200
    assert client.post(url, headers=AUTH, json={"decision": "reject"}).status_code == 400


def test_unknown_approval_is_404(client):
    r = client.post(
        "/api/command/approvals/apr-nope/decide", headers=AUTH, json={"decision": "approve"}
    )
    assert r.status_code == 404


@pytest.mark.parametrize("payload", [
    {"title": "", "risk": "high"},
    {"title": "ok", "risk": "enormous"},
    {"risk": "high"},
])
def test_bad_approval_payload_is_400(client, payload):
    assert client.post("/api/command/approvals", headers=AUTH, json=payload).status_code == 400


# --------------------------------------------------------------------------- #
# The pause switch has to actually stop things
# --------------------------------------------------------------------------- #

def test_pause_stops_the_message_endpoint(client):
    """An emergency stop that does not stop is worse than none, because it is trusted."""
    ok = client.post("/api/command/pause", headers=AUTH, json={"paused": True, "reason": "stop"})
    assert ok.status_code == 200
    assert ok.json() == {"paused": True, "reason": "stop"}

    blocked = client.post("/api/letta/message", headers=AUTH, json={"input": "hello"})
    assert blocked.status_code == 503
    assert blocked.json()["detail"]["error"] == "paused_by_owner"
    assert blocked.json()["detail"]["reason"] == "stop"

    # The owner can still see why, and can still release it.
    assert client.get("/api/command/status", headers=AUTH).json()["paused"] is True
    released = client.post("/api/command/pause", headers=AUTH, json={"paused": False})
    assert released.json() == {"paused": False, "reason": ""}
    assert client.post("/api/letta/message", headers=AUTH, json={"input": "hello"}).status_code != 503


def test_pause_is_audited(client, capsys):
    client.post("/api/command/pause", headers=AUTH, json={"paused": True, "reason": "drill"})
    out = capsys.readouterr().out
    assert "command_pause" in out
    assert "drill" in out


def test_pause_does_not_need_a_restart_to_take_effect(client):
    """The switch is read per request, so it cannot be stale."""
    assert client.post("/api/letta/message", headers=AUTH, json={"input": "x"}).status_code != 503
    client.post("/api/command/pause", headers=AUTH, json={"paused": True})
    assert client.post("/api/letta/message", headers=AUTH, json={"input": "x"}).status_code == 503


def test_the_audit_endpoint_can_actually_return_something(client):
    """It could not, and that is the point of this test.

    `remember()` existed and nothing ever called it, so /api/command/audit
    returned {"records": []} no matter what the owner did. An endpoint whose
    result cannot vary is worse than no endpoint: it reads as a clean audit.
    Found by pausing the service and then asking what the audit said.
    """
    before = client.get("/api/command/audit", headers=AUTH).json()["records"]
    assert before == []

    r = client.post("/api/command/pause", headers=AUTH,
                    json={"paused": True, "reason": "audit regression test"})
    assert r.status_code == 200

    records = client.get("/api/command/audit", headers=AUTH).json()["records"]
    assert records, "a control-surface action must be readable back from the audit"
    assert records[-1]["event"] == "command_pause"
    assert records[-1]["paused"] is True
    assert records[-1]["reason"] == "audit regression test"

    # Leave the service unpaused so this test cannot affect another one.
    client.post("/api/command/pause", headers=AUTH, json={"paused": False, "reason": ""})


def test_an_approval_decision_is_audited(client):
    created = client.post("/api/command/approvals", headers=AUTH,
                          json={"title": "audit test", "detail": "d", "risk": "high"}).json()
    client.post("/api/command/approvals/%s/decide" % created["id"], headers=AUTH,
                json={"decision": "approve", "note": "n"})
    events = [r["event"] for r in client.get("/api/command/audit", headers=AUTH).json()["records"]]
    assert "command_approval_created" in events
    assert "command_approval_decided" in events
