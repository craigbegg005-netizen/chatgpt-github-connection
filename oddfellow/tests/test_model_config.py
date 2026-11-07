"""The model handle must have one source, not four hardcoded copies.

Why this file exists
--------------------
The agent's configured model was retired on 2026-11-07 (`letta/auto` is no longer among
the handles the API returns), and the handle was hardcoded in **four places across three
files** -- `rehearsal.sh`, `rehearsal_watchdog.sh` and `fault_injection_check.py`. Applying
the fix therefore meant editing all four consistently, and any one of them left behind
would keep a retired handle alive on one path while the others moved on. That is the
divergence mechanism this project has paid for repeatedly: two copies of a rule drift.

The runtime sites now read a single `ODDFELLOW_MODEL` environment variable, defaulting to
the current value, so applying a model decision is one setting rather than four edits.

These guards hold that property. They do NOT assert which model is configured -- that is
Craig's decision, and a guard that pinned a handle would have to be edited to change it,
which is the problem being solved.
"""

from __future__ import annotations

import os
import re

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
ODDFELLOW = os.path.join(REPO, "oddfellow")

# Files that configure the model a running process actually uses.
RUNTIME_SITES = (
    os.path.join(ODDFELLOW, "rehearsal.sh"),
    os.path.join(ODDFELLOW, "rehearsal_watchdog.sh"),
    os.path.join(ODDFELLOW, "fault_injection_check.py"),
)


def _read(path: str) -> str:
    if not os.path.isfile(path):
        pytest.skip(f"{os.path.basename(path)} not present in this checkout")
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def test_runtime_sites_read_the_shared_model_variable():
    """Every runtime site must consult ODDFELLOW_MODEL, not a bare literal."""
    for path in RUNTIME_SITES:
        text = _read(path)
        assert "ODDFELLOW_MODEL" in text, (
            f"{os.path.basename(path)} configures a model without reading ODDFELLOW_MODEL. "
            "A hardcoded handle here is a fourth copy of a value that has to change in "
            "lockstep with the others -- see oddfellow/evidence/MODEL-RETIRED-2026-11-07.md."
        )


def test_no_runtime_site_hardcodes_a_model_handle():
    """A literal handle assigned to LETTA_MODEL is the defect this guards.

    Only the *assignment* is checked, not any mention of a handle in prose or in a
    comment -- an over-broad guard that fails on honest text gets deleted.
    """
    literal = re.compile(r"""LETTA_MODEL\s*[=:]\s*["']?[A-Za-z0-9._/-]+["']?""")
    for path in RUNTIME_SITES:
        text = _read(path)
        for m in literal.finditer(text):
            line = m.group(0)
            assert "ODDFELLOW_MODEL" in line, (
                f"{os.path.basename(path)} assigns a literal model handle ({line!r}). "
                "It must come from ODDFELLOW_MODEL so one setting moves every path."
            )


def test_the_default_is_still_present_so_nothing_changes_silently():
    """Control: the variable must have a default, or an unset env breaks the rehearsal.

    Without this, a future edit could make the variable mandatory and turn a missing
    setting into a startup failure rather than a fallback.
    """
    for path in RUNTIME_SITES:
        text = _read(path)
        if "ODDFELLOW_MODEL" not in text:
            continue
        assert re.search(r"ODDFELLOW_MODEL\s*:?-", text) or "get(" in text, (
            f"{os.path.basename(path)} reads ODDFELLOW_MODEL with no default. An unset "
            "variable must fall back to the previous value, not break the run."
        )
