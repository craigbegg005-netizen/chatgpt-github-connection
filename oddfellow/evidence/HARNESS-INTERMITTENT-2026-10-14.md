# Acceptance harness — an intermittent GATE 1 history failure

**Date:** 2026-10-14 09:05 UTC · **Rehearsal URL:** `flour-life-fred-reasonably.trycloudflare.com`

## What happened

The acceptance harness failed **one** check that is not a known blocker:

```
RESULT: 1 check(s) FAILED
  - history: the turn we just took is in it: HTTP 200 | 0 message(s) |
    owner turn present=False | reply present=False
```

The sequence the harness runs is: send a message → receive a reply → read history and assert the
turn is present. **The message succeeded and the reply came back.** Then history returned
**0 messages**.

**Everything else passed** — status, auth, agent resolution, frontend, manifest, icons, service
worker, and all of GATE 3 (401s, no key-shaped strings).

## Reproducibility — tested, not assumed

| Run | Result |
|---|---|
| original | ❌ **FAILED** — `0 message(s)` |
| re-run 1 | ✅ passed — `2 message(s)` |
| re-run 2 | ✅ passed — `2 message(s)` |
| re-run 3 | ✅ passed — `2 message(s)` |

**1 failure in 4 runs. It cleared on retry.**

## Why I am recording it anyway

**"A failure that clears on retry is still a failure"** is a rule I already hold, learned the hard
way on this project. A passing retry is evidence about *the retry*, not about the cause. The
temptation here is to write "transient, cleared" and move on — which is exactly how a real defect
stays invisible until it costs something.

## Most likely cause, stated as a hypothesis

**A read-after-write consistency window.** The harness reads history *immediately* after the reply.
If Letta's history read is eventually consistent, an immediate read can miss a turn that is about
to become visible — which fits the observation precisely: the write succeeded (a reply came back),
and the *read* returned empty, then returned 2 messages seconds later.

**This is a hypothesis, not a finding.** I did not reproduce the window deliberately, and a single
occurrence cannot distinguish it from a one-off platform hiccup.

## What would make this a real defect

- **Frequency rising.** At 1-in-4 this is noise; at 1-in-2 it is a product problem.
- **A case where the write itself is lost** — i.e. the reply returns but the turn never appears.
  That would be data loss, not latency, and it would matter for a product whose whole premise is
  persistence.

## Action

**No fix attempted.** Changing the harness to retry the history read would *mask* the signal, and
the signal is the point — a persistence product failing to show a just-written turn is exactly what
this gate exists to catch.

**Watch it.** The hourly rehearsal check runs the same harness, so recurrence will be visible
without extra work. If it appears again, capture the timestamp and check whether the conversation
id from the *failing* run ever shows the turn.

## Not claimed

Not a known blocker. Not a confirmed defect. **Not dismissed as a transient either.** One
occurrence, unreproduced, with a plausible cause and an explicit trigger for escalating it.
