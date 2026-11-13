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

EXPECTED_TEST_COUNT = 808


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
    m = re.search(r"\*\*(\d[\d,]*)\s+tests?\s+(?:pass|collected)\*\*", text)
    assert m, (
        "CURRENT_STATE.md carries no bold test count (pass or collected) to guard. The "
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


# --- The coordination status carries the same claim, and was outside this guard ---
#
# It is described as "the single source for cross-AI state", so a stale count there
# misleads every other AI reading it -- and it had drifted to 780 while the suite grew
# to 797, because this guard only ever looked at CURRENT_STATE.md.
#
# That is the third instance of one flaw in this project's guards: coverage narrower
# than the defect class. A guard that reports green over a file it never opens is worse
# than no guard, because it says the claim is checked when it is not.


def _coordination_status_count():
    """The count in the coordination status's `Test suite` row."""
    path = Path(__file__).resolve().parents[2] / "oddfellow" / "COORDINATION-STATUS.md"
    if not path.is_file():
        return None
    text = path.read_text(encoding="utf-8")
    m = re.search(r"\|\s*Test suite\s*\|\s*\*\*(\d[\d,]*)\s+passed", text)
    return int(m.group(1).replace(",", "")) if m else None


def test_coordination_status_count_matches_the_guard_constant():
    claimed = _coordination_status_count()
    if claimed is None:
        return  # the row is absent in this checkout; nothing to contradict
    assert claimed == EXPECTED_TEST_COUNT, (
        f"COORDINATION-STATUS.md says {claimed} tests passed but the suite is "
        f"{EXPECTED_TEST_COUNT}. That file is the cross-AI source of truth, so a stale "
        "count there misleads every other reader. Update both in the same commit."
    )


# --- The hand-maintained-value class -----------------------------------------
#
# Four separate documents in this repo carried a value derived from state that was
# maintained by hand, and every one of them went stale:
#
#   1. the DB card's day-countdown ("13 days")            -> an absolute timestamp
#   2. the coordination status's test count (780 vs 805)  -> guarded by the count guard
#   3. CURRENT_STATE.md's header date (5 weeks stale)     -> derived from git
#   4. the coordination status's stamp AND canonical SHA  -> derived from git
#
# Finding them one at a time cost four cycles. The rule that covers all four is:
# **a value derived from state must be derived, or not written.** This guard covers the
# one form that is mechanically detectable -- a bold date stamp in a document that is
# meant to stay current.
#
# Dated SNAPSHOT documents are exempt, and the filename is what says so: a file called
# `...-2026-10-13.md` is a record of that day, and a date inside it is a fact about the
# record, not a claim about now. A file with no date in its name is a living document,
# and a stamp in it will drift the moment nobody updates it.

# Two forms, because the first version of this guard only caught one and the README
# slipped through: its stale date was in a HEADING ("## Current state - re-verified
# 2026-10-02"), not in a bold field. A guard that catches one form of the defect and
# not the other reports green over the case that actually occurred.
_STAMP_FIELD = re.compile(
    r"(?m)^\*\*(Date|Last verified|Last updated|Updated|As of):\*\*"
)
# Narrowed after the first widening: a heading like "## Branch map (verified 2026-10-01)"
# LABELS A SNAPSHOT and is legitimate -- the date is a fact about the record. A heading
# like "## Current state -- re-verified 2026-10-02" CLAIMS CURRENTNESS and will drift.
# The wording is what separates them, so the guard keys on the freshness words.
# Third form, found the same way as the second: this one was inline prose --
# "Last updated **2026-10-14**" -- which is neither a bold field nor a heading.
#
# THREE widenings, each finding real cases, is the honest signal here: **this guard is a
# net, not a proof.** It catches the forms that have occurred. The rule that actually
# covers the class is the one a human applies -- derive the value, or do not write it --
# and the guard exists to catch the cases where that rule was forgotten in a form I have
# already seen. Do not read a green run as "no hand-maintained dates anywhere".
# Fourth form, found the same way: "Verified by: Oddfellow, 2026-09-30" in the deploy doc.
# Each widening has found a real case, which is why the net is worth keeping -- and why
# the honest claim about it stays "catches the forms seen", not "catches the class".
# Lines that record a defect rather than asserting one.
_CORRECTION_MARKERS = (
    "corrected", "read \"", "this header read", "this line carried", "removed",
    "no date stamp", "derive it", "do not trust", "was wrong", "used to read",
)

_INLINE_DATE = re.compile(
    r"(?i)\b(?:last updated|last verified|last checked|verified by)\b[^\n]{0,40}"
    r"(?:\*\*)?\d{4}-\d{2}-\d{2}"
)
_HEADING_DATE = re.compile(
    r"(?m)^#{1,4}\s.*\b(?:current|re-verified|last updated|updated)\b.*\d{4}-\d{2}-\d{2}",
    re.IGNORECASE,
)
_DATED_FILENAME = re.compile(r"\d{4}-\d{2}-\d{2}")


def _living_markdown_files():
    root = Path(__file__).resolve().parents[2]
    for path in root.rglob("*.md"):
        parts = set(path.parts)
        if parts & {".git", ".venv", "node_modules", "__pycache__"}:
            continue
        if _DATED_FILENAME.search(path.name):
            continue  # a dated snapshot; a date inside it is not a claim about now
        yield path


def test_living_documents_do_not_carry_hand_maintained_date_stamps():
    offenders = []
    for path in _living_markdown_files():
        text = path.read_text(encoding="utf-8", errors="replace")
        for m in list(_STAMP_FIELD.finditer(text)) + list(_HEADING_DATE.finditer(text)) \
                + list(_INLINE_DATE.finditer(text)):
            # A line that RECORDS the defect is not the defect. Correction notes quote the
            # old stamp ("this header read 'Last verified: 2026-11-07'"), and a guard that
            # fails on those gets deleted the first time it is useful -- the same
            # instructions-vs-mentions distinction the phone guard needed.
            line = text[:m.start()].rsplit("\n", 1)[-1]
            if line.lstrip().startswith(">"):
                # Correction notes are blockquotes by convention in this repo, and the
                # marker word is often on the PREVIOUS line of the same note -- which is
                # why the per-line marker check alone missed this one.
                continue
            if any(marker in line.lower() for marker in _CORRECTION_MARKERS):
                continue
            offenders.append(f"{path.name}: {m.group(0).strip()[:90]}")

    assert not offenders, (
        "these documents are meant to stay current but carry a hand-maintained date "
        "stamp, which goes stale the moment nobody updates it:\n  "
        + "\n  ".join(offenders)
        + "\n\nFix it one of two ways: derive the value (e.g. "
        "`git log -1 --format=%ad --date=iso -- <file>`), or put the date in the "
        "filename and let the document be a dated snapshot. Do not leave a stamp that "
        "nothing updates."
    )


# --- The README carries the count too, and was outside this guard ---------------
#
# It called itself "the front door for every branch" and claimed 232 tests against a suite
# of 806 -- six weeks of drift, in the first document a cold reader opens. The count guard
# read CURRENT_STATE.md and the coordination status; the front door was never checked.
#
# That is the fourth time coverage has been narrower than the class in this repo's guards,
# so it is worth naming: a guard that reports green over a file it never opens is worse
# than no guard, because it says the claim is checked when it is not.


def _readme_counts():
    """Every test-count claim in a README TABLE ROW.

    The first version matched only the `| Tests |` row, and the README carried a SECOND
    stale count in the Branches table ("109 backend + 123 connector = 232 tests") that it
    never saw. Same coverage mistake, in the same file, one row apart.

    Scoped to table rows on purpose: prose may legitimately quote an OLD count when
    recording a correction, and a guard that fails on honest prose gets deleted.
    """
    path = Path(__file__).resolve().parents[2] / "README.md"
    if not path.is_file():
        return []
    found = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.lstrip().startswith("|"):
            continue
        for m in re.finditer(r"(\d[\d,]*)\s+tests?\b", line, re.IGNORECASE):
            found.append((int(m.group(1).replace(",", "")), line.strip()[:80]))
    return found


def test_every_readme_table_count_matches_the_guard_constant():
    offenders = [
        (n, where) for n, where in _readme_counts() if n != EXPECTED_TEST_COUNT
    ]
    assert not offenders, (
        "README.md carries test counts that disagree with the suite "
        f"({EXPECTED_TEST_COUNT}):\n  "
        + "\n  ".join(f"{n} tests -- {where}" for n, where in offenders)
        + "\n\nThe README is the front door for every branch, so a stale count there "
        "misleads a cold reader before they open anything else. Update every occurrence "
        "in the same commit."
    )


# --- The Gate A requirement must not be stated as two variables ----------------
#
# FIVE documents described the Gate A owner action as "two secrets" or "the two variables":
# the owner card, the coordination status, the README, the deploy doc and the acceptance
# checklist. The branch requires THREE -- LETTA_MODEL is the third -- so every one of them
# would have sent the owner to set two variables and still find the service fail-closed.
#
# Found one document per cycle for five cycles, which is the same lesson as the stamp guard:
# fix the pattern, not the instance. This flags a line that names both of the older two
# variables, names no LETTA_MODEL, and reads as an INSTRUCTION.
#
# Two deliberate exclusions, because both occur legitimately:
#   * a line carrying a date is a historical record ("on 2026-09-30 the missing pair was ...")
#   * a line quoting live output is describing the DEPLOYED build, which genuinely needs two
_REQUIREMENT_VERB = re.compile(r"\b(?:set|add|enter|must|need|require)\b", re.IGNORECASE)
_HAS_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")


def test_no_living_doc_states_gate_a_as_two_variables():
    offenders = []
    for path in _living_markdown_files():
        text = path.read_text(encoding="utf-8", errors="replace")
        for line in text.splitlines():
            if "LETTA_API_KEY" not in line or "ODDFELLOW_OWNER_TOKEN" not in line:
                continue
            if "LETTA_MODEL" in line:
                continue
            if _HAS_DATE.search(line):
                continue  # a dated record, not an instruction
            if "checks_failed" in line or "livez" in line.lower():
                continue  # quoting the deployed build, which does need only two
            if not _REQUIREMENT_VERB.search(line):
                continue
            offenders.append(f"{path.name}: {line.strip()[:100]}")

    assert not offenders, (
        "these lines tell a reader to set only LETTA_API_KEY and ODDFELLOW_OWNER_TOKEN, but "
        "the branch requires LETTA_MODEL as well:\n  " + "\n  ".join(offenders)
        + "\n\nAdd LETTA_MODEL, or mark the line as a dated historical record."
    )
