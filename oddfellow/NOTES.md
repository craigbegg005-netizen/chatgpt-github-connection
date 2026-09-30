# Oddfellow Letta backend v0.20.2

Written and tested by Oddfellow (Letta agent), 2026-09-29 → 2026-09-30.

**Status: IMPLEMENTED + TESTED end to end locally. NOT DEPLOYED.**

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

## Automated test suite

`tests/test_backend.py` — **26 tests, 26 passing, 0.6 s, no network, no API key.**

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
