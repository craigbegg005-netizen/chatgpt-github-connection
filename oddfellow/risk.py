"""Server-side risk classification for owner commands.

This module is the **authority** on whether an owner message is elevated risk.
It exists because the previous design classified risk only in the browser, and a
browser is not a security boundary: anything that talks to the API directly
steps around it. See ``SECURITY-REVIEW-2026-10-02.md`` finding 1.

The front end keeps a copy of these rules so it can colour the plan chip and
decide whether to pre-create an approval *without* a round trip. That copy is a
UX hint, never the enforcement. If the two ever disagree, the server wins and
the front end recovers by creating the approval the server asked for -- so
drift is self-healing rather than a silent hole. ``tests/test_risk.py`` asserts
the two agree on a corpus, so drift is also caught in CI.

Risk is about what the owner is *asking for*, not what the sentence mentions.
A bare substring match flagged "what is the zero-spend rule?" as elevated
because it contains "spend". Two rules fix that: questions are excluded, and
the terms are actionable verbs rather than topic words.
"""

from __future__ import annotations

import re

# A question is not a command. Matched at the start, or by a trailing "?".
_ASKING = re.compile(
    r"^\s*(what|how|why|when|where|who|which|is|are|does|do|can|could|should"
    r"|explain|tell me|describe|show me)\b"
)
_QUESTION_TAIL = re.compile(r"\?\s*$")

# Actionable terms: things that change state outside this chat.
_RISKY = re.compile(
    r"\b(delete|remove|erase|publish|post to|send (an? )?(email|message|money|payment)"
    r"|spend|buy|purchase|pay|transfer|deploy to production|production deploy"
    r"|password|credential|api key|payment)\b"
)

NORMAL = "normal"
ELEVATED = "elevated"


def is_elevated(text: str) -> bool:
    """True when this text is an elevated-risk command.

    Fail-closed in the direction that matters: a non-string or empty input is
    *not* elevated (there is nothing to authorise), but any text that matches an
    actionable term and is not a question is elevated.
    """
    if not isinstance(text, str):
        return False
    lowered = text.lower()
    if _ASKING.search(lowered) or _QUESTION_TAIL.search(lowered):
        return False
    return bool(_RISKY.search(lowered))


def classify(text: str) -> str:
    """Return ``"elevated"`` or ``"normal"``."""
    return ELEVATED if is_elevated(text) else NORMAL
