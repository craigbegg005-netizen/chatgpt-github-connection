"""
Offline test suite for oddfellow_letta_backend.

Runs with NO network access and no API key: every Letta call is intercepted by a
fake transport, so the suite is free, fast, and safe to run in CI or on a phone-
adjacent machine. It verifies the contract the backend promises, including the
fail-closed paths and the workarounds for the known Letta API quirks.

    pip install -r requirements-dev.txt
    python -m pytest oddfellow/tests -v
"""

import asyncio
import importlib
import os
import sys
import time

import pytest
from fastapi.testclient import TestClient

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, APP_DIR)
MODULE = "oddfellow_letta_backend"

OWNER_TOKEN = "test-owner-token"
AGENT_ID = "agent-00000000-0000-0000-0000-000000000001"
CONV_ID = "conv-00000000-0000-0000-0000-000000000002"

BASE_ENV = {
    "LETTA_API_KEY": "test-key-not-real",
    "ODDFELLOW_OWNER_TOKEN": OWNER_TOKEN,
    "LETTA_MODEL": "letta/auto",
    "ODDFELLOW_AGENT_ID": AGENT_ID,
}

ALL_ENV = [
    "LETTA_API_KEY", "ODDFELLOW_OWNER_TOKEN", "LETTA_MODEL", "ODDFELLOW_AGENT_ID",
    "ALLOWED_ORIGIN", "LETTA_BASE_URL", "ODDFELLOW_ALLOW_PAID_MODEL",
    "ODDFELLOW_RATE_PER_MIN", "ODDFELLOW_FRONTEND_DIR",
]


def load_app(monkeypatch, **overrides):
    """Import (or re-import) the app with a controlled environment."""
    for key in ALL_ENV:
        monkeypatch.delenv(key, raising=False)
    for key, value in {**BASE_ENV, **overrides}.items():
        if value is not None:
            monkeypatch.setenv(key, value)
    if MODULE in sys.modules:
        return importlib.reload(sys.modules[MODULE])
    return importlib.import_module(MODULE)


# --------------------------------------------------------------------------- #
# Fake Letta transport
# --------------------------------------------------------------------------- #

class LettaError(Exception):
    def __init__(self, status, detail):
        self.status = status
        self.detail = detail


def sse(*events):
    body = "".join("data: %s\n\n" % e for e in events) + "data: [DONE]\n\n"
    return body


ASSISTANT_TURN = sse(
    '{"message_type":"assistant_message","content":"I am Oddfellow."}',
    '{"message_type":"stop_reason","stop_reason":"end_turn"}',
    '{"message_type":"usage_statistics","prompt_tokens":10,"completion_tokens":4}',
)


class FakeLetta:
    """Routes (method, path) to canned responses and records every call."""

    def __init__(self, module):
        self.m = module
        self.calls = []
        self.agent = {"id": AGENT_ID, "name": "Oddfellow", "metadata": None,
                      "llm_config": {"handle": "letta/auto", "context_window": 180000}}
        self.search_result = [self.agent]
        self.get_by_id = {AGENT_ID: self.agent}
        self.create_status = 201
        self.create_body = {"id": AGENT_ID}
        self.create_makes_readable = True
        self.conversations = {}
        self.next_conv = 0
        self.message_sse = ASSISTANT_TURN
        self.message_status = 200
        self.fail_models_with = None

    # --- helpers ---
    def _record(self, method, path, json_body, params):
        self.calls.append({"method": method, "path": path,
                           "json": json_body, "params": params})

    def _fail(self, status, detail):
        raise LettaError(status, detail)

    def _json(self, method, path, json_body, params):
        if path.endswith("/v1/models/"):
            if self.fail_models_with:
                self._fail(self.fail_models_with, {"error": "nope"})
            return [{"handle": "letta/auto"}]

        if path.endswith("/v1/agents/search"):
            return {"agents": list(self.search_result), "nextCursor": None}

        # Create must be matched BEFORE the get-by-id branch, because the create
        # path "/v1/agents/" also starts with "/v1/agents/".
        if path.rstrip("/").endswith("/v1/agents") and method == "POST":
            if self.create_status >= 400:
                self._fail(self.create_status, {"error": "You have reached your limit "
                                                "for agents, please upgrade your plan "
                                                "or delete some agents", "limit": 3})
            if not self.create_makes_readable:
                # 201 accepted, but the agent is unreadable afterwards (real quirk).
                return self.create_body
            self.get_by_id[self.create_body["id"]] = self.agent
            return self.create_body

        if path.startswith("/v1/agents/"):
            agent_id = path.split("/v1/agents/")[1].split("/")[0]
            if agent_id in self.get_by_id:
                return self.get_by_id[agent_id]
            self._fail(404, {"error": "Not found", "message": "Agent not found"})

        if path.endswith("/v1/conversations/"):
            self.next_conv += 1
            conv_id = "conv-00000000-0000-0000-0000-%012d" % self.next_conv
            self.conversations[conv_id] = {"id": conv_id, "agent_id": agent_id_of(params)}
            return self.conversations[conv_id]

        if "/v1/conversations/" in path:
            conv_id = path.split("/v1/conversations/")[1].split("/")[0]
            if conv_id not in self.conversations:
                self._fail(404, {"error": "Not found", "message": "Conversation not found"})
            return self.conversations[conv_id]

        self._fail(404, {"error": "unhandled fake path", "path": path})

    def _text(self, method, path, json_body, params):
        if path.endswith("/messages"):
            if self.message_status >= 400:
                self._fail(self.message_status, {"error": "boom"})
            return self.message_sse
        self._fail(404, {"error": "unhandled fake raw path", "path": path})

    # --- wired into the module ---
    async def letta(self, method, path, json_body=None, params=None):
        self._record(method, path, json_body, params)
        return self._json(method, path, json_body, params)

    async def letta_raw(self, method, path, json_body=None, params=None):
        self._record(method, path, json_body, params)
        return self._text(method, path, json_body, params)


