#!/usr/bin/env python3
"""Run the Cognitive Capability Profile and print it.

    python3 oddfellow/cognition/run_profile.py [--json] [--live] [--repo PATH]

`--live` permits network probes (the deployed-commit check). Without it the
profile runs entirely offline and says so, rather than reporting a network
failure as a capability failure.

Exit status is 0 when the profile ran, 1 when it could not run at all. It is
deliberately NOT 1 for a low score: this is an instrument, not a gate, and
turning it into a gate would create pressure to move the numbers rather than
the behaviour.

Why there is no composite score
-------------------------------
Thirteen dimensions collapsed into one figure would invite exactly the claim the
directive forbids. The profile reports each dimension with its own evidence and
its own falsifier, and refuses to summarise them into a single number.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from oddfellow.cognition.profile import (  # noqa: E402
    Context,
    build_profile,
    render,
    summarise,
)


def _recorded_claims(repo_root: Path, memory_dir: Path | None) -> dict:
    """Claims the memory makes, so the profile can try to falsify them.

    Read from the memory files rather than hard-coded, so that when memory is
    corrected the check follows it instead of drifting from it.
    """
    claims: dict = {}
    if not memory_dir:
        return claims

    text = ""
    for rel in ("projects/oddfellow.md", "projects/oddfellow/cycles.md"):
        p = memory_dir / rel
        if p.exists():
            text += p.read_text(encoding="utf-8", errors="replace")

    import re

    # Take the LAST match, not the first. Memory is append-ordered, so the newest
    # claim is the one the system currently believes. Reading the first match
    # would compare today's reality against a claim from days ago and report a
    # failure that is not one.
    tests = re.findall(r"(\d{3,5})\s+(?:tests?\s+|checks?\s+)?pass", text)
    if tests:
        claims["test_count"] = int(tests[-1])

    deploys = re.findall(r"deployed[- ]commit[^0-9a-f]{0,40}([0-9a-f]{7,40})", text, re.I)
    if deploys:
        claims["deployed_commit"] = deploys[-1]

    # The recorded head must come from MEMORY, not from git. Reading it from git
    # and comparing it to git would be a check that cannot fail -- a tautology
    # dressed as a verification, which is the exact shape this project has had to
    # remove eleven times.
    heads = re.findall(r"\*\*Branch head:\*\*\s*`([0-9a-f]{7,40})`", text)
    if heads:
        claims["canonical_head"] = heads[-1]
    return claims


def main() -> int:
    ap = argparse.ArgumentParser(description="Cognitive Capability Profile")
    ap.add_argument("--json", action="store_true", help="emit machine-readable output")
    ap.add_argument("--live", action="store_true", help="allow network probes")
    ap.add_argument("--repo", default=None, help="repository root (default: infer)")
    ap.add_argument("--memory", default=os.environ.get("MEMORY_DIR"),
                    help="memory directory (default: $MEMORY_DIR)")
    args = ap.parse_args()

    repo_root = Path(args.repo).resolve() if args.repo else Path(__file__).resolve().parents[2]
    memory_dir = Path(args.memory) if args.memory else None

    ctx = Context(
        repo_root=repo_root,
        memory_dir=memory_dir,
        live=args.live,
        recorded_claims=_recorded_claims(repo_root, memory_dir),
    )

    try:
        measurements = build_profile(ctx)
    except Exception as exc:  # noqa: BLE001
        print(f"profile could not run: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(
            {"summary": summarise(measurements),
             "measurements": [m.as_dict() for m in measurements]},
            indent=2,
        ))
    else:
        print(render(measurements))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
