"""Bounded JSON transport for local opt-in Oddfellow integrations.

No proxies, credentials, remote hosts or redirects. Does not start services.
Third-party response bodies are untrusted and never executed.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from urllib.parse import urlsplit

MAX_RESPONSE_BYTES = 1_048_576


class IntegrationUnavailable(RuntimeError):
    """Local integration refused or unavailable; never a fallback to a paid API."""


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class LoopbackJSON:
    """Only HTTP loopback literals, never DNS names or userinfo.

    Base URL may end in / or /v1. API methods use explicit child paths.
    Validate the base before any network request, including probes.
    """

    def __init__(self, base_url: str, *, timeout: float = 5.0):
        if not isinstance(base_url, str):
            raise ValueError("base URL must be a string")
        parts = urlsplit(base_url)
        try:
            port = parts.port
        except ValueError as exc:
            raise ValueError("invalid port") from exc
        if (parts.scheme != "http" or parts.hostname not in ("127.0.0.1", "::1")
                or port is None or port == 0 or parts.username is not None or parts.password is not None
                or parts.query or parts.fragment or parts.path.rstrip("/") not in ("", "/v1")
                or parts.netloc.count("@") != 0):
            raise ValueError("only http://127.0.0.1:PORT[/v1] or http://[::1]:PORT[/v1] is allowed")
        if not 0 < timeout <= 60:
            raise ValueError("timeout must be between 0 and 60 seconds")
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect())

    def request(self, method: str, path: str, body: dict | None = None) -> dict:
        if method not in ("GET", "POST") or not path.startswith("/") or path.startswith("//"):
            raise ValueError("only GET/POST and relative API paths are allowed")
        path_parts = urlsplit(path)
        if (path_parts.scheme or path_parts.netloc or path_parts.fragment
                or any(segment in (".", "..") for segment in path_parts.path.split("/"))):
            raise ValueError("invalid relative API path")
        if method == "GET" and body is not None:
            raise ValueError("GET must not include a body")
        if method == "POST" and not isinstance(body, dict):
            raise ValueError("POST requires JSON object")
        payload = None if body is None else json.dumps(body, separators=(",", ":")).encode("utf-8")
        if payload is not None and len(payload) > 65_536:
            raise ValueError("request exceeds size limit")
        req = urllib.request.Request(
            self.base_url + path, data=payload, method=method,
            headers={"Accept": "application/json", "Content-Type": "application/json"},
        )
        try:
            with self._opener.open(req, timeout=self.timeout) as response:
                raw = response.read(MAX_RESPONSE_BYTES + 1)
        except (urllib.error.URLError, OSError, TimeoutError) as exc:
            raise IntegrationUnavailable("local service unavailable or refused the request") from exc
        if len(raw) > MAX_RESPONSE_BYTES:
            raise IntegrationUnavailable("local response exceeds safety limit")
        try:
            result = json.loads(raw)
        except (UnicodeDecodeError, ValueError) as exc:
            raise IntegrationUnavailable("local response is not valid JSON") from exc
        if not isinstance(result, dict):
            raise IntegrationUnavailable("local response is not a JSON object")
        return result
