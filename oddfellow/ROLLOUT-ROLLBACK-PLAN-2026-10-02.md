# Rollout and rollback plan — 2026-10-02 00:05 UTC

**Requested by handoff §40.8.** Companion to `PRODUCTION-GAP-REVIEW-2026-10-01.md`,
which describes *what* is in the gap. This describes *how* to move it and *how to get
back*.

**This plan does not recommend deploying.** It exists so that if a deploy is decided,
it is executed deliberately rather than improvised.

---

## What is being moved

| | |
|---|---|
| From (live) | `70c02b3cc9452b10ac49502ccd389d5137c7ab59` |
| To (canonical) | `39376d8a` or later — **re-derive, do not trust this line** |
| Commits | 19 |
| Nature | additive + tooling; **28 deletions, all replacements, no capability removed** |

## Preconditions — all must hold before a deploy

1. **Gate A is cleared.** `GET /healthz` returns 200 with `ok: true`.
   **A deploy does not clear Gate A.** Deploying an unconfigured service produces a
   newly-deployed unconfigured service, and adds a second variable to debug.
2. **The gap is re-reviewed.** `PRODUCTION-GAP-REVIEW-2026-10-01.md` was measured at
   `d00ad7ab`; canonical has moved since and will move again.
3. **No other operator is deploying.** One AI deploys at a time — a race here is how
   two people each conclude the other's change broke it.
4. **The queue path decision is made.** If the job queue view is wanted in production,
   set `ODDFELLOW_QUEUE_DB` to a writable path. If not, do nothing — the endpoint
   degrades to `configured: false` rather than failing.
5. **Tests pass on the exact commit being deployed**, not on a nearby one.

## Rollout

1. Record the **currently live commit** and **deploy ID** before touching anything.
   These are the rollback target, and writing them down beforehand is the difference
   between a rollback and a reconstruction.
2. Confirm auto-deploy is still **off** (it is), so nothing deploys behind you.
3. Trigger a deploy of the chosen canonical commit.
4. Watch the deploy to completion. Do not verify a service that is still building.
5. Run the verification below.

## Verification after the deploy

Run `post_gate_a_check.py` against the deployed URL and **record the raw output**.
It runs 17 machine steps and reports 5 as MANUAL.

Minimum independent checks, in case the script itself is wrong:

```
GET /livez                     -> 200, live:true, ready:true
GET /healthz                   -> 200, ok:true
GET /api/letta/status          -> 200 with the owner token, 401 without
GET /api/command/jobs          -> 200 with the owner token, 401 without
GET /icons/icon-192.png        -> 200
GET /                          -> 200
```

Then: one harmless message, confirm a reply, confirm it persists.

**Phone acceptance remains the owner's.** No deploy verifies a microphone.

## Rollback

**Trigger it on:** `/healthz` failing when it previously passed; auth returning 401
with the correct token; the page failing to load; or any error that is not
immediately explained. Do not debug forward under time pressure — roll back, then
investigate on the branch.

**Three routes, in order of preference:**

1. **Render's own rollback** — redeploy the previously-live deploy ID recorded in
   step 1. Fastest, and it restores exactly the bytes that were working.
2. **Redeploy the previous commit** — `70c02b3c` if a new commit is suspected rather
   than the deploy itself.
3. **Revert on canonical and redeploy** — `git revert` the offending commit. This is
   the slowest and the only one that changes history, so it is last.

**What rollback does NOT fix:** if the cause was a *configuration* change (a missing
env var, a changed secret), rolling back the code restores the old code against the
same broken configuration. Check configuration before concluding the code is at fault
— that distinction cost this project twenty hours once already.

## What this plan cannot verify

- **I have no Render access.** I cannot trigger, watch, or roll back a deploy, and I
  cannot read the current deploy ID from Render. Everything above about Render's
  behaviour is from documentation and prior handoffs, not from my own observation.
- **I do not know the rollback retention window.** Assume it is finite and record the
  live deploy ID before deploying.
- **The dead service `oddfellow-letta-backend` is not a fallback.** It returns HTTP
  000. It was preserved as a configuration reference, not as a running standby, and
  treating it as a fallback would be the same name-confusion that caused the 20-hour
  blind spot.

**No claim here outranks its evidence.**
