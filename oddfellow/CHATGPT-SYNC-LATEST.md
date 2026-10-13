# Working alongside Oddfellow — coordination lane

**Read this first if you are another AI picking up BSI work.** Written 2026-10-13 11:10 UTC.
Full dated sync reports live on the documentation-only branch
`coordination/oddfellow-chatgpt-sync` under `oddfellow/handoffs/`. This file is the pointer and
the protocol, kept on the canonical branch so it is findable from the repo root.

⚠️ **A pointer that nothing maintains drifts.** If the branch's reports are newer than this
file's date, trust the branch and update this file — do not trust this line alone.

---

## 1. How not to collide

The single most expensive failure in this repository has been **two sessions doing the same
work**, or one session acting on a stale snapshot of another's. Rules that follow from that:

1. **Re-fetch before you act.** `git fetch --all` then read the remote head. The canonical
   branch moved **11 commits** under one session and **2 more** under another, on 2026-10-13
   alone. A local SHA is not a baseline.
2. **One writer per mutable resource.** Do not let two writers touch the same file, service,
   store or product. If you intend to change something, say so in a dated commit first.
3. **Rebase, never force-push.** When the remote has moved, `git pull --rebase`. If a push is
   rejected, that is the repository telling you a parallel session exists.
4. **Append, do not rewrite, shared logs.** `cycles.md` and the handoff series are append-only;
   newer owner decisions are **new dated versions** (v1.1, v1.2 …), never silent edits.
5. **Evidence outranks timestamps.** A newer report is not automatically authoritative. Check
   the platform.
6. **Probe before you believe a status line.** Several recorded blockers turned out to be stale
   — see §4.

## 2. Where things live

| What | Where |
|---|---|
| Fresh-AI entry point | [`CURRENT_STATE.md`](../CURRENT_STATE.md) — guarded, see below |
| Where the branch head is | newest `oddfellow/HANDOFF-*.md` (see README for the **correct** sort command) |
| This coordination lane | `coordination/oddfellow-chatgpt-sync` → `oddfellow/handoffs/` |
| All services, IDs, URLs | [`RESOURCES.md`](../RESOURCES.md) |
| Commerce lane | `commerce/` — canon, inventory, demand evidence, offer payloads |
| Recovered artefacts | `recovered/` — hash-verified evidence of the lost codebase |

**A test enforces that `CURRENT_STATE.md` names the newest handoff**
(`oddfellow/tests/test_handoff_pointer.py`). That file is the safe cross-check when any other
pointer looks stale.

## 3. Current verified state — 2026-10-13

Confirmed by my own probes today, not carried from a handoff on trust:

| Item | State |
|---|---|
| Tests at canonical head | **727 passed** (both test roots; a single-root run silently skips the count guard) |
| Letta connectivity | **VERIFIED** — `letta_auth`, `letta_reachable`, `agent_found` all true |
| Render `oddfellow-letta-backend-v0206` | **LIVE, NOT READY** — `/livez` 200; `/healthz` `ok:false` |
| Gate A | **BLOCKED (owner)** — `LETTA_API_KEY`, `ODDFELLOW_OWNER_TOKEN` |
| Deployed SHA | **NOT VERIFIABLE** — no build endpoint; bounded to **no newer than 2026-10-05 08:07:56 UTC** |
| Persistent workforce | **NOT PROVISIONED** — `letta agents create` → 402, `"limit":3`. The roster is **manifest only** |
| Rehearsal | **LIVE but ephemeral** — dies with the sandbox; not a deployment |
| **Revenue / orders / payouts** | **NONE, on every platform** |

## 4. Blockers, and the stale ones we already burned

**Open, owner-only:** Gate A (two env vars) · Render DB preservation (deadline
**2026-10-27T23:21:01Z**, nothing backed up) · Fourthwall artwork upload · Spreadshop access ·
GitHub Pages toggle · the art archive (never received).

**Already repaired — do NOT redo these.** Each was recorded as broken and has since been fixed
or was never true:

- **Gumroad listing typo** — the "Inside the oil find" string (meta description, `og:description`
  and JSON-LD) is **gone**. The listing now reads **"11-page"** consistently. Verified 2026-10-13.
- **The tee margin** was recorded as $18.50; it is **$12.55** (base $15.45, not $9.50) — the DTG
  `front_large` print charge is additive.
- **README's "find the latest handoff" command** was wrong (alphabetical `sort` returns a
  2026-10-01 file). Fixed 2026-10-13 with a tested replacement.
- **The offer payloads** (`tee/poster/mug.json`) were in no commit and nowhere on disk despite a
  document calling them "ready". Reconstructed from the live catalog.

## 5. What is blocked, and on whom

- **Fourthwall artwork** — the three media-library MCP tools are referenced by name but **not
  exposed** (`hits=0`). No zero-cost MCP path to create a product design. One owner action
  unblocks it.
- **Spreadshop** — no MCP server and **no integration-catalog entry**. The login form sits in a
  cross-origin iframe behind **reCAPTCHA**, so it cannot be automated past; it needs a human
  sign-in in the sandbox browser.
- **Print resolution** — source PNGs ≈1122×1402 px ≈ **3.74×4.67 in at 300dpi**. **GATED** for
  wall prints.

## 6. Status vocabulary — use it exactly

`CONCEPT` → `IMPLEMENTED` → `TESTED` → `CONNECTED` → `PUBLISHED/LIVE` → `VERIFIED`, plus
`BLOCKED`, `NOT CHECKED`, `UNVERIFIED`.

**`COMPLETE` is not `VERIFIED`. A listing is not a sale. A suggested margin is not profit.**
Two distinctions that have caused real errors here:

- **`NOT CHECKED` ≠ `BLOCKED`.** If you have no evidence either way, say `NOT CHECKED` — do not
  inherit someone else's verdict.
- **Never describe a manifest as running.** The roster, the department heads and the job
  manifest are design artefacts until something is provisioned **and** verified.

## 7. Hard limits

**Zero spend.** No purchases, ads, trial upgrades, inventory, samples, metered tools, legal fees
or billing without explicit owner authorization. No secret in a repo, chat or front end —
counts only, never print a matched value. **No publication, deployment or irreversible action
without owner approval.** Keep EM Brooks, the affiliate venture and the Global Peace framework
**separate** from BSI.
