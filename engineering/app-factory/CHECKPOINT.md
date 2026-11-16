# BSI application recovery checkpoint — 2026-11-06

Development branch: `work/bsi-app-portfolio-20261106`, based on canonical
`4295e299a124d1c27ee92c21777073001b8fe6c2`. No production change or spending.

## Current verified inventory

Sites returned 38 owner projects with no next cursor. Metadata is preserved in
`sites-inventory.json`; metadata discovery does not establish a functional app.
Two source repositories are recovered in this workspace and mirrored under
`applications/`: the original Planner and the App Factory catalog. The catalog
contains 54 implementations: 14 games and 40 other utilities/creative tools.
Clean Sweep, Merge Forge and Sort Sprint are three additional game discovery
targets in current metadata; their source is not recovered in this workspace.
Duplicate Planner editions and containers prevent summing these as unique apps.

`catalog-inventory.json` gives each catalog app's current status, test limits,
remaining blockers, release readiness, branch and next priority. None is READY.
This is a verified partial recovery; it is not a complete audit of every BSI
application or of live customer data.

## Actual engineering completed

The existing Planner Site source (`ff5f449`) already contains daily plans,
optional original worksheets and guided/custom challenges. It was recovered
rather than replaced. Save guards now reject stale-tab writes in both editions,
preserve corrupt worksheet data, validate daily saves, retain unsaved edits,
and warn before leaving. The Site checkout commit is `03e757b` on local branch
`work/bsi-planner-safety-20261106`. Source, tests and provenance are mirrored under
`applications/seven-day-reset-planner/` for durable GitHub review.

Actual Chromium tests pass at desktop and Pixel 7 emulated viewports, covering
six storage scenarios per profile. A baseline control fails on stale daily
writes before the fix. Four original Node regression scripts pass. The 54-app
catalog regression passes script parsing and its selected static behavior and
accessibility checks; it does not verify all 54 end-to-end workflows.
See `evidence/` and the Planner's `DEVELOPMENT-2026-11-06.md`.

## Readiness and priorities

| Application/workstream | Release readiness | Next priority |
|---|---|---|
| 7-Day Reset Planner | IN DEVELOPMENT | Make two-key backup import recoverable on partial storage failure; verify original PDF, accessibility, real Android/offline installation and licensing. |
| Loan Snapshot / catalog | IN DEVELOPMENT | Reinspect current calculator and test numeric accuracy, validation and mobile workflows. Previous unpushed improvements are not in this recovered source. |
| 14 catalog games | IN DEVELOPMENT | Verify complete gameplay loops individually; start closest to completion. |
| Remaining 37 Site records | IN DEVELOPMENT | Recover source and evaluate intended workflows; preserve duplicate/infra distinctions. |
| Oddfellow canonical | IN DEVELOPMENT | Reuse current canonical APIs; keep application changes independent until an authorized operation has a tested permission boundary. |

No more than five product streams may be active. Current work modifies Planner
only; catalog recovery and metadata collection are not 54 active streams.
No game is claimed complete. Profitability and customer demand are unverified.

## Canonical and PR review

The primary repository and its remote branches are recovered. PR #1 is closed,
unmerged; canonical history contains its separate salvage merge. PR #9 is open,
draft and unmerged at head `cd15c35`; its queue/research changes remain separate.
This branch adds application source and records without changing Oddfellow's
runtime, queue, secrets, database, deployment configuration, or canonical branch.
Historical 780/805/809 backend test results were not rerun in this application
increment and are not presented as fresh evidence.

## Resuming and rollback

Earlier October local-only commits/archive disappeared when the execution
workspace changed. They are historical conversation evidence, not recoverable
source in this workspace and not published results. The latest recovered
Planner includes a separate October upgrade, so no old candidate is rebuilt.

Start with this file, both inventory JSON files, source provenance JSON and the
Planner development notes. Run each app's listed tests before further changes.
Keep source changes on development branches, prepare draft PRs, and require
owner approval before merge/deployment. Rollback is a revert of the application
increment; the Planner's existing storage keys and schema are unchanged.
No persistent background execution system was configured.
