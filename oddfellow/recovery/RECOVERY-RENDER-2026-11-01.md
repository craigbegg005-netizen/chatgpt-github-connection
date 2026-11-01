# Render Infrastructure Recovery — 2026-11-01

Trigger: owner directive ("Render access has been restored… 19 Render services, 1 PostgreSQL
database"). No Render API access exists from the sandbox (no MCP server, no API key) — this
census used **public endpoint probes only**: zero-spend, read-only, no service was modified,
restarted, or redeployed. Probed 2026-11-01 ~06:55 UTC.

## Census — the 10 services documented in repo records

| Service | /livez | / | VERDICT |
|---|---|---|---|
| oddfellow-letta-backend-v0206 | **200 · v0.20.6 · live:true · ready:false** | — | **LIVE** (primary backend; Gate A secrets still unset — known blocker, unchanged) |
| oddfellow-letta-backend | 000 (75 s timeout) | — | **NOT SERVING** (dead since 2026-10-01; do not probe as primary — 20-hour blind-spot lesson) |
| begg-ai-core-v010 | 404 (no route) | 200 · 14,290 B · "Begg AI Command Center" | **LIVE** |
| begg-ai-industries-v013 | 404 (no route) | 200 · 17,260 B · "Begg AI Industries Command Center" | **LIVE** |
| oddfellow-letta-ui-v020-pwa | 404 (no route) | 200 · 20,897 B · "Oddfellow Synthetic v0.20" | **LIVE** |
| oddfellow-letta-ui-v020 | 404 (no route) | 200 · 20,216 B · "Oddfellow Synthetic v0.20" | **LIVE** |
| oddfellow-synthetic-v020 | 404 (no route) | 200 · 15,721 B · "Oddfellow Synthetic v0.20" | **LIVE** |
| oddfellow-personal-secure | 404 (no route) | 303 redirect | **LIVE** (redirects — auth-gated, not probed further) |
| oddfellow-personal-staging-v017b | 404 (no route) | 303 redirect | **LIVE** (redirects — auth-gated, not probed further) |
| oddfellow-letta-poc | 404 (22 B platform page) | 404 (22 B) | **NOT SERVING** (both paths return the platform 404 — deleted, renamed, or no routes) |

**Gap vs owner's report:** owner sees 19 services; repo records document 10. The other 9 are
unknown to this repo — their names, purpose, and status are **UNVERIFIED**. If they matter,
the owner's dashboard list is the only source (no API access).

## Findings

1. **Three Command Center variants exist; no two match.**
   - repo `oddfellow/frontend/command.html` — 9,610 B · "Begg AI Command Center"
   - `begg-ai-core-v010` deployed — 14,290 B · "Begg AI Command Center" (same title, different body)
   - `begg-ai-industries-v013` deployed — 17,260 B · "Begg AI Industries Command Center"
   The deployed sources were **never in this repo** — both live copies are now preserved in
   `oddfellow/recovery/` (secret-scanned: 0 hits; the one "Bearer" string is placeholder UI text).
2. **The deployed Command Center is static.** No external scripts, no live data fetches —
   consistent with (and now explained by) the **empty database** finding of 2026-11-01 06:44 UTC
   (coordination commit `6155dd0`): nothing ever wired it to data. The v013 page references an
   `mcpUrl` field and a `/mcp` route in instructional text — recovered configuration hint.
3. **Three different builds of the v0.20 UI are serving simultaneously** (20,897 / 20,216 /
   15,721 B). Repo frontend source exists; which build is canonical is **UNDETERMINED**.
4. **Probe-hygiene note (self-correction):** in the census loop, a timed-out curl left the
   previous iteration's response file in place, so one 000 row displayed the *prior* service's
   JSON — discarded. Stale-artifact shape; output files must be removed between probes.

## PR #1 — "Preserve saved progress and recover missing cross-AI handoffs"

`work/oddfellow-continuity-upgrade-20261016` → canonical. **OPEN, 15 days stale, 69 commits
behind canonical, 2 unique commits** (8 files, +263/−21). Unique content **not on canonical**:

- `oddfellow/run_offline_tests.py` — credential-free offline test runner (50 lines)
- `oddfellow/connector/worker.py` — `_fingerprint()` upgraded from job-ID digest (16 hex) to
  full handoff-document digest (64 hex: detects recipient/input/progress changes, not just set
  membership) + `canonical_provider()` normalization + `limit` input validation
- `oddfellow/UPGRADE-REVIEW-2026-10-16.md` — the only cross-AI handoff doc not on canonical
- Tests for the above (+60 lines `test_worker.py`)

**Recommendation (owner decision):** salvage the three code pieces onto canonical via a fresh
branch (the PR itself is too stale to merge as-is); close PR #1 as superseded after salvage.
No merge action taken — approval gate.

## Status labels

LIVE: backend-v0206, core-v010, industries-v013, ui-v020-pwa, ui-v020, synthetic-v020,
personal-secure, personal-staging-v017b · NOT SERVING: backend (old), poc · VERIFIED: census
above, 2026-11-01 ~06:55 UTC · BLOCKED: Gate A secrets (unchanged), 9 undocumented services,
Command Center deployed-source provenance.

---

## Addendum 2026-11-01 07:45 UTC — full 20-service reconciliation (owner dashboard screenshots)

Owner uploaded 6 dashboard screenshots ("SERVICE NAME 20"). Combined with probes, every service
is now documented. **Dashboard status ≠ serving status** (proven below: v019 "Failed deploy"
still serves; PgHero sleeping ≠ down).

| # | Service | Dashboard | Probe | Verdict |
|---|---|---|---|---|
| 1 | begg-ai-core | Failed deploy | 000 | NOT SERVING — cleanup candidate |
| 2 | **begg-ai-core-db** | **Available · PostgreSQL 18 · updated 1 h ago** | dumped, verified empty | **LIVE, EMPTY** — delete/downgrade is owner's tap |
| 3 | begg-ai-core-v010 | Deployed | 200 · 14,290 B CC | LIVE |
| 4 | begg-ai-industries-v013 | Deployed | 200 · 17,260 B CC | LIVE |
| 5 | global-peace-human-security-framework | Failed deploy | 404 | NOT SERVING — cleanup candidate |
| 6 | global-peace-human-security-full-rc1 | Deployed | 200 · 36,808 B | LIVE (peace lane) |
| 7 | global-peace-human-security-rc1 | Deployed | 200 · 4,049 B | LIVE (peace lane) |
| 8 | oddfellow-letta-backend | Failed deploy | 000 | NOT SERVING (dead since 10-01) — cleanup candidate |
| 9 | oddfellow-letta-backend-v0206 | Deployed | 200 · v0.20.6 · ready:false | **LIVE, NOT READY** (Gate A secrets unset) |
| 10 | oddfellow-letta-poc | (row cut off in screenshot) | 404 platform | NOT SERVING — cleanup candidate |
| 11 | oddfellow-letta-ui-v020 | Deployed | 200 · 20,216 B | LIVE |
| 12 | oddfellow-letta-ui-v020-pwa | Deployed | 200 · 20,897 B | LIVE |
| 13 | oddfellow-personal-secure | Deployed | 303 | LIVE (auth redirect) |
| 14 | oddfellow-personal-staging-v017 | Failed deploy | 000 | NOT SERVING — cleanup candidate |
| 15 | oddfellow-personal-staging-v017b | Deployed | 303 | LIVE |
| 16 | **oddfellow-personal-v019** | **Failed deploy** | **200 · 16,223 B** | **LIVE — failed deploy left last good build serving** |
| 17 | oddfellow-personal-v019b | Deployed | 200 · 16,276 B | LIVE (near-duplicate build of v019) |
| 18 | oddfellow-synthetic-v020 | Deployed | 200 · 15,721 B | LIVE |
| 19 | peace-framework-global-language-access | Deployed | 200 · 2,277 B | LIVE (peace lane) |
| 20 | **PgHero-dpg-dasq9ne0tbcc738ifeug-a** | (row cut off) | **401** (75 s retry — first 25 s probe hit cold-start 000) | **LIVE, auth-gated — wired to begg-ai-core-db** (name carries the DB's internal host ID) |

**Tally: 14 LIVE · 1 DB Available (empty) · 5 NOT SERVING = 20.**

### New findings

5. **A PgHero monitoring instance is wired to the rescued DB** (suffix = its internal host ID,
   `dpg-dasq9ne0tbcc738ifeug-a`). Deployer unknown (not in repo records). Consequence for the
   owner's DB decision: deleting `begg-ai-core-db` orphans PgHero — delete both together.
   Keeping a paid $6/mo plan for a verified-empty DB + its monitor has no value.
6. **Five safe-deletion candidates** (failed deploy + confirmed not serving): `begg-ai-core`,
   `global-peace-human-security-framework`, `oddfellow-letta-backend`,
   `oddfellow-personal-staging-v017`, `oddfellow-letta-poc`. Owner decision; deleting them
   changes nothing that serves.
7. **"Failed deploy" can still serve.** `oddfellow-personal-v019` proves it: dashboard red,
   HTTP 200. Never trust the dashboard badge alone — probe.
8. **Dashboard badge drift:** header says 20 services; owner's directive said 19 — the 20th
   (PgHero) is likely newer or was missed. Dashboard is authoritative.