def agent_id_of(params):
    return (params or {}).get("agent_id", AGENT_ID)


@pytest.fixture
def fake(monkeypatch):
    m = load_app(monkeypatch)
    f = FakeLetta(m)
    monkeypatch.setattr(m, "letta", f.letta)
    monkeypatch.setattr(m, "letta_raw", f.letta_raw)
    monkeypatch.setattr(m, "LettaError", LettaError)
    return m, f, TestClient(m.app, raise_server_exceptions=False)


def auth():
    return {"X-Owner-Token": OWNER_TOKEN}


# --------------------------------------------------------------------------- #
# Configuration is fail-closed
# --------------------------------------------------------------------------- #

def test_missing_api_key_refuses_to_serve(monkeypatch):
    m = load_app(monkeypatch, LETTA_API_KEY=None)
    client = TestClient(m.app)
    r = client.get("/api/letta/status", headers=auth())
    assert r.status_code == 503
    assert "LETTA_API_KEY is not set" in str(r.json()["detail"]["problems"])


def test_missing_owner_token_refuses_to_serve(monkeypatch):
    m = load_app(monkeypatch, ODDFELLOW_OWNER_TOKEN=None)
    r = TestClient(m.app).get("/api/letta/status", headers=auth())
    assert r.status_code == 503


def test_missing_model_refuses_to_guess(monkeypatch):
    m = load_app(monkeypatch, LETTA_MODEL=None)
    r = TestClient(m.app).get("/api/letta/status", headers=auth())
    assert r.status_code == 503
    assert "refusing to guess a model" in str(r.json()["detail"]["problems"])


def test_paid_model_is_blocked_by_zero_spend_doctrine(monkeypatch):
    m = load_app(monkeypatch, LETTA_MODEL="openai/gpt-5")
    r = TestClient(m.app).get("/api/letta/status", headers=auth())
    assert r.status_code == 503
    assert "zero-spend" in str(r.json()["detail"]["problems"]).lower()


def test_paid_model_allowed_only_with_explicit_opt_in(monkeypatch):
    m = load_app(monkeypatch, LETTA_MODEL="openai/gpt-5",
                 ODDFELLOW_ALLOW_PAID_MODEL="true")
    r = TestClient(m.app).get("/api/letta/status", headers=auth())
    assert r.status_code == 200


def test_healthz_needs_no_auth(fake):
    m, f, client = fake
    assert client.get("/healthz").status_code == 200


def test_healthz_is_ok_when_configured(fake):
    m, f, client = fake
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json()["ok"] is True
    assert r.json()["checks_failed"] == []


