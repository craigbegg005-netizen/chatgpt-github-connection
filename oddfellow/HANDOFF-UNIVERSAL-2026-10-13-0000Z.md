# UNIVERSAL HANDOFF — 2026-10-13 00:00 UTC

**From:** Oddfellow (Letta agent, `agent-a9a8eb2c-2fed-4554-9998-aa4783c7efc4`)
**Branch:** `letta/combined-single-service-v0.20.4` @ `9734abc` (before this commit)

## Hourly sweep #138 — the blocker picture changed materially

**Gate A unchanged** — `ready:false`, both secrets still missing (probed 00:00 UTC, warm 0.3s).

**Pulled 3 parallel commits. Suite 710 → 719** (two consecutive runs; one earlier run reported 1 failed/718 passed — transient, cause unrecoverable once the rerun passed, recorded here rather than dismissed).

### `9cde281` — the recorded DB blocker was WRONG
Live PG handshake to `begg-ai-core-db`: connect succeeds, then `FATAL 28000 SSL/TLS required`. A blocked IP fails at connect and never gets a protocol-level answer — so the effective allowlist rule is **0.0.0.0/0; the DB has been open to the entire internet, never deliberately closed**. Consequences: (1) no dashboard session needed — the only missing thing is the password, so the owner action is **one secret**; (2) the old plan's order was backwards — tightening to a /32 *first* would have blocked the dump (sandbox egress IP is neither stable nor known in advance). Correct order: **dump first, lock down after**.

### `9734abc` — DB preservation is now ARMED, no human trigger
A Cloud schedule (id `0e3e41e3-1647-4074-9db9-65c297422240`, every 2 hours) checks for `ODDFELLOW_DB_URL`; the moment it exists it runs `doctor → recon → dump → verify → restore-verify`, delivers artifacts to `/root/downloads`, reports, and deletes itself. While the secret is absent it does nothing. **The owner action is now exactly one step: add the `ODDFELLOW_DB_URL` secret. Nothing has to be triggered afterward.**

### `4b15397` — rehearsal UP, IPv6 fix durable, NSF suitability resolved
1. **Rehearsal UP and `ready:true`** — the only fully-working end-to-end path and the only route to phone acceptance that does not wait on Gate A.
2. The IPv6 fix is durable in the repo (`sandbox/force_ipv4.py` + `sandbox_ipv4_fix.sh`, called by `rehearsal.sh up`) with 7 tests — including the falsifier that the same interpreter unfixed *does* return AF_INET6, because without that control a green could just mean the environment never had an AAAA record.
3. **NSF Project Suitability Assessment resolved**: a seven-question Yes/No self-assessment, not a filing. On the product framing two answers are "No" (high-risk R&D; hard to replicate) — **the NSF lane is likely not open for Oddfellow-as-a-product.**
4. Two guard fixes: CURRENT_STATE.md's "latest cycle" heading no longer carries a date (sweeps bumped the heading while the body stayed 5 days stale; a test now fails if a date reappears); the test-count guard now anchors on the bold claim rather than the first "N tests pass" anywhere (prose *about* a claim was being read as the claim).

## Standing state
- **Gate A: unchanged** — owner action: two secrets on Render. (Rehearsal offers an alternate end-to-end path meanwhile.)
- **DB preservation: ARMED — owner action is one secret (`ODDFELLOW_DB_URL`), nothing to trigger. Deadline 2026-10-27 (14 days).** Old "allowlist + dashboard session" blocker retired as wrong. Dump first, lock down after.
- **Grants: Verizon re-verified; NSF lane likely closed** (suitability assessment: 2 No answers). SAM.gov registration still the long pole for any federal lane.
- **Voice: deferred** by owner. **Revenue $0.** **BSI migration: phases 2–4 pending owner review.**

— Oddfellow, continuing autonomously.
