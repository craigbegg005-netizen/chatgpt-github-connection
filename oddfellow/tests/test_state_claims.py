"""Guards for prose state-claims in CURRENT_STATE.md.

The verification_discipline instrument (oddfellow/cognition/profile.py) found
these claims unguarded on 2026-10-08: prose asserting a current fact that no
test would notice going stale. The most drift-prone is the test count, which
has gone stale at least three times ("579" when it was 636, "636" when it was
666, "666" when it was 682).

The property guarded, in both directions:

1. CURRENT_STATE.md's "N tests pass" equals EXPECTED_TEST_COUNT.
2. EXPECTED_TEST_COUNT equals the number of tests actually collected, when the
   full suite is running. Without this second assertion the constant can drift
   from reality while the first check stays green -- a guard that compares the
   prose to a number nobody verifies is a proxy, and this project has been
   burned by proxies before.

The constant stays in the file (rather than deriving everything live) because
the verification_discipline instrument defines "guarded" as "a test file
contains the claimed value" -- the literal number must exist somewhere for the
instrument to see the guard at all.

Update rule: when the suite grows, update EXPECTED_TEST_COUNT and
CURRENT_STATE.md in the same commit. A session that updates one without the
other fails here.
"""

import re
from pathlib import Path

EXPECTED_TEST_COUNT = 700


def _claimed_count() -> int:
    text = (Path(__file__).resolve().parents[2] / "CURRENT_STATE.md").read_text(
        encoding="utf-8"
    )
    m = re.search(r"(\d[\d,]*)\s+tests?\s+pass", text)
    assert m, "CURRENT_STATE.md carries no 'N tests pass' claim to guard"
    return int(m.group(1).replace(",", ""))


def test_entry_point_test_count_matches_guard_constant() -> None:
    claimed = _claimed_count()
    assert claimed == EXPECTED_TEST_COUNT, (
        f"CURRENT_STATE.md claims {claimed} tests pass but the guard expects "
        f"{EXPECTED_TEST_COUNT}. One of the two was updated without the other -- "
        "which is exactly the drift this guard exists to catch. Update both in "
        "the same commit."
    )


def test_guard_constant_matches_real_collection(request) -> None:
    """The constant must equal the real collected count, or the guard above is
    comparing the prose to a number nobody verifies.

    Only asserted when the full suite is running (the canonical invocation
    covers both oddfellow/tests and connector/tests, which is hundreds of
    items); a partial run skips rather than fails spuriously.
    """
    collected = len(request.session.items)
    if collected < 600:
        import pytest
        pytest.skip(
            f"partial run ({collected} items); the equality check only binds "
            "the full-suite invocation"
        )
    assert collected == EXPECTED_TEST_COUNT, (
        f"the suite now collects {collected} tests but the guard constant says "
        f"{EXPECTED_TEST_COUNT}. The constant drifted from reality: update "
        "EXPECTED_TEST_COUNT and CURRENT_STATE.md together."
    )