def test_healthz_names_the_missing_keys_without_values(monkeypatch):
    """The 2026-09-30 outage: deployed and serving, but undiagnosable from outside."""
    m = load_app(monkeypatch, LETTA_API_KEY=None, ODDFELLOW_OWNER_TOKEN=None)
    r = TestClient(m.app).get("/healthz")
    assert r.status_code == 503, "a service that cannot serve must fail closed"
    body = r.json()
    assert body["ok"] is False
    assert set(body["checks_failed"]) == {"LETTA_API_KEY", "ODDFELLOW_OWNER_TOKEN"}
    # names only -- never the values
    assert "test-owner-token" not in str(body)


def test_healthz_names_a_misconfigured_paid_model(monkeypatch):
    m = load_app(monkeypatch, LETTA_MODEL="openai/gpt-5")
    r = TestClient(m.app).get("/healthz")
    assert r.status_code == 503
    assert r.json()["checks_failed"] == ["ODDFELLOW_ALLOW_PAID_MODEL"]


# --------------------------------------------------------------------------- #
# Authentication
# --------------------------------------------------------------------------- #

def test_missing_token_is_401(fake):
    m, f, client = fake
    assert client.get("/api/letta/status").status_code == 401


def test_wrong_token_is_401(fake):
    m, f, client = fake
    r = client.get("/api/letta/status", headers={"X-Owner-Token": "wrong"})
    assert r.status_code == 401


def test_correct_token_is_200(fake):
    m, f, client = fake
    assert client.get("/api/letta/status", headers=auth()).status_code == 200


# --------------------------------------------------------------------------- #
# Agent resolution
# --------------------------------------------------------------------------- #

def test_status_reports_pinned_agent(fake):
    m, f, client = fake
    body = client.get("/api/letta/status", headers=auth()).json()
    assert body["letta_auth"] is True
    assert body["agent_found"] is True
    assert body["agent_id"] == AGENT_ID
    assert body["agent_name"] == "Oddfellow"


def test_pinned_but_unreadable_agent_fails_loudly(monkeypatch):
    m = load_app(monkeypatch)
    f = FakeLetta(m)
    f.get_by_id = {}
    monkeypatch.setattr(m, "letta", f.letta)
    monkeypatch.setattr(m, "letta_raw", f.letta_raw)
    monkeypatch.setattr(m, "LettaError", LettaError)
    client = TestClient(m.app, raise_server_exceptions=False)

    body = client.get("/api/letta/status", headers=auth()).json()
    assert body["agent_found"] is False
    assert body["agent_error"]["error"] == "pinned_agent_unreadable"


def test_find_by_name_uses_search_endpoint_not_list(monkeypatch):
    """The list endpoint always returns [] -- the backend must use search."""
    m = load_app(monkeypatch, ODDFELLOW_AGENT_ID=None)
    f = FakeLetta(m)
    monkeypatch.setattr(m, "letta", f.letta)
    monkeypatch.setattr(m, "letta_raw", f.letta_raw)
    monkeypatch.setattr(m, "LettaError", LettaError)
    TestClient(m.app, raise_server_exceptions=False).get("/api/letta/status", headers=auth())

    paths = [c["path"] for c in f.calls]
    assert any(p.endswith("/v1/agents/search") for p in paths)
    assert not any(p.rstrip("/").endswith("/v1/agents") for p in paths)


def test_402_agent_limit_becomes_409_with_guidance(monkeypatch):
    m = load_app(monkeypatch, ODDFELLOW_AGENT_ID=None)
    f = FakeLetta(m)
    f.search_result = []
    f.create_status = 402
    monkeypatch.setattr(m, "letta", f.letta)
    monkeypatch.setattr(m, "letta_raw", f.letta_raw)
    monkeypatch.setattr(m, "LettaError", LettaError)
    client = TestClient(m.app, raise_server_exceptions=False)

    r = client.post("/api/letta/message", headers=auth(), json={"input": "hi"})
    assert r.status_code == 409
    assert r.json()["detail"]["error"] == "agent_limit_reached"


def test_create_is_never_trusted_without_a_reread(monkeypatch):
    """A 201 can be followed by an unreadable agent. Do not report success."""
    m = load_app(monkeypatch, ODDFELLOW_AGENT_ID=None)
    f = FakeLetta(m)
    f.search_result = []
    f.get_by_id = {}          # nothing is readable, including the id we just "created"
    f.create_status = 201
    f.create_makes_readable = False
    monkeypatch.setattr(m, "letta", f.letta)
    monkeypatch.setattr(m, "letta_raw", f.letta_raw)
    monkeypatch.setattr(m, "LettaError", LettaError)
    client = TestClient(m.app, raise_server_exceptions=False)

    r = client.post("/api/letta/message", headers=auth(), json={"input": "hi"})
    assert r.status_code == 502
    assert r.json()["detail"]["error"] == "created_agent_not_readable"


