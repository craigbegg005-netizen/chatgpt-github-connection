"""Phase 3: read-only Command Center visibility of the workforce roster.

These endpoints exist because `/api/command/status` returns `DEPARTMENTS`, a
hand-maintained list of prose whose own note admits the problem: "the claims are
hand-maintained, so read registry_as_of before trusting them -- two of them were
already stale when this date was added." A roster derived from the registry
cannot drift from the registry.

The auth test in `test_command_center.py` enumerates routes from the OpenAPI
document, so these routes are covered there too. What is checked *here* is the
payload and the read-only property.
"""

from __future__ import annotations

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
ALL_ENV = list(BASE_ENV) + [
    "ALLOWED_ORIGIN", "LETTA_BASE_URL", "ODDFELLOW_ALLOW_PAID_MODEL",
    "ODDFELLOW_RATE_PER_MIN", "ODDFELLOW_FRONTEND_DIR", "ODDFELLOW_AUDIT_LOG",
    "ODDFELLOW_MAX_BODY_BYTES",
]
AUTH = {"X-Owner-Token": OWNER_TOKEN}


@pytest.fixture()
def client(monkeypatch):
    for key in ALL_ENV:
        monkeypatch.delenv(key, raising=False)
    for key, value in BASE_ENV.items():
        monkeypatch.setenv(key, value)
    mod = importlib.reload(sys.modules[MODULE]) if MODULE in sys.modules \
        else importlib.import_module(MODULE)
    return TestClient(mod.app)


# ------------------------------------------------------------------- auth


@pytest.mark.parametrize("path", [
    "/api/command/departments", "/api/command/workers",
    "/api/command/workers/eng_backend",
])
def test_requires_the_owner_token(client, path):
    assert client.get(path).status_code == 401
    assert client.get(path, headers={"X-Owner-Token": "wrong"}).status_code == 401


@pytest.mark.parametrize("path", [
    "/api/command/departments", "/api/command/workers",
    "/api/command/workers/eng_backend",
])
def test_serves_with_the_owner_token(client, path):
    assert client.get(path, headers=AUTH).status_code == 200


# ------------------------------------------------------------ departments


def test_departments_lists_all_twelve(client):
    body = client.get("/api/command/departments", headers=AUTH).json()
    assert body["count"] == 12
    assert len(body["departments"]) == 12


def test_every_department_spend_ceiling_is_zero(client):
    """Zero-spend is reported as roster data, not asserted in prose."""
    body = client.get("/api/command/departments", headers=AUTH).json()
    ceilings = {d["department_id"]: d["spend_ceiling_usd"] for d in body["departments"]}
    assert set(ceilings.values()) == {0.0}, ceilings


def test_no_department_holds_a3_or_above(client):
    """Consequential authority stays with the owner; the registry is the source."""
    body = client.get("/api/command/departments", headers=AUTH).json()
    assert body["max_authority"] == "A2"
    assert all(d["authority"] in ("A0", "A1", "A2") for d in body["departments"])


def test_department_capabilities_carry_their_required_authority(client):
    """A capability and its authority are separate on purpose; the payload keeps
    them separate so a reader can see what each one costs."""
    body = client.get("/api/command/departments", headers=AUTH).json()
    caps = body["departments"][0]["capabilities"]
    assert caps and all("name" in c and "required_authority" in c for c in caps)


def test_departments_says_it_is_derived_not_hand_maintained(client):
    body = client.get("/api/command/departments", headers=AUTH).json()
    assert "not hand-maintained" in body["source"]


# ---------------------------------------------------------------- workers


def test_workers_lists_all_twenty_eight(client):
    body = client.get("/api/command/workers", headers=AUTH).json()
    assert body["count"] == 28


def test_workers_can_be_filtered_by_department(client):
    body = client.get("/api/command/workers?department_id=engineering", headers=AUTH).json()
    assert body["count"] > 0
    assert all(w["department_id"] == "engineering" for w in body["workers"])


def test_an_unknown_department_filters_to_nothing_not_to_everything(client):
    """A filter that silently ignores an unknown value would show the whole
    roster under a heading that says otherwise."""
    body = client.get("/api/command/workers?department_id=nope", headers=AUTH).json()
    assert body["count"] == 0
    assert body["workers"] == []


def test_verifiers_are_identifiable_from_the_payload(client):
    body = client.get("/api/command/workers", headers=AUTH).json()
    verifiers = {w["worker_id"] for w in body["workers"] if w["can_verify"]}
    assert verifiers == {"qa_claim_verifier", "qa_evidence_reviewer", "qa_adversarial"}


def test_no_worker_spends(client):
    body = client.get("/api/command/workers", headers=AUTH).json()
    assert {w["spend_ceiling_usd"] for w in body["workers"]} == {0.0}


# --------------------------------------------------------- worker detail


def test_worker_detail_returns_the_roster_entry(client):
    body = client.get("/api/command/workers/eng_backend", headers=AUTH).json()
    assert body["found"] is True
    assert body["worker_id"] == "eng_backend"
    assert body["department_id"] == "engineering"
    assert body["authority"] in ("A0", "A1", "A2")


def test_an_unknown_worker_is_not_found_and_says_why(client):
    body = client.get("/api/command/workers/nobody_here", headers=AUTH).json()
    assert body["found"] is False
    assert "lowercase" in body["error"]


def test_a_near_miss_worker_id_is_not_found(client):
    """Ids are validated, not compared near: `ENG_BACKEND` is a different
    identity, not a case variant of one."""
    body = client.get("/api/command/workers/ENG_BACKEND", headers=AUTH).json()
    assert body["found"] is False


# ------------------------------------------------------------- read-only


def test_only_get_is_offered_on_the_workforce_routes(client):
    """The control surface reports the roster; it does not change it. A surface
    that can alter what it reports is a much larger decision."""
    spec = client.get("/openapi.json").json()["paths"]
    for path in ("/api/command/departments", "/api/command/workers",
                 "/api/command/workers/{worker_id}"):
        assert set(spec[path]) == {"get"}, f"{path} exposes {sorted(spec[path])}"
