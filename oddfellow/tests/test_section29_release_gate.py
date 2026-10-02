"""§29 release gate — the security checklist, verified against running code.

The universal handoff carries a numbered checklist (§29) that must be satisfied
before the canonical branch is deployed. It is a *list of claims about the
code*, which is exactly the kind of document this project has learned not to
trust: four of the day's five false controls were written in prose that asserted
a discipline the code did not enforce.

So every item is a test here rather than a tick in a document. If an item
regresses, this file fails, and the checklist cannot quietly become true again.

Items marked "not applicable to this layer" are stated as such rather than
silently omitted — an item that is absent from a checklist is indistinguishable
from an item nobody checked.
"""

from __future__ import annotations

import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)

import test_backend as tb  # noqa: E402

auth = tb.auth
fake = tb.fake


def _approve(client, text, risk="high"):
    r = client.post(
        "/api/command/approvals",
        headers=auth(),
        json={"title": "t", "detail": text[:200], "risk": risk, "binding_text": text},
    )
    assert r.status_code == 200, r.text
    aid = r.json()["id"]
    d = client.post(
        f"/api/command/approvals/{aid}/decide",
        headers=auth(),
        json={"decision": "approve", "note": "gate"},
    )
    assert d.status_code == 200, d.text
    return aid


def _send(client, text, approval_id=None, headers=None):
    body = {"input": text}
    if approval_id:
        body["approval_id"] = approval_id
    return client.post("/api/letta/message", headers=headers or auth(), json=body)


# --------------------------------------------------------------------------- #
# The record itself
# --------------------------------------------------------------------------- #

def test_29_approvals_are_persisted_with_an_id(fake):
    m, f, client = fake
    rec = client.post(
        "/api/command/approvals", headers=auth(),
        json={"title": "t", "detail": "d", "risk": "high", "binding_text": "x"},
    ).json()
    assert rec["id"].startswith("apr-")
    # ...and it is readable back, which is what "persisted" has to mean.
    listed = client.get("/api/command/approvals", headers=auth()).json()["approvals"]
    assert rec["id"] in [a["id"] for a in listed]


def test_29_the_record_carries_actor_decision_and_timestamps(fake):
    m, f, client = fake
    rec = client.post(
        "/api/command/approvals", headers=auth(),
        json={"title": "t", "detail": "d", "risk": "high", "binding_text": "x"},
    ).json()
    assert isinstance(rec["created_at"], (int, float))
    assert rec["decided_by"] is None and rec["decided_at"] is None

    decided = client.post(
        f"/api/command/approvals/{rec['id']}/decide", headers=auth(),
        json={"decision": "approve", "note": "gate"},
    ).json()
    assert decided["decided_by"] == "owner"
    assert decided["decision"] == "approve"
    assert isinstance(decided["decided_at"], (int, float))
    assert decided["state"] == "APPROVED"


def test_29_the_binding_is_a_normalized_digest(fake):
    m, f, client = fake
    rec = client.post(
        "/api/command/approvals", headers=auth(),
        json={"title": "t", "detail": "d", "risk": "high", "binding_text": "delete   the  branch"},
    ).json()
    assert len(rec["binding"]) == 64
    # Normalized: a whitespace variant of the same command hashes identically.
    from command_center import binding_hash, normalized_binding_text

    assert binding_hash(normalized_binding_text("delete   the  branch")) == rec["binding"]


# --------------------------------------------------------------------------- #
# Server-side validation and every refusal
# --------------------------------------------------------------------------- #

def test_29_missing_approval_is_refused(fake):
    m, f, client = fake
    r = _send(client, "delete the old branch")
    assert r.status_code == 403
    assert r.json()["detail"]["reason"] == "no_approval_supplied"
    assert not [c for c in f.calls if c["path"].endswith("/messages")]


def test_29_unknown_approval_is_refused(fake):
    m, f, client = fake
    r = _send(client, "delete the old branch", "apr-nope")
    assert r.status_code == 403
    assert r.json()["detail"]["reason"] == "unknown_approval"


