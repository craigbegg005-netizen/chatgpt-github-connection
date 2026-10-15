# An intermittent failure in `test_verify_mode_passes_with_the_system_patch`

**Date:** 2026-10-15 08:2x UTC · **Status: ⚠️ UNEXPLAINED. Not reproduced in 14 consecutive full-suite runs.**

## What happened

One full-suite run failed:

```
FAILED oddfellow/tests/test_sandbox_ipv4_fix.py::test_verify_mode_passes_with_the_system_patch
1 failed, 769 passed
```

The same test **passes 7/7 when its file is run alone**, and passed on every subsequent
full-suite run.

## Reproducibility — tested, not assumed

| Runs | Result |
|---|---|
| 1 (original) | ❌ **FAILED** |
| 2, then 8 more | ✅ all passed |
| 6 more | ✅ all passed |
| **14 consecutive full-suite runs total** | ✅ **all passed, 770 each** |

So this is a genuine intermittent — roughly 1 in 15 or rarer — and **not** a broken build.

## What I checked, and ruled out

- **The patch is installed and working on both interpreters.** `sandbox_ipv4_fix.sh verify`
  returns OK for the system `python3` and for the repo venv. The failure is not a missing patch.
- **The probe is not DNS-dependent any more.** It uses numeric literals (`127.0.0.1`, `::1`),
  so it cannot fail for a network reason. That was the cause of an *earlier* intermittent in
  this same test, fixed on 2026-10-13 — this is a different occurrence.
- **A write race on the `.pth` was considered and NOT demonstrated.** `install_into` did write
  non-atomically (plain `>` redirect) into a directory every interpreter reads at startup, and
  there are concurrent callers (`rehearsal.sh up` via the watchdog, and the test suite itself).
  That is a real hazard and it is now fixed (`b5ab6d6`) — but a harness hammering `apply`
  against a continuous `verify` loop produced **0 failures in 233 runs with the fix and 0 in
  207 runs without it**. The race is not demonstrated by that test either way, so the fix is
  hardening, **not** the explanation for this failure.

## What remains

**The cause is not known.** The honest record is: it happened once, it has not recurred in 14
full-suite runs, and the two candidate mechanisms I could test were both negative.

## What would make this a real defect

- A second occurrence, especially one that does **not** clear on retry.
- An occurrence in a run where the sandbox did **not** cycle. The sandbox cycled at ~08:01 and
  ~08:33 UTC on this date, and the venv's patch files carry an 08:33 timestamp — so a cycle
  landing mid-run is a live alternative explanation that I cannot rule out from one sample.

**Do not close this as "transient".** A failure that clears on retry is evidence about the
retry, not about the cause — the rule this project already holds, and the reason the earlier
DNS-dependent version of this same test stayed invisible for days.
