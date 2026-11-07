"""Guards for internal consistency in the grants pipeline.

Why this file exists
--------------------
`GRANTS-NON-DILUTIVE-PIPELINE-2026-10-01.md` is long and is read in pieces: someone
skims the §1 summary table, or jumps to "Next actions". Twice now a *later, more
specific* finding in the same document has contradicted an earlier summary, with
nothing comparing them:

* 2026-11-07 — §1's table said "ELIGIBILITY UNKNOWN" and named "Next realistic target:
  March 4 2027", while the same section, forty lines below, recorded that the required
  Project Suitability Assessment is "very likely NOT clearable on the product framing".
  NSF's rule is that one "No" ends it. The Next-actions list had the same gap.
* The same shape appeared in `oddfellow/OWNER-ACTIONS.md` (guarded in
  `test_owner_actions.py`), where a card named the wrong machine for an allowlist.

The pattern is not "the document is wrong" — the document was right in the place where
the detail lived. It is that **a summary is a claim, and a claim nothing compares to its
source drifts.** These guards compare them.

Deliberately narrow: they assert that a recorded verdict is *referenced* by the summary
and the action list, not how either is worded. An over-broad guard that fails on honest
prose gets deleted, which is worse than not having one.
"""

from __future__ import annotations

import os
import re

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
GRANTS = os.path.join(REPO, "GRANTS-NON-DILUTIVE-PIPELINE-2026-10-01.md")

# Phrases that mean "this lane's suitability gate is recorded as failing".
_VERDICT_MARKERS = ("not clearable", "not open for oddfellow-as-a-product", "likely not open")


def _grants_text() -> str:
    if not os.path.isfile(GRANTS):
        pytest.skip("grants pipeline not present in this checkout")
    with open(GRANTS, encoding="utf-8") as fh:
        return fh.read()


def _nsf_section(text: str) -> str:
    m = re.search(r"(?m)^##\s*1\.\s*NSF.*?(?=^##\s|\Z)", text, re.S)
    return m.group(0) if m else ""


def _next_actions(text: str) -> str:
    m = re.search(r"(?m)^##\s*Next actions.*?(?=^##\s|\Z)", text, re.S)
    return m.group(0) if m else ""


def test_nsf_summary_references_the_suitability_verdict():
    """If a failing suitability verdict is recorded, §1's summary must say so.

    The summary is the first ~1,200 characters of the section — the status line and the
    table. That is what a skimmer reads.
    """
    text = _grants_text()
    if not any(m in text.lower() for m in _VERDICT_MARKERS):
        pytest.skip("no suitability verdict recorded in this checkout")

    nsf = _nsf_section(text)
    assert nsf, "no NSF section found in the grants pipeline"

    summary = nsf[:1200].lower()
    assert any(m in summary for m in _VERDICT_MARKERS), (
        "the NSF section records a failing suitability verdict further down, but its summary "
        "(status line + table) does not reference it. A reader of the summary alone would treat "
        "the lane as live. Say so in the summary, or remove the verdict."
    )


def test_next_actions_references_the_suitability_gate():
    """The action list must not read as though the NSF steps are free to take."""
    text = _grants_text()
    if not any(m in text.lower() for m in _VERDICT_MARKERS):
        pytest.skip("no suitability verdict recorded in this checkout")

    actions = _next_actions(text)
    assert actions, "no Next actions section found in the grants pipeline"

    assert any(m in actions.lower() for m in _VERDICT_MARKERS), (
        "the Next-actions list does not mention the suitability gate, so its NSF steps read as "
        "free to take when the lane is recorded as likely closed."
    )


def test_the_open_lanes_are_named_in_next_actions():
    """Control in the other direction: the list must still name what IS open.

    Without this, the two guards above could be satisfied by a list that says only what is
    closed — which would be a different way of being useless.
    """
    actions = _next_actions(_grants_text())
    if not actions:
        pytest.skip("no Next actions section in this checkout")

    lowered = actions.lower()
    assert "verizon" in lowered, "the Next-actions list no longer names Verizon"
    assert "emergent ventures" in lowered, (
        "the Next-actions list no longer names Emergent Ventures"
    )
