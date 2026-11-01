"""Offline, read-only SQLite preservation. No provider calls or schema migrations.

Run: python -m connector.snapshot --source queue.db --destination private/queue.sqlite
The snapshot contains private queue data; keep it outside public repositories.
"""
from __future__ import annotations

import argparse
from contextlib import closing
import hashlib
import json
import math
import os
from pathlib import Path
import sqlite3
import tempfile
import time


def snapshot(source: str | Path, destination: str | Path, *, timeout: float = 30) -> dict:
    """Publish a checked, mode-0600 snapshot without replacing any destination.

    SQLite's backup API includes committed WAL pages. The source is opened in
    read-only mode and never initialized or migrated through Store. Publication
    uses a same-directory hard link so readers see a complete file and competing
    writers cannot overwrite one another. A trusted local filesystem supporting
    hard links and fsync is required. This is not encryption or an off-host backup.
    """
    if isinstance(timeout, bool) or not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("timeout must be finite and positive")
    source = Path(source).resolve(strict=True)
    destination = Path(destination).absolute()
    if not source.is_file():
        raise ValueError("source must be an existing SQLite file")
    if os.path.lexists(destination):
        raise FileExistsError("destination already exists")
    deadline = time.monotonic() + timeout

    def progress(status, remaining, total):
        if time.monotonic() >= deadline:
            raise TimeoutError("snapshot exceeded timeout")

    fd, temporary = tempfile.mkstemp(prefix=".oddfellow-snapshot-", dir=destination.parent)
    os.close(fd)  # mkstemp creates a private 0600 file even with a permissive umask.
    temporary = Path(temporary)
    try:
        with closing(sqlite3.connect(source.as_uri() + "?mode=ro", uri=True)) as src:
            with closing(sqlite3.connect(temporary)) as dst:
                src.backup(dst, pages=128, progress=progress, sleep=0.01)
                if dst.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
                    raise ValueError("snapshot integrity check failed")
        digest = hashlib.sha256()
        with temporary.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
            os.fsync(stream.fileno())
        size = temporary.stat().st_size
        os.link(temporary, destination)  # Atomic no-clobber, including dangling symlinks.
        directory_fd = os.open(destination.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
        return {"status": "snapshot_verified", "bytes": size,
                "sha256": digest.hexdigest(), "integrity_check": "ok"}
    finally:
        temporary.unlink(missing_ok=True)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True)
    parser.add_argument("--destination", required=True)
    parser.add_argument("--timeout", type=float, default=30)
    args = parser.parse_args(argv)
    try:
        result = snapshot(args.source, args.destination, timeout=args.timeout)
    except (OSError, ValueError, sqlite3.Error):
        # Do not print DB content, connection details, or private filesystem paths.
        print(json.dumps({"status": "failed", "reason":
                          "check source, unused destination, directory permissions and timeout"}))
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
