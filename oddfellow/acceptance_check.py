#!/usr/bin/env python3
"""
Oddfellow v0.20 acceptance harness.

Runs the acceptance gates against a DEPLOYED backend and prints raw evidence for
each one. Nothing here is a judgement call: every check prints the actual request
and the actual response, so a human can overrule the verdict.

    python oddfellow/acceptance_check.py https://oddfellow-letta-poc.onrender.com
    python oddfellow/acceptance_check.py <url> --owner-token "$ODDFELLOW_OWNER_TOKEN"
    python oddfellow/acceptance_check.py --base-url <url> --owner-token "$ODDFELLOW_OWNER_TOKEN"

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


def _strings(value):
    """Yield every string inside a parsed JSON value, at any depth.

    call() returns a parsed object, so a leak scan that only handles `str`
    inspects nothing on a real endpoint.
    """
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for key, item in value.items():
            yield str(key)
            for text in _strings(item):
                yield text
    elif isinstance(value, (list, tuple)):
        for item in value:
            for text in _strings(item):
                yield text


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
    # Scan every endpoint we can reach, and scan the *parsed* body recursively.
    #
    # An earlier version of this check could never fail: it tested
    # `isinstance(body, str)`, but call() JSON-parses every JSON response, so
    # `body` was a dict for every real endpoint and the scan always reported
    # "none found". It also looked at a single endpoint. That is the worst kind
    # of check -- it returns green on exactly the property gate 3 exists to
    # prove. It now fails loudly if it manages to scan nothing at all.
    shapes = ("sk-", "Bearer")
    hits, scanned = [], 0
    for path in ("/api/letta/status", "/api/letta/agent", "/api/letta/history?limit=5"):
        _, body, _ = call(base + path, token=token or "x")
        for text in _strings(body):
            scanned += 1
            for w in shapes:
                if w in text:
                    hits.append("%s in %s" % (w, path))
    r.add(3, "no key-shaped string in responses", not hits and scanned > 0,
          "scanned %d string(s) across 3 endpoints for %s -> %s"
          % (scanned, "/".join(shapes), hits or "none found"))


def main(argv):
    if len(argv) < 2 or argv[1] in ("-h", "--help"):
        print(__doc__)
        return 2
    # Accept the URL positionally (documented) or as --base-url. Anything else
    # starting with "-" is a misuse: fail with the usage text and exit 2, rather
    # than passing the flag through as a URL and dying on a urllib traceback
    # several frames deep, which reads like a bug in the service under test.
    if argv[1] == "--base-url":
        if len(argv) < 3:
            print("--base-url needs a value\n")
            print(__doc__)
            return 2
        base = argv[2].rstrip("/")
    elif argv[1].startswith("-"):
        print("unrecognised option: %s\n" % argv[1])
        print(__doc__)
        return 2
    else:
        base = argv[1].rstrip("/")
    if not base.startswith(("http://", "https://")):
        print("base URL must start with http:// or https:// (got %r)\n" % base)
        print(__doc__)
        return 2
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
