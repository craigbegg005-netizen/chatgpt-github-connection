"""Small, local episodic memory for Oddfellow's cognition package.

This is a persistence and retrieval primitive, not a reasoning engine. Records
are untrusted context with provenance; callers must not treat retrieved text as
instructions, approval, or verified fact. Retrieval is exact-token overlap and
is intentionally transparent rather than semantic.

Use an explicit database path for persistence. File databases are restricted to
the current user on POSIX systems. No network, model, or optional dependency is
used.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import stat
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

_TOKEN_RE = re.compile(r"[\w-]+", re.UNICODE)
_SCHEMA = """
CREATE TABLE IF NOT EXISTS memories (
    memory_id TEXT NOT NULL,
    namespace TEXT NOT NULL,
    content TEXT NOT NULL,
    source_ref TEXT NOT NULL,
    confidence TEXT NOT NULL,
    tags_json TEXT NOT NULL,
    content_sha256 TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY(namespace, memory_id)
);
CREATE INDEX IF NOT EXISTS memories_scope_time
    ON memories(namespace, created_at DESC);
CREATE TABLE IF NOT EXISTS memory_terms (
    namespace TEXT NOT NULL,
    memory_id TEXT NOT NULL,
    term TEXT NOT NULL,
    PRIMARY KEY(namespace, memory_id, term),
    FOREIGN KEY(namespace, memory_id) REFERENCES memories(namespace, memory_id)
        ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS memory_terms_lookup ON memory_terms(namespace, term);
"""


@dataclass(frozen=True)
class Memory:
    """A retrieved memory record. ``score`` is query-token overlap, not truth."""

    memory_id: str
    namespace: str
    content: str
    source_ref: str
    confidence: str
    tags: tuple[str, ...]
    content_sha256: str
    created_at: str
    score: float = 0.0

    @property
    def trust_label(self) -> str:
        return "UNTRUSTED_CONTEXT"


def _tokens(text: str) -> set[str]:
    return {token.casefold() for token in _TOKEN_RE.findall(text) if len(token) > 1}


def _bounded_text(value: str, field: str, limit: int, *, empty_ok: bool = False) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field} must be text")
    value = value.strip()
    if (not value and not empty_ok) or len(value) > limit or "\x00" in value:
        raise ValueError(f"{field} must contain 1..{limit} characters without NUL")
    return value


class MemoryStore:
    """Append, retrieve, and explicitly forget local episodic records.

    The store scopes every operation by namespace to prevent accidental
    cross-agent retrieval. Namespace is a caller-supplied boundary, not an
    authentication mechanism. Keep each trusted caller on its own database or
    enforce authorization before calling this class.
    """

    def __init__(self, path: str | Path) -> None:
        raw = os.fspath(path)
        if not raw:
            raise ValueError("an explicit database path is required")
        self.path = raw
        if raw != ":memory:":
            db_path = Path(raw).expanduser()
            if db_path.is_symlink():
                raise ValueError("memory database path must not be a symlink")
            db_path.parent.mkdir(parents=True, exist_ok=True)
            self.path = str(db_path)
            if os.name == "posix":
                # Pre-create with a restrictive mode so the database is never
                # briefly visible under the process umask while SQLite opens it.
                descriptor = os.open(
                    self.path, os.O_CREAT | os.O_WRONLY | getattr(os, "O_NOFOLLOW", 0),
                    stat.S_IRUSR | stat.S_IWUSR,
                )
                os.close(descriptor)
                try:
                    os.chmod(self.path, stat.S_IRUSR | stat.S_IWUSR)
                except OSError as exc:
                    raise RuntimeError(
                        "could not restrict memory database permissions"
                    ) from exc
        self._conn = sqlite3.connect(self.path, timeout=5.0)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._conn.execute("PRAGMA secure_delete = ON")
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> "MemoryStore":
        return self

    def __exit__(self, *_exc) -> None:
        self.close()

    def remember(
        self,
        *,
        namespace: str,
        content: str,
        source_ref: str,
        confidence: str = "unverified",
        tags: Iterable[str] = (),
        memory_id: str | None = None,
    ) -> Memory:
        """Persist one immutable record and its exact-token index."""
        namespace = _bounded_text(namespace, "namespace", 128)
        content = _bounded_text(content, "content", 32_000)
        source_ref = _bounded_text(source_ref, "source_ref", 512)
        confidence = _bounded_text(confidence, "confidence", 64)
        if isinstance(tags, str):
            raise TypeError("tags must be an iterable of text values, not one string")
        tag_values = tuple(sorted({_bounded_text(t, "tag", 64) for t in tags}))
        if len(tag_values) > 32:
            raise ValueError("at most 32 tags are allowed")
        record_id = _bounded_text(
            str(uuid.uuid4()) if memory_id is None else memory_id, "memory_id", 128
        )
        created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
        terms = _tokens(content)
        try:
            with self._conn:
                self._conn.execute(
                    "INSERT INTO memories(memory_id, namespace, content, source_ref, "
                    "confidence, tags_json, content_sha256, created_at) "
                    "VALUES(?,?,?,?,?,?,?,?)",
                    (record_id, namespace, content, source_ref, confidence,
                     json.dumps(tag_values, ensure_ascii=False), digest, created_at),
                )
                self._conn.executemany(
                    "INSERT INTO memory_terms(namespace,memory_id,term) VALUES(?,?,?)",
                    ((namespace, record_id, term) for term in terms),
                )
        except sqlite3.IntegrityError as exc:
            if "UNIQUE constraint failed" in str(exc):
                raise ValueError("memory_id already exists") from None
            raise
        return Memory(record_id, namespace, content, source_ref, confidence,
                      tag_values, digest, created_at)

    def search(self, *, namespace: str, query: str, limit: int = 10) -> list[Memory]:
        """Return records ranked by fraction of query tokens matched.

        Search is deliberately lexical. It does not infer semantic similarity,
        freshness, or truth. Empty-token queries return no results.
        """
        namespace = _bounded_text(namespace, "namespace", 128)
        query = _bounded_text(query, "query", 2_000)
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 100:
            raise ValueError("limit must be an integer from 1 to 100")
        terms = sorted(_tokens(query))
        if not terms:
            return []
        placeholders = ",".join("?" for _ in terms)
        rows = self._conn.execute(
            "SELECT m.*, COUNT(DISTINCT t.term) AS matches "
            "FROM memories AS m JOIN memory_terms AS t "
            "ON t.namespace=m.namespace AND t.memory_id=m.memory_id "
            f"WHERE m.namespace=? AND t.term IN ({placeholders}) "
            "GROUP BY m.namespace, m.memory_id "
            "ORDER BY matches DESC, m.created_at DESC, m.memory_id ASC LIMIT ?",
            (namespace, *terms, limit),
        ).fetchall()
        denominator = len(terms)
        return [Memory(
            row["memory_id"], row["namespace"], row["content"], row["source_ref"],
            row["confidence"], tuple(json.loads(row["tags_json"])),
            row["content_sha256"], row["created_at"], row["matches"] / denominator,
        ) for row in rows]

    def forget(self, *, namespace: str, memory_id: str) -> bool:
        """Delete one record only when both its namespace and id match."""
        namespace = _bounded_text(namespace, "namespace", 128)
        memory_id = _bounded_text(memory_id, "memory_id", 128)
        with self._conn:
            result = self._conn.execute(
                "DELETE FROM memories WHERE namespace=? AND memory_id=?",
                (namespace, memory_id),
            )
        return result.rowcount == 1
