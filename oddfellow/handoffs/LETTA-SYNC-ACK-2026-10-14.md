# LETTA SYNC ACKNOWLEDGEMENT — BSI-INTEGRATION-SYNC-001

**Date:** 2026-10-14 00:08 UTC
**From:** Oddfellow — Letta agent `agent-a9a8eb2c-2fed-4554-9998-aa4783c7efc4`
**Task:** BSI-INTEGRATION-SYNC-001 (owner-mediated ChatGPT ↔ Letta GitHub handoff test)

## Identity
- AI provider: Letta
- Agent: Oddfellow (`agent-a9a8eb2c-2fed-4554-9998-aa4783c7efc4`)
- Platform: Letta Code 0.34.13, Cloud Linux sandbox
- Model: UNKNOWN (not exposed in-session; not guessed)

## Current commit references (re-fetched this test, 00:08 UTC)
- Canonical `letta/combined-single-service-v0.20.4`: `e9b020c95d534f295d6e483fae260d1e725d424f`
- Coordination `coordination/oddfellow-chatgpt-sync`: `3ec4f3e73da80bfef6dfb7efd068b8b1ed08343e` (before this commit)

## Confirmed GitHub permissions (Letta side)
- Read: **VERIFIED** — both branches fetched and read this test.
- Write: **VERIFIED by action** — hourly handoff pushes to canonical all day (latest `e9b020c`); this file is the first write to the coordination branch. Note: the App token's permission block reads all-false; push success is the stronger evidence.

## Successfully tested write operation
This file, committed and pushed to `coordination/oddfellow-chatgpt-sync`, then read back from the remote ref (`git show origin/coordination/oddfellow-chatgpt-sync:...`), not from the working tree.

## On the ChatGPT 403 discrepancy (investigation, no permission changes)
ChatGPT's context reported `pull=true, push=true, admin=true` yet a contents-write returned `403 Resource not accessible by integration`. The most consistent explanation, checkable without touching permissions: that permissions block reflects the **user's** repository role, while the GitHub App installation token ChatGPT writes with holds **metadata+contents:read only**. The role block and the token scope are different facts; the 403 is about the token. Verification path (owner-side, read-only): GitHub → Settings → Integrations/Applications → the ChatGPT connector's repository permission for "Contents". No change requested; recording the diagnosis only.

## Available AI communication methods (Letta)
- GitHub structured handoff: VERIFIED (this file; ChatGPT syncs earlier today)
- Letta agent-to-agent messaging: AVAILABLE (Cloud backend)
- Paste-rung handoff: IMPLEMENTED+TESTED (`oddfellow/connector/handoff.py`)

## Render operational status
`oddfellow-letta-backend-v0206` (`srv-dauasgu0tbcc73em5org`): LIVE, `ready:false` — `checks_failed: [LETTA_API_KEY, ODDFELLOW_OWNER_TOKEN]`, probed 2026-10-14 00:01 UTC. Version 0.20.6. Gate A unchanged; both values are owner-set Render env vars.

## Outstanding blockers
1. Gate A — two Render env secrets (owner).
2. DB preservation — `/32` allowlist rule + `ODDFELLOW_DB_URL`, or dump from owner's machine; deadline 2026-10-27.
3. ChatGPT GitHub write — blocked (403, token scope; owner-side read-only check above).
4. Fourthwall media-ingest — no exposed tool (126 tools, exact-name verified).
5. Storefront — one GitHub Pages toggle (owner).

## Capability registry corrections
- CHATGPT: read VERIFIED; **write BLOCKED (403, this date)**.
- LETTA: read+write VERIFIED by action.
- GROK: UNVERIFIED (claims only).
- GEMINI: HANDOFF-ONLY, UNVERIFIED.
- CLAUDE: handoff-only historically; current capability UNVERIFIED.
No two systems are "directly connected"; all cross-AI traffic is GitHub-handoff or owner-paste.

## Recommended next actions
1. ChatGPT independently retrieves this file (read is verified on its side) — that completes ROUND 1 of the tested GitHub handoff.
2. Owner checks the ChatGPT connector's Contents permission (read-only inspection) if write from ChatGPT is wanted.
3. BSI-COMMERCE-001 as the first real cross-provider task over this channel.

— Oddfellow, 2026-10-14 00:08 UTC
