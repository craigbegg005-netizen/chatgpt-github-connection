"""End-to-end: the harness must NAME the cause when a live call fails.

Why this file exists
--------------------
`_error_hint` is unit-tested against the exact body the backend returned on 2026-11-07,
but that only proves the helper works. It does not prove the *harness* prints it -- the
integration was the untested part, and I recorded that limit rather than glossing it.

This closes it. A stub service satisfies gate 0 and the first step of gate 1, then fails
the message call with the real retired-model body. The harness is run against it as a
subprocess, exactly as an operator would, and the output must contain the cause.

Why a stub rather than a real target: neither available target reaches the message call.
The live service fails closed at gate 0 (Gate A), and the rehearsal is not always running.
A stub is the only way to exercise this path on demand -- and it is honest about what it
tests, because it asserts the harness's *output*, not the stub's behaviour.
"""

from __future__ import annotations

import http.server
import json
import os
import socket
import subprocess
import sys
import threading

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
HARNESS = os.path.join(REPO, "oddfellow", "acceptance_check.py")

# The body the backend actually returned on 2026-11-07, verbatim in shape.
RETIRED_MODEL_BODY = {
    "detail": {
        "error": "letta_message_failed",
        "status": 400,
        "detail": {
            "error": (
                "letta/auto is no longer available. Select a hosted model using "
                "credits or connect an external provider."
            ),
            "reasons": ["model-retired"],
        },
    }
}

OPENAPI = {
    "info": {"title": "Oddfellow (stub)", "version": "0.20.6"},
    "paths": {
        p: {}
        for p in (
            "/healthz", "/api/letta/status", "/api/letta/agent", "/api/letta/message",
            "/api/letta/new-session", "/api/letta/history",
        )
    },
    "components": {"schemas": {"MessageIn": {"properties": {"input": {}, "mode": {}}}}},
}


class _Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *args):  # silence the stub
        pass

    def _send(self, code, payload):
        raw = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/livez":
            return self._send(200, {"live": True, "ready": True, "checks_failed": []})
        if path == "/healthz":
            return self._send(200, {"ok": True})
        if path == "/openapi.json":
            return self._send(200, OPENAPI)
        if path == "/api/letta/status":
            return self._send(200, {"letta_auth": True, "agent_found": True,
                                    "conversation_id": "conv-stub"})
        if path == "/api/letta/history":
            return self._send(200, {"messages": []})
        return self._send(404, {"error": "stub: no such path", "path": path})

    def do_POST(self):
        path = self.path.split("?")[0]
        if path == "/api/letta/message":
            # The failure under test: a model-retired error, exactly as the backend
            # returns it.
            return self._send(502, RETIRED_MODEL_BODY)
        return self._send(404, {"error": "stub: no such path", "path": path})


@pytest.fixture()
def stub_service():
    if not os.path.isfile(HARNESS):
        pytest.skip("acceptance_check.py not present in this checkout")
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    server = http.server.ThreadingHTTPServer(("127.0.0.1", port), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield "http://127.0.0.1:%d" % port
    finally:
        server.shutdown()
        server.server_close()


def test_harness_output_names_the_cause_of_a_retired_model_failure(stub_service):
    """The whole point: an operator reading the harness output learns WHY it failed."""
    proc = subprocess.run(
        [sys.executable, HARNESS, stub_service, "--owner-token", "dummy-token"],
        capture_output=True, text=True, timeout=180,
    )
    out = proc.stdout + proc.stderr

    # It must still FAIL -- a stub that returns a model error is not a passing build.
    assert proc.returncode != 0, "the harness passed against a stub that returns an error"

    assert "cause:" in out, (
        "the harness reported the failure without naming a cause. This is the exact "
        "regression the helper was added for -- the detail used to read '| None'.\n"
        f"--- harness output ---\n{out}"
    )
    assert "no longer available" in out, (
        "the harness named a cause but not the real one; it should surface the inner "
        f"error string, not the 'letta_message_failed' wrapper.\n--- output ---\n{out}"
    )


# --- The revision row: a version string cannot detect a stale build ------------
#
# Added 2026-11-14. The harness's "deployed build is current" row compares the
# OpenAPI version STRING, and it PASSED against a build six weeks old because that
# build reports the same version as HEAD. These tests hold the row that actually
# answers the question: does the SERVED front end match this checkout?


def test_revision_row_fails_when_the_served_front_end_differs(stub_service):
    """A stub serving a front end that is not this checkout must FAIL that row."""
    proc = subprocess.run(
        [sys.executable, HARNESS, stub_service, "--owner-token", "dummy-token"],
        capture_output=True, text=True, timeout=180,
    )
    out = proc.stdout + proc.stderr
    assert "served front end matches this checkout" in out, (
        "the revision row did not run at all.\n" + out
    )
    assert "STALE DEPLOY" in out, (
        "the stub serves a front end that is not this checkout, so the revision row "
        "must report STALE DEPLOY -- otherwise it cannot detect a stale build, which "
        "is the whole reason it exists.\n" + out
    )


def test_revision_row_passes_when_the_served_front_end_matches():
    """The other direction: serving the real files must PASS.

    Without this, a row that always failed would look like a working check -- the
    same vacuous-control shape, inverted.
    """
    import http.server
    import socket
    import threading

    repo = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    frontend = os.path.join(repo, "oddfellow", "frontend")
    if not os.path.isdir(frontend):
        pytest.skip("no frontend directory in this checkout")

    class _Static(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *a, **kw):
            super().__init__(*a, directory=frontend, **kw)

        def log_message(self, *a):
            pass

    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    server = http.server.ThreadingHTTPServer(("127.0.0.1", port), _Static)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        proc = subprocess.run(
            [sys.executable, HARNESS, "http://127.0.0.1:%d" % port,
             "--owner-token", "dummy-token"],
            capture_output=True, text=True, timeout=180,
        )
    finally:
        server.shutdown()
        server.server_close()

    out = proc.stdout + proc.stderr
    assert "byte-identical to this checkout" in out, (
        "serving the checkout's own front end must PASS the revision row.\n" + out
    )
