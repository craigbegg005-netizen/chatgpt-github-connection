# Cross-AI correlation — Oddfellow / Begg AI — 2026-09-30

> 🔴 **HISTORICAL RECORD — corrected 2026-10-02.** This correlation was written 2026-09-30,
> before the `oddfellow-letta-backend` (dead) vs `oddfellow-letta-backend-v0206` (live)
> confusion was found. Its "Open items, by owner" section tells the owner to deploy and branch-check
> `oddfellow-letta-backend`, which is **DEAD** (`/livez` → 000). The **live** service is
> **`oddfellow-letta-backend-v0206`**. The chronology is preserved; the actionable items below
> are void and the live owner action is in `README.md` and `oddfellow/ACCEPTANCE.md`.

**Purpose:** one chronological record of what each AI did, when, and how the simultaneous
workstreams relate. Built from commit timestamps on the canonical branch, the handoff files, and
my own verified probes. Times are **UTC**; Central Time (CDT = UTC−5) is given where a handoff
used it.

**Read the labels strictly.** `VERIFIED` means I checked it myself during this window.
`REPORTED` means another AI or the owner stated it and I have not independently confirmed it.

---

## The correlation problem, stated plainly

**Three different committer identities are writing the same branch, and two of them are the same
agent.** On `letta/combined-single-service-v0.20.4`:

| Committer identity | Who it is |
|---|---|
| `Craig Begg` | This session (Oddfellow, Letta agent `agent-a9a8eb2c…`), committing under the owner's name per the repo convention |
| `Letta Integration` | Parallel Letta sessions — the default bot identity |
| `Oddfellow` | A third parallel Letta session |

So "Letta" is not one writer here. That is why a push was rejected mid-session (the remote had
seven commits I did not have), why a rebase was needed rather than a force, and why one commit
had to explicitly *merge* two sessions' independent fixes for the same defect (`68693b1`).

**Rule that follows:** on this branch, `git fetch` before every push, rebase rather than force,
and never assume the branch is where you left it. Two sessions finding the same bug independently
is normal here, not an error.

---

## Chronology

### 2026-09-29 — before the window

| UTC | Actor | Event |
|---|---|---|
| ~23:05 | **ChatGPT** | Universal Begg AI handoff (6:05 PM CT). Source of the company-wide state. |
| ~23:30 | **Oddfellow** | Re-probed Begg AI Core services: `begg-ai-industries-v013` → 200, `begg-ai-core-v010` → 200. |
| ~23:36 | **Owner** | Decisions: delete nothing yet; **this agent IS the Oddfellow agent**; stage order backend-then-Core. |

### 2026-09-30 00:00–03:00 — build-out

| UTC | Actor | Event |
|---|---|---|
| 00:15–00:16 | **Oddfellow** | Found the source-control gap: the GitHub App grants **exactly one repo**, whose contents are a single `README.md`. |
| 00:56–00:58 | **Oddfellow** | Recovered the older services' API surfaces (`oddfellow-personal-staging-v017b`, `oddfellow-personal-secure`, `begg-ai-industries-v013`, `begg-ai-core-v010`). |
| 01:31 | **ChatGPT** | Parts 1–3 of a new universal handoff (20:31 CT). |
| 01:31–01:46 | **Oddfellow** | Verified the handoff independently; built the single-service option (removes CORS rather than patching it). |
| 01:53–02:00 | **Oddfellow** | Sandbox reset #1. Re-verified; fixed the acceptance harness; found the third env var. |
| 02:12–02:58 | **Oddfellow** | Recovery capture, v0.20.5, deploy-failure diagnosis, the Worker as a second deploy target. |
| 02:45–02:57 | `Letta Integration` | Harness GATE 2 automation; the Cloudflare Worker; front end stops hard-coding the backend hostname. |
| 02:53 | `Letta Integration` | `ACCEPTANCE.md` version table corrected. |
| 02:56 | **Claude** | *(REPORTED)* Render deploys `dep-dau6thad0e5s73egkpa0`, `dep-dau73tdbifpc73emav6g` — builds succeeded, deploys `update_failed`. |

