"""Opt-in SearXNG local search adapter; searches the web, not an offline index.

Search responses are untrusted leads, never verified historical or scientific
claims. No page fetch, auto-submission, browser execution, or remote instance.
"""

from __future__ import annotations

from urllib.parse import urlencode, urlsplit

from .loopback_http import IntegrationUnavailable, LoopbackJSON


class LocalSearch:
    def __init__(self, base_url: str = "http://127.0.0.1:8888", *, timeout: float = 10.0):
        self.http = LoopbackJSON(base_url, timeout=timeout)
        if urlsplit(self.http.base_url).path not in ("", "/"):
            raise ValueError("SearXNG local search requires a server root URL")

    def search(self, query: str, *, limit: int = 8) -> list[dict[str, str]]:
        if not isinstance(query, str) or not query.strip() or len(query) > 500:
            raise ValueError("query must contain 1..500 characters")
        if type(limit) is not int or not 1 <= limit <= 20:
            raise ValueError("limit must be 1..20")
        data = self.http.request("GET", "/search?" + urlencode({"q": query, "format": "json"}))
        raw = data.get("results")
        if not isinstance(raw, list):
            raise IntegrationUnavailable("search JSON disabled or response malformed")
        out: list[dict[str, str]] = []
        seen: set[str] = set()
        for item in raw:
            if not isinstance(item, dict):
                continue
            url, title, snippet = item.get("url"), item.get("title"), item.get("content", "")
            if not all(isinstance(v, str) for v in (url, title, snippet)):
                continue
            parsed = urlsplit(url)
            if parsed.scheme not in ("http", "https") or not parsed.hostname or parsed.username or parsed.password:
                continue
            if url in seen:
                continue
            seen.add(url)
            out.append({"title": title[:300], "url": url[:2048], "snippet": snippet[:1200], "status": "unverified_lead"})
            if len(out) >= limit:
                break
        return out
