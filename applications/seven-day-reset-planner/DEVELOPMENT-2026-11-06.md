# Planner save protection — 2026-11-06

Source recovered: existing Site commit `ff5f449`, including its daily planner,
guided/custom challenges, history, backup merging and original worksheets. This
build extends that implementation without recreating the previous lost candidate.

## Implemented and tested

Both daily plans and original worksheets compare the current stored value with
the value this tab last read or saved before writing. A stale tab retains its
edits in memory and reports recovery guidance instead of replacing newer data.
Unreadable original worksheet JSON and invalid structures are preserved and
block automatic writes. Daily state is validated before saving. Failed saves
retain the visible edits and warn before leaving the tab. Worker cache version
advances to v5 for the updated public files; storage keys and data schema remain.

`python3 tests/storage-browser.py` passes in actual Chromium at desktop and Pixel
7 emulated viewports: daily stale writes, daily reload persistence, worksheet
stale writes, unreadable worksheet/daily preservation, and quota failure feedback
with in-memory retention. The same browser regression fails on the recovered
baseline because a stale tab reports a successful save. Four existing Node
regression scripts pass. No production dependencies were added.

## Readiness and limits

Application: 7-Day Reset Planner. Release readiness: **IN DEVELOPMENT**.
No real Android install, native package, Safari/iOS, comprehensive accessibility
audit, or full historical credential/license review was performed. Backup import
still writes the daily and original worksheet keys separately; it is not a
transaction across both keys and needs failure-recovery work before release.
Worksheet unsaved edits can be printed; the all-data JSON backup includes the
saved original worksheet copy, not unsaved worksheet edits. Browser storage is
not an encrypted or permanent backup. Multi-tab comparison is best effort and
does not provide transactional synchronization between processes.

Serve `dist/` on localhost for development. The Python browser test starts and
stops its own loopback server; it requires Python Playwright and system Chromium.
Run `node tests/daily-model.cjs`, `node tests/accessibility-regression.cjs`,
`node tests/url-regression.cjs`, and `node tests/service-worker-regression.cjs`.
No build transformation is needed: `dist/` is the existing buildless application.

Rollback: revert the save-protection commit in the development branch. The
stored schema is unchanged. No Site source push, production deployment,
database mutation, paid API, or payment activation occurred.