### 03:00–04:00 — first end-to-end pass

| UTC | Actor | Event |
|---|---|---|
| 03:14–03:22 | **Oddfellow** | **First full end-to-end pass.** v0.20.5 in the sandbox, published via a Cloudflare quick tunnel. Every gate green. `1037c35` |
| 03:24 | `Letta Integration` | Rehearsal tooling; PWA installability proven by read-back. `9651d1e` |
| 03:42 | **Sandbox reset #2** | Workspace empty; recovered from GitHub with all four branch heads matching. |
| 03:50–03:54 | **Oddfellow** | Rehearsal watchdog; stopped trusting `pgrep -f`. `d8db4be` |
| 03:54 | `Letta Integration` | Memory/history check made non-vacuous. `dd97f8a` |
| 03:54–03:56 | **Oddfellow** | Rehearsal tooling returns promptly; never prints a URL that is not live. `ea3a929` |
| 03:56 | `Letta Integration` | Gate 0 asserts the deployed build rather than printing it. `18e9803` |

### 04:00–05:00 — fault injection and v0.20.6

| UTC | Actor | Event |
|---|---|---|
| 04:06 | `Oddfellow` | Worker verified with a real Letta key; spurious `deploy.sh` error fixed. `bfaa64a` |
| 04:08 | `Letta Integration` | An unreachable provider was an opaque 500 → now a 502 with the cause. `512fb61` |
| 04:13 | `Letta Integration` | Fuzzed the API: 12 hostile requests, no unhandled 500. `4dc8eba` |
| 04:21 | `Letta Integration` | Front end shows the owner what actually broke. `1c1561a` |
| 04:21 | **Oddfellow** | **v0.20.6** — fault-injection harness, 39 checks; separates *reachable* from *authorised*. `7c33404` |
| ~04:25 | **Sandbox reset #3** | Recovered; found a bug in my own fix and one in the check itself. |
| 04:41–04:55 | **Oddfellow** | Scheduled check caught reset #4; rehearsal state moved to `/root/.oddfellow` so it survives a cycle. `bfe9eb8` |

### 05:00–06:00 — the handoff round

