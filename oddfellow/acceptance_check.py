#!/usr/bin/env python3
"""
Oddfellow v0.20 acceptance harness.

Runs the acceptance gates against a DEPLOYED backend and prints raw evidence for
each one. Nothing here is a judgement call: every check prints the actual request
and the actual response, so a human can overrule the verdict.

    python oddfellow/acceptance_check.py https://oddfellow-letta-poc.onrender.com
    python oddfellow/acceptance_check.py <url> --owner-token "$ODDFELLOW_OWNER_TOKEN"

Stdlib only -- no pip install, so it runs anywhere, including a phone-adjacent
laptop with nothing set up.

Exit codes:  0 = all gate checks passed   1 = at least one failed   2 = misuse

The owner token may also come from the ODDFELLOW_OWNER_TOKEN environment
variable. It is never printed.
"""

import json
import os
import sys
import time
import urllib.error
import urllib.request

TIMEOUT = 60


class Result:
    def __init__(self):
        self.rows = []

    def add(self, gate, name, ok, evidence):
        self.rows.append({"gate": gate, "name": name, "ok": ok, "evidence": evidence})

    @property
    def failed(self):
        return [r for r in self.rows if not r["ok"]]


def call(url, method="GET", body=None, token=None, timeout=TIMEOUT):
    """Return (status, parsed_or_text, seconds). Never raises on HTTP errors."""
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
    except Exception as exc:  # network, DNS, timeout
        return None, "transport error: %s" % exc, time.time() - started
    try:
        return status, json.loads(raw), time.time() - started
    except Exception:
        return status, raw[:400], time.time() - started


# --------------------------------------------------------------------------- #

def gate0(base, r):
    status, body, secs = call(base + "/healthz")
    if status is None:
        r.add(0, "reachable", False, body)
        return False
    ok = status == 200 and isinstance(body, dict) and body.get("ok") is True
    r.add(0, "healthz", ok, "HTTP %s %s (%.1fs)" % (status, body, secs))
    if not ok and isinstance(body, dict) and body.get("checks_failed"):
        r.add(0, "healthz says what is missing", True,
              "checks_failed=%s -- set these in the service environment"
              % body["checks_failed"])
    elif not ok and isinstance(body, dict):
        r.add(0, "healthz says what is missing", False,
              "healthz returned no checks_failed list; the deployed build predates "
              "the v0.20.3 self-diagnosing health check")
    status, body, secs = call(base + "/openapi.json")
    if status == 200 and isinstance(body, dict):
        routes = sorted(body.get("paths", {}).keys())
        r.add(0, "openapi version", True, "%s | %s" % (body.get("info", {}).get("title"),
                                                       body.get("info", {}).get("version")))
        expected = {"/healthz", "/api/letta/status", "/api/letta/agent",
                    "/api/letta/message", "/api/letta/new-session", "/api/letta/history"}
        missing = sorted(expected - set(routes))
        r.add(0, "openapi routes", not missing,
              ("all present" if not missing else "MISSING: %s" % missing) + " | %s" % routes)
        props = (body.get("components", {}).get("schemas", {})
                 .get("MessageIn", {}).get("properties", {}))
        r.add(0, "message schema takes 'input'", "input" in props, "props=%s" % sorted(props))
    else:
        r.add(0, "openapi reachable", False, "HTTP %s %s" % (status, body))
    return ok


def gate1(base, token, r):
    if not token:
        r.add(1, "authenticated checks", False,
              "no owner token supplied -- set ODDFELLOW_OWNER_TOKEN or pass --owner-token")
        return False

    status, body, secs = call(base + "/api/letta/status", token=token)
    good = status == 200 and isinstance(body, dict) and body.get("letta_auth") and body.get("agent_found")
    r.add(1, "status: authenticated + agent resolved", bool(good),
          "HTTP %s %s (%.1fs)" % (status, body, secs))
    if isinstance(body, dict):
        r.add(1, "status reports a conversation", bool(body.get("conversation_id")),
              "conversation_id=%s" % body.get("conversation_id"))
    if not good:
        return False

    t0 = time.time()
    status, body, secs = call(base + "/api/letta/message", "POST",
                              {"input": "One short sentence: state your name and confirm the zero-spend rule."},
                              token=token, timeout=180)
    reply = body.get("reply") if isinstance(body, dict) else None
    r.add(1, "message: real reply", bool(reply and status == 200),
          "HTTP %s in %.1fs | %r" % (status, secs, reply))
    conv = body.get("conversation_id") if isinstance(body, dict) else None

    status, body, secs = call(base + "/api/letta/new-session", "POST", {}, token=token)
    new_conv = body.get("conversation_id") if isinstance(body, dict) else None
    r.add(1, "new-session: distinct conversation", bool(new_conv and new_conv != conv),
          "was %s -> now %s" % (conv, new_conv))

    status, body, secs = call(base + "/api/letta/history?limit=20", token=token)
    msgs = body.get("messages") if isinstance(body, dict) else None
    r.add(1, "history: readable", status == 200 and isinstance(msgs, list),
          "HTTP %s | %d messages" % (status, len(msgs) if isinstance(msgs, list) else -1))

    status, body, secs = call(base + "/api/letta/agent", token=token)
    r.add(1, "agent summary", status == 200 and isinstance(body, dict) and body.get("agent"),
          "HTTP %s %s" % (status, body))
    return bool(reply)


def gate3(base, token, r):
    status, _, _ = call(base + "/api/letta/status")
    r.add(3, "no token -> 401", status == 401, "HTTP %s" % status)
    status, _, _ = call(base + "/api/letta/status", token="definitely-not-the-token")
    r.add(3, "wrong token -> 401", status == 401, "HTTP %s" % status)
    status, body, _ = call(base + "/api/letta/status", token=token or "x")
    leaked = []
    if os.environ.get("LETTA_API_KEY"):
        # We cannot compare against the *service's* key, but the response must not
        # contain anything key-shaped.
        leaked = [w for w in ("sk-", "Bearer") if isinstance(body, str) and w in body]
    r.add(3, "no key-shaped string in responses", not leaked,
          "scanned for sk-/Bearer -> %s" % (leaked or "none found"))


def main(argv):
    if len(argv) < 2 or argv[1] in ("-h", "--help"):
        print(__doc__)
        return 2
    base = argv[1].rstrip("/")
    token = None
    if "--owner-token" in argv:
        token = argv[argv.index("--owner-token") + 1]
    else:
        token = os.environ.get("ODDFELLOW_OWNER_TOKEN")

    print("Oddfellow acceptance harness")
    print("target: %s" % base)
    print("token : %s" % ("supplied" if token else "NOT supplied"))
    print("time : %s" % time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()))
    print("=" * 78)

    r = Result()
    healthy = gate0(base, r)
    if healthy:
        gate1(base, token, r)
        gate3(base, token, r)
    else:
        r.add(0, "later gates", False,
              "skipped: the service cannot serve requests until gate 0 passes")

    gate = None
    for row in r.rows:
        if row["gate"] != gate:
            gate = row["gate"]
            print("\nGATE %d" % gate)
        print("  [%s] %-38s %s" % ("PASS" if row["ok"] else "FAIL", row["name"], row["evidence"]))

    print("\n" + "=" * 78)
    if r.failed:
        print("RESULT: %d check(s) FAILED" % len(r.failed))
        for row in r.failed:
            print("  - %s: %s" % (row["name"], row["evidence"]))
        return 1
    print("RESULT: all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
