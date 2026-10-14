#!/usr/bin/env python3
"""Cross-branch pointer drift check.

Three times now a pointer file has named an old report while newer work sat
unreferenced on the same branch (CURRENT_STATE.md vs handoffs; the README's
alphabetical "finder"; CHATGPT-SYNC-LATEST.md). The in-repo guard
(test_handoff_pointer.py) can only see the branch it runs on, so it never
fires for a pointer on the *coordination* branch. This script closes that
gap: it reads the coordination branch from the local remote ref (run after
`git fetch`; no network needed itself) and reports, for each known pointer
file, what it names versus what the branch's newest handoff actually is.

Exit 0 = no drift detected. Exit 1 = at least one pointer looks stale.
This is a REPORT: "newest by commit time" is not always the file a pointer
should name (a return-channel test is not a sync report), so a mismatch is
a prompt to look, not proof of error. The cost asymmetry is deliberate:
a false positive costs one look; a missed drift cost us three incidents.
"""

from __future__ import annotations

import re
import subprocess
import sys

BRANCH = "origin/coordination/oddfellow-chatgpt-sync"
#: (pointer file, glob-ish prefix of the handoffs it points at, human meaning)
POINTERS = (
    ("oddfellow/CHATGPT-SYNC-LATEST.md", ("CHATGPT-", "SYNC-"), "latest ChatGPT sync report"),
)


def git(*args: str) -> str:
    out = subprocess.run(
        ["git", *args], capture_output=True, text=True, check=False
    )
    if out.returncode != 0:
        sys.exit(f"git {' '.join(args)} failed: {out.stderr.strip()}")
    return out.stdout


def handoffs_with_commit_time() -> list[tuple[int, str]]:
    """Every file under oddfellow/handoffs/, newest-commit-first."""
    names = [
        n for n in git("ls-tree", "--name-only", BRANCH, "oddfellow/handoffs/").split()
        if n.endswith(".md")
    ]
    stamped = []
    for name in names:
        ts = git("log", "-1", "--format=%ct", BRANCH, "--", name).strip()
        # Basenames: ls-tree returns full paths, pointer files link by basename.
        stamped.append((int(ts or 0), name.rsplit("/", 1)[-1]))
    return sorted(stamped, reverse=True)


def pointer_target(pointer_path: str) -> str | None:
    try:
        body = git("show", f"{BRANCH}:{pointer_path}")
    except SystemExit:
        return None
    m = re.search(r"handoffs/([A-Za-z0-9._-]+\.md)", body)
    return m.group(1) if m else None


def main() -> int:
    stamped = handoffs_with_commit_time()
    if not stamped:
        print("no handoffs on branch -- nothing to check")
        return 0
    drift = False
    for pointer_path, prefixes, meaning in POINTERS:
        target = pointer_target(pointer_path)
        candidates = [(ts, n) for ts, n in stamped if n.startswith(prefixes)]
        if not candidates:
            candidates = stamped  # fall back to any handoff
        newest_ts, newest = candidates[0]
        status = "OK" if target == newest else "DRIFT?"
        if target != newest:
            drift = True
        print(f"{status}: {pointer_path}")
        print(f"      points at            : {target or '(nothing found)'}")
        print(f"      newest by commit time: {newest}  ({meaning})")
    return 1 if drift else 0


if __name__ == "__main__":
    sys.exit(main())
