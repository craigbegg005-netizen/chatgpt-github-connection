# Independent verification of `letta/combined-single-service-v0.20.4`

**By:** Oddfellow (Letta agent `agent-a9a8eb2c-…`), 2026-09-30 13:08–13:09 UTC
**Verified revision:** branch head `0f5b837`
**Method:** detached worktree, their own test runner, then the live app driven through `TestClient`.

The point of this file is that it is **not** written by the author of the thing being
verified. Another agent wrote the branch and the handoff; this is a second pair of
hands reproducing its claims. Where a claim did not reproduce, the cause is stated
— including when the cause was my own mistake.

## Claims reproduced

| Claim (from their 08:15 UTC handoff) | Result |
|---|---|
| "107 tests passing" | ✅ **109 passed** in 2.75 s — their figure was conservative |
| `/livez` 200 while `/healthz` 503 with secrets absent | ✅ reproduced exactly |
| `/healthz` names the missing config keys | ✅ `checks_failed: ["ODDFELLOW_OWNER_TOKEN"]` — and `LETTA_MODEL` correctly absent from the list when set, proving it reads the live environment |
| Command Center is owner-only | ✅ no token → 401, wrong token → 401, owner token → 200 (`service: begg_ai_command_center`, 12 departments) |
| "Pause → `/api/letta/message` 503 `paused_by_owner`" | ✅ reproduced. The switch genuinely stops work rather than warning about it |
| "Pause is audited" | ✅ `/api/command/audit` returns the `command_pause` record with the reason |
| Route parity must be read from OpenAPI, not `app.routes` | ✅ confirmed: `app.openapi()` lists the `/api/command/*` routes that `app.routes` hides behind a single `_IncludedRouter` entry |

Also observed and worth recording: structured JSON logging on every request with a
`request_id`, including `auth_denied` records that carry the **reason**
(`no_token` vs `bad_token`) rather than a single undifferentiated 401. And with a
deliberately invalid `LETTA_API_KEY`, a message attempt fails **closed** with a
visible `letta_api_error` — it does not silently degrade.

## Two claims that appeared to fail, and did not

I reported these to myself as failures before checking the contract. Both were my
errors, and the correction is recorded here so the record is accurate:

1. **`POST /api/command/pause` returned `{"paused": false}`.** I sent
   `{"reason": "…"}`. The handler is `set_paused(bool(payload.get("paused")), …)`,
   so the body must be `{"paused": true, "reason": "…"}`. With the correct body it
   pauses and the next message returns 503. **Not a defect.**
2. **`GET /api/audit` and `POST /api/command/resume` returned 404.** The audit
   path is `/api/command/audit`, and no resume route exists — unpausing is
   `POST /api/command/pause` with `{"paused": false}`. **Not defects.**

The lesson is small but real: two of the three things I was about to report as
defects were me guessing an interface instead of reading the OpenAPI document
that was sitting right there.

## What this does and does not establish

**Does:** the branch's test suite passes, and its headline security and
state-management claims hold under independent execution.

**Does not:** establish that anything is deployed. `oddfellow-letta-backend`
still returns no HTTP response, `oddfellow-letta-poc` is still missing both
`LETTA_API_KEY` and `ODDFELLOW_OWNER_TOKEN`, and the deployed PWA still points at
the unconfigured service. Passing tests are not a running product.
