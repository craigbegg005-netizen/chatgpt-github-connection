"""Manual local integration probes. No background processes or auto-connections.

Run from oddfellow/: python -m connector.integrations --help
"""
from __future__ import annotations

import argparse
import json
import sys

from . import IntegrationUnavailable, LocalInference, LocalSearch


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Oddfellow opt-in loopback integrations")
    commands = parser.add_subparsers(dest="command", required=True)
    models = commands.add_parser("models", help="List models advertised by a local server")
    models.add_argument("--endpoint", default="http://127.0.0.1:8080/v1")

    chat = commands.add_parser("chat", help="Explicit single chat using a locally verified model")
    chat.add_argument("--endpoint", default="http://127.0.0.1:8080/v1")
    chat.add_argument("--model", required=True)
    chat.add_argument("--prompt", required=True)
    chat.add_argument("--confirm-local", action="store_true", help="I verified this model runs locally, not through a cloud proxy")
    chat.add_argument("--max-tokens", type=int, default=512)

    search = commands.add_parser("search", help="Query a self-hosted SearXNG server (requires Internet upstream)")
    search.add_argument("--endpoint", default="http://127.0.0.1:8888")
    search.add_argument("--query", required=True)
    search.add_argument("--limit", type=int, default=8)

    args = parser.parse_args(argv)
    try:
        if args.command == "models":
            result = {"status": "observed_local_endpoint", "models": LocalInference(args.endpoint).models()}
        elif args.command == "chat":
            if not args.confirm_local:
                parser.error("chat requires --confirm-local; verify the server is not routing to paid cloud models")
            response = LocalInference(args.endpoint, allowed_models=(args.model,)).chat(
                args.model, args.prompt, max_tokens=args.max_tokens)
            result = {"status": "unverified_model_output", "model": args.model, "text": response}
        else:
            result = {"status": "unverified_search_leads", "results": LocalSearch(args.endpoint).search(
                args.query, limit=args.limit)}
    except (IntegrationUnavailable, ValueError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}), file=sys.stderr)
        return 1
    print(json.dumps({"ok": True, **result}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