# --------------------------------------------------------------------------- #
# SSE parsing and messaging
# --------------------------------------------------------------------------- #

def test_parse_sse_extracts_events():
    m = load_app_standalone()
    events = m.parse_sse(ASSISTANT_TURN)
    assert [e["message_type"] for e in events] == [
        "assistant_message", "stop_reason", "usage_statistics"]
    assert events[0]["content"] == "I am Oddfellow."


def test_parse_sse_ignores_done_and_garbage():
    m = load_app_standalone()
    body = "data: [DONE]\n\ndata: not-json\n\ndata: {\"message_type\":\"x\"}\n\n"
    assert m.parse_sse(body) == [{"message_type": "x"}]


def load_app_standalone():
    if MODULE not in sys.modules:
        importlib.import_module(MODULE)
    return sys.modules[MODULE]


def test_message_returns_reply_and_metadata(fake):
    m, f, client = fake
    r = client.post("/api/letta/message", headers=auth(), json={"input": "who are you"})
    assert r.status_code == 200
    body = r.json()
    assert body["reply"] == "I am Oddfellow."
    assert body["agent_id"] == AGENT_ID
    assert body["stop_reason"] == "end_turn"
    assert body["usage"]["completion_tokens"] == 4


def test_message_is_sent_to_the_conversation_scoped_route(fake):
    """The agent default conversation has a cached prompt; use our own."""
    m, f, client = fake
    client.post("/api/letta/message", headers=auth(), json={"input": "hi"})
    msg_calls = [c for c in f.calls if c["path"].endswith("/messages")]
    assert msg_calls, "no message call was made"
    assert "/v1/conversations/" in msg_calls[-1]["path"]
    assert "/v1/agents/" not in msg_calls[-1]["path"]


def test_missing_assistant_message_does_not_invent_a_reply(fake):
    m, f, client = fake
    f.message_sse = sse('{"message_type":"stop_reason","stop_reason":"max_steps"}')
    r = client.post("/api/letta/message", headers=auth(), json={"input": "hi"})
    assert r.status_code == 502
    assert r.json()["detail"]["error"] == "no_assistant_message"


def test_empty_input_is_rejected(fake):
    m, f, client = fake
    r = client.post("/api/letta/message", headers=auth(), json={"input": ""})
    assert r.status_code == 422


# --------------------------------------------------------------------------- #
# Conversation handling
# --------------------------------------------------------------------------- #

def test_conversation_id_is_persisted_to_agent_metadata(fake):
    m, f, client = fake
    client.post("/api/letta/message", headers=auth(), json={"input": "hi"})
    patches = [c for c in f.calls if c["method"] == "PATCH"]
    assert patches, "conversation id was not persisted"
    assert "oddfellow_conversation_id" in patches[-1]["json"]["metadata"]


def test_existing_conversation_is_reused_across_calls(fake):
    m, f, client = fake
    first = client.post("/api/letta/message", headers=auth(), json={"input": "a"}).json()
    f.agent["metadata"] = {"oddfellow_conversation_id": first["conversation_id"]}
    f.conversations[first["conversation_id"]] = {"id": first["conversation_id"]}
    second = client.post("/api/letta/message", headers=auth(), json={"input": "b"}).json()
    assert second["conversation_id"] == first["conversation_id"]


def test_stale_conversation_id_is_replaced(fake):
    m, f, client = fake
    f.agent["metadata"] = {"oddfellow_conversation_id": "conv-gone"}
    body = client.post("/api/letta/message", headers=auth(), json={"input": "a"}).json()
    assert body["conversation_id"] != "conv-gone"


def test_new_session_creates_a_conversation(fake):
    m, f, client = fake
    r = client.post("/api/letta/new-session", headers=auth())
    assert r.status_code == 200
    assert r.json()["conversation_id"].startswith("conv-")


# --------------------------------------------------------------------------- #
# Rate limiting
# --------------------------------------------------------------------------- #

def test_rate_limit_returns_429(monkeypatch):
    m = load_app(monkeypatch, ODDFELLOW_RATE_PER_MIN="2")
    f = FakeLetta(m)
    monkeypatch.setattr(m, "letta", f.letta)
    monkeypatch.setattr(m, "letta_raw", f.letta_raw)
    monkeypatch.setattr(m, "LettaError", LettaError)
    client = TestClient(m.app, raise_server_exceptions=False)

    codes = [client.post("/api/letta/message", headers=auth(),
                         json={"input": "hi"}).status_code for _ in range(3)]
    assert codes[:2] == [200, 200]
    assert codes[2] == 429


