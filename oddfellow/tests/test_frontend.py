"""
Offline guards for the front end.

Why this file exists
--------------------
Every front-end defect in this project so far was found by *looking* -- a human
on a phone, or an agent driving a browser. That is the same pattern as the
Worker drift: a whole artifact with no check, where the only detector is someone
noticing. Two of those defects are now known precisely enough to guard, and
both are the kind that return silently:

  1. **Doubled chip prefix.** `setBackendChip` used to prepend "Backend: " while
     every caller already supplied it, so the owner saw "Backend: Backend: off".
     The fix was to remove it from the function. Re-adding it looks harmless and
     is invisible until someone reads the chip.

  2. **Mic double-tap.** Calling `start()` while already listening raises
     InvalidStateError. On a phone a second tap is the most natural thing in the
     world, and it produced a silent console error with no feedback. The fix is
     a toggle with a re-entry guard and an `onend` that resets the flag.

These are static checks on `index.html`, not a browser harness. They are
deliberately *negative* assertions about the specific bug shapes -- "this must
not happen" -- rather than snapshots of the current code, so ordinary
refactoring does not trip them.

Each one is written to fail on the real defect and pass on the real fix. A guard
that cannot fail is worse than no guard, so the shapes are checked by injecting
the bug and confirming the failure (done when this file was written).
"""

from __future__ import annotations

import os
import re

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
FRONTEND = os.path.join(os.path.dirname(HERE), "frontend", "index.html")


def page() -> str:
    if not os.path.isfile(FRONTEND):
        pytest.skip("frontend/index.html not present in this checkout")
    return open(FRONTEND, encoding="utf-8").read()


def function_body(src: str, name: str) -> str:
    """Return the body of `function <name>(...) { ... }`, braces balanced."""
    start = src.index(f"function {name}(")
    open_brace = src.index("{", start)
    depth, i = 0, open_brace
    while i < len(src):
        if src[i] == "{":
            depth += 1
        elif src[i] == "}":
            depth -= 1
            if depth == 0:
                return src[open_brace : i + 1]
        i += 1
    raise AssertionError(f"unbalanced braces in {name}")


def call_sites(src: str, name: str) -> list[str]:
    """Every literal string passed as the first argument to `name(...)`."""
    return re.findall(rf"{name}\(\s*'([^']*)'", src)


# --------------------------------------------------------------------------- #
# 1. The chip prefix is supplied by callers, never by the function
# --------------------------------------------------------------------------- #

def test_set_backend_chip_does_not_add_the_prefix_its_callers_already_supply():
    src = page()
    body = function_body(src, "setBackendChip")
    assert "'Backend: '" not in body and '"Backend: "' not in body, (
        "setBackendChip is adding the 'Backend: ' prefix again, but every caller "
        "already supplies it -- this is the doubled-prefix defect. The owner "
        "would see 'Backend: Backend: off'."
    )


def test_the_chip_prefix_guard_is_not_vacuous():
    """If callers stopped supplying the prefix, the guard above would pass
    while the chip rendered bare text. Pin the other half of the invariant."""
    src = page()
    literals = call_sites(src, "setBackendChip")
    assert literals, "no literal setBackendChip call sites found to check"
    prefixed = [t for t in literals if t.startswith("Backend: ")]
    assert prefixed, (
        "no caller passes a 'Backend: ' prefixed string, so either the callers "
        "changed or the prefix moved -- the chip text is now unverified"
    )


# --------------------------------------------------------------------------- #
# 2. The mic is a toggle, bound once, and cannot be double-started
# --------------------------------------------------------------------------- #

def test_the_mic_is_not_bound_by_two_mechanisms():
    """`onclick=` replaces a handler; `addEventListener` adds one. Using both
    on the same element is how a single tap becomes two."""
    src = page()
    mic_refs = re.findall(r"\$\('mic'\)[^;\n]*", src)
    assert mic_refs, "no $('mic') references found"
    assigns = [r for r in mic_refs if ".onclick" in r]
    listeners = [r for r in mic_refs if ".addEventListener(" in r]
    assert not (assigns and listeners), (
        "the mic is bound with both onclick= and addEventListener -- one tap "
        "would run two handlers, which is the double-tap defect"
    )


def test_the_mic_handler_guards_against_starting_while_listening():
    """start() while listening raises InvalidStateError and used to fail
    silently. The handler must check the flag before starting."""
    src = page()
    match = re.search(r"\$\('mic'\)\.onclick\s*=\s*\(\)\s*=>\s*\{", src)
    assert match, "the mic onclick handler was not found"
    start = match.start()
    body = src[start : start + 700]
    assert "listening" in body, (
        "the mic handler no longer consults the listening flag -- a second tap "
        "will raise InvalidStateError with no feedback"
    )
    assert "r.stop()" in body, "the mic handler no longer stops an active session"
    assert "catch" in body, (
        "the mic handler no longer catches -- start() can throw on a phone and "
        "the failure must be visible, not silent"
    )


def test_recognition_end_resets_the_listening_flag():
    """A recognition that ends without a result must not leave the button stuck."""
    src = page()
    assert re.search(r"r\.onend\s*=\s*\(\)\s*=>\s*setListening\(false\)", src), (
        "r.onend no longer resets the listening flag -- the mic button can get "
        "stuck showing 'listening' after a recognition that produced no result"
    )


def test_voice_setup_runs_exactly_once():
    """setupVoice assigns the mic handler; running it twice is another way to
    double-bind."""
    src = page()
    calls = len(re.findall(r"(?<!function )setupVoice\(\)", src))
    assert calls == 1, f"setupVoice() is invoked {calls} times, expected exactly 1"


# --------------------------------------------------------------------------- #
# 3. The owner token is not written to storage unless asked for
# --------------------------------------------------------------------------- #

def test_the_owner_token_is_only_persisted_when_remember_is_set():
    """localStorage is readable by the third-party Puter SDK in this origin."""
    src = page()
    body = function_body(src, "saveBackend")
    assert re.search(r"if\s*\(\s*backend\.remember\s*\)", body), (
        "saveBackend no longer guards the token behind backend.remember -- the "
        "owner token would be written to localStorage unconditionally"
    )
    assert "rec.token" in body, "saveBackend no longer stores the token at all"
