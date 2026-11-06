"""Behavior and boundary tests for the local episodic memory primitive."""

from __future__ import annotations

import os

import pytest

from oddfellow.cognition.memory import MemoryStore


def test_memories_survive_reopen_and_retrieval_preserves_provenance(tmp_path):
    database = tmp_path / "memories.sqlite3"
    with MemoryStore(database) as store:
        saved = store.remember(
            namespace="agent:odd", content="SQLite queue survives restart",
            source_ref="test:continuity", confidence="tested", tags=("queue", "local"),
            memory_id="episode-1",
        )
        assert saved.trust_label == "UNTRUSTED_CONTEXT"
    with MemoryStore(database) as store:
        found = store.search(namespace="agent:odd", query="sqlite restart", limit=5)
    assert [memory.memory_id for memory in found] == ["episode-1"]
    assert found[0].content == "SQLite queue survives restart"
    assert found[0].source_ref == "test:continuity"
    assert found[0].confidence == "tested"
    assert found[0].tags == ("local", "queue")
    assert found[0].score == 1.0
    assert len(found[0].content_sha256) == 64


def test_namespace_scoping_and_ranking_are_explicit(tmp_path):
    with MemoryStore(tmp_path / "mem.sqlite3") as store:
        store.remember(namespace="alpha", content="red blue green", source_ref="a",
                       memory_id="a1")
        store.remember(namespace="alpha", content="red blue", source_ref="b",
                       memory_id="a2")
        store.remember(namespace="beta", content="red blue green", source_ref="c",
                       memory_id="b1")
        found = store.search(namespace="alpha", query="red blue green")
    assert [row.memory_id for row in found] == ["a1", "a2"]
    assert [row.score for row in found] == [1.0, pytest.approx(2 / 3)]


def test_forget_requires_both_namespace_and_id_and_removes_terms(tmp_path):
    with MemoryStore(tmp_path / "mem.sqlite3") as store:
        store.remember(namespace="alpha", content="private phrase", source_ref="a",
                       memory_id="same-id")
        store.remember(namespace="beta", content="private phrase", source_ref="b",
                       memory_id="same-id")
        assert store.forget(namespace="alpha", memory_id="same-id")
        assert not store.forget(namespace="alpha", memory_id="same-id")
        assert [m.namespace for m in store.search(namespace="beta", query="private phrase")] == ["beta"]
        assert store.search(namespace="alpha", query="private phrase") == []


@pytest.mark.parametrize("kwargs", [
    {"namespace": "", "content": "x", "source_ref": "s"},
    {"namespace": "n", "content": "\x00", "source_ref": "s"},
    {"namespace": "n", "content": "x", "source_ref": ""},
    {"namespace": "n", "content": "x", "source_ref": "s", "tags": "not-a-list"},
    {"namespace": "n", "content": "x", "source_ref": "s", "memory_id": ""},
])
def test_invalid_memory_input_is_refused(tmp_path, kwargs):
    with MemoryStore(tmp_path / "mem.sqlite3") as store:
        with pytest.raises((TypeError, ValueError)):
            store.remember(**kwargs)


def test_search_bounds_and_empty_token_queries(tmp_path):
    with MemoryStore(tmp_path / "mem.sqlite3") as store:
        store.remember(namespace="n", content="short note", source_ref="s")
        assert store.search(namespace="n", query="!!!") == []
        for limit in (0, 101, True, 1.5):
            with pytest.raises(ValueError, match="limit"):
                store.search(namespace="n", query="short", limit=limit)


@pytest.mark.skipif(os.name != "posix", reason="POSIX permission bits only")
def test_database_file_is_owner_only(tmp_path):
    path = tmp_path / "private.sqlite3"
    with MemoryStore(path):
        assert path.stat().st_mode & 0o777 == 0o600


@pytest.mark.skipif(os.name != "posix", reason="symlink policy is POSIX-specific")
def test_database_symlink_is_refused(tmp_path):
    target = tmp_path / "target.sqlite3"
    target.touch()
    link = tmp_path / "linked.sqlite3"
    link.symlink_to(target)
    with pytest.raises(ValueError, match="symlink"):
        MemoryStore(link)