def test_29_pending_approval_is_refused(fake):
    m, f, client = fake
    rec = client.post(
        "/api/command/approvals", headers=auth(),
        json={"title": "t", "detail": "d", "risk": "high", "binding_text": "delete the old branch"},
    ).json()
    r = _send(client, "delete the old branch", rec["id"])
    assert r.status_code == 403
    assert r.json()["detail"]["reason"] == "not_approved"


def test_29_denied_approval_is_refused(fake):
    m, f, client = fake
    # Create then reject -- `_approve` would already have approved it, and
    # re-deciding is itself refused, so the approval would have stayed APPROVED
    # and the send would have succeeded.
    text = "delete the old branch"
    rec = client.post(
        "/api/command/approvals", headers=auth(),
        json={"title": "t", "detail": text, "risk": "high", "binding_text": text},
    ).json()
    rejected = client.post(
        f"/api/command/approvals/{rec['id']}/decide", headers=auth(),
        json={"decision": "reject", "note": "no"},
    )
    assert rejected.status_code == 200, rejected.text
    assert rejected.json()["state"] == "REJECTED"
    r = _send(client, text, rec["id"])
    assert r.status_code == 403
    assert r.json()["detail"]["reason"] == "not_approved"


def test_29_expired_approval_is_refused(fake, monkeypatch):
    import command_center

    m, f, client = fake
    aid = _approve(client, "delete the old branch")
    monkeypatch.setattr(command_center, "APPROVAL_TTL_SECONDS", 0)
    import time

    time.sleep(0.01)
    r = _send(client, "delete the old branch", aid)
    assert r.status_code == 403, r.text
    assert r.json()["detail"]["reason"] in ("not_approved", "approval_unavailable")
    # And it is retired rather than left APPROVED for a later attempt.
    listed = client.get("/api/command/approvals", headers=auth()).json()["approvals"]
    row = [a for a in listed if a["id"] == aid][0]
    assert row["state"] == "EXPIRED", row["state"]


def test_29_payload_mismatch_is_refused(fake):
    m, f, client = fake
    aid = _approve(client, "delete the old branch")
    r = _send(client, "delete the production database", aid)
    assert r.status_code == 403
    assert r.json()["detail"]["reason"] == "approval_mismatch"


def test_29_a_prefix_does_not_authorise_a_longer_command(fake):
    m, f, client = fake
    aid = _approve(client, "delete the branch")
    r = _send(client, "delete the branch and transfer the balance", aid)
    assert r.status_code == 403
    assert r.json()["detail"]["reason"] == "approval_mismatch"


def test_29_replay_is_refused(fake):
    """Single-use, atomically consumed."""
    m, f, client = fake
    aid = _approve(client, "delete the old branch")
    assert _send(client, "delete the old branch", aid).status_code == 200
    second = _send(client, "delete the old branch", aid)
    assert second.status_code == 403
    listed = client.get("/api/command/approvals", headers=auth()).json()["approvals"]
    assert [a for a in listed if a["id"] == aid][0]["state"] == "CONSUMED"


def test_29_wrong_owner_token_is_refused_even_with_a_valid_approval(fake):
    m, f, client = fake
    aid = _approve(client, "delete the old branch")
    r = _send(client, "delete the old branch", aid, headers={"X-Owner-Token": "wrong"})
    assert r.status_code == 401


def test_29_pause_overrides_a_valid_approval(fake):
    m, f, client = fake
    aid = _approve(client, "delete the old branch")
    client.post("/api/command/pause", headers=auth(), json={"paused": True, "reason": "gate"})
    r = _send(client, "delete the old branch", aid)
    assert r.status_code == 503
    assert r.json()["detail"]["error"] == "paused_by_owner"


