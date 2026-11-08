"""The acceptance harness must name the cause of a failure it can see.

Why this file exists
--------------------
The retired-model failure (2026-11-07) reached the harness as:

    [FAIL] message: real reply   HTTP 502 in 0.8s | None

The real message -- *"letta/auto is no longer available. Select a hosted model using
credits or connect an external provider."* -- was in the response body the whole time
and was never printed. Diagnosing it meant calling the endpoint by hand with the right
header, which cost an hour that the harness could have saved.

`_error_hint` now walks the body for the deepest error string and the failure detail
includes it. These tests hold two properties: it FINDS the real cause in the shape the
backend actually returns, and it INVENTS nothing when there is no cause to report --
the second matters more, because a diagnostic that guesses is worse than one that stays
quiet.
"""

from __future__ import annotations

import importlib.util
import os

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
HARNESS = os.path.join(REPO, "oddfellow", "acceptance_check.py")


def _harness():
    if not os.path.isfile(HARNESS):
        pytest.skip("acceptance_check.py not present in this checkout")
    spec = importlib.util.spec_from_file_location("_acceptance_check", HARNESS)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_finds_the_cause_in_the_real_retired_model_body():
    """The exact body the backend returned on 2026-11-07."""
    body = {
        "detail": {
            "error": "letta_message_failed",
            "status": 400,
            "detail": {
                "error": (
                    "letta/auto is no longer available. Select a hosted model using "
                    "credits or connect an external provider."
                ),
                "reasons": ["model-retired"],
            },
        }
    }
    hint = _harness()._error_hint(body)
    assert "no longer available" in hint, (
        "the helper did not reach the deepest error string, so the harness would still "
        f"report a bare 502. Got: {hint!r}"
    )
    # The outer wrapper is less useful than the inner cause; preferring the longest
    # string is what picks the specific one.
    assert hint != "letta_message_failed", (
        "the helper returned the outer wrapper instead of the specific cause"
    )


@pytest.mark.parametrize("body", [None, {}, [], "", {"ok": True}, {"reply": "hi"}])
def test_invents_nothing_when_there_is_no_cause(body):
    """A diagnostic that guesses is worse than one that stays quiet."""
    assert _harness()._error_hint(body) == ""


def test_is_bounded():
    """A pathological body must not produce an unbounded detail line."""
    deep = {"detail": {"detail": {"detail": {"detail": {"detail": {"detail": {"detail": {
        "error": "x" * 5000}}}}}}}}
    hint = _harness()._error_hint(deep)
    assert len(hint) <= 240, f"hint was not truncated: {len(hint)} chars"
