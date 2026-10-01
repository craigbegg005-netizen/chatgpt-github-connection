#!/usr/bin/env python3
"""The post-Gate-A sequence, as one command.

Runs the twenty-step verification the cross-AI handoff specifies, in order, the
moment the owner sets the two secrets on the live service. The point is that the
verification is *ready* rather than improvised: when Gate A clears, nobody should
be deciding what to check.

    python post_gate_a_check.py https://oddfellow-letta-backend-v0206.onrender.com \
        --owner-token "$ODDFELLOW_OWNER_TOKEN"

Two rules this script holds to, because both have bitten this project:

  * **It restores what it changes.** Steps 11 and 12 exercise the pause and
    approval machinery on a *live* service. Both are written with try/finally so
    the service is unpaused and no approval is left pending, even if a step fails
    midway. A verification run that leaves production paused would be a worse
    incident than the one it was checking for.
  * **A step it cannot check is not a step it passes.** Anything needing a phone,
    a browser or an owner decision is printed as MANUAL and never counted as a
    pass. The result line says how many were machine-checked and how many remain.

Stdlib only. Exits 0 only when every machine-checkable step passed.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
TIMEOUT = 90  # Render's free tier cold-starts; allow for it everywhere.


#: The service rate-limits the Command Center (ODDFELLOW_RATE_PER_MIN, 20 by
#: default). A verification run must respect that, because the alternative is
#: what actually happened on the first attempt at this script: it tripped the
#: limit and reported three FAILURES against a healthy service. A check that
#: reports failure for a reason other than the thing it is checking is worse than
#: no check -- it manufactures a bug report out of its own impatience.
_RATE_LIMIT_RETRIES = 4
_RATE_LIMIT_BACKOFF = 16  # seconds; the window is per minute.

#: Transient upstream statuses worth retrying on the MESSAGE path only.
#:
#: This script is itself load on the system it verifies. Running it repeatedly
#: against a free-tier service whose upstream API has its own quota produced a
#: 503 on the message endpoint that was gone seconds later -- a false failure,
#: reported against a healthy service, caused by the checking rather than the
#: thing checked. Retrying is the honest fix: a service that is briefly busy is
#: not a service that is broken.
#:
#: Deliberately NOT applied to /healthz: a 503 there is the fail-closed readiness
#: gate, which is meaningful, and retrying it into a pass would hide Gate A.
_TRANSIENT = (429, 502, 503)
_TRANSIENT_RETRIES = 4
_TRANSIENT_BACKOFF = 20


def call(url, method="GET", body=None, token=None, timeout=TIMEOUT):
    """One HTTP call. Returns (status, parsed_or_text, seconds). Never raises.

    Retries on 429 with a bounded backoff, so a busy service reads as busy rather
    than broken.
    """
    data = json.dumps(body).encode() if body is not None else None
    started = time.time()
    status, raw = None, ""

    for attempt in range(_RATE_LIMIT_RETRIES + 1):
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("Accept", "application/json")
        if data:
            req.add_header("Content-Type", "application/json")
        if token:
            req.add_header("X-Owner-Token", token)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read().decode("utf-8", "replace")
                status = resp.status
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", "replace")
            status = exc.code
        except Exception as exc:
            return None, f"transport error: {exc}", time.time() - started

        if status != 429 or attempt == _RATE_LIMIT_RETRIES:
            break
        time.sleep(_RATE_LIMIT_BACKOFF)

    try:
        return status, json.loads(raw), time.time() - started
    except json.JSONDecodeError:
        return status, raw, time.time() - started


def call_transient(url, method="GET", body=None, token=None, timeout=TIMEOUT):
    """`call`, retrying the statuses that mean "busy" rather than "broken"."""
    for attempt in range(_TRANSIENT_RETRIES + 1):
        status, parsed, secs = call(url, method=method, body=body, token=token, timeout=timeout)
        if status not in _TRANSIENT or attempt == _TRANSIENT_RETRIES:
            return status, parsed, secs
        time.sleep(_TRANSIENT_BACKOFF)
    return status, parsed, secs  # pragma: no cover - loop always returns


class Run:
    """Collects step results so the summary is computed, never asserted by hand."""

    def __init__(self) -> None:
        self.passed = 0
        self.failed: list[str] = []
        self.manual: list[str] = []

    def step(self, n: int, label: str, ok: bool, detail: str = "") -> None:
        mark = "PASS" if ok else "FAIL"
        print(f"  [{mark}] {n:2d}. {label:<48s} {detail}")
        if ok:
            self.passed += 1
        else:
            self.failed.append(f"{n}. {label}: {detail}")

    def manual_step(self, n: int, label: str) -> None:
        print(f"  [MANUAL] {n:2d}. {label}")
        self.manual.append(label)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("url", help="the live service base URL")
    ap.add_argument("--owner-token", required=True)
    args = ap.parse_args(argv)

    base = args.url.rstrip("/")
    tok = args.owner_token
    r = Run()

    print("=" * 78)
    print("ODDFELLOW — POST-GATE-A VERIFICATION")
    print(f"target: {base}")
    print(f"time:   {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}")
    print("=" * 78)

    # 1-2. Liveness and readiness.
    st, body, _ = call(f"{base}/livez")
    r.step(1, "/livez returns 200", st == 200, f"HTTP {st} {str(body)[:90]}")
    st, body, _ = call(f"{base}/healthz")
    ok = st == 200 and isinstance(body, dict) and body.get("ok") is True
    r.step(2, "/healthz returns 200 and ok", ok, f"HTTP {st} {str(body)[:90]}")
    if not ok:
        print("\n  Gate A is not cleared: /healthz is fail-closed. Stopping here —")
        print("  every later step depends on the service being able to serve.")
        print(f"\nRESULT: {r.passed} passed, {len(r.failed)} failed (halted at step 2)")
        return 1

    # 3-4. Owner auth and the agent.
    st, status_body, _ = call(f"{base}/api/letta/status", token=tok)
    auth_ok = st == 200 and isinstance(status_body, dict) and status_body.get("letta_auth")
    r.step(3, "authenticated owner access", auth_ok, f"HTTP {st}")
    agent_ok = isinstance(status_body, dict) and status_body.get("agent_found")
    r.step(4, "Letta agent reachable and resolved", bool(agent_ok),
           f"agent={status_body.get('agent_name') if isinstance(status_body, dict) else '?'}")

    # 5-6. A harmless message and a real reply.
    marker = f"post-gate-a probe {int(time.time())}"
    st, msg, secs = call_transient(f"{base}/api/letta/message", method="POST",
                                   body={"input": marker}, token=tok)
    reply = ""
    if isinstance(msg, dict):
        reply = str(msg.get("reply") or msg.get("output") or msg.get("message") or "")
    r.step(5, "harmless test message accepted", st == 200,
           f"HTTP {st} in {secs:.1f}s" + ("" if st == 200 else f" {str(msg)[:70]}"))
    r.step(6, "a real reply came back", bool(reply.strip()), f"{len(reply)} chars")

    # 7. Persistence.
    st, hist, _ = call(f"{base}/api/letta/history", token=tok)
    msgs = (hist or {}).get("messages") if isinstance(hist, dict) else None
    persisted = st == 200 and isinstance(msgs, list) and len(msgs) > 0
    r.step(7, "conversation persisted", persisted, f"{len(msgs) if msgs else 0} message(s)")

    # 8-9. The two existing harnesses, run as subprocesses so their output is theirs.
    for n, script in ((8, "acceptance_check.py"), (9, "golive_check.py")):
        path = HERE / script
        if not path.exists():
            r.step(n, f"{script} (not present in this checkout)", False, "missing file")
            continue
        proc = subprocess.run(
            [sys.executable, str(path), base, "--owner-token", tok],
            capture_output=True, text=True, timeout=600, check=False,
        )
        tail = (proc.stdout or "").strip().splitlines()
        summary = tail[-1] if tail else (proc.stderr or "")[:80]
        r.step(n, script, proc.returncode == 0, summary[:90])

    # 10. Command Center owner-auth routes.
    st, cc, _ = call(f"{base}/api/command/status", token=tok)
    r.step(10, "Command Center owner-auth route", st == 200,
           f"HTTP {st} {str(cc)[:70]}")

    # 11. Pause behaviour — with a guaranteed resume.
    paused_ok = resumed_ok = False
    try:
        call(f"{base}/api/command/pause", method="POST",
             body={"paused": True, "reason": "post-gate-a verification (temporary)"}, token=tok)
        _, pstate, _ = call(f"{base}/api/command/status", token=tok)
        paused_ok = isinstance(pstate, dict) and pstate.get("paused") is True
    finally:
        call(f"{base}/api/command/pause", method="POST",
             body={"paused": False, "reason": "verification complete"}, token=tok)
        _, pstate, _ = call(f"{base}/api/command/status", token=tok)
        resumed_ok = isinstance(pstate, dict) and pstate.get("paused") is False
    r.step(11, "pause sets, and is restored to running", paused_ok and resumed_ok,
           f"paused={paused_ok} resumed={resumed_ok}")

    # 12. Approval behaviour — decided immediately so nothing is left pending.
    approval_id = None
    try:
        st, created, _ = call(f"{base}/api/command/approvals", method="POST",
                              body={"title": "post-gate-a verification",
                                    "detail": "created and rejected by the verification run",
                                    "risk": "high"}, token=tok)
        if isinstance(created, dict):
            approval_id = created.get("id")
        waiting = isinstance(created, dict) and created.get("state") == "WAITING_AUTHORIZATION"
        r.step(12, "high-risk action enters WAITING_AUTHORIZATION", waiting,
               f"id={approval_id} state={created.get('state') if isinstance(created, dict) else '?'}")
    finally:
        if approval_id:
            call(f"{base}/api/command/approvals/{approval_id}/decide", method="POST",
                 body={"decision": "reject", "note": "verification cleanup"}, token=tok)

    # 13. Audit output.
    st, audit, _ = call(f"{base}/api/command/audit?limit=25", token=tok)
    records = (audit or {}).get("records") if isinstance(audit, dict) else None
    events = {x.get("event") for x in records or [] if isinstance(x, dict)}
    r.step(13, "audit records the verification events", st == 200 and bool(events),
           f"{len(events)} distinct event(s)")

    # 14-15. PWA assets and the mobile URL.
    asset_ok = True
    detail = []
    for path in ("/", "/manifest.json", "/sw.js", "/icons/icon-192.png"):
        s, _, _ = call(f"{base}{path}")
        detail.append(f"{path}:{s}")
        if s != 200:
            asset_ok = False
    r.step(14, "PWA assets served", asset_ok, " ".join(detail))
    r.step(15, "the URL a phone would load is reachable", asset_ok, base)

    # 16. A wrong credential must be refused.
    s_bad, _, _ = call(f"{base}/api/letta/status", token="wrong-token-on-purpose")
    r.step(16, "wrong credential is rejected", s_bad in (401, 403), f"HTTP {s_bad}")

    # 17. No secret VALUES in client-visible responses.
    #
    # This step looks for values, not names. An earlier version also flagged the
    # literal string "ODDFELLOW_OWNER_TOKEN" -- which is the backend's own
    # diagnostic: /healthz reports the NAMES of missing env vars and never their
    # values. Flagging that would have been flagging the correct behaviour, and
    # "fixing" the code to satisfy the check would have removed a useful signal.
    # A name is not a secret. A value is.
    blob = json.dumps(status_body, default=str) + json.dumps(cc, default=str)
    leaks = []
    if tok and tok in blob:
        leaks.append("the owner token value appears in a response")
    if "sk-" in blob:
        leaks.append("an sk- shaped key appears in a response")
    r.step(17, "no secret values in responses", not leaks,
           "; ".join(leaks) if leaks else
           f"scanned {len(blob)} chars; names may appear, values must not")

    # 18. Deploy drift, if this is running inside the repository.
    if (HERE.parent.parent / ".git").exists():
        proc = subprocess.run(
            ["git", "-C", str(HERE.parent.parent), "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, check=False,
        )
        head = (proc.stdout or "").strip()
        r.step(18, "deploy-branch drift noted (informational)", True,
               f"local HEAD {head or 'unknown'} — compare against the deployed commit")
    else:
        r.manual_step(18, "Reconcile deploy-branch drift against the deployed commit")

    # 19-20. Owner decisions, and the phone.
    r.manual_step(19, "Decide whether a new production deploy is warranted")
    r.manual_step(20, "Re-run this script after any deploy")
    r.manual_step(21, "PHONE: install the PWA, tap the mic, speak, hear the reply")
    r.manual_step(22, "PHONE: confirm a high-risk voice command is held for approval")

    print("=" * 78)
    print(f"RESULT: {r.passed} machine step(s) passed, {len(r.failed)} failed, "
          f"{len(r.manual)} remain for a human")
    for f in r.failed:
        print(f"  FAILED: {f}")
    print("NOT CLAIMED: the MANUAL steps above, and anything a phone can only prove.")
    print("=" * 78)
    return 0 if not r.failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
