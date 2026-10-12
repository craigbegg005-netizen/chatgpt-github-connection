"""
The only surviving record of the lost codebase must stay in the repository.

Two Render services run a codebase whose source exists nowhere in version control
(see `projects/bsi-codebase-reconciliation.md` in agent memory). Until 2026-10-12 its
API surface lived only in `/root/workspace/capture/out/` -- a sandbox directory that is
not version-controlled and does not survive a sandbox reset. The surviving record of a
lost codebase was one reset away from being lost with it.

These are existence and shape checks, not content checks. They cannot tell whether the
captures are *accurate* -- nothing can, the source is gone. They can tell whether the
artifact is still here, which is the failure that actually happened.
"""

from __future__ import annotations

import json
import os

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
EVIDENCE = os.path.join(REPO, "oddfellow", "evidence", "lost-codebase-2026-10-01")

EXPECTED = [
    "README.md",
    "industries-v013.openapi.json",
    "industries-v013.root.html",
    "industries-v013.health.json",
    "industries-v013.ready.json",
    "core-v010.openapi.json",
    "core-v010.root.html",
    "core-v010.health.json",
    "core-v010.ready.json",
]


def test_the_lost_codebase_captures_are_still_here():
    if not os.path.isdir(EVIDENCE):
        pytest.fail(
            "the lost-codebase evidence directory is gone. It is the only surviving "
            "record of a codebase whose source is in no branch and no history."
        )
    missing = [n for n in EXPECTED if not os.path.isfile(os.path.join(EVIDENCE, n))]
    assert not missing, f"missing evidence files: {missing}"


def test_the_openapi_captures_are_real_documents():
    """A truncated or empty capture would satisfy a plain existence check."""
    for name in ("industries-v013.openapi.json", "core-v010.openapi.json"):
        path = os.path.join(EVIDENCE, name)
        if not os.path.isfile(path):
            pytest.skip(f"{name} not present in this checkout")
        with open(path, encoding="utf-8") as fh:
            doc = json.load(fh)
        assert isinstance(doc, dict), f"{name} is not a JSON object"
        assert doc.get("paths"), f"{name} has no paths, so it is not an API surface"
