"""
The fresh-AI entry point must point at the newest handoff.

Why this file exists
--------------------
`CURRENT_STATE.md` is meant to be the first thing a fresh AI reads, and it carries
a line marked "newest handoff". On 2026-10-05 that line named a handoff from
2026-10-01 while the newest handoff on the branch was from 2026-10-03 — two days
of work the entry point did not mention, and an agent-memory note asserting the
file "points to the newest dated handoff". It did not, and nothing could catch it:
no test read either file.

This is the same shape as the Command Center's hard-coded status notes, found the
same week: **a pointer that nothing maintains drifts, and the drift is invisible
until someone reads it and counts.** The guard is deliberately about the *pointer*
rather than the prose — no test can check whether the surrounding summary is
honest, but it can check that the file names the newest handoff.

Ordering is by the timestamp embedded in the filename, not by mtime: a fresh clone
gives every file the checkout time, so mtime ordering would be meaningless there.
"""

from __future__ import annotations

import os
import re

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))          # the repository root
STATE = os.path.join(REPO, "CURRENT_STATE.md")
HANDOFF_DIR = os.path.join(REPO, "oddfellow")

_STAMP = re.compile(r"(\d{4})-(\d{2})-(\d{2})-(\d{4})Z")


def _handoffs() -> list[tuple[tuple[str, str, str, str], str]]:
    """Every handoff file, keyed by the timestamp in its name."""
    if not os.path.isdir(HANDOFF_DIR):
        return []
    out = []
    for name in os.listdir(HANDOFF_DIR):
        if not (name.startswith("HANDOFF-") and name.endswith(".md")):
            continue
        m = _STAMP.search(name)
        if m:
            out.append((m.groups(), name))
    return sorted(out)


def test_current_state_names_the_newest_handoff():
    """The entry point must mention the newest handoff by filename.

    A string check, not a live probe: it catches the pointer going stale, which is
    what happened, and says nothing about whether the summary around it is true.
    """
    if not os.path.isfile(STATE):
        pytest.skip("CURRENT_STATE.md not present in this checkout")
    handoffs = _handoffs()
    if not handoffs:
        pytest.skip("no handoff files present in this checkout")

    newest = handoffs[-1][1]
    text = open(STATE, encoding="utf-8").read()
    assert newest in text, (
        f"CURRENT_STATE.md does not name the newest handoff ({newest}). "
        f"It is the fresh-AI entry point, so a fresh AI would not learn that "
        f"{newest} exists. Newest three: "
        f"{[n for _, n in handoffs[-3:]]}"
    )


def test_current_state_does_not_call_an_old_handoff_the_newest():
    """The specific defect, guarded directly.

    The file said "newest handoff" against a 2026-10-01 file for two days. Naming
    the newest one is not enough on its own — the *label* has to be on it.
    """
    if not os.path.isfile(STATE):
        pytest.skip("CURRENT_STATE.md not present in this checkout")
    handoffs = _handoffs()
    if not handoffs:
        pytest.skip("no handoff files present in this checkout")

    newest = handoffs[-1][1]
    text = open(STATE, encoding="utf-8").read()
    for line in text.splitlines():
        # Only lines that *name a handoff file* and call it the newest. Prose that
        # merely uses the phrase ("while the newest handoff on the branch was ...")
        # is not a pointer and must not trip this -- an over-broad guard that fails
        # on honest prose gets deleted, which is worse than not having it.
        if "newest handoff" not in line.lower():
            continue
        if not re.search(r"HANDOFF-[A-Za-z0-9._-]*\.md", line):
            continue
        assert newest in line, (
            f"a line calls itself the newest handoff but names a different file: "
            f"{line.strip()[:160]!r} (newest is {newest})"
        )
