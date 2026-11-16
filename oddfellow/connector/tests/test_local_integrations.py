"""Offline contract tests: two local integrations, no real providers or fees."""
from __future__ import annotations

import json
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from connector.integrations import IntegrationUnavailable, LocalInference, LocalSearch  # noqa: E402
from connector.integrations.loopback_http import LoopbackJSON  # noqa: E402


@pytest.fixture
def fake_server():
    calls = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def send_obj(self, value, *, status=200):
            raw = json.dumps(value).encode("utf8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def do_GET(self):
            calls.append(("GET", self.path))
            if self.path == "/v1/models":
                return self.send_obj({"data": [{"id": "local-fixture"}, {"id": "cloud:cloud"}]})
            if self.path.startswith("/search?"):
                q = parse_qs(urlsplit(self.path).query)
                if q.get("format") != ["json"]:
                    return self.send_obj({"error": "missing format"}, status=400)
                return self.send_obj({"results": [
                    {"url": "https://example.org/1", "title": q["q"][0], "content": "source lead"},
                    {"url": "https://example.org/1", "title": "duplicate"},
                    {"url": "javascript:alert(1)", "title": "unsafe"},
                    {"url": "https://example.org/2", "title": "second", "content": ""},
                ]})
            if self.path == "/redirect":
                self.send_response(302)
                self.send_header("Location", "http://example.com/evil")
                self.end_headers()
                return
            if self.path == "/bad":
                return self.send_obj([1, 2, 3])
            if self.path == "/large":
                return self.send_obj({"oversized": "X" * 1_048_576})
            return self.send_obj({"error": "unknown"}, status=404)

        def do_POST(self):
            calls.append(("POST", self.path))
            payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            if self.path != "/v1/chat/completions":
                return self.send_obj({"error": "invalid path"}, status=404)
            if payload["stream"] is not False or "tools" in payload:
                return self.send_obj({"error": "unexpected settings"}, status=400)
            return self.send_obj({"choices": [{"message": {"content": "local-only reply"}}]})

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}", calls
    server.shutdown()
    server.server_close()
    thread.join(timeout=3)


@pytest.mark.parametrize("invalid", [
    "https://127.0.0.1:8080/v1", "http://localhost:8080/v1",
    "http://example.com:8080/v1", "http://127.0.0.1:8080/path",
    "http://127.0.0.1:8080/v1?secret=x", "http://me@127.0.0.1:8080/v1",
    "http://127.0.0.1:0/v1", "http://127.0.0.1:missing/v1",
    "http://127.0.0.1:8080/v1#frag", "file:///tmp/private.json",
])
def test_reject_remote_or_unsafe_endpoint(invalid):
    with pytest.raises(ValueError):
        LoopbackJSON(invalid)


def test_allow_ipv6_loopback_literal_without_connecting():
    http = LoopbackJSON("http://[::1]:8080/v1")
    assert http.base_url == "http://[::1]:8080/v1"


def test_inference_fail_closed_and_explicit_local_model(fake_server):
    base, calls = fake_server
    bridge = LocalInference(base + "/v1")
    assert bridge.models() == ("local-fixture", "cloud:cloud")
    with pytest.raises(IntegrationUnavailable, match="not explicitly approved"):
        bridge.chat("local-fixture", "hello")
    approved = LocalInference(base + "/v1", allowed_models=("local-fixture",))
    assert approved.chat("local-fixture", "hello") == "local-only reply"
    assert ("POST", "/v1/chat/completions") in calls
    assert len([c for c in calls if c[0] == "POST"]) == 1


def test_refuse_cloud_even_when_allowed(fake_server):
    base, calls = fake_server
    bridge = LocalInference(base + "/v1", allowed_models=("cloud:cloud",))
    with pytest.raises(IntegrationUnavailable, match="cloud"):
        bridge.chat("cloud:cloud", "hi")
    assert not any(c[0] == "POST" for c in calls)


def test_refuse_unavailable_model_and_invalid_prompt(fake_server):
    base, calls = fake_server
    bridge = LocalInference(base + "/v1", allowed_models=("not-there",))
    with pytest.raises(IntegrationUnavailable, match="not found"):
        bridge.chat("not-there", "hello")
    with pytest.raises(ValueError):
        bridge.chat("not-there", "", max_tokens=1)
    with pytest.raises(ValueError):
        bridge.chat("not-there", "hello", max_tokens=50000)
    assert not any(c[0] == "POST" for c in calls)


def test_search_normalizes_and_deduplicates_unverified_results(fake_server):
    base, calls = fake_server
    search = LocalSearch(base)
    results = search.search('test query & sample')
    assert len(results) == 2
    assert results[0]["title"] == 'test query & sample'
    assert results[0]["status"] == "unverified_lead"
    assert results[1]["url"] == "https://example.org/2"
    assert len(calls) == 1 and calls[0][0] == "GET"
    with pytest.raises(ValueError):
        search.search("x", limit=21)
    with pytest.raises(ValueError):
        LocalSearch(base + "/v1")


def test_no_redirect_non_object_or_large_response(fake_server):
    base, _ = fake_server
    client = LoopbackJSON(base)
    for path in ("/redirect", "/bad", "/large"):
        with pytest.raises(IntegrationUnavailable):
            client.request("GET", path)
    with pytest.raises(ValueError):
        client.request("GET", "//example.org")
    with pytest.raises(ValueError):
        client.request("GET", "/../private")
    with pytest.raises(ValueError):
        client.request("GET", "http://example.com")


def test_cli_probes_local_fixture(fake_server, capsys):
    from connector.integrations.__main__ import main
    base, _ = fake_server
    assert main(["models", "--endpoint", base + "/v1"]) == 0
    assert 'local-fixture' in capsys.readouterr().out
    assert main(["search", "--endpoint", base, "--query", "some research"]) == 0
    assert 'unverified_search_leads' in capsys.readouterr().out
    assert main(["chat", "--endpoint", base + "/v1", "--model", "local-fixture",
                 "--prompt", "hello", "--confirm-local"]) == 0
    assert 'local-only reply' in capsys.readouterr().out


def test_cli_rejects_remote_services(capsys):
    from connector.integrations.__main__ import main
    assert main(["models", "--endpoint", "http://example.com:8080/v1"]) == 1
    assert 'only http' in capsys.readouterr().err
