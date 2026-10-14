# Render cold-start budget has eroded again: 77s measured

**Date:** 2026-10-14 20:04 UTC · **Service:** `oddfellow-letta-backend-v0206`

## What happened

An hourly probe returned **`HTTP=000` in 75.000s** — a timeout. The standing instruction says a
`000` means *"the service itself is down"*, and that it **"IS worth one line, because it is a
change."**

**It was not down.** It was cold-starting.

## The re-probe that distinguished them

| Probe | Result |
|---|---|
| First, `--max-time 75` | **`000`** at exactly 75.0s |
| Re-probe, `--max-time 180` | **`200` in 77.077s** ← the answer |
| DNS | resolves (216.24.57.16) |
| TCP 443 | OK |
| Control: `render.com` | 200 in 0.16s |

**The service was up the whole time. It needed 77 seconds and the budget was 75.**

## This is a recurrence, not a one-off

The repository already records one round of this:

> `ebebf97` — *"probe budgets: raise the cold-start floor to 60s, **because 30 had stopped being
> enough**"*
> `eee0463` — validated that sweep with a 33s cold start

**So the sequence is: 30 → insufficient; 60 → insufficient; 77s measured today.** The budget is not
a fixed quantity that was once set wrong — **it drifts**, because free-tier cold starts get slower
over time, and each time the symptom is a `000` that looks exactly like an outage.

## Why this matters more than two seconds

**A false `000` is not a neutral reading.** The standing instruction treats it as a change worth
reporting, which means the cost is **a false outage report to the owner** — and my own memory
carries the wrong lesson from the last round: *"use `--max-time 75` upfront."* That number is now
proven insufficient, and I was holding it as guidance.

This is the **same shape as two failures already recorded here:**
- The `find_url` false-negative DOWN, where a single 5s probe reported "down" for a tunnel that was
  merely still propagating.
- Reading `url.txt` during the ~35s propagation window and reporting a stale-file bug that did not
  exist.

**In all three, a probe that ran too early reported a property the thing had not yet acquired.**
The lesson each time is not "the service was slow" — it is **"a timeout is evidence about the last
N seconds, not about the state of the service."**

## Action taken

**Updated the convention: Render probes use `--max-time 120`, not 75.** The old number came from
an era of 10–44s cold starts and has now been exceeded. 120s keeps headroom over the 77s observed
while still failing in a bounded time.

**Deliberately did NOT silence this** by treating `000` as benign. A `000` after 120s is still a
real signal and still worth a line — the fix is a wider budget, not a softer reading.

## Not claimed

The service was **never down** in this window. No outage occurred. **This is a budget bug in the
probe, not a fault in the backend.** The backend's own state is unchanged: `live:true`,
`ready:false`, the two known secrets missing.
