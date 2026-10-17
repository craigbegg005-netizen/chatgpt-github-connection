"""The queue tick: the thing that turns a durable queue into actual work.

The connector had a durable queue and **nothing draining it**. A job sat `READY`
forever unless a human remembered to run the CLI by hand, which means the queue was
storage rather than a workflow -- and a queue nobody drains is a queue that silently
grows.

This module is the smallest thing that fixes that: one idempotent tick, safe to run
on a schedule, that reports the queue and renders a handoff when there is work.

Three properties make it safe to automate, and each exists because of a specific way
scheduled work goes wrong:

  * **Idempotent.** It fingerprints the ready set and records it. Running it twice
    with no change does nothing the second time rather than rewriting the same
    document forever. A scheduled job that always does work is a scheduled job that
    floods.
  * **Quiet when there is nothing to do.** No ready jobs means no output file and a
    reason in the report -- not an empty document that looks like work.
  * **It does not decide anything.** It renders a handoff. It does not claim, approve,
    submit, or requeue. Those are the gates, and a background tick is exactly the
    wrong place to loosen them.

The handoff it writes is still human-mediated: the tick prepares the work, a person
carries it to an AI, and the reply comes back through `apply_handoff` with the same
enforcement as any other transport.
"""

from __future__ import annotations

import hashlib
import os
from datetime import datetime, timezone
from pathlib import Path

from .handoff import render_handoff
from .schema import canonical_provider
from .store import Store

#: Where the last rendered handoff's fingerprint is remembered.
FINGERPRINT_KEY = "worker.last_handoff_fingerprint"


def _fingerprint(document: str) -> str:
    """Digest the actual handoff, including recipient, input and saved progress."""
    return hashlib.sha256(document.encode("utf-8")).hexdigest()


def _handoff_path(out: Path, provider: str) -> Path:
    """Resolve the handoff filename, refusing anything that escapes ``out``.

    The provider id is interpolated into a filename, so it is an arbitrary-write
    primitive if it is not validated. The ``handoff-`` prefix blocks a leading
    ``..`` but not a later segment: ``provider="../../../tmp/pwn"`` resolved
    outside the output directory. ``canonical_provider`` rejects it outright, and
    the containment check below is the belt to that braces -- it catches a future
    caller that builds the path some other way.
    """
    provider = canonical_provider(provider)
    path = out / f"handoff-{provider}.md"
    resolved = path.resolve()
    if resolved.parent != out.resolve():
        raise ValueError(f"handoff path {resolved} escapes the output directory")
    return path


def tick(
    store: Store,
    provider: str,
    out_dir: str | os.PathLike[str],
    limit: int = 20,
) -> dict:
    """One idempotent pass. Returns a report; writes a handoff only when useful.

    Deliberately returns rather than prints, so the caller decides whether this is a
    scheduled run whose output goes to a log, or an operator asking what is pending.
    """
    provider = canonical_provider(provider)
    if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
        raise ValueError("limit must be a positive integer")
    ready = list(store.ready_jobs())[:limit]
    dead = store.dead_letter_report()
    paused = store.is_paused()

    report: dict = {
        "at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "provider": provider,
        "paused": paused,
        "ready": len(ready),
        "dead_letters": dead["count"],
        "rendered": None,
        "skipped": None,
    }

    if paused:
        # The emergency stop applies to preparation too. Rendering work for a
        # provider while the queue is paused would hand out jobs the system has
        # been told not to run.
        report["skipped"] = "emergency pause is set"
        return report

    if not ready:
        report["skipped"] = "no ready jobs"
        return report

    out = Path(out_dir)
    path = _handoff_path(out, provider)
    document = render_handoff(store, provider, limit=limit)
    digest = _fingerprint(document)
    # A durable flag can outlive an ephemeral output directory. Only skip when
    # the actual file also matches; otherwise restore missing or damaged output.
    try:
        file_matches = path.read_bytes() == document.encode("utf-8")
    except FileNotFoundError:
        file_matches = False
    if store.flag_get(FINGERPRINT_KEY) == digest and file_matches:
        report["skipped"] = "identical to the last handoff; not rewritten"
        return report

    out.mkdir(parents=True, exist_ok=True)
    path.write_text(document, encoding="utf-8")

    store.flag_set(FINGERPRINT_KEY, digest)
    store.audit(
        "worker",
        "worker.handoff_rendered",
        provider=provider,
        jobs=len(ready),
        fingerprint=digest,
        path=str(path),
    )
    report["rendered"] = str(path)
    report["fingerprint"] = digest
    return report


def reset_fingerprint(store: Store) -> None:
    """Forget the last fingerprint, so the next tick renders even if unchanged.

    This is an explicit operator override. Content changes and missing or damaged
    output files already trigger a refresh without resetting this flag.
    """
    store.flag_set(FINGERPRINT_KEY, "")
