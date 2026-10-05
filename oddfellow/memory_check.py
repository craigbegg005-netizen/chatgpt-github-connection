#!/usr/bin/env python3
"""Check memory files against the per-file character limit.

Why this exists
---------------
On 2026-10-05 two memory files sat at **55 and 90 characters of headroom** and
nothing in the system would have said so. The failure mode is not exotic: the
next session appends an entry, the write is refused or the file is silently
oversize, and the cost lands on whoever is mid-task at that moment -- which is
what produced the conflict this was written after resolving.

The project's own rule is: *before writing a claim about the state of a system,
ask what would break if it became wrong; if nothing checks it, add a check.*
File size had no check. This is it.

The unit is CHARACTERS, not bytes
---------------------------------
`wc -c` counts bytes. The limit is characters. These files carry emoji and em
dashes, which are 3 bytes each in UTF-8, so a byte count overstates the real
figure by roughly 1.6% -- enough to make a file look over the limit when it is
not, and to make "55 characters of headroom" look like more than it is.

I got this wrong on 2026-10-04, wrote the lesson down, and then reached for
`wc -c` again on 2026-10-05. So this script prints the unit next to every number
it reports, rather than trusting the next reader to remember.

Exit status: 0 if every file fits, 1 if any file is over the limit.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

#: The limit the Letta harness enforces per memory file, in CHARACTERS.
LIMIT = 20000

#: Headroom below which a file is reported as due a trim. A file that fits is not
#: a file that is fine: the point of warning early is to avoid the wall entirely,
#: because hitting it costs whoever is mid-task at that moment.
TIGHT = 500


def character_count(path: Path) -> int:
    """Characters, not bytes. See the module docstring for why that matters."""
    return len(path.read_text(encoding="utf-8"))


def scan(memory_dir: Path, limit: int = LIMIT, tight: int = TIGHT) -> dict:
    """Measure every markdown file. Returns a report; does not raise."""
    rows = []
    for path in sorted(memory_dir.rglob("*.md")):
        if ".git" in path.parts:
            continue
        n = character_count(path)
        rows.append({
            "path": str(path.relative_to(memory_dir)),
            "characters": n,
            "headroom": limit - n,
            "over": n > limit,
            "tight": limit - n < tight,
        })
    rows.sort(key=lambda r: r["headroom"])
    return {
        "limit": limit,
        "unit": "characters",
        "files": rows,
        "over": [r for r in rows if r["over"]],
        "tight": [r for r in rows if r["tight"] and not r["over"]],
    }


def render(report: dict) -> str:
    lines = [f"memory file sizes (limit {report['limit']} {report['unit']})", ""]
    for r in report["files"]:
        if r["over"]:
            mark = "OVER "
        elif r["tight"]:
            mark = "TIGHT"
        else:
            mark = "     "
        lines.append(f"  {mark} {r['characters']:>6} {report['unit']:<10} headroom {r['headroom']:>6}  {r['path']}")
    lines.append("")
    if report["over"]:
        lines.append(f"FAIL: {len(report['over'])} file(s) over the limit")
    else:
        lines.append("OK: every file is within the limit")
    if report["tight"]:
        lines.append(
            f"WARN: {len(report['tight'])} file(s) close to the limit and due a trim "
            "before the next append:"
        )
        for r in report["tight"]:
            lines.append(f"  {r['path']} — {r['headroom']} {report['unit']} left")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument(
        "--memory-dir",
        default=os.environ.get("MEMORY_DIR"),
        help="memory directory to scan (default: $MEMORY_DIR)",
    )
    p.add_argument("--limit", type=int, default=LIMIT)
    p.add_argument("--tight", type=int, default=TIGHT,
                   help="headroom below which a file is reported as due a trim")
    args = p.parse_args(argv)

    if not args.memory_dir:
        print("MEMORY_DIR is not set and --memory-dir was not given", file=sys.stderr)
        return 2
    root = Path(args.memory_dir)
    if not root.is_dir():
        print(f"not a directory: {root}", file=sys.stderr)
        return 2

    report = scan(root, limit=args.limit, tight=args.tight)
    print(render(report))
    return 1 if report["over"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
