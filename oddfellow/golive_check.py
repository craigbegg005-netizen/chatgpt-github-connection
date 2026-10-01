#!/usr/bin/env python3
"""
Go-live verification for Oddfellow — the protocol's post-secret sequence, as one command.

The operating protocol names a twelve-step sequence to run after the owner saves the
production secrets. Ten of those steps are things a machine can check. Two are not:
voice behaviour and offline behaviour need a human on a phone, and PWA install needs a
browser. This script runs the machine-checkable ones, states the human ones plainly,
and refuses to call the result ACCEPTED — because it cannot.

    python golive_check.py https://oddfellow-letta-backend-v0206.onrender.com \
        --owner-token "$ODDFELLOW_OWNER_TOKEN"

NOTE ON THE TARGET: use `oddfellow-letta-backend-v0206`. The similar-looking
`oddfellow-letta-backend` is a different, dead service (HTTP 000), and pointing this
script at it produced a 20-hour blind spot on 2026-10-01. A tool whose usage example
names the wrong service will be run against the wrong service.

Stdlib only. Exits 0 only when every machine-checkable step passed.

Why this exists next to acceptance_check.py: that harness verifies the *contract* of
whatever URL it is pointed at, and is happy against the rehearsal. This one asks the
narrower, blunter question a deployment raises — "is this the deployed build, is it
configured, and can the owner actually use it?" — and it names the steps that remain
human so they cannot be quietly skipped.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
TIMEOUT = 60

# The version the repository says is current. Kept here rather than inferred so a
# stale deploy is caught by the script and not only by a human reading a table.
EXPECTED_VERSION = "0.20.6"


def call(url, method="GET", body=None, token=None, timeout=TIMEOUT):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Accept", "application/json")
    if data:
        req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("X-Owner-Token", token)
    started = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", "replace")
            status = resp.status
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", "replace")
        status = exc.code
    except Exception as exc:
        return None, "transport error: %s" % exc, time.time() - started
    try:
        return status, json.loads(raw), time.time() - started
    except Exception:
        return status, raw[:400], time.time() - started


class Report:
    def __init__(self):
        self.rows = []

    def add(self, step, name, ok, evidence):
        self.rows.append({"step": step, "name": name, "ok": ok, "evidence": evidence})

    @property
    def failed(self):
        return [r for r in self.rows if not r["ok"]]


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    base = argv[1].rstrip("/")
    token = None
    if "--owner-token" in argv:
        token = argv[argv.index("--owner-token") + 1]
    if not token:
        print("ERROR: --owner-token is required; this script never reads it from a file.")
        return 2

    r = Report()
    print("=" * 78)
    print("ODDFELLOW GO-LIVE VERIFICATION")
    print("target: %s" % base)
    print("=" * 78)

    # 1 — is anything there at all?
    status, body, secs = call(base + "/livez")
    reachable = status == 200
    r.add(1, "service is reachable", reachable,
          "HTTP %s in %.2fs" % (status, secs) if reachable else "no HTTP response (%s)" % body)
    if not reachable:
        print("\nNothing is serving. A 502 or no response means the process never came up;")
        print("that is a build or start problem, not a credentials problem.")
        render(r)
        return 1

    checks_failed = body.get("checks_failed", []) if isinstance(body, dict) else []
    version = body.get("version") if isinstance(body, dict) else None

    # 2 — startup configuration
    r.add(2, "startup configuration complete", not checks_failed,
          "checks_failed=%s" % (checks_failed or "[]"))

    # 3 — readiness, which is the fail-closed gate
    hstatus, hbody, hsecs = call(base + "/healthz")
    r.add(3, "/healthz returns 200", hstatus == 200,
          "HTTP %s %s" % (hstatus, json.dumps(hbody)[:160] if isinstance(hbody, dict) else hbody))

    # 4 — is this the build we think it is?
    r.add(4, "deployed build is current", version == EXPECTED_VERSION,
          "reports %s, expected %s" % (version, EXPECTED_VERSION))

    # 5 — the full contract, via the harness that already exists
    harness = os.path.join(HERE, "acceptance_check.py")
    if os.path.isfile(harness):
        proc = subprocess.run(
            [sys.executable, harness, base, "--owner-token", token],
            capture_output=True, text=True, timeout=600,
        )
        tail = [l for l in proc.stdout.strip().splitlines() if l.strip()][-1:]
        r.add(5, "acceptance harness", proc.returncode == 0,
              tail[0] if tail else "no output")
    else:
        r.add(5, "acceptance harness", False, "acceptance_check.py not found next to this script")

    # 6 — the owner can authenticate
    sstatus, sbody, _ = call(base + "/api/letta/status", token=token)
    authed = sstatus == 200 and isinstance(sbody, dict) and sbody.get("letta_auth") and sbody.get("agent_found")
    r.add(6, "owner authenticates and the agent resolves", bool(authed),
          "HTTP %s letta_auth=%s agent_found=%s agent=%s" % (
              sstatus,
              isinstance(sbody, dict) and sbody.get("letta_auth"),
              isinstance(sbody, dict) and sbody.get("agent_found"),
              isinstance(sbody, dict) and sbody.get("agent_name")))

    # 7 — a real reply, not a simulated one
    marker = "go-live check %d" % int(time.time())
    mstatus, mbody, msecs = call(base + "/api/letta/message", method="POST",
                                 body={"input": "Reply with one short sentence. " + marker},
                                 token=token, timeout=180)
    reply = mbody.get("reply") if isinstance(mbody, dict) else None
    r.add(7, "a real reply comes back", bool(reply),
          "HTTP %s, %d chars, %.1fs" % (mstatus, len(reply or ""), msecs))

    # 8 — history actually persists, on the conversation the turn was taken in
    conv = mbody.get("conversation_id") if isinstance(mbody, dict) else None
    hstatus, hbody, _ = call(base + "/api/letta/history?limit=40", token=token)
    messages = hbody.get("messages") if isinstance(hbody, dict) else None
    has_marker = any(marker in json.dumps(m) for m in (messages or []))
    r.add(8, "history persists and contains this turn", bool(messages) and has_marker,
          "HTTP %s, %d message(s), this turn present=%s, conversation=%s" % (
              hstatus, len(messages or []), has_marker, conv))

    render(r)

    print("\n" + "=" * 78)
    print("STEPS A MACHINE CANNOT DO — they need a human, and are NOT claimed here")
    print("=" * 78)
    for line in [
        "9.  Voice: speak to it and confirm a spoken reply comes back.",
        "10. PWA install: install it from the phone home screen.",
        "11. Offline/failure: with the network off, confirm it fails closed and says so.",
    ]:
        print("  [MANUAL] " + line)
    print("\n  Step 12 (mark ACCEPTED) is the owner's call, after 9-11.")

    if r.failed:
        print("\nRESULT: %d machine-checkable step(s) FAILED" % len(r.failed))
        return 1
    print("\nRESULT: every machine-checkable step passed. Steps 9-11 remain, on a phone.")
    return 0


def render(r):
    print()
    for row in r.rows:
        mark = "PASS" if row["ok"] else "FAIL"
        print("  [%s] %2d. %-46s %s" % (mark, row["step"], row["name"], row["evidence"]))


if __name__ == "__main__":
    sys.exit(main(sys.argv))