def test_29_ambiguous_approval_cannot_be_applied(fake):
    """The spoken-approval rule: exactly one pending, or nothing is approved.

    The page refuses when the server reports more than one pending approval,
    because it cannot tell which one was meant. The server side of that contract
    is that the pending list is authoritative and filterable -- checked here.
    """
    m, f, client = fake
    for text in ("delete the old branch", "publish this to the store"):
        client.post("/api/command/approvals", headers=auth(),
                    json={"title": "t", "detail": text, "risk": "high", "binding_text": text})
    pend = client.get("/api/command/approvals?state=WAITING_AUTHORIZATION",
                      headers=auth()).json()["approvals"]
    assert len(pend) == 2, "the page refuses on >1; the server must report both"
    assert all(a["state"] == "WAITING_AUTHORIZATION" for a in pend)


def test_29_the_connector_records_persisted_approval_evidence(fake):
    """The connector's gate is a record too, not a boolean."""
    from connector import ClaimRefused, Job, Risk, Store, TaskKind, Transport, new_job_id

    s = Store(":memory:")
    try:
        j = Job(job_id=new_job_id(TaskKind.CODE, "gate", {"s": "x"}), kind=TaskKind.CODE,
                title="gate", payload={"s": "x"}, risk=Risk.CRITICAL)
        s.create_job(j, actor="owner")
        rec = s.request_approval(j.job_id, actor="owner", note="please run")
        assert rec["state"] == "WAITING_AUTHORIZATION"
        with pytest.raises(ClaimRefused):
            s.claim_job(j.job_id, "letta", Transport.API, actor="letta")

        decided = s.decide_approval(rec["approval_id"], "approve", actor="owner",
                                    note="ok", evidence="reviewed the plan")
        assert decided["decided_by"] == "owner"
        assert decided["evidence"] == "reviewed the plan"
        assert decided["decided_at"]
        claimed = s.claim_job(j.job_id, "letta", Transport.API, actor="letta",
                              approval_id=rec["approval_id"])
        assert claimed.status.value == "RUNNING"
    finally:
        s.close()


# --------------------------------------------------------------------------- #
# The three lower findings §29 also names
# --------------------------------------------------------------------------- #

def test_29_provider_name_path_traversal_is_refused():
    from connector.schema import canonical_provider

    for bad in ("../../../tmp/pwn", "..", "a/b", "a\\b", "with space", "", None):
        with pytest.raises(ValueError):
            canonical_provider(bad)


def test_29_provider_disconnect_is_case_normalized():
    from connector import Scope, Store, TokenStore, disconnect_provider

    s = Store(":memory:")
    try:
        tokens = TokenStore(s._conn, owner_token="master")
        plaintext, _ = tokens.issue("Anthropic", {Scope.READ})
        report = disconnect_provider(s, tokens, "anthropic", actor="owner")
        assert report.tokens_revoked, "a case difference left the credential live"
        assert report.clean
    finally:
        s.close()


def test_29_letta_error_payloads_are_not_logged(fake, capsys):
    m, f, client = fake
    secret = "GATE-SECRET delete the production database"
    assert m._error_kind({"error": secret}) == "unrecognised"
    assert m._error_kind(secret) == "unrecognised"
    m.audit("letta_error", None, status=400, kind=m._error_kind({"error": secret}))
    out = capsys.readouterr().out
    assert "GATE-SECRET" not in out
    assert "unrecognised" in out


def test_29_security_regression_tests_exist():
    """The checklist's last item, checked rather than asserted.

    A gate that says "add regression tests" is satisfied by the tests existing
    and running -- so this counts them from the filesystem rather than trusting
    a commit message.
    """
    files = {
        "tests/test_risk.py": "classifier and three-way drift",
        "tests/test_qa_adversarial.py": "adversarial QA findings",
        "connector/tests/test_security.py": "connector refusals",
    }
    for rel, purpose in files.items():
        path = os.path.join(os.path.dirname(HERE), rel)
        assert os.path.exists(path), f"missing regression suite: {rel} ({purpose})"
        body = open(path, encoding="utf-8").read()
        assert body.count("def test_") >= 10, f"{rel} has too few tests to be a suite"


