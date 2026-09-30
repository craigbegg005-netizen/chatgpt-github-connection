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

Gate 0 asserts the deployed build is at least EXPECTED_VERSION, because "which
build is actually live?" has been the most expensive question in this project.
Pass --allow-older to accept an older build deliberately.

Gates:
  0  the service is up and is the build you think it is  (/livez, /healthz, OpenAPI)
  1  authenticated work: status, a real reply, a new session, history, agent summary
  2  the page and its PWA assets: installable manifest, every declared icon
     resolves, a service worker, and a static mount that does not shadow /api
  3  security: no token -> 401, wrong token -> 401, no key-shaped string in any
     response body

Gate 2 is skipped with a clear message when the target does not serve a front
end; run it against the static front end service in that case.

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

# The backend revision this harness expects to find. Bump it when the backend is
# bumped: the whole point of reading /openapi.json is to answer "which build is
# actually live?", and a check that only prints the answer cannot answer it.
EXPECTED_VERSION = "0.20.5"
ALLOW_OLDER = False


def _version_tuple(text):
    """'0.20.5' -> (0, 20, 5). Unparseable chunks count as 0 rather than raising."""
    parts = []
    for chunk in str(text).split("."):
        digits = "".join(c for c in chunk if c.isdigit())
        parts.append(int(digits) if digits else 0)
    return tuple(parts) or (0,)


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
    # Liveness first. Render's healthCheckPath points at /livez, and a non-200
    # health check is a FAILED DEPLOY -- so if this endpoint is missing or not
    # 200, the service can never come up no matter how correct the rest is.
    status, body, secs = call(base + "/livez")
    if status == 200 and isinstance(body, dict):
        r.add(0, "livez (the deploy health check)", body.get("live") is True,
              "HTTP %s live=%s ready=%s checks_failed=%s"
              % (status, body.get("live"), body.get("ready"), body.get("checks_failed")))
    else:
        r.add(0, "livez (the deploy health check)", False,
              "HTTP %s %s -- a 404 here means the deployed build predates v0.20.5, "
              "so render.yaml must still point healthCheckPath at /healthz"
              % (status, body))

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
        # This row used to be hard-coded True: it PRINTED the version but could
        # never fail, so a stale deploy passed silently. "Which build is live?"
        # has been the single most expensive question in this project, so it is
        # now an assertion. Pass --allow-older to accept a build older than
        # EXPECTED_VERSION deliberately.
        info = body.get("info", {}) or {}
        deployed = str(info.get("version") or "")
        current = _version_tuple(deployed) >= _version_tuple(EXPECTED_VERSION)
        r.add(0, "deployed build is current", current or ALLOW_OLDER,
              "%s | version %s (expected at least %s)%s"
              % (info.get("title"), deployed or "(none)", EXPECTED_VERSION,
                 "" if current else "  <-- STALE BUILD: not the revision you think it is"))
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

    probe = "One short sentence: state your name and confirm the zero-spend rule."
    t0 = time.time()
    status, body, secs = call(base + "/api/letta/message", "POST",
                              {"input": probe}, token=token, timeout=180)
    reply = body.get("reply") if isinstance(body, dict) else None
    r.add(1, "message: real reply", bool(reply and status == 200),
          "HTTP %s in %.1fs | %r" % (status, secs, reply))
    conv = body.get("conversation_id") if isinstance(body, dict) else None

    # Memory, checked properly. The previous version read history only AFTER
    # creating a new session, so it always looked at an empty conversation and
    # always passed -- it reported "0 messages" as a PASS. That is the same class
    # of vacuous check as the old leak scan. This reads history on the
    # conversation the turn was actually taken in, and requires both the owner's
    # message and the reply to be there.
    status, body, secs = call(base + "/api/letta/history?limit=20", token=token)
    msgs = body.get("messages") if isinstance(body, dict) else None
    contents = [str(m.get("content") or "") for m in msgs] if isinstance(msgs, list) else []
    saw_user = any(probe[:40] in c for c in contents)
    saw_reply = any((reply or "")[:40] in c for c in contents) if reply else False
    r.add(1, "history: the turn we just took is in it", bool(saw_user and saw_reply),
          "HTTP %s | %d message(s) | owner turn present=%s | reply present=%s"
          % (status, len(contents), saw_user, saw_reply))

    status, body, secs = call(base + "/api/letta/new-session", "POST", {}, token=token)
    new_conv = body.get("conversation_id") if isinstance(body, dict) else None
    r.add(1, "new-session: distinct conversation", bool(new_conv and new_conv != conv),
          "was %s -> now %s" % (conv, new_conv))

    # The new session must be a genuinely separate conversation, not the old one
    # relabelled: its history should not contain the turn taken before it.
    status, body, secs = call(base + "/api/letta/history?limit=20", token=token)
    msgs = body.get("messages") if isinstance(body, dict) else None
    new_contents = [str(m.get("content") or "") for m in msgs] if isinstance(msgs, list) else []
    carried = any(probe[:40] in c for c in new_contents)
    r.add(1, "new session starts empty", status == 200 and not carried,
          "HTTP %s | %d message(s) | carries the previous turn=%s"
          % (status, len(new_contents), carried))

    status, body, secs = call(base + "/api/letta/agent", token=token)
    r.add(1, "agent summary", status == 200 and isinstance(body, dict) and body.get("agent"),
          "HTTP %s %s" % (status, body))
    return bool(reply)


