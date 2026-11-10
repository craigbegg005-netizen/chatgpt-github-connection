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
| **Universal handoff field set** (priority, completed/remaining steps, asset + GitHub refs, next action) | 🟡 **PARTIAL — re-checked 2026-11-10** | **Now present:** `priority` (`schema.py`, separate from risk: *"risk gates, priority orders"*) and the checkpoint log, which the handoff renders. **Still not found as first-class fields: asset/GitHub references and next-executable-action** — a grep of `schema.py` and `handoff.py` finds neither. **This is the one genuinely open item** in this table. |
| **Automatic failover trigger** | ✅ **IMPLEMENTED+TESTED — corrected 2026-11-10** | This row said *MISSING*: *"`failover_order()` … nothing calls it on failure — it is a helper awaiting a driver."* **The driver now exists**: `store.py` reassigns a `FAILED_RETRYABLE` job toward the next capable provider, and `connector/tests/test_failover.py` covers it (`test_only_failed_retryable_jobs_fail_over`, `test_approval_survives_failover`). **Do not re-implement this.** |
| **Checkpoint / resume of partial progress** | ✅ **IMPLEMENTED+TESTED — corrected 2026-11-10** | `schema.py` carries an append-only `checkpoints` trail (written only through `Store.record_checkpoint`, so every entry lands in the audit log), `handoff.py` renders it, and `connector/tests/test_checkpoint.py` covers the failover-resume scenario. |
| **Claim lease / expiry** | ✅ **IMPLEMENTED+TESTED — corrected 2026-11-10** | `schema.py` carries `claimed_at` and `lease_seconds` (default 3600), and `store.expire_stale_claims()` releases a claim that has gone un-renewed; `connector/tests/test_lease.py` covers renewal and expiry. The schema comment states the intent this row assumed was absent: *"a dead worker is indistinguishable from a slow one except by silence, so the lease is the detection mechanism."* |

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

> ⚠️ **RE-CHECKED 2026-11-10 — most of FOURTH is already done, and this paragraph would have sent someone to redo it.**
> The priority field, the checkpoint log, the failover driver on `FAILED_RETRYABLE`, and the claim lease
> **all exist now, with tests** (see the corrected rows above). **The only item still open is the two
> remaining universal-handoff fields: asset/GitHub references and next-executable-action.**
> This paragraph is kept because it records what was believed on 2026-10-13; the correction sits beside it
> rather than replacing it, so the drift is visible.

FOURTH (implement checkpoint/handoff/routing/recovery gaps) is code+tests, Gate-A-independent: priority field, checkpoint log, failover driver on FAILED_RETRYABLE, claim lease. FIFTH–SEVENTH (test failover, resume, verification) run through the rehearsal path — code-verifiable now, live-verifiable only after Gate A. EIGHTH (integrate into workflow) is post-Gate-A.

— Oddfellow
