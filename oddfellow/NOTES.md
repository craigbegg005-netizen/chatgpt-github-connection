# Oddfellow Letta backend v0.20.1

Written and tested by Oddfellow (Letta agent) on 2026-09-29.

**Status: IMPLEMENTED + TESTED locally. NOT DEPLOYED.**

A FastAPI service that holds the Letta API key server-side and mediates between
the Oddfellow front end and the Letta API. The key never reaches the browser.

## Why this file exists here

It was pushed to this repository only because it was the one repo the Letta
GitHub App had been granted, and the file otherwise lived only in a cloud
sandbox. It is not related to the ChatGPT GitHub connector the main README
describes. Move it to its proper home when one exists.

## Test evidence (local uvicorn, real Letta API)

- 401 on missing token; 401 on wrong token
- 503 fail-closed on missing or non-free LETTA_MODEL
- GET /api/letta/status -> 200, letta_auth true, agent_found true
- GET /api/letta/agent and /api/letta/history -> 200
- POST /api/letta/message -> 200 in 2.5s, real reply, stop_reason end_turn
- Unreadable pinned agent -> 502 (reports failure, does not fake success)
- Rate limiting implemented, NOT exercised

## Known blocker (2026-09-29)

`POST /v1/agents/{id}/messages` runs the agent with `system: null` and no memory
blocks, so an API-driven run does NOT see Letta Code MemFS memory. The agent
replied "My name is Bob, and no, a zero-spend rule is not part of my standing
instructions." This backend is correct, but it is talking to an agent with
amnesia. Resolution pending: (A) server-side memory blocks, (B) inject the
doctrine per request / set the agent system prompt, or (C) Letta Agent SDK /
App Server.
