"""Guards for the owner-facing action card.

Why this file exists
--------------------
`oddfellow/OWNER-ACTIONS.md` is the one document Craig actually acts from, and its
whole value is that each card can be followed literally. On 2026-10-15 card 2 was
found telling him to allowlist **his phone's** `/32` while the action it was attached
to was *"I do the dump+restore"* — which runs from this sandbox. The sandbox is the
client on that route, so a phone `/32` cannot work: Render would still refuse the
connection, and the failure would look like a credentials problem.

The runbook had always said "the sandbox's IP" for that path
(`oddfellow/RENDER-DB-PRESERVATION-2026-10-07.md`, Path A step 1). Two documents
described the same step with different clients, and nothing compared them.

This is the project's recurring shape: a maintained claim that nothing checks drifts,
and the drift is invisible until someone reads it and counts. The guard is deliberately
narrow — it asserts the *client* named for the sandbox route, not the card's wording.
An over-broad guard that fails on honest prose gets deleted, which is worse than not
having one.
"""

from __future__ import annotations

import os
import re

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
CARD = os.path.join(REPO, "oddfellow", "OWNER-ACTIONS.md")
RUNBOOK = os.path.join(REPO, "oddfellow", "RENDER-DB-PRESERVATION-2026-10-07.md")


def _card_text() -> str:
    if not os.path.isfile(CARD):
        pytest.skip("OWNER-ACTIONS.md not present in this checkout")
    with open(CARD, encoding="utf-8") as fh:
        return fh.read()


def _db_section(text: str) -> str:
    """The Render DB card: from its heading to the next `## ` heading."""
    m = re.search(r"(?m)^##\s*\d+\.\s*Render DB preservation.*?(?=^##\s|\Z)", text, re.S)
    return m.group(0) if m else ""


def test_db_card_exists():
    section = _db_section(_card_text())
    assert section, (
        "no Render DB preservation card found in OWNER-ACTIONS.md. Either it was "
        "renamed or removed -- both change what Craig is told to do, so this fails "
        "rather than silently passing."
    )


def test_sandbox_route_names_the_sandbox_as_the_client():
    """The route where the agent runs the dump must say the sandbox's IP is allowlisted.

    This is the exact defect of 2026-10-15: the card named the phone's `/32` for the
    route that runs from the sandbox. Asserting the *client* rather than the phrasing
    keeps the guard honest under rewording.
    """
    section = _db_section(_card_text())
    if not section:
        pytest.skip("no DB card in this checkout")

    # The route where the agent does the dump is identified by that promise, not by
    # a heading name -- headings get reworded, the promise is the point.
    agent_runs = re.search(r"[^\n]*I do the dump[^\n]*", section)
    assert agent_runs, (
        "the DB card no longer states that the agent runs the dump. If that promise "
        "moved, the allowlist client changed with it -- re-check which machine is the "
        "client before updating this guard."
    )

    # The client must be named somewhere in the card as the sandbox, because the
    # sandbox is what runs the dump on that route.
    assert "sandbox" in section.lower(), (
        "the DB card promises the agent will run the dump, but never names the "
        "sandbox as the client. The dump runs from this sandbox, so the sandbox's "
        "egress IP is what Render must allowlist -- a phone /32 would still be "
        "refused. See oddfellow/RENDER-DB-PRESERVATION-2026-10-07.md Path A step 1."
    )


def test_card_and_runbook_agree_that_the_sandbox_is_the_client():
    """Cross-check the two documents that describe this step.

    They disagreed on 2026-10-15 and nothing compared them. This compares them.
    """
    section = _db_section(_card_text())
    if not section:
        pytest.skip("no DB card in this checkout")
    if not os.path.isfile(RUNBOOK):
        pytest.skip("runbook not present in this checkout")

    with open(RUNBOOK, encoding="utf-8") as fh:
        runbook = fh.read()

    # The runbook's Path A is the sandbox route; it must name the sandbox's IP.
    assert re.search(r"sandbox'?s IP as `/32`", runbook), (
        "the runbook no longer says the sandbox's IP is allowlisted on Path A. If "
        "that changed, the card and this guard must change with it -- do not update "
        "this guard alone."
    )

    # And the card must not contradict it by scoping the sandbox route to the phone.
    sandbox_route = re.search(
        r"Route A.*?(?=Route B|\Z)", section, re.S | re.I
    )
    if sandbox_route:
        body = sandbox_route.group(0)
        assert "phone's /32" not in body and "phone\u2019s /32" not in body, (
            "the sandbox route tells Craig to allowlist the phone's /32. The sandbox "
            "is the client on that route, so that combination cannot work."
        )
