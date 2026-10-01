"""Operator command line for the connector.

The structured handoff is the one path that works today, and until this module
existed it was a library with no command -- which means "usable" only in the sense
that a programmer could write the three lines to call it. The workflow in the
cross-AI handoff (render -> paste into an AI -> paste the reply back) needs to be
something an operator can actually run.

    python -m connector.cli --db state.db jobs
    python -m connector.cli --db state.db handoff --provider claude > to-claude.md
    python -m connector.cli --db state.db apply --provider claude --file reply.md
    python -m connector.cli --db state.db dead-letters
    python -m connector.cli --db state.db connect --provider claude --scopes read
    python -m connector.cli --db state.db disconnect --provider claude --reason "rotating"

Three properties are deliberate:

  * **`connect` prints a token once and never again.** It is not stored anywhere the
    CLI can read back, so a lost token is reissued rather than recovered.
  * **The owner master token is never accepted as a connector credential.** If it is
    present in the environment it is loaded *only* so it can be refused by value.
  * **`apply` is not a bypass.** It goes through the same claim and approval
    enforcement as every other transport; the CLI adds convenience, not authority.

Stdlib only.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

from .handoff import apply_handoff, render_handoff
from .lifecycle import connect_provider, disconnect_provider
from .schema import Status
from .store import Store
from .tokens import Scope, TokenStore


def _open(path: str) -> tuple[Store, TokenStore]:
    store = Store(path)
    # The owner token is loaded ONLY so verify() can refuse it by value. It is
    # never stored, never logged, and never compared as a valid credential.
    tokens = TokenStore(store._conn, owner_token=os.environ.get("ODDFELLOW_OWNER_TOKEN", ""))
    return store, tokens


def _emit(value) -> None:
    print(json.dumps(value, indent=2, default=str))


def cmd_jobs(store, tokens, args) -> int:
    status = Status(args.status) if args.status else None
    jobs = store.jobs(status)
    _emit([
        {
            "job_id": j.job_id,
            "title": j.title,
            "kind": j.kind.value,
            "risk": j.risk.value,
            "status": j.status.value,
            "provider": j.provider,
            "attempts": j.attempts,
            "verified": j.verified,
        }
        for j in jobs
    ])
    return 0


def cmd_handoff(store, tokens, args) -> int:
    # Printed to stdout so it can be redirected straight into a file to paste.
    sys.stdout.write(render_handoff(store, args.provider, limit=args.limit))
    return 0


def cmd_apply(store, tokens, args) -> int:
    if args.file:
        with open(args.file, encoding="utf-8") as fh:
            text = fh.read()
    else:
        text = sys.stdin.read()
    report = apply_handoff(
        store, text, provider=args.provider, actor=args.provider, approved=args.approved
    )
    _emit(report)
    # A refusal is a normal outcome, but it is not a success: exit non-zero so a
    # script cannot treat "nothing was accepted" as "done".
    return 0 if report["accepted"] and not report["refused"] else 1


def cmd_dead_letters(store, tokens, args) -> int:
    _emit(store.dead_letter_report())
    return 0


def cmd_requeue(store, tokens, args) -> int:
    job = store.requeue(args.job_id, actor=args.actor, reason=args.reason)
    _emit({"job_id": job.job_id, "status": job.status.value})
    return 0


def cmd_connect(store, tokens, args) -> int:
    scopes = {Scope(s.strip()) for s in args.scopes.split(",") if s.strip()}
    plaintext, summary = connect_provider(tokens, args.provider, scopes, note=args.note)
    summary["token"] = plaintext
    _emit(summary)
    print(
        "\nThis token is shown ONCE and is not recoverable. Put it in the provider,\n"
        "not in a document, a chat, or this repository.",
        file=sys.stderr,
    )
    return 0


def cmd_tokens(store, tokens, args) -> int:
    _emit([
        {
            "token_id": t.token_id,
            "provider": t.provider,
            "scopes": sorted(s.value for s in t.scopes),
            "revoked": t.revoked,
            "created_at": t.created_at,
        }
        for t in tokens.list_tokens()
    ])
    return 0


def cmd_disconnect(store, tokens, args) -> int:
    report = disconnect_provider(store, tokens, args.provider, actor=args.actor, reason=args.reason)
    _emit(report.as_dict())
    return 0 if report.clean else 1


def cmd_audit(store, tokens, args) -> int:
    _emit(store.audit_trail(limit=args.limit))
    return 0


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="connector", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", required=True, help="path to the connector SQLite file")
    sub = ap.add_subparsers(dest="command", required=True)

    p = sub.add_parser("jobs", help="list jobs")
    p.add_argument("--status", help="filter by status")
    p.set_defaults(fn=cmd_jobs)

    p = sub.add_parser("handoff", help="print a handoff document for a provider")
    p.add_argument("--provider", required=True)
    p.add_argument("--limit", type=int, default=20)
    p.set_defaults(fn=cmd_handoff)

    p = sub.add_parser("apply", help="apply a provider's reply")
    p.add_argument("--provider", required=True)
    p.add_argument("--file", help="read the reply from a file instead of stdin")
    p.add_argument("--approved", action="store_true",
                   help="the owner has approved high/critical work in this batch")
    p.set_defaults(fn=cmd_apply)

    p = sub.add_parser("dead-letters", help="show jobs that exhausted their retries")
    p.set_defaults(fn=cmd_dead_letters)

    p = sub.add_parser("requeue", help="revive a dead-lettered job")
    p.add_argument("--job-id", required=True)
    p.add_argument("--reason", required=True)
    p.add_argument("--actor", default="owner")
    p.set_defaults(fn=cmd_requeue)

    p = sub.add_parser("connect", help="issue a scoped token for a provider")
    p.add_argument("--provider", required=True)
    p.add_argument("--scopes", default="read", help="comma-separated: read,claim,submit,audit,approve")
    p.add_argument("--note", default="")
    p.set_defaults(fn=cmd_connect)

    p = sub.add_parser("tokens", help="list connector tokens (never their values)")
    p.set_defaults(fn=cmd_tokens)

    p = sub.add_parser("disconnect", help="revoke a provider's tokens and release its claims")
    p.add_argument("--provider", required=True)
    p.add_argument("--reason", default="")
    p.add_argument("--actor", default="owner")
    p.set_defaults(fn=cmd_disconnect)

    p = sub.add_parser("audit", help="show the audit trail")
    p.add_argument("--limit", type=int, default=30)
    p.set_defaults(fn=cmd_audit)

    return ap


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    store, tokens = _open(args.db)
    try:
        return args.fn(store, tokens, args)
    except (KeyError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    finally:
        store.close()


if __name__ == "__main__":
    raise SystemExit(main())
