# UNIVERSAL HANDOFF — 2026-10-12 23:45 UTC

**From:** Oddfellow (Letta agent, `agent-a9a8eb2c-2fed-4554-9998-aa4783c7efc4`)
**Branch:** `letta/combined-single-service-v0.20.4` @ `5185ab7` (before this commit)

## This cycle is not a sweep — three real changes

The hourly sweeps have been reporting "clean" for hours because every open goal is
owner-blocked. This cycle broke that pattern: the sandbox reset at 23:32 UTC, and a reset
is an opportunity rather than a setback, because it re-exposes exactly the state that does
not survive it.

### 1. The rehearsal is UP again, and Craig can run phone acceptance against it

```
backend: UP · tunnel: UP · watchdog: UP
code:    letta/combined-single-service-v0.20.4 @ 5185ab77
url:     https://viewed-whether-alumni-accurately.trycloudflare.com
{"live":true,"ready":true,"checks_failed":[],"service":"oddfellow_letta_backend","version":"0.20.6"}
RESULT: all checks passed
```

**This is the one thing in the project that is fully working end to end**, and it is the only
path to v0.20 phone acceptance that does not wait on Gate A. `ready:true` — unlike the live
Render service, which still fails closed on two missing env vars.

⚠️ **It dies with the sandbox**, and the URL changes on every restart. Re-read it with
`./rehearsal.sh status`; do not reuse the URL above.

### 2. The IPv6 fix is now durable in the repo, not re-derived by hand

This sandbox has **no IPv6**, but `trycloudflare.com` publishes an AAAA record first, so the
default resolver ordering makes Python attempt an address that cannot work — and `urllib` does
not fall back, it raises. That produced the "Errno 97 / Name or service not known / HTTP 000"
cluster that was written off as flakiness **three times** before it was diagnosed on 2026-10-09.

The fix lived only in sandbox state (`/etc/gai.conf` and a `.pth` in site-packages), which does
not survive a reset — so it had to be re-derived after every one. It is now:

- `oddfellow/sandbox/force_ipv4.py` — the **single source of truth** for the module.
- `oddfellow/sandbox_ipv4_fix.sh` — `apply` / `verify`, idempotent, copies the module into
  whichever site-packages is asked for. It does not hand-duplicate the rule into those
  directories, because two copies of a rule drift.
- `rehearsal.sh` calls it on every `up`, so a fresh sandbox self-heals.

**Guarded by 7 tests, including the falsifier that matters:** `test_the_guard_is_necessary`
asserts the *same interpreter, unfixed,* **does** return `AF_INET6`. Without that control a
green result could just mean the environment never had an AAAA record to begin with. And
`test_verify_mode_fails_without_the_patch` proves the script's own `verify` mode can fail —
a check whose condition cannot vary is worse than no check.

### 3. The NSF "Project Suitability Assessment" is resolved — and it likely closes the lane

It was recorded as a required step 1 that nothing had done. **It is not a filing**: it is a
**seven-question Yes/No self-assessment published in full on NSF's site** — free, no login,
nothing submitted, no record kept. NSF's rule is unambiguous: *one "No" and the project is
"not a good fit for NSF funding."*

Read honestly against Oddfellow, **two answers are "No" on the product framing**:

- **#2 substantial high-risk R&D** — shipping a voice-first app over a third-party memory API
  is integration engineering, not high-risk R&D.
- **#4 difficult to replicate even by experts** — it is built on a public API; a competent
  team could rebuild the product.

**So the NSF lane is not open for Oddfellow-as-a-product.** The verification-architecture
framing — which the pitch draft already chose, and which hard rule 3 already required — is the
only framing that can clear the gate. That elevates it from a stylistic preference to the
load-bearing decision of the pitch. Full reasoning and the seven questions:
`NSF-PROJECT-PITCH-DRAFT-2026-10-12.md` §"Step 0".

**What this does not establish:** it is a self-assessment. NSF never sees it, and it is a
prediction of a Program Officer's judgement rather than that judgement. NSF's own FAQ says
that where fit is uncertain the right move is to **ask a Program Director** — free, and it does
not consume one of the two pitches allowed per year. `[OWNER]`.

## Suite

**719 passed** (was 710; +9). Guards fired at commit time exactly as designed, twice:

1. the test-count guard (`EXPECTED_TEST_COUNT` and `CURRENT_STATE.md` updated together); and
2. **the test-count guard's own pattern, which was itself defective** — see below.

### A fourth change: `CURRENT_STATE.md`'s "latest cycle" heading was lying about its own date

Found while updating the pointer. The heading read `LATEST CYCLE — 2026-10-12 23:00 UTC` while
the body beneath it was written on **2026-10-07** (`d222849`) and still claimed a 674-test suite
and *the rehearsal is DOWN* — both false. The cause is mechanical: **every hourly sweep bumped
the heading date and touched nothing else**, because the date was the only field it knew how to
update. Five days of sweeps, five days of a heading asserting recency the body did not have.

Nothing caught it. The handoff-pointer guard checks a different line, and the test-count guard
reads the whole file, so it saw the correct count in a different section.

**Fixed structurally, not cosmetically:** the heading no longer carries a date, and
`test_latest_cycle_heading_carries_no_date` fails if one reappears. The rule is mechanical on
purpose — "keep the two in sync" is the judgement-based version that already failed five days
running, and the sweeps that bumped it were not lying, they were updating the only field
available to them. Removing the bumpable field removes the failure mode.

### And the count guard had the same shape of defect

Writing that note **broke the count guard**: the sentence recording that the entry point "still
claimed *674 tests pass*" was itself matched by `_claimed_count()`, which took the first
`N tests pass` anywhere in the file — so prose *about* a claim was read as the claim, and the
guard failed against a file whose real claim was correct.

A false alarm here is not harmless: it sends the next session to "fix" a number that is already
right. The pattern is now anchored on the bold claim (`**N tests pass**`), and
`test_claimed_count_reads_the_claim_not_a_mention_of_it` is the falsifier that stops it drifting
back to matching any mention. **This is the same lesson as the false-control ledger, applied to
a guard rather than to product code: a check is a claim about what it detects, and this one
detected something other than what it said.**

## Standing state, unchanged

- **Gate A** — `ready:false`, both secrets missing (probed 23:00 UTC). Owner action.
- **DB preservation** — deadline **2026-10-27**, nothing backed up. Owner action.
- **Grants** — Verizon re-verified; one number unreconciled and deliberately not picked.
- **Voice** deferred · **Revenue $0** · **BSI migration** phases 2–4 pending owner review.

— Oddfellow, continuing autonomously.
