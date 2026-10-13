# Failover directive — implementation assessment (FIRST + SECOND + THIRD)

**Date:** 2026-10-13 23:15 UTC · **By:** Oddfellow (Letta agent)
**Scope:** owner directive "Universal AI/SI Integration & Failover" — steps FIRST (inspect connector + job queue), SECOND (implemented vs missing), THIRD (provider connection status). Read against `oddfellow/connector/` at canonical head, not from memory.

## FIRST — what the connector actually is

2,908 lines, stdlib-only, 6 test files, all passing in the 727-suite. Modules: `schema` (job + status vocabulary + risk), `store` (SQLite durable queue + append-only audit), `tokens` (scoped provider tokens), `lifecycle` (connect/disconnect: revoke tokens, release claims, audit), `handoff` (paste-based structured handoff — the zero-credential rung), `router` (capability + zero-spend aware, fail-closed), `providers` (declared vs verified registry), `gateway`, `worker`, `verify_capabilities`, `cli`.

## SECOND — implemented vs missing, against the directive

| Directive requirement | Status | Evidence |
|---|---|---|
| One canonical job schema + status vocabulary | **IMPLEMENTED+TESTED** | `schema.py`: READY/RUNNING/WAITING_*/BLOCKED/FAILED_*/COMPLETE; VERIFIED is a separate flag, never a status |
| Durable queue + audit trail | **IMPLEMENTED+TESTED** | `store.py` SQLite; audit is append-only and strips payload-class values |
| Task claiming + ownership | **IMPLEMENTED+TESTED** | claim enforcement in `submit_result`; `release_claim` returns RUNNING→READY |
| Idempotency | **IMPLEMENTED+TESTED** | keyed on (job_id, result_hash) |
| Approval gate before execution | **IMPLEMENTED+TESTED** | HIGH/CRITICAL in `APPROVAL_REQUIRED`; router checks approval before capability |
| Denial must not trigger failover | **HELD BY CONSTRUCTION** | `failover_order` is only walked for FAILED_RETRYABLE; a WAITING_AUTHORIZATION job is not a failure and is never re-routed |
| Capability routing on VERIFIED only | **IMPLEMENTED+TESTED** | `providers.py`: declared ≠ verified; routing reads `verified` only |
| Independent verification (executor ≠ verifier; evidence must be checkable) | **IMPLEMENTED+TESTED** | `verify_result` refuses same-provider verification AND refuses evidence that names no URL/path/identifier |
| Handoff carries no secrets; returned results untrusted | **IMPLEMENTED+TESTED** | `handoff.py` |
| **Universal handoff field set** (priority, completed/remaining steps, asset + GitHub refs, next action) | **PARTIAL** | job has kind/title/payload/risk/depends_on/assigned_department/origin_objective. **Missing as first-class fields: `priority`, required-capabilities, checkpoint log (completed/remaining steps), asset/GitHub references, next-executable-action** |
| **Automatic failover trigger** | **MISSING** | `failover_order()` computes the ordered provider list (excludes failed, zero-spend aware, prefers polling providers) but **nothing calls it on failure** — it is a helper awaiting a driver |
| **Checkpoint / resume of partial progress** | **MISSING** | no completed-steps record; a transferred job restarts from its payload, not from a checkpoint |
| **Claim lease / expiry** | **NOT VERIFIED** | no lease field found in this read; a crashed provider's claim persists until explicit release (disconnect handles it; a silent crash does not) |

## THIRD — provider connection status (honest labels)

| Provider | Channel | Status |
|---|---|---|
| **Letta (this agent)** | native | **VERIFIED** — hourly schedules firing; MCP tools live |
| **ChatGPT Work** | structured handoff via coordination branch | **VERIFIED as a channel** — syncs 2026-10-13 10:19 + 11:10 UTC |
| **Claude** | structured handoff (historical) | **HANDOFF-ONLY** — no live connector |
| **Grok (xAI)** | handoff document received 2026-10-13 | **UNVERIFIED — claims not tested.** Document claims: web/X research, document production, GitHub integration, Automations scheduling, image generation. Per directive §3 none of these count until tested. Suggested first test: a harmless reversible research task via the paste handoff rung |
| **Gemini** | none | **NO CHANNEL** |
| Fourthwall MCP | native MCP | **VERIFIED** — 126 tools live (media-ingest tools NOT exposed) |
| BeggAi MCP | native MCP | **VERIFIED** — 10 tools |
| Sentry / Cloudflare MCP | native MCP | **CONNECTED, 0 tools exposed** |

## What FOURTH–EIGHTH need

FOURTH (implement checkpoint/handoff/routing/recovery gaps) is code+tests, Gate-A-independent: priority field, checkpoint log, failover driver on FAILED_RETRYABLE, claim lease. FIFTH–SEVENTH (test failover, resume, verification) run through the rehearsal path — code-verifiable now, live-verifiable only after Gate A. EIGHTH (integrate into workflow) is post-Gate-A.

— Oddfellow
