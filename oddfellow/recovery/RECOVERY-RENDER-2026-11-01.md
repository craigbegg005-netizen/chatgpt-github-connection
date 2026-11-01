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