def gate2(base, r):
    """The page and its PWA assets.

    GATE 2 is "install it on the phone". It was unreachable for a whole cycle
    because the deployed front end shipped no icons and a manifest with no
    `icons` array, so the page could never be installed -- and nothing in the
    harness noticed. It is checked here now, including that every icon the
    manifest declares actually resolves, because a manifest that promises an
    icon the server 404s is exactly the failure that was missed.
    """
    status, body, _ = call(base + "/")
    serves_page = status == 200 and isinstance(body, str) and "<html" in body.lower()
    # call() truncates a non-JSON body, so report the fact rather than a length
    # that would read as the real page size.
    r.add(2, "front end served from this origin", serves_page,
          "HTTP %s, %s" % (status, "html" if serves_page else body))
    if not serves_page:
        r.add(2, "PWA assets", False,
              "this origin does not serve a front end; run gate 2 against the "
              "static front end service instead")
        return False

    # A static mount at "/" must not swallow the API. If it does, every
    # authenticated call 404s and looks like a routing bug in the client.
    status, _, _ = call(base + "/api/letta/status")
    r.add(2, "static mount does not shadow /api", status in (401, 403, 503),
          "GET /api/letta/status -> HTTP %s (401/403/503 expected, 404 means shadowed)" % status)

    status, manifest, _ = call(base + "/manifest.json")
    icons = manifest.get("icons") if isinstance(manifest, dict) else None
    r.add(2, "manifest declares icons", status == 200 and bool(icons),
          "HTTP %s icons=%s" % (status,
                                [i.get("sizes") for i in icons] if isinstance(icons, list) else icons))
    if isinstance(icons, list) and icons:
        bad = []
        for icon in icons:
            src = icon.get("src") or ""
            st, _, _ = call(base + src)
            if st != 200:
                bad.append("%s -> HTTP %s" % (src, st))
        r.add(2, "every declared icon resolves", not bad,
              "checked %d icon(s)%s" % (len(icons), "" if not bad else " | BROKEN: %s" % bad))
    else:
        r.add(2, "every declared icon resolves", False,
              "no icons array, so there is nothing to install")
    status, _, _ = call(base + "/sw.js")
    r.add(2, "service worker served", status == 200, "HTTP %s" % status)
    return True


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
    global ALLOW_OLDER
    if "--allow-older" in argv:
        ALLOW_OLDER = True

    if argv[1] == "--base-url":
        if len(argv) < 3:
            print("--base-url needs a value\n")
            print(__doc__)
            return 2
        base = argv[2].rstrip("/")
    elif argv[1] == "--allow-older":
        print("--allow-older needs a URL too\n")
        print(__doc__)
        return 2
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
        gate2(base, r)
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
