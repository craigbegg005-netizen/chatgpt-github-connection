"""The tool-invocation audit corpus -- the evidence source for tool_selection_accuracy.

Why this module exists
----------------------
`tool_selection_accuracy` sat in UNMEASURABLE with the reason "no audit corpus of
tool invocations is available in this environment". That reason was honest: the
dimension cannot be measured until invocations are recorded somewhere durable,
with their outcomes, in a form a measurement can re-derive without trusting
anyone's narrative. This module is that somewhere.

What it deliberately is
-----------------------
A JSONL append log. One line per invocation:

    {"ts": "...", "tool": "...", "first_attempt_success": true|false, "note": "..."}

JSONL rather than JSON because a corpus is appended to constantly and rewritten
never; a file that must be re-serialised on every write is a file that drifts.
Append-only is the same discipline the cycle log follows.

What it deliberately is NOT
---------------------------
Not a claim that the recorded invocations are representative. A corpus records
what was recorded; selection bias in what gets logged is a real limitation and
the measurement says so in its own evidence rather than leaving it to a reader.

It never claims consciousness, sentience, or self-awareness. It records
computational behaviour -- which tool was invoked and whether it worked.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

#: Where the corpus lives inside the repo. Under version control so it survives
#: a sandbox reset -- the same "done is not shipped" lesson the goal register
#: encodes. A corpus that dies with the sandbox is not a corpus.
CORPUS_RELATIVE = Path("oddfellow/cognition/tool_invocations.jsonl")

#: Below this many entries the corpus cannot support a fraction. Ten is
#: arbitrary and the measurement says the actual count in its evidence; the
#: floor exists so that a corpus of two lines does not produce a confident 0.5.
MIN_CORPUS_SIZE = 10


def record_invocation(
    path: Path,
    tool: str,
    first_attempt_success: bool,
    note: str = "",
) -> dict[str, Any]:
    """Append one invocation to the corpus. Returns the entry written.

    The caller records the outcome honestly, including failures -- a corpus
    that only logs successes is not an audit, it is advertising.
    """
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "tool": tool,
        "first_attempt_success": bool(first_attempt_success),
        "note": note,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, sort_keys=True) + "\n")
    return entry


def load_corpus(path: Path) -> list[dict[str, Any]]:
    """Read the corpus. A missing file is an empty corpus, not an error.

    Malformed lines are dropped rather than fatal: a corpus that crashes its
    reader on one bad line teaches the logger to stop logging.
    """
    if not path.exists():
        return []
    entries: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(entry, dict) and "first_attempt_success" in entry:
            entries.append(entry)
    return entries
