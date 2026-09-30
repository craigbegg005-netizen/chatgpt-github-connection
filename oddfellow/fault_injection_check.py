#!/usr/bin/env python3
"""
Fault injection for the Oddfellow backend: what happens when Letta is broken?

Why this exists
---------------
The acceptance harness proves the happy path. It cannot prove what the backend
does when the model provider fails, because a healthy provider does not fail on
demand. "Model/provider failure handling" sat on the unverified list for exactly
that reason -- it needs a fault, and nobody was injecting one.

This script injects them. It runs a local stub that impersonates the Letta API
and can be told to misbehave in specific ways, points a real backend instance at
it, and asserts that the backend fails *honestly*:

  * it returns a named error, never a fabricated reply
  * it does not report success when the provider did not answer
  * it does not hang forever
  * it never leaks key material in an error body

Nothing here touches api.letta.com and nothing costs anything: the stub is a
local http.server and the "API key" is a literal dummy.

Usage:
    python fault_injection_check.py            # uses /tmp/venv if present
    python fault_injection_check.py --verbose

Stdlib only, like acceptance_check.py.
"""

from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
VENV_PY = os.environ.get("ODDFELLOW_VENV", "/tmp/venv") + "/bin/python"

# A dummy that is shaped like a key so the leak assertion is meaningful.
DUMMY_KEY = "sk-letmein-this-is-not-a-real-key-0000000000000000"
OWNER_TOKEN = "fault-injection-owner-token"

AGENT_ID = "agent-faultinject-0000-0000-000000000000"
CONV_ID = "conv-faultinject-0000-0000-000000000000"

# The stub's behaviour, switched per test.
MODE = {"name": "ok"}

REPLY_TEXT = "Stub reply: the provider answered."


def sse(*events: dict) -> bytes:
    body = "".join(f"data: {json.dumps(e)}\n\n" for e in events) + "data: [DONE]\n\n"
    return body.encode()


class StubHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *args):  # keep the output readable
        pass

    def _send(self, code: int, body: bytes, ctype: str = "application/json"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _json(self, code: int, obj):
        self._send(code, json.dumps(obj).encode())

    def do_GET(self):
        if self.path.startswith("/v1/agents/"):
            return self._json(
                200,
                {
                    "id": AGENT_ID,
                    "name": "Oddfellow",
                    "agent_type": "letta_v1_agent",
                    "llm_config": {"handle": "letta/auto", "context_window": 32000},
                    "blocks": [],
                    "metadata": {"oddfellow_conversation_id": CONV_ID},
                },
            )
        if self.path.startswith("/v1/conversations/"):
            return self._json(200, {"id": CONV_ID})
        return self._json(404, {"error": "stub: no such path", "path": self.path})

    def do_PATCH(self):
        length = int(self.headers.get("Content-Length") or 0)
        if length:
            self.rfile.read(length)
        return self._json(200, {"id": AGENT_ID})

    def do_POST(self):
        length = int(self.headers.get("Content-Length") or 0)
        if length:
            self.rfile.read(length)

        if not self.path.endswith("/messages"):
            return self._json(404, {"error": "stub: no such path", "path": self.path})

        mode = MODE["name"]

        if mode == "http500":
            return self._json(500, {"error": "stub: internal server error"})
        if mode == "http401":
            return self._json(401, {"error": "stub: invalid api key"})
        if mode == "http429":
            return self._json(429, {"error": "stub: rate limited"})
        if mode == "garbage":
            return self._send(200, b"this is not an event stream at all", "text/plain")
        if mode == "empty":
            return self._send(200, b"", "text/event-stream")
        if mode == "no_assistant":
            # A well-formed stream that simply never produces an assistant message.
            return self._send(
                200,
                sse(
                    {"message_type": "stop_reason", "stop_reason": "end_turn"},
                    {"message_type": "usage_statistics", "completion_tokens": 0},
                ),
                "text/event-stream",
            )
        # ok
        return self._send(
            200,
            sse(
                {"message_type": "assistant_message", "content": REPLY_TEXT},
                {"message_type": "stop_reason", "stop_reason": "end_turn"},
                {"message_type": "usage_statistics", "prompt_tokens": 11, "completion_tokens": 7},
            ),
            "text/event-stream",
        )


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def start_stub() -> tuple[ThreadingHTTPServer, int]:
    port = free_port()
    srv = ThreadingHTTPServer(("127.0.0.1", port), StubHandler)
    srv.daemon_threads = True
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, port


class Backend:
    """A real backend process, pointed wherever we want."""

    def __init__(self, env_overrides: dict, port: int | None = None):
        self.port = port or free_port()
        env = dict(os.environ)
        env.update(
            {
                "LETTA_API_KEY": DUMMY_KEY,
                "ODDFELLOW_OWNER_TOKEN": OWNER_TOKEN,
                "LETTA_MODEL": "letta/auto",
                "ODDFELLOW_AGENT_ID": AGENT_ID,
                "ODDFELLOW_AUDIT_LOG": "false",
                "ODDFELLOW_RATE_PER_MIN": "600",
            }
        )
        env.update(env_overrides)
        self.env = env
        self.proc: subprocess.Popen | None = None

    def start(self, timeout: float = 30.0) -> None:
        self.proc = subprocess.Popen(
            [
                VENV_PY, "-m", "uvicorn",
                "oddfellow_letta_backend:app",
                "--host", "127.0.0.1", "--port", str(self.port),
                "--log-level", "warning",
            ],
            cwd=HERE,
            env=self.env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self.proc.poll() is not None:
                raise RuntimeError(f"backend exited early with code {self.proc.returncode}")
            try:
                self.request("GET", "/livez", timeout=2)
                return
            except Exception:
                time.sleep(0.2)
        raise RuntimeError("backend never answered /livez")

    def stop(self) -> None:
        if not self.proc:
            return
        try:
            os.killpg(os.getpgid(self.proc.pid), 15)
        except Exception:
            try:
                self.proc.terminate()
            except Exception:
                pass
        try:
            self.proc.wait(timeout=10)
        except Exception:
            try:
                os.killpg(os.getpgid(self.proc.pid), 9)
            except Exception:
                pass
        self.proc = None

    def request(self, method: str, path: str, body=None, token: str | None = OWNER_TOKEN,
                timeout: float = 30.0, raw: bool = False):
        url = f"http://127.0.0.1:{self.port}{path}"
        data = None
        headers = {}
        if body is not None:
            data = json.dumps(body).encode()
            headers["Content-Type"] = "application/json"
        if token is not None:
            headers["X-Owner-Token"] = token
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        started = time.time()
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                payload = resp.read()
                code = resp.status
        except urllib.error.HTTPError as exc:
            payload = exc.read()
            code = exc.code
        elapsed = time.time() - started
        if raw:
            return code, payload, elapsed
        try:
            return code, json.loads(payload), elapsed
        except Exception:
            return code, {"_raw": payload.decode("utf-8", "replace")[:300]}, elapsed


# --------------------------------------------------------------------------- #
# Assertions
# --------------------------------------------------------------------------- #

RESULTS: list[tuple[bool, str, str]] = []


def check(ok: bool, label: str, detail: str = "") -> None:
    RESULTS.append((bool(ok), label, detail))
    mark = "PASS" if ok else "FAIL"
    print(f"  [{mark}] {label}" + (f"   {detail}" if detail else ""))


def looks_like_a_secret(text: str) -> bool:
    return "sk-" in text or "Bearer " in text or DUMMY_KEY in text or OWNER_TOKEN in text


def named_error(body) -> str:
    """Extract the error name from a FastAPI detail payload, whatever its shape."""
    detail = body.get("detail") if isinstance(body, dict) else None
    if isinstance(detail, dict):
        return str(detail.get("error") or detail)
    if isinstance(detail, str):
        return detail
    return str(body)[:120]


def transport_kind(body) -> str | None:
    """Dig out the transport exception name from wherever it was nested.

    A transport failure can be reported three ways, and all three are correct:
      * by the route that hit it   -> {"detail": {..., "detail": {"kind": ...}}}
      * by the app-level backstop  -> {"detail": {..., "detail": {"kind": ...}}}
      * by /api/letta/status, which reports rather than raises
                                   -> {"letta_error": {"detail": {"kind": ...}}}

    So assert the *cause* is named rather than pinning the wrapper -- but do
    look in all three places. An earlier version of this helper only searched
    `detail`, so it reported "kind=None" against a status response that named
    the cause perfectly well. A check that looks in the wrong place fails just
    as convincingly as a real defect, and costs the same to chase.
    """
    roots = []
    if isinstance(body, dict):
        roots = [body.get("detail"), body.get("letta_error")]
    for root in roots:
        node = root
        for _ in range(4):
            if not isinstance(node, dict):
                break
            if node.get("kind"):
                return str(node["kind"])
            node = node.get("detail")
    return None


# --------------------------------------------------------------------------- #
# Tests
# --------------------------------------------------------------------------- #

def test_provider_errors(stub_port: int) -> None:
    """Provider returns 4xx/5xx -> backend must relay a named failure, not invent a reply."""
    for mode, expect_status in (("http500", 500), ("http401", 401), ("http429", 429)):
        MODE["name"] = mode
        b = Backend({"LETTA_BASE_URL": f"http://127.0.0.1:{stub_port}"})
        try:
            b.start()
            code, body, elapsed = b.request(
                "POST", "/api/letta/message", {"input": "hello"}, timeout=30
            )
            check(
                code == 502 and named_error(body) == "letta_message_failed",
                f"provider {mode} -> 502 letta_message_failed",
                f"HTTP {code} {named_error(body)} in {elapsed:.1f}s",
            )
            check(
                isinstance(body.get("detail"), dict) and body["detail"].get("status") == expect_status,
                f"provider {mode} -> upstream status relayed",
                f"detail.status={body.get('detail', {}).get('status')}",
            )
            check(
                "reply" not in body,
                f"provider {mode} -> no fabricated reply field",
            )
            check(
                not looks_like_a_secret(json.dumps(body)),
                f"provider {mode} -> error body carries no key material",
            )
        finally:
            b.stop()


def test_malformed_streams(stub_port: int) -> None:
    """200 OK but no assistant message -> must be reported, never guessed."""
    for mode, label in (
        ("no_assistant", "stream with no assistant message"),
        ("garbage", "non-SSE body"),
        ("empty", "empty body"),
    ):
        MODE["name"] = mode
        b = Backend({"LETTA_BASE_URL": f"http://127.0.0.1:{stub_port}"})
        try:
            b.start()
            code, body, elapsed = b.request(
                "POST", "/api/letta/message", {"input": "hello"}, timeout=30
            )
            check(
                code == 502 and named_error(body) == "no_assistant_message",
                f"{label} -> 502 no_assistant_message",
                f"HTTP {code} {named_error(body)} in {elapsed:.1f}s",
            )
            check("reply" not in body, f"{label} -> no fabricated reply")
        finally:
            b.stop()


def test_happy_path_through_stub(stub_port: int) -> None:
    """Control: the same stub, behaving, must produce the exact reply it sent.

    Without this row the fault rows prove nothing -- they could be passing
    because the backend is broken in every direction.
    """
    MODE["name"] = "ok"
    b = Backend({"LETTA_BASE_URL": f"http://127.0.0.1:{stub_port}"})
    try:
        b.start()
        code, body, elapsed = b.request(
            "POST", "/api/letta/message", {"input": "hello"}, timeout=30
        )
        check(code == 200, "control: healthy stub -> 200", f"HTTP {code} in {elapsed:.1f}s")
        check(
            body.get("reply") == REPLY_TEXT,
            "control: reply is exactly what the provider sent",
            repr(body.get("reply"))[:80],
        )
        check(
            body.get("stop_reason") == "end_turn" and body.get("conversation_id") == CONV_ID,
            "control: stop_reason and conversation id parsed",
            f"stop_reason={body.get('stop_reason')} conv={str(body.get('conversation_id'))[:20]}",
        )
    finally:
        b.stop()


def test_unreachable_provider() -> None:
    """A closed port must fail fast and by name.

    This row failed the first time it was run: the backend answered a bare
    `500 Internal Server Error`, because only HTTP status codes were wrapped and
    a connection failure raised httpx's own exception. Two sessions of the same
    agent found that independently within minutes of each other.
    """
    b = Backend({"LETTA_BASE_URL": "http://127.0.0.1:9"})
    try:
        b.start()
        code, body, elapsed = b.request(
            "POST", "/api/letta/message", {"input": "hello"}, timeout=60
        )
        check(
            code == 502,
            "unreachable provider -> 502, not a bare 500",
            f"HTTP {code} {named_error(body)} in {elapsed:.1f}s",
        )
        check(
            elapsed < 20,
            "unreachable provider -> fails fast, does not retry into a hang",
            f"{elapsed:.1f}s",
        )
        check("reply" not in body, "unreachable provider -> no fabricated reply")
        check(
            transport_kind(body) == "ConnectError",
            "unreachable provider -> names the cause (ConnectError)",
            f"kind={transport_kind(body)}",
        )
        check(
            not looks_like_a_secret(json.dumps(body)),
            "unreachable provider -> error body carries no key material",
        )
    finally:
        b.stop()


def test_connect_timeout_is_bounded() -> None:
    """A black-holed address must not hang the request forever.

    connect=15s in the backend, so this is the one deliberately slow row. It
    also proves the timeout is *bounded*: the first run returned after exactly
    15.0s, which is the connect timeout doing its job -- the defect was never
    the duration, it was that the result was an unnamed 500.
    """
    b = Backend({"LETTA_BASE_URL": "http://10.255.255.1:9"})
    try:
        b.start()
        code, body, elapsed = b.request(
            "POST", "/api/letta/message", {"input": "hello"}, timeout=90
        )
        check(
            code == 502,
            "black-holed provider -> 502, not a bare 500",
            f"HTTP {code} {named_error(body)} in {elapsed:.1f}s",
        )
        check(
            elapsed < 60,
            "black-holed provider -> bounded by the connect timeout, not a hang",
            f"{elapsed:.1f}s",
        )
        check(
            transport_kind(body) in ("ConnectTimeout", "ConnectError", "ReadTimeout"),
            "black-holed provider -> names the cause",
            f"kind={transport_kind(body)}",
        )
    finally:
        b.stop()


def test_status_distinguishes_unreachable_from_rejected() -> None:
    """"The API said no" and "the API never answered" are different questions."""
    b = Backend({"LETTA_BASE_URL": "http://127.0.0.1:9"})
    try:
        b.start()
        code, body, _ = b.request("GET", "/api/letta/status", timeout=30)
        check(
            code == 200 and body.get("letta_reachable") is False,
            "status -> reports letta_reachable:false when the provider is down",
            f"HTTP {code} letta_reachable={body.get('letta_reachable')}",
        )
        check(
            body.get("letta_auth") is False,
            "status -> does not claim authentication it never obtained",
            f"letta_auth={body.get('letta_auth')}",
        )
        check(
            transport_kind(body) == "ConnectError",
            "status -> names the transport cause",
            f"kind={transport_kind(body)}",
        )
    finally:
        b.stop()


def test_status_reports_reachable_when_the_api_rejects_the_key(stub_port: int) -> None:
    """A rejected key still proves the API answered -- reachable, not authorised."""
    MODE["name"] = "http401"
    b = Backend({"LETTA_BASE_URL": f"http://127.0.0.1:{stub_port}"})
    try:
        b.start()
        code, body, _ = b.request("GET", "/api/letta/status", timeout=30)
        check(
            code == 200 and body.get("letta_reachable") is True,
            "status -> reachable:true when the API answers with an error",
            f"HTTP {code} letta_reachable={body.get('letta_reachable')}",
        )
        check(
            body.get("letta_auth") is False,
            "status -> still refuses to claim authentication",
            f"letta_auth={body.get('letta_auth')}",
        )
    finally:
        b.stop()


def test_paid_model_refused() -> None:
    """Zero-spend doctrine: a paid model must be refused, not silently used."""
    b = Backend({"LETTA_MODEL": "openai/gpt-4o", "LETTA_BASE_URL": "https://api.letta.com"})
    try:
        b.start()
        code, body, _ = b.request("GET", "/api/letta/status", timeout=20)
        check(
            code == 503,
            "paid model without authorization -> 503 refused",
            f"HTTP {code} {named_error(body)}",
        )
        check(
            not looks_like_a_secret(json.dumps(body)),
            "paid-model refusal leaks nothing",
        )
    finally:
        b.stop()


def test_oversized_body() -> None:
    b = Backend({"LETTA_BASE_URL": "https://api.letta.com"})
    try:
        b.start()
        code, body, _ = b.request(
            "POST", "/api/letta/message", {"input": "x" * 200_000}, timeout=20
        )
        check(code == 413, "oversized body -> 413", f"HTTP {code} {named_error(body)}")
    finally:
        b.stop()


def test_auth_still_guards_failure_paths() -> None:
    """An unauthenticated caller must not be able to probe provider state."""
    b = Backend({"LETTA_BASE_URL": "http://127.0.0.1:9"})
    try:
        b.start()
        code, _, _ = b.request("POST", "/api/letta/message", {"input": "hi"}, token=None, timeout=20)
        check(code == 401, "no token -> 401 even with a broken provider", f"HTTP {code}")
        code, _, _ = b.request("POST", "/api/letta/message", {"input": "hi"}, token="wrong", timeout=20)
        check(code == 401, "wrong token -> 401 even with a broken provider", f"HTTP {code}")
    finally:
        b.stop()


def main() -> int:
    ap = argparse.ArgumentParser(description="Inject provider faults and assert honest failure.")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    if not os.path.exists(VENV_PY):
        print(f"ERROR: no python at {VENV_PY} -- run ./rehearsal.sh up once to build the venv")
        return 2

    print("=" * 78)
    print("Oddfellow fault injection -- what the backend does when Letta is broken")
    print("=" * 78)
    print(f"stub: local http.server, dummy key, no real API calls, no spend\n")

    srv, stub_port = start_stub()
    try:
        print("provider returns an error")
        test_provider_errors(stub_port)
        print("\nprovider answers 200 with an unusable stream")
        test_malformed_streams(stub_port)
        print("\ncontrol -- the same stub, behaving")
        test_happy_path_through_stub(stub_port)
        print("\nprovider is unreachable")
        test_unreachable_provider()
        test_status_distinguishes_unreachable_from_rejected()
        test_status_reports_reachable_when_the_api_rejects_the_key(stub_port)
        print("\nprovider black-holes the connection")
        test_connect_timeout_is_bounded()
        print("\nzero-spend guard")
        test_paid_model_refused()
        print("\ninput limits and auth")
        test_oversized_body()
        test_auth_still_guards_failure_paths()
    finally:
        srv.shutdown()

    passed = sum(1 for ok, _, _ in RESULTS if ok)
    total = len(RESULTS)
    print("\n" + "=" * 78)
    for ok, label, detail in RESULTS:
        if not ok:
            print(f"  [FAIL] {label}   {detail}")
    print(f"{passed}/{total} checks passed")
    print("RESULT: " + ("all checks passed" if passed == total else "FAILURES PRESENT"))
    print("=" * 78)
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