# --------------------------------------------------------------------------- #
# Secrets hygiene
# --------------------------------------------------------------------------- #

def test_status_never_echoes_the_api_key(fake):
    m, f, client = fake
    raw = client.get("/api/letta/status", headers=auth()).text
    assert "test-key-not-real" not in raw
    assert OWNER_TOKEN not in raw


# --------------------------------------------------------------------------- #
# CORS (v0.20.4)
# --------------------------------------------------------------------------- #

def test_single_allowed_origin_still_works(monkeypatch):
    """Backwards compatibility: one origin behaves exactly as it did before."""
    m = load_app(monkeypatch, ALLOWED_ORIGIN="https://oddfellow.example.com")
    assert m.ALLOWED_ORIGINS == ["https://oddfellow.example.com"]


def test_allowed_origin_accepts_a_comma_separated_list(monkeypatch):
    m = load_app(
        monkeypatch,
        ALLOWED_ORIGIN="https://oddfellow.example.com, http://localhost:8080",
    )
    assert m.ALLOWED_ORIGINS == [
        "https://oddfellow.example.com",
        "http://localhost:8080",
    ]


def test_allowed_origin_ignores_blanks_and_trailing_slashes(monkeypatch):
    m = load_app(monkeypatch, ALLOWED_ORIGIN=" https://a.example.com/ ,, ,http://b.test ")
    assert m.ALLOWED_ORIGINS == ["https://a.example.com", "http://b.test"]


def test_no_allowed_origin_means_no_cors_middleware(monkeypatch):
    """Unset must stay unset -- never silently allow every origin."""
    m = load_app(monkeypatch, ALLOWED_ORIGIN=None)
    assert m.ALLOWED_ORIGINS == []


def test_preflight_succeeds_for_each_listed_origin(monkeypatch):
    m = load_app(
        monkeypatch,
        ALLOWED_ORIGIN="https://oddfellow.example.com,http://localhost:8080",
    )
    f = FakeLetta(m)
    monkeypatch.setattr(m, "letta", f.letta)
    monkeypatch.setattr(m, "letta_raw", f.letta_raw)
    monkeypatch.setattr(m, "LettaError", LettaError)
    client = TestClient(m.app, raise_server_exceptions=False)

    for origin in m.ALLOWED_ORIGINS:
        r = client.options(
            "/api/letta/status",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "x-owner-token",
            },
        )
        assert r.status_code == 200, origin
        assert r.headers.get("access-control-allow-origin") == origin


