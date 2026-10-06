"""
The self-directed improvement log must cite commits that exist.

Why this file exists
--------------------
`SELF_DIRECTED_IMPROVEMENTS.md` says every autonomous fix is recorded in
`SELF_DIRECTED_LOG.md` with a commit SHA, so the owner can review autonomous
behaviour and narrow the bounds if it drifts. On 2026-10-06 the log held four
entries while eight autonomous fixes from the preceding three days were missing —
including three of the five false controls. The trail read as a complete account of
autonomous work while omitting most of it.

What a test can and cannot check here is worth stating plainly, because the honest
limit is the point:

  * **It cannot check completeness.** Nothing can tell a test which fixes *should*
    have been logged — that requires reading every commit and judging which were
    autonomous. A test claiming to verify "every fix is logged" would be a false
    control of exactly the kind this project keeps finding.
  * **It can check that the citations resolve.** A log entry naming a commit that
    does not exist is a false record, and that is decidable.

So this guards the citations, not the completeness. The completeness gap is recorded
in the log itself, where a human reading it will see it.
"""

from __future__ import annotations

import os
import re
import subprocess

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
LOG = os.path.join(REPO, "oddfellow", "SELF_DIRECTED_LOG.md")

# A *citation* is a SHA on a "Commit:" line, not any backticked hex string. The
# first version of this guard matched every backticked hex run and tripped on
# `abc1234` in the build-identity entry -- an example env-var value, not a citation.
# An over-broad guard that fails on honest content gets deleted, which is worse than
# not having it, so this one is scoped to the line the log actually uses.
_CITE = re.compile(r"^\s*\*\*Commit:\*\*\s*`([0-9a-f]{7,40})`", re.M)


def _git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", REPO, *args], capture_output=True, text=True, timeout=60
    )


def _cited_shas() -> list[str]:
    if not os.path.isfile(LOG):
        return []
    return sorted(set(_CITE.findall(open(LOG, encoding="utf-8").read())))


def test_every_cited_commit_exists():
    """A log entry naming a commit that does not exist is a false record."""
    if not os.path.isdir(os.path.join(REPO, ".git")):
        pytest.skip("not a git checkout")
    cited = _cited_shas()
    if not cited:
        pytest.skip("no commit SHAs cited in the log")

    missing = []
    for sha in cited:
        proc = _git("cat-file", "-e", f"{sha}^{{commit}}")
        if proc.returncode != 0:
            missing.append(sha)
    assert not missing, (
        f"SELF_DIRECTED_LOG.md cites commits that do not exist: {missing}. "
        f"A review trail with unresolvable citations is not a review trail."
    )


def test_the_log_records_the_incompleteness_gap():
    """The gap must stay visible, not be quietly filled and forgotten.

    The backfill is only honest if a reader can see that the log *was* partial and
    why. If this note is deleted the file reads as though it was always complete.
    """
    if not os.path.isfile(LOG):
        pytest.skip("log not present in this checkout")
    text = open(LOG, encoding="utf-8").read()
    assert "Backfill" in text and "the log was incomplete" in text, (
        "the note recording that this log was incomplete has been removed; without "
        "it the file reads as a complete account of autonomous work, which it was not"
    )
