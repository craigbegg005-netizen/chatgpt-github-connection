"""
The recovered API surfaces must stay on the canonical branch.

Why this file exists
--------------------
Three services run code whose **source exists nowhere** — it was never in version
control and cannot be reconstructed. The only surviving record of what those
services actually expose is the OpenAPI document each one serves, captured into
`recovered/`.

Until 2026-10-12 those captures lived **only** on a side branch,
`letta/recovered-api-surface`. A fresh reader of canonical could not see them at
all, and a routine branch cleanup would have deleted the last record of that
source. Nothing would have noticed: no test read either location.

The captures were verified accurate on 2026-10-12 by canonical-JSON SHA256
against the live services — all three hash-identical. That verification is worth
exactly as much as the files' continued presence, which is what this guards.

Why the assertions are shaped this way
--------------------------------------
Not "the file exists". A truncated or empty capture is a file that exists, and
this project has been burned by existence-as-evidence before (see the false
control ledger — a `pg_dump` that aborts *after* creating its output file). So
each capture must parse as JSON, carry a non-empty `paths` object, and report the
version its filename claims. `test_the_guard_would_catch_an_empty_capture` is the
negative control: without it, a green result could just mean the check never
looks at anything.
"""

from __future__ import annotations

import json
import os

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
RECOVERED = os.path.join(REPO, "recovered")

# filename -> the version the capture must report
CAPTURES = {
    "begg-core-v0.13.0-openapi.json": "0.13.0",
    "begg-core-v0.12.1-openapi.json": "0.12.1",
    "oddfellow-personal-v0.16-openapi.json": "0.16.0",
}


def _load(name: str) -> dict:
    path = os.path.join(RECOVERED, name)
    assert os.path.isfile(path), (
        f"{name} is missing from the canonical branch. These captures are the only "
        "surviving record of source that exists nowhere else -- if they moved to a "
        "side branch, bring them back rather than deleting this test."
    )
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def test_recovered_directory_is_on_canonical() -> None:
    assert os.path.isdir(RECOVERED), (
        "recovered/ is absent from canonical. It holds the only record of three "
        "services' API surfaces; their source is not in version control anywhere."
    )
    assert os.path.isfile(os.path.join(RECOVERED, "README.md"))


@pytest.mark.parametrize("name", sorted(CAPTURES))
def test_capture_is_a_real_openapi_document(name: str) -> None:
    """Parses, and actually describes an API -- not an empty or truncated file."""
    doc = _load(name)
    paths = doc.get("paths")
    assert isinstance(paths, dict) and paths, (
        f"{name} parses but carries no paths. A capture that exists and is empty is "
        "the failure mode this check is for."
    )
    assert doc.get("openapi") or doc.get("swagger"), (
        f"{name} has no openapi/swagger version key -- it is not an OpenAPI document"
    )


@pytest.mark.parametrize("name,version", sorted(CAPTURES.items()))
def test_capture_reports_the_version_its_filename_claims(name: str, version: str) -> None:
    """Catches a swapped or mislabelled capture, which a size check cannot."""
    doc = _load(name)
    reported = str(doc.get("info", {}).get("version", ""))
    assert reported == version, (
        f"{name} claims version {version} in its name but reports {reported!r}. One "
        "of the two is wrong, and the filename is what a reader trusts."
    )


def test_the_guard_would_catch_an_empty_capture() -> None:
    """Negative control: prove the assertions above can actually fail.

    A guard whose condition cannot vary is worse than no guard, because it
    manufactures confidence. This feeds the same predicates an empty document.
    """
    empty = {"openapi": "3.0.0", "info": {"version": "0.0.0"}, "paths": {}}
    with pytest.raises(AssertionError):
        paths = empty.get("paths")
        assert isinstance(paths, dict) and paths, "no paths"
