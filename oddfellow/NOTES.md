# Oddfellow Letta backend v0.20.3

> 🔴 **HISTORICAL — superseded. Do not use this as current state.** Written 2026-09-29/30 about
> v0.20.3, when v0.20.2 was the only deployed build. Since then: the code reports **0.20.6**,
> the live service is **`oddfellow-letta-backend-v0206`** (`/livez` → 200, `ready:false`), and
> the test count is **109 backend + 123 connector**. This file is kept for the v0.20.3 design
> notes (conversation rotation, SSE parsing, `/healthz` fail-closed); it is not current status.
> See `README.md` and `CURRENT_STATE.md`.

Written and tested by Oddfellow (Letta agent), 2026-09-29 → 2026-09-30.

**Status:** v0.20.2 is 🚀 **DEPLOYED** at
`https://oddfellow-letta-poc.onrender.com` (deploy `dep-dau5m8ee0cbs73d9qcjg`,
promoted by ChatGPT through Render) and its API version was independently
verified against the live OpenAPI document. It is **NOT acceptance-LIVE**: its
service environment is missing `LETTA_API_KEY` and/or `ODDFELLOW_OWNER_TOKEN`, so
`/healthz` returns `{"ok": false}`.

**v0.20.3** (this branch) is 🛠 IMPLEMENTED + 🧪 TESTED locally, NOT deployed.

A FastAPI service that holds the Letta API key server-side and mediates between
the Oddfellow front end and the Letta API. The key never reaches the browser.

## Why this file exists here

Pushed here only because it was the one repo the Letta GitHub App had been
granted, and the file otherwise lived only in a cloud sandbox. It is unrelated
to the ChatGPT GitHub connector the main README describes. Move it to its proper
home when one exists.

## What v0.20.2 fixed (the important part)

v0.20.1 was correct code talking to an agent with amnesia. The agent answered
"My name is Bob, and no, a zero-spend rule is not part of my standing
instructions."

Root cause: `POST /v1/agents/{id}/messages` runs against the agent's DEFAULT
conversation, and that conversation's system prompt is compiled once and then
cached. It never picks up later memory or a rename.

Fix (zero cost, no new infrastructure):

1. Attach `persona` + `doctrine` memory blocks: `PATCH /v1/agents/{id}` with
   `block_ids`. The response echoes the attached blocks.
2. Create a fresh conversation: `POST /v1/conversations/?agent_id=<id>`.
   `agent_id` must be a QUERY PARAMETER — the body form is rejected (ZodError).
3. Message it: `POST /v1/conversations/{conversation_id}/messages`.
   Returns **Server-Sent Events** (`data: {...}`, ending `data: [DONE]`).
4. Persist the conversation id in the agent's `metadata` so it survives restarts.

## v0.20.3 changes

1. **`/healthz` now names the failing configuration keys.** v0.20.2 returned only
   `{"ok": false}`, which cannot distinguish "not configured" from "down". That
   cost a deployment on 2026-09-30. It now also returns `checks_failed` — env var
   **names only, never values**.
2. **`/healthz` fails closed.** It returned HTTP 200 even when the service could
   not answer a single request, so a platform health check would happily route
   traffic to a broken instance. It now returns **503** when configuration is
   invalid.
3. **`render.yaml`** — a Render Blueprint so the service can be built normally
   from a branch instead of being materialised from the `ODDFELLOW_LETTA_SRC`
   environment variable. That workaround makes Render's commit metadata report
   `main`/`1e04fb5` regardless of what is actually running, so provenance is
   unverifiable from the platform side.
4. `tests/test_backend.py` extended from 26 to **29 tests**.

## Acceptance harness

`acceptance_check.py` runs the acceptance gates against a **deployed** backend and
prints the raw request/response for every check, so its verdict can be overruled
by a human. Stdlib only — no pip install.

```bash
python oddfellow/acceptance_check.py https://oddfellow-letta-poc.onrender.com
ODDFELLOW_OWNER_TOKEN=... python oddfellow/acceptance_check.py <url>
```

Exit code 0 = all checks passed, 1 = at least one failed, 2 = misuse. It checks
`/healthz`, the live OpenAPI version, the expected route set, the `MessageIn`
schema, then (only if the service is actually healthy) authenticated status,
a real message reply, conversation rotation, history, and the 401 paths.

Run against the deployed service on 2026-09-30 00:51 UTC it correctly reported
gate 0 FAILED: `healthz HTTP 200 {"ok": false}`, version 0.20.2, routes all
present, `MessageIn` props `['input','mode']`.

## Automated test suite

`tests/test_backend.py` — **29 tests, 29 passing, 0.6 s, no network, no API key.**

```bash
pip install -r requirements-dev.txt
python -m pytest oddfellow/tests -v
```

The Letta transport is faked, so the suite runs offline and costs nothing. It
covers the fail-closed config paths, auth, agent resolution (including the 402
agent-limit and the created-but-unreadable quirk), SSE parsing, conversation
reuse and replacement, rate limiting, and that no secret is ever echoed back.

## Test evidence (local uvicorn, real Letta API, free `letta/auto`)

- 401 on missing token; 401 on wrong token
- 503 fail-closed on missing or non-free `LETTA_MODEL`
- `GET /api/letta/status` -> 200, `letta_auth` true, `agent_found` true, `conversation_ready` true
- `GET /api/letta/agent`, `GET /api/letta/history` -> 200
- `POST /api/letta/message` -> 200 in 2.2 s, reply:
  *"I'm Oddfellow, and yes — the zero-spend rule (free tiers only, no paid
  service or provider without your explicit authorization) is a standing
  instruction I hold permanently."*
- Unreadable pinned agent -> 502 (reports failure, does not fake success)
- Persistence: fact planted in turn 1 recalled in turn 2; backend killed and
  restarted; same conversation id reused from agent metadata; fact still recalled
- Doctrine in practice: asked to remember a credential-shaped value, the agent
  refused to write it to git-tracked memory and refused to recite it in chat
- Rate limiting implemented, NOT exercised

## Known API oddities (verified 2026-09-30)

- `GET /v1/agents/{id}` reports `blocks: []` even immediately after a PATCH that
  returned two attached blocks. Trust the PATCH response, not a follow-up GET.
- `POST /v1/agents/{id}/core-memory/blocks` and `.../blocks/attach/{block_id}`
  both 404 despite appearing in docs.letta.com.
- `GET /v1/agents/` (list) always returns `[]`. Use `POST /v1/agents/search`.

## Setup (one-time, manual)

1. Attach the memory blocks (see step 1 above).
2. Deploy with `LETTA_API_KEY`, `ODDFELLOW_OWNER_TOKEN`, `LETTA_MODEL`,
   `ALLOWED_ORIGIN`, `ODDFELLOW_AGENT_ID`. It creates its own conversation on
   first request.
