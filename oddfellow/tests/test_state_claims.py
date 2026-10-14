"""Guards for prose state-claims in CURRENT_STATE.md.

The verification_discipline instrument (oddfellow/cognition/profile.py) found
these claims unguarded on 2026-10-08: prose asserting a current fact that no
test would notice going stale. The most drift-prone is the test count, which has gone stale at least three
times ("579" when it was 636, "636" when it was 666, "666" when it was 682).
On 2026-10-11 the guard caught two changes at commit time -- six new tests took the
suite to 706, and a seventh to 707 -- each time failing until the constant and
CURRENT_STATE.md were updated together, which is the behaviour it exists for.

RUN IT FROM THE REPO ROOT. The canonical invocation collects both test roots
(`oddfellow/tests` and `oddfellow/connector/tests`) and totals ~706 items. A run
scoped to `oddfellow/tests` alone collects ~529, which is under the 600-item
threshold below -- so the binding assertion *skips* and a green result means
nothing. That is the documented trade-off, not a bug, but it is a trap: on
2026-10-11 a partial run made this guard look inert and the "700 tests pass"
claim look fabricated. It was neither.

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

EXPECTED_TEST_COUNT = 758


def _claimed_count() -> int:
    """The claim, written as `**N tests pass**`.

    Anchored on the bold form deliberately. The first version matched any
    `N tests pass` anywhere in the file, which made the guard read *prose about*
    a claim as the claim itself: on 2026-10-12 a sentence recording that the
    entry point "still claimed *674 tests pass*" was picked up as the current
    claim, and the guard failed against a file whose real claim was correct.
    A false alarm here is not harmless -- it sends the next session to "fix" a
    number that is already right.
    """
    text = (Path(__file__).resolve().parents[2] / "CURRENT_STATE.md").read_text(
        encoding="utf-8"
    )
    m = re.search(r"\*\*(\d[\d,]*)\s+tests?\s+pass\*\*", text)
    assert m, (
        "CURRENT_STATE.md carries no '**N tests pass**' claim to guard. The "
        "claim must be written in bold so this guard can tell it apart from "
        "prose that merely mentions a test count."
    )
    return int(m.group(1).replace(",", ""))


def test_claimed_count_reads_the_claim_not_a_mention_of_it() -> None:
    """Falsifier for the guard's own pattern.

    Without this, a future rewording of `_claimed_count` could quietly go back to
    matching any mention, and the guard would fail on files that are correct.
    """
    sample = (
        "Prose: the heading still claimed *674 tests pass* and the service was down.\n"
        "The claim: **718 tests pass** -- run pytest from the repo root.\n"
    )
    m = re.search(r"\*\*(\d[\d,]*)\s+tests?\s+pass\*\*", sample)
    assert m, "the anchored pattern found no claim in the fixture"
    assert m.group(1) == "718", (
        f"the pattern read {m.group(1)!r} instead of the bold claim 718 -- it is "
        "matching a mention of a claim again"
    )


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


# --- the "latest cycle" heading must not carry a bumpable date ----------------

_LATEST_HEADING = re.compile(r"^#+\s*.*LATEST.*CYCLE.*$", re.MULTILINE)
_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")


def test_latest_cycle_heading_carries_no_date() -> None:
    """The heading must not carry a date that automation can advance alone.

    Why this guard exists
    ---------------------
    The heading read `LATEST CYCLE — <date>`, and every hourly sweep bumped that
    date while leaving the body untouched. By 2026-10-12 the heading claimed
    23:00 *that day* over a body written on **2026-10-07** (`d222849`) that still
    said "674 tests pass" and "the rehearsal is DOWN" — both false by then.
    Nothing caught it: the handoff-pointer guard checks a different line, and the
    test-count guard reads the whole file, so it saw the (correct) count in a
    different section.

    The rule is deliberately mechanical rather than "keep the two in sync". The
    sweeps that bumped the heading were not lying; they were updating the only
    field they knew how to update. A heading is a label, and a label that
    automation can advance independently of its content is a claim of recency the
    content does not support. Removing the bumpable field removes the failure
    mode; asking for discipline does not.
    """
    text = (Path(__file__).resolve().parents[2] / "CURRENT_STATE.md").read_text(
        encoding="utf-8"
    )
    m = _LATEST_HEADING.search(text)
    assert m, "CURRENT_STATE.md has no 'LATEST ... CYCLE' heading to guard"
    assert not _DATE.search(m.group(0)), (
        f"the latest-cycle heading carries a date ({m.group(0).strip()!r}). A "
        "date in the heading can be bumped by a sweep while the body stays put, "
        "which is how this heading came to claim 2026-10-12 over 2026-10-07 "
        "content. Put the date in the body instead."
    )
