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
#
# This is an allowlist of *verbs*, and an allowlist is incomplete by
# construction. It catches intent expressed in English and misses everything
# expressed as code -- see _DESTRUCTIVE_CODE below, which is the second layer
# and exists because a QA pass found `rm -rf / --no-preserve-root` classified
# "normal" and forwarded to Letta with no approval at all.
_RISKY = re.compile(
    r"\b(delete|remove|erase|publish|post to|send (an? )?(email|message|money|payment)"
    r"|spend|buy|purchase|pay|transfer|deploy to production|production deploy"
    r"|password|credential|api key|payment"
    # Added 2026-10-02 after QA showed these were classified normal:
    r"|wipe|exfiltrate|destroy|drain|revoke|terminate|overwrite|uninstall"
    r"|wire (the )?(money|funds)|empty (the )?(account|table)"
    r")\b"
)

# Structural: input that is *code*, not prose.
#
# The verb allowlist above cannot see these, because the destructive part is a
# flag, a pipe, or a keyword rather than an English verb. This layer is still a
# heuristic and still incomplete -- it is not a sandbox and must not be
# described as one. What it does is close the class QA demonstrated: a command
# whose danger is structural rather than lexical.
#
# The honest limit: this cannot be made complete by adding patterns. The real
# fix is to gate the *actions* (the agent's tools) rather than to classify free
# text, which is option (b) in SECURITY-REVIEW-2026-10-02.md and remains open.
_DESTRUCTIVE_CODE = re.compile(
    r"(?:"
    r"\brm\s+-[a-z]*[rf]"                          # rm -rf, rm -fr
    r"|\brm\s+.*\s-[a-z]*[rf]"
    r"|\bdrop\s+(?:table|database|schema|index)\b"
    r"|\btruncate\s+table\b"
    r"|\bdelete\s+from\b"
    r"|\bupdate\s+\w+\s+set\b"
    r"|\bgit\s+push\b[^\n]*--force\b"
    r"|\bgit\s+reset\s+--hard\b"
    r"|\bgit\s+clean\s+-[a-z]*[fd]"
    r"|\bgit\s+branch\s+-d\b"                    # -d and -D both, post-lowercase
    r"|\bmkfs(?:\.\w+)?\b"                       # mkfs, mkfs.ext4
    r"|\bdd\b[^\n]*\bof=/dev/"
    r"|\bchmod\s+(?:-r\s+)?777\b"
    r"|\bchown\s+(?:-r\s+)?root\b"
    r"|\b(?:shutdown|reboot|halt|poweroff)\b"
    r"|\b(?:curl|wget)\b[^\n|]*\|\s*(?:ba|z|k|da)?sh\b"   # curl … | bash
    r"|:\(\)\s*\{.*\}\s*;\s*:"                # fork bomb (no \b: ':' is not a word char)
    r"|\btruncate\s+-s\s*0\b"
    r"|>\s*/dev/sd[a-z]"
    r"|\bkill\s+-9\s+-1\b"
    r"|\bsudo\s+rm\b"
    r")"
)

NORMAL = "normal"
ELEVATED = "elevated"


def is_elevated(text: str) -> bool:
    """True when this text is an elevated-risk command.

    Two layers, either of which is enough:

    1. an actionable English verb, and not a question;
    2. a structural destructive pattern (``rm -rf``, ``DROP TABLE``,
       ``curl … | bash``), which is checked **before** the question rule.

    Layer 2 deliberately ignores the question exemption. ``"what does rm -rf /
    do?"`` is a question and is not gated -- but ``"rm -rf /"`` is not a
    question, and a command that *contains* a question mark should not be
    excused by it. Ordering the structural check first means the exemption
    cannot be used as a bypass.

    Fail-closed in the direction that matters: a non-string or empty input is
    *not* elevated (there is nothing to authorise).
    """
    if not isinstance(text, str):
        return False
    lowered = text.lower()
    if _DESTRUCTIVE_CODE.search(lowered):
        # A *leading* interrogative still excuses it -- "what does rm -rf do?"
        # is a question. A trailing "?" alone does not: "rm -rf / ?" is a
        # command, and letting a stray question mark excuse a destructive
        # pattern would make the exemption a bypass.
        return not _ASKING.search(lowered)
    if _ASKING.search(lowered) or _QUESTION_TAIL.search(lowered):
        return False
    return bool(_RISKY.search(lowered))


def classify(text: str) -> str:
    """Return ``"elevated"`` or ``"normal"``."""
    return ELEVATED if is_elevated(text) else NORMAL