def test_preflight_rejects_an_unlisted_origin(monkeypatch):
    m = load_app(monkeypatch, ALLOWED_ORIGIN="https://oddfellow.example.com")
    f = FakeLetta(m)
    monkeypatch.setattr(m, "letta", f.letta)
    monkeypatch.setattr(m, "letta_raw", f.letta_raw)
    monkeypatch.setattr(m, "LettaError", LettaError)
    client = TestClient(m.app, raise_server_exceptions=False)

    r = client.options(
        "/api/letta/status",
        headers={
            "Origin": "https://evil.example.com",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert r.headers.get("access-control-allow-origin") is None


def test_status_reports_allowed_origins_so_cors_is_diagnosable(fake):
    """A browser 'Failed to fetch' must be tellable apart from a dead backend."""
    m, f, client = fake
    body = client.get("/api/letta/status", headers=auth()).json()
    assert "allowed_origins" in body
    assert isinstance(body["allowed_origins"], list)


# --------------------------------------------------------------------------- #
# Optional single-service mode (v0.20.4)
# --------------------------------------------------------------------------- #

def test_frontend_is_not_served_by_default(fake):
    """Off unless asked for: this must not change the deployed behaviour."""
    m, f, client = fake
    assert client.get("/").status_code == 404


def test_frontend_dir_that_does_not_exist_is_ignored(monkeypatch):
    m = load_app(monkeypatch, ODDFELLOW_FRONTEND_DIR="/nonexistent/frontend/dir")
    f = FakeLetta(m)
    monkeypatch.setattr(m, "letta", f.letta)
    monkeypatch.setattr(m, "letta_raw", f.letta_raw)
    monkeypatch.setattr(m, "LettaError", LettaError)
    client = TestClient(m.app, raise_server_exceptions=False)
    assert client.get("/").status_code == 404


def test_frontend_dir_serves_the_page_without_shadowing_the_api(monkeypatch, tmp_path):
    (tmp_path / "index.html").write_text("<title>Oddfellow</title>", encoding="utf-8")
    m = load_app(monkeypatch, ODDFELLOW_FRONTEND_DIR=str(tmp_path))
    f = FakeLetta(m)
    monkeypatch.setattr(m, "letta", f.letta)
    monkeypatch.setattr(m, "letta_raw", f.letta_raw)
    monkeypatch.setattr(m, "LettaError", LettaError)
    client = TestClient(m.app, raise_server_exceptions=False)

    # The page is served at the root...
    root = client.get("/")
    assert root.status_code == 200
    assert "Oddfellow" in root.text

    # ...and the API and health check are still reachable underneath it.
    assert client.get("/healthz").status_code == 200
    assert client.get("/api/letta/status", headers=auth()).status_code == 200
    assert client.get("/api/letta/status").status_code == 401


# --------------------------------------------------------------------------- #
# Regressions from the 2026-09-30 GATE 3 security review
# --------------------------------------------------------------------------- #

class _StubRequest:
    """Just enough Request for client_key()."""

    def __init__(self, host):
        self.client = type("C", (), {"host": host})()


def test_oversized_body_is_rejected_before_it_is_parsed(monkeypatch):
    """Over the limit -> 413, even with no token at all.

    FastAPI parses the body before the route function runs, so require_owner()
    cannot protect the parser. An unauthenticated caller could previously make
    the service buffer and JSON-parse an arbitrarily large body and get a 422
    back for the trouble.
    """
    m = load_app(monkeypatch)
    client = TestClient(m.app, raise_server_exceptions=False)
    resp = client.post("/api/letta/message", json={"input": "x" * (m.MAX_BODY_BYTES + 1)})
    assert resp.status_code == 413
    assert resp.json()["max_bytes"] == m.MAX_BODY_BYTES


def test_body_within_the_limit_still_reaches_auth(monkeypatch):
    m = load_app(monkeypatch)
    client = TestClient(m.app, raise_server_exceptions=False)
    assert client.post("/api/letta/message", json={"input": "hi"}).status_code == 401


def test_rate_limit_covers_the_read_routes(monkeypatch):
    """The limiter used to guard only /api/letta/message."""
    m = load_app(monkeypatch, ODDFELLOW_RATE_PER_MIN="3")
    f = FakeLetta(m)
    monkeypatch.setattr(m, "letta", f.letta)
    monkeypatch.setattr(m, "letta_raw", f.letta_raw)
    monkeypatch.setattr(m, "LettaError", LettaError)
    client = TestClient(m.app, raise_server_exceptions=False)
    codes = [client.get("/api/letta/status", headers=auth()).status_code for _ in range(5)]
    assert codes[:3] == [200, 200, 200]
    assert codes[3:] == [429, 429]


def test_healthz_is_never_rate_limited(monkeypatch):
    """A platform health check must not be throttled into a false failure."""
    m = load_app(monkeypatch, ODDFELLOW_RATE_PER_MIN="2")
    client = TestClient(m.app, raise_server_exceptions=False)
    assert [client.get("/healthz").status_code for _ in range(6)] == [200] * 6


def test_rate_limit_key_never_contains_the_token(monkeypatch):
    """The limiter keys on a digest, so the token cannot leak through it."""
    m = load_app(monkeypatch)
    key = m.client_key(_StubRequest("1.2.3.4"), OWNER_TOKEN)
    assert OWNER_TOKEN not in key
    assert key.startswith("tok:")
    # With no token it falls back to the peer address rather than crashing.
    assert m.client_key(_StubRequest("1.2.3.4"), None) == "host:1.2.3.4"


def test_rate_limit_map_does_not_grow_without_bound(monkeypatch):
    """Empty windows are swept, so the map cannot grow for the process lifetime."""
    m = load_app(monkeypatch)
    m._hits.clear()
    m.rate_limit("tok:aaaa")
    assert "tok:aaaa" in m._hits
    m._last_sweep = 0.0          # force the next call to sweep
    m._hits["tok:aaaa"].append(time.time() - 3600.0)
    m.rate_limit("tok:bbbb")
    assert "tok:aaaa" not in m._hits