# --------------------------------------------------------------------------- #
# Persistence, verified across a real process boundary
# --------------------------------------------------------------------------- #
#
# §29 requires *persisted* approvals. The test that closed this item created a
# second CommandCenter in the same process, which proves in-process readability
# and not persistence -- a test named for a property it does not exercise is the
# same shape as the five false controls. These run the store in a child
# interpreter each time, so "survives a restart" means a restart.

_CHILD = r'''
import os, sys, json
sys.path.insert(0, {app_dir!r})
os.environ["ODDFELLOW_APPROVAL_JOURNAL"] = {journal!r}
import command_center as cc
cc.APPROVAL_JOURNAL_PATH = {journal!r}
center = cc.CommandCenter()
step = sys.argv[1]
if step == "create":
    rec = center.add_approval("t", "d", "high", binding_text="delete the old branch")
    center.decide(rec["id"], "approve", note="ok", actor="owner")
    print(json.dumps({{"id": rec["id"], "state": center.get_approval(rec["id"])["state"]}}))
elif step == "consume":
    rows = list(center._approvals.values())
    assert rows, "the journal replayed nothing"
    r = rows[0]
    assert r["state"] == "APPROVED", f"state is {{r['state']}}"
    assert r["decided_by"] == "owner", f"actor lost: {{r['decided_by']!r}}"
    assert r["binding"], "binding lost"
    print(json.dumps({{"id": r["id"], "state": center.consume_approval(r["id"])["state"]}}))
elif step == "recheck":
    rows = list(center._approvals.values())
    assert rows, "the journal replayed nothing"
    r = rows[0]
    assert r["state"] == "CONSUMED", f"CONSUMED resurrected as {{r['state']}}"
    try:
        center.consume_approval(r["id"])
        raise SystemExit("a consumed approval was consumable again")
    except ValueError:
        pass
    print(json.dumps({{"id": r["id"], "state": r["state"]}}))
'''


def _child(step, journal):
    import json
    import subprocess

    app_dir = os.path.dirname(HERE)
    src = _CHILD.format(app_dir=app_dir, journal=journal)
    proc = subprocess.run(
        [sys.executable, "-c", src, step],
        capture_output=True, text=True, timeout=60, cwd=app_dir,
    )
    assert proc.returncode == 0, f"child {step} failed:\n{proc.stdout}\n{proc.stderr}"
    return json.loads(proc.stdout.strip().splitlines()[-1])


def test_29_an_approved_approval_survives_a_real_restart(tmp_path):
    journal = str(tmp_path / "approvals.jsonl")
    created = _child("create", journal)
    assert created["state"] == "APPROVED"
    # A different interpreter, reading only the journal.
    consumed = _child("consume", journal)
    assert consumed["id"] == created["id"]
    assert consumed["state"] == "CONSUMED"
    # And a third: CONSUMED must not resurrect on replay.
    assert _child("recheck", journal)["state"] == "CONSUMED"


def test_29_a_corrupt_journal_does_not_break_the_gate(tmp_path):
    """Fail-open on the journal is fail-closed on the gate.

    A record that cannot be parsed cannot be found, and an approval that cannot
    be found cannot be consumed. The gate must still start.
    """
    import subprocess

    journal = tmp_path / "approvals.jsonl"
    journal.write_text('{"id": "apr-orphan"}\n{not json at all\n\n', encoding="utf-8")
    app_dir = os.path.dirname(HERE)
    src = (
        "import os, sys\n"
        f"sys.path.insert(0, {app_dir!r})\n"
        f"os.environ['ODDFELLOW_APPROVAL_JOURNAL'] = {str(journal)!r}\n"
        "import command_center as cc\n"
        f"cc.APPROVAL_JOURNAL_PATH = {str(journal)!r}\n"
        "c = cc.CommandCenter()\n"
        "print(len(c._approvals))\n"
    )
    proc = subprocess.run([sys.executable, "-c", src], capture_output=True, text=True,
                          timeout=60, cwd=app_dir)
    assert proc.returncode == 0, proc.stderr
    # The orphan parses; the garbage line does not. Neither may crash startup.
    assert proc.stdout.strip().splitlines()[-1] == "1"