| UTC | Actor | Event |
|---|---|---|
| 05:06 | `Letta Integration` | Handoff written for Claude/ChatGPT takeover. `013ae35` |
| 05:42–05:50 | `Letta Integration` | Approval gate; watchdog proved; stale-process gotcha. |
| 05:46 | `Letta Integration` | *"A risk flag that gates nothing is decoration."* `ea80dda` |
| ~05:50 | **Claude** | *(REPORTED)* Set non-secret env vars on `oddfellow-letta-backend` (`srv-dau6tgqd0e5s73egkocg`, workspace `tea-darhbk97lnhs73dd86qg`); triggered deploy `dep-daua0d893c1s73dce2lg` building `013ae35`. |
| ~05:55 | **Claude** | Handoff to ChatGPT and Letta: **do not ask the owner for a `RENDER_API_KEY`**; one AI deploys at a time; Render is the permanent home. |
| 05:56–05:58 | **Oddfellow** | 429 back-off in the harness (Claude's request); fault harness no longer hard-codes `/tmp/venv`. `5df9ed9`, `86c50a3` |
| 06:00 | **Oddfellow** | Handoff back; deploy target confirmed dead **from outside**. `1cf94f8` |

### 06:00–07:00 — protocol, registry, and the blueprint finding

| UTC | Actor | Event |
|---|---|---|
| ~06:00 | **Owner** | Issued the full **Begg AI Industries operating protocol** as standing instructions. |
| 06:03–06:05 | **Oddfellow** | `RESOURCES.md` registry; deploy-branch README corrected (it still described a ChatGPT connection demo). `50d90ff`, `ac1b4bf` |
| 06:15–06:30 | **Oddfellow** | Owner reports the secrets are saved. Deploy target **still no HTTP response** (20/45/60/90/120s). Handoff addendum written. `451ca9f` |
| 06:21 | **Oddfellow** | Caught a **false positive in my own watcher** — reported success on `000000`. |
| 06:26 | **Oddfellow** | Fallback defect fixed: the Worker was a version behind and could not tell "never answered" from "said no". `a4a2710` |
| 06:43–06:44 | **Oddfellow** | **Blueprint finding**: `rootDir: oddfellow` with no pinned branch, and `autoDeploy: false`. `a652c55`, `62fecf5` |
| 06:51 | `Letta Integration` | Merged my Worker transport fix with a parallel session's rather than picking one. `68693b1` |
| 06:57 | **Oddfellow** | Two real front-end defects fixed and **verified in a real browser**; `ACCEPTANCE.md` brought current. `7871d12` |

---

## Where the simultaneous work overlapped

Three cases, all resolved without loss:

1. **The unreachable-provider defect** — two sessions found it independently within minutes
   (`512fb61` and `7c33404`). Resolved by keeping one as the base and integrating what it lacked.
2. **The Worker transport fix** — I wrote it; a parallel session wrote its own; `68693b1` merged
   both rather than picking one.
3. **The push collision** — my push was rejected because the remote had seven commits I did not
   have. File sets were disjoint, so a rebase was clean.

**Nothing was lost in any of the three.** That is the payoff of fetch-before-push and
rebase-not-force.

---

## Current authoritative state — 07:00 UTC

| Thing | Value | Status |
|---|---|---|
| Canonical branch | `letta/combined-single-service-v0.20.4` @ `7871d12` | ✅ VERIFIED (local == remote) |
| Backend version | `0.20.6` (branch *named* v0.20.4) | ✅ VERIFIED |
| Tests | 84 pass · fault injection 39/39 | ✅ VERIFIED |
| Acceptance vs live rehearsal | all gates pass | ✅ VERIFIED |
| PWA installability | SW registered/active/activated; manifest complete; 3 icons resolve | ✅ VERIFIED (read back from the live page) |
| `oddfellow-letta-backend` | **no HTTP response** at 20/45/60/90/120s | ✅ VERIFIED |
| Rehearsal | live, self-healing | ✅ VERIFIED |
| Render deploy state | *(REPORTED)* `update_failed`, both secrets missing at startup | REPORTED |

## Open items, by owner

**Owner (Craig) — the only person who can do these**
1. ~~Confirm which **branch** `oddfellow-letta-backend` is set to. If `main`, that is the bug.~~
   🔴 **VOID — corrected 2026-10-02.** `oddfellow-letta-backend` is dead and was never the
   deploy target. The live service is `oddfellow-letta-backend-v0206`.
2. ~~Trigger a **manual deploy** (Render → Deploy → Deploy latest commit).~~
   🔴 **VOID — corrected 2026-10-02.** The live service already serves; the remaining action is
   the two secrets on `oddfellow-letta-backend-v0206`, not a deploy of the dead name.
3. Ensure `ODDFELLOW_OWNER_TOKEN` is the **same string** in Render and in the Letta agent secret.

**Claude** — holds Render access. Read Events/Logs after the manual deploy; run the acceptance
harness (**it now backs off on 429**); report the deploy state.

**ChatGPT** — holds Render access and the company-side automations. No action pending on Oddfellow.

**Oddfellow (me)** — watching the deploy target; will run acceptance the moment it answers. Lanes
that need no credential are being advanced continuously.

**Unchanged structural blocker** — the GitHub App still grants exactly **one** repository. No
Oddfellow or Begg AI codebase is under version control anywhere reachable. Owner must grant repo
access or name where the code lives.
