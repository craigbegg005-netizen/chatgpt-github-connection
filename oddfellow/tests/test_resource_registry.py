"""
The resource registry must say when it was last verified, and that date must be recent.

`RESOURCES.md` opens with "Last verification sweep: <date>", and its whole value rests on
that date being true. The file's own header says *"Do not guess resource locations — if a
value here is not marked VERIFIED, treat it as reported and re-check before relying on
it"*, which only works if a reader can trust the date. On 2026-10-12 it was seven days old
and nothing noticed.

This cannot check whether the sweep actually happened — no test can. It checks the one
thing that is mechanically checkable: the date is present, parseable, not in the future,
and not older than the threshold below. A registry that has not been re-verified in a
month is not a registry; it is a document that reads like one.
"""

from __future__ import annotations

import datetime as dt
import os
import re

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
REGISTRY = os.path.join(REPO, "RESOURCES.md")

# Generous on purpose: this should fire on neglect, not on a busy week.
MAX_AGE_DAYS = 30

_STAMP = re.compile(
    r"Last verification sweep:\s*\*\*(\d{4})-(\d{2})-(\d{2}) (\d{2}):(\d{2}) UTC\*\*"
)


def test_registry_verification_date_is_present_and_fresh():
    if not os.path.isfile(REGISTRY):
        pytest.skip("RESOURCES.md not present in this checkout")

    with open(REGISTRY, encoding="utf-8") as fh:
        text = fh.read()

    m = _STAMP.search(text)
    assert m, (
        "RESOURCES.md carries no parseable 'Last verification sweep: **YYYY-MM-DD HH:MM UTC**' "
        "date. Without it a reader cannot tell whether the registry is current."
    )

    stamped = dt.datetime(*(int(g) for g in m.groups()), tzinfo=dt.timezone.utc)
    now = dt.datetime.now(dt.timezone.utc)

    assert stamped <= now + dt.timedelta(hours=1), (
        f"the registry's verification date ({stamped:%Y-%m-%d %H:%M} UTC) is in the future. "
        "A date that cannot have happened is worse than no date."
    )

    age = now - stamped
    assert age <= dt.timedelta(days=MAX_AGE_DAYS), (
        f"the resource registry was last verified {age.days} days ago "
        f"({stamped:%Y-%m-%d %H:%M} UTC), over the {MAX_AGE_DAYS}-day limit. Re-probe the "
        "rows by actual request and update the date — a stale registry reads exactly like "
        "a current one."
    )
