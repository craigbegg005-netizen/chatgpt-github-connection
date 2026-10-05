"""Tests for the memory file-size guard.

The test that matters most is `test_counts_characters_not_bytes`. Every other
test here checks plumbing; that one checks the thing this script got wrong once
already, and it would pass against a byte-counting implementation only if the
fixture happened to be pure ASCII -- so the fixture deliberately is not.
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import memory_check  # noqa: E402


# ------------------------------------------------- the unit, which is the point


def test_counts_characters_not_bytes(tmp_path):
    """A file of 10 characters that is 30 bytes must report 10.

    `wc -c` reports 30 here. The limit is stated in characters, so counting
    bytes overstates by the multibyte ratio -- enough to make a file look over
    the limit when it is not. This fixture is chosen so the two disagree.
    """
    f = tmp_path / "mixed.md"
    text = "🔴🔴🔴🔴🔴🔴🔴🔴🔴🔴"          # 10 characters, 40 bytes in UTF-8
    f.write_text(text, encoding="utf-8")

    assert len(text) == 10
    assert len(text.encode("utf-8")) == 40, "fixture must make bytes differ from characters"
    assert memory_check.character_count(f) == 10


def test_a_file_under_the_character_limit_is_not_reported_over(tmp_path):
    """The specific error a byte count causes: refusing a file that fits."""
    # 7,000 emoji = 7,000 characters but 28,000 bytes. Under the limit in
    # characters, over it in bytes.
    (tmp_path / "emoji.md").write_text("🔵" * 7000, encoding="utf-8")
    report = memory_check.scan(tmp_path)
    assert report["over"] == [], "7000 characters is under a 20000-character limit"
    assert report["files"][0]["characters"] == 7000


# ------------------------------------------------------------------- scanning


def test_reports_headroom_from_the_limit(tmp_path):
    (tmp_path / "a.md").write_text("x" * 19950, encoding="utf-8")
    report = memory_check.scan(tmp_path)
    assert report["files"][0]["headroom"] == 50
    assert report["files"][0]["tight"] is True
    assert report["files"][0]["over"] is False


def test_a_file_over_the_limit_is_reported_over(tmp_path):
    (tmp_path / "big.md").write_text("x" * 20001, encoding="utf-8")
    report = memory_check.scan(tmp_path)
    assert [r["path"] for r in report["over"]] == ["big.md"]
    assert report["files"][0]["headroom"] == -1


def test_a_file_exactly_at_the_limit_is_within_it(tmp_path):
    """The boundary: `> limit` is over; `== limit` is not. Off-by-one here would
    refuse a file the harness accepts."""
    (tmp_path / "exact.md").write_text("x" * 20000, encoding="utf-8")
    report = memory_check.scan(tmp_path)
    assert report["over"] == []
    assert report["files"][0]["headroom"] == 0


def test_scan_ignores_the_git_directory(tmp_path):
    """A checkout can hold large .md files under .git; they are not memory."""
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "blob.md").write_text("x" * 99999, encoding="utf-8")
    (tmp_path / "real.md").write_text("small", encoding="utf-8")
    report = memory_check.scan(tmp_path)
    assert [r["path"] for r in report["files"]] == ["real.md"]


def test_scan_finds_files_in_subdirectories(tmp_path):
    (tmp_path / "projects").mkdir()
    (tmp_path / "projects" / "deep.md").write_text("x" * 100, encoding="utf-8")
    report = memory_check.scan(tmp_path)
    assert [r["path"] for r in report["files"]] == ["projects/deep.md"]


def test_tight_and_over_are_disjoint(tmp_path):
    """A file over the limit must not also be reported as merely 'tight' --
    otherwise the warning list implies something actionable where a failure is
    the actual situation."""
    (tmp_path / "over.md").write_text("x" * 20050, encoding="utf-8")
    report = memory_check.scan(tmp_path)
    assert len(report["over"]) == 1
    assert report["tight"] == []


# ------------------------------------------------------------------ reporting


def test_render_names_the_unit(tmp_path):
    """The script prints the unit beside every number, because the last reader
    of these numbers (me) confused bytes with characters and wrote it down."""
    (tmp_path / "a.md").write_text("x" * 10, encoding="utf-8")
    out = memory_check.render(memory_check.scan(tmp_path))
    assert "characters" in out
    assert "limit 20000" in out


def test_render_warns_about_a_tight_file(tmp_path):
    (tmp_path / "a.md").write_text("x" * 19990, encoding="utf-8")
    out = memory_check.render(memory_check.scan(tmp_path))
    assert "due a trim" in out
    assert "10 characters left" in out


def test_render_says_ok_when_every_file_fits(tmp_path):
    (tmp_path / "a.md").write_text("small", encoding="utf-8")
    out = memory_check.render(memory_check.scan(tmp_path))
    assert "OK: every file is within the limit" in out
    assert "FAIL" not in out


# ----------------------------------------------------------------- exit status


def test_exit_code_is_one_when_a_file_is_over(tmp_path, monkeypatch):
    (tmp_path / "big.md").write_text("x" * 20001, encoding="utf-8")
    assert memory_check.main(["--memory-dir", str(tmp_path)]) == 1


def test_exit_code_is_zero_when_every_file_fits(tmp_path):
    (tmp_path / "a.md").write_text("small", encoding="utf-8")
    assert memory_check.main(["--memory-dir", str(tmp_path)]) == 0


def test_missing_memory_dir_is_an_error_not_a_silent_pass(tmp_path, monkeypatch):
    """A check that cannot run must not report success -- that is the shape of
    every false control this project has found."""
    monkeypatch.delenv("MEMORY_DIR", raising=False)
    assert memory_check.main([]) == 2


def test_a_nonexistent_directory_is_an_error(tmp_path):
    assert memory_check.main(["--memory-dir", str(tmp_path / "nope")]) == 2
