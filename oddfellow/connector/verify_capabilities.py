"""Manual capability-detection harness -- run deliberately, never in CI.

The connector's central rule is that a capability is only routable once it has
been *observed*. That rule is worthless if the detection path itself has never
been executed, so this script exists to run it against something real.

It is NOT part of the offline test suite. The tests must stay deterministic and
credential-free; this needs a live server and a real connection, and it is
therefore a thing a human runs on purpose.

    python -m connector.verify_capabilities --list
    python -m connector.verify_capabilities --probe stripe-mcp

What it does and does not do:

  * it calls the probe, records the returned evidence string verbatim, and prints
    what was observed;
  * it makes NO writes, spends nothing, and touches no owner data;
  * a probe that fails records nothing. Silence is not evidence of absence, but it
    is also not evidence of presence, and this harness refuses to guess between
    the two -- which is the exact confusion that cost this project 20 hours.

Exit code is 0 when at least one capability was verified, 1 when none were, so a
caller can tell "proved nothing" from "proved something".
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from typing import Callable

from .providers import Capability, Provider, detect_http_liveness
from .schema import TaskKind, Transport


def _run(cmd: list[str], timeout: int = 30) -> tuple[int, str]:
    """Run a command, returning (returncode, combined output). Never raises on failure."""
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout, check=False
        )
        return proc.returncode, (proc.stdout or "") + (proc.stderr or "")
    except FileNotFoundError as exc:
        return 127, f"command not found: {exc}"
    except subprocess.TimeoutExpired:
        return 124, f"timed out after {timeout}s"


def probe_stripe_mcp() -> tuple[bool, str]:
    """Probe the Stripe MCP server through the local MCP client.

    Read-only: it lists the accounts visible to this session. No writes, no
    charges, and the response contains only account identifiers and a livemode
    flag, which is exactly the kind of evidence a capability record should carry.
    """
    code, out = _run(
        ["letta", "mcp", "call", "mcp__BeggAi__list_available_accounts_or_orgs",
         "--args", "{}"]
    )
    if code != 0:
        return False, f"mcp call exited {code}"
    if '"isError": true' in out or '"tool_not_found"' in out:
        return False, "mcp call reported an error"
    # The MCP client returns its payload as an escaped JSON string inside a JSON
    # envelope, so the useful keys arrive as \"accounts\" rather than "accounts".
    # Matching on the bare word is deliberate: it is the only form that survives
    # both the escaped and unescaped renderings.
    if "accounts" not in out:
        return False, "mcp call returned no accounts payload"
    # Report what was observed, not merely that something answered. The livemode
    # flag is the part that matters: it is what makes "no live charge is possible
    # from this connection" a verified statement rather than an inherited one.
    count = out.count("stripe_context")
    live = "true" if ('"livemode\\":true' in out or '"livemode":true' in out) else "false"
    return True, f"mcp call ok; {count} account(s) visible; livemode={live}"


#: Named probes. Add one per provider as real credentials arrive. A provider with
#: no entry here simply stays unverified, which is the honest default.
PROBES: dict[str, Callable[[], tuple[bool, str]]] = {
    "stripe-mcp": probe_stripe_mcp,
}

#: Which capability each probe, when it succeeds, is evidence FOR.
PROBE_CLAIMS: dict[str, tuple[Transport, frozenset[TaskKind]]] = {
    "stripe-mcp": (Transport.MCP, frozenset({TaskKind.EXTERNAL_ACTION, TaskKind.ANALYSIS})),
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--probe", help="name of the probe to run")
    parser.add_argument("--list", action="store_true", help="list available probes")
    args = parser.parse_args(argv)

    if args.list or not args.probe:
        print("available probes:")
        for name in PROBES:
            transport, kinds = PROBE_CLAIMS[name]
            print(f"  {name:14s} -> {transport.value:8s} {sorted(k.value for k in kinds)}")
        return 0

    if args.probe not in PROBES:
        print(f"unknown probe: {args.probe}", file=sys.stderr)
        return 2

    transport, kinds = PROBE_CLAIMS[args.probe]
    provider = Provider(
        name=args.probe,
        label=args.probe,
        declared=(Capability(transport, kinds, "declared for detection"),),
    )

    print(f"probing {args.probe} for {transport.value} ...")
    detect_http_liveness(provider, transport, PROBES[args.probe])

    if transport in provider.verified:
        print(f"  VERIFIED  {transport.value}: {provider.verified[transport]}")
        print(f"  routable: {provider.supports(transport, TaskKind.EXTERNAL_ACTION)}")
        return 0

    print("  NOT VERIFIED -- nothing recorded. This is not proof the provider is")
    print("  down; it is proof we did not observe it. The registry stays honest.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
