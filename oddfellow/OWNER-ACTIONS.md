# Owner actions — the whole queue, tap-sized (updated 2026-11-06 20:0x UTC)

Everything currently blocked on Craig, one card per action, phone-first. Each card: what, where to tap, time, what it unblocks. Nothing here spends money except the two items marked **decision** — plus one caution: since the 2026-11-01 Letta Pro upgrade, card 1's `LETTA_API_KEY` may enable credit-billing API calls (see card 1).

## 1. Gate A — two Render secrets  🔴 blocks Oddfellow v0.20 acceptance
Render dashboard → service **oddfellow-letta-backend-v0206** → Environment → add:
- `LETTA_API_KEY` (from letta.com dashboard → API keys)
- `ODDFELLOW_OWNER_TOKEN` (any long random string; must match what the app stores)
Save → service redeploys (~2 min). Time: ~5 min.

🔴 **Setting these two is NOT sufficient any more — do not expect the phone to work straight after.**
Added 2026-11-07. The agent's configured model **`letta/auto` has been retired** (it is not among the
89 handles the API returns), so the chat path fails with HTTP 502 the moment it is reached. Production
is insulated today **only** because Gate A still 503s before the model call — which means the failure
surfaces at the worst possible moment: **the first time you try the phone.** Evidence:
`oddfellow/evidence/MODEL-RETIRED-2026-11-07.md`.

**The model fix needs your call** (it is a spend/quality decision). What is known about the options:
- 🔴 **`letta/auto-fast` is NOT a viable fix right now — and this is not a one-window problem.**
  Corrected twice on 2026-11-07: I first wrote the bucket was "empty until 12:00Z", then that it was
  "still empty after that window rolled". **Re-checked at 16:00Z, and again at 2026-11-08T00:0xZ after the
  daily window rolled: still `empty`**
  — four consecutive windows including a daily reset (`letta usage` → `Bucket: empty (daily: empty)`).
  **A daily reset did not refill it, so this is not a "wait for the window" problem.** So a `letta/*` handle fails
  for an exhausted bucket, not for a bad choice — and switching to one would look like a model problem.
  **Do not pick a `letta/*` model until the bucket is non-empty.**
- ⚠️ **I WAS WRONG ABOUT THE "ZERO-SPEND" OPTION — corrected 2026-11-08 00:0x UTC.** I wrote here that
  a BYOK/external-provider model "draws neither the quota nor the credits", and recommended the one this
  agent runs on. **The credits balance then fell from 12,763 to 12,055 in about four hours**, so
  something non-BYOK *is* drawing credits — and this agent's own model is the obvious candidate. **So the
  external-provider option is NOT verified as zero-spend, and I should not have called it that.** I
  cannot attribute the draw precisely: `letta usage` reports a single balance with no per-model
  breakdown. **Treat every option as possibly billable until a breakdown says otherwise.**
- **`letta/echo`** is probably free and I will not use it: it satisfies a "reply present" check
  *without producing a real reply* — the vacuous-check shape this codebase has been burned by twice.
**Tell me which you want and I will apply it — it is now one setting, not four edits.** The handle was
hardcoded in four places across three files (`rehearsal.sh`, `rehearsal_watchdog.sh`,
`fault_injection_check.py`); all three now read a single **`ODDFELLOW_MODEL`** variable defaulting to the
current value, so nothing has changed behaviourally yet and applying your choice is one line.

⚠️ **On billing:** the balance was **12,763 credits** on 2026-11-07 and **12,055** the next midnight —
so credits are being drawn, and I cannot yet say by which model (`letta usage` gives one balance and no
breakdown). `letta/*` models draw on the separate quota bucket instead, which has been empty for four
consecutive windows. **Neither pool is a safe assumption of "free".**

## 2. Render DB preservation — ✅ RESOLVED 2026-11-01 06:44 UTC: the database was EMPTY

**Resolved:** the full dump + verify + restore-verify ran against the real server and passed.
The database held **0 user tables (7,686 kB virgin)** — it never contained data, so nothing was
ever at stake. You may now **delete or downgrade `begg-ai-core-db` at will — verified zero-loss.**
⚠️ **Delete PgHero together with it** (the 2026-11-01 census found PgHero is wired to this
database — removing one without the other leaves a broken service pointing at nothing).
Dump artifacts are preserved in `/root/oddfellow-db-backups/` and the owner downloads. **No
further action is needed on this card.**

The route mechanics below are kept for the record only (they worked; the allowlist was the
blocker all along — TLS completes, startup gets a clean close when the IP isn't allowlisted).

**Pick ONE of the two routes. They need different IPs allowlisted, and mixing them fails.**

**Route A — I take the dump (fewer taps).** The dump runs **from this sandbox**, so the sandbox's
egress IP is what must be allowlisted — *not your phone's*. Ask me for the current value first
(it changes when the sandbox restarts, so never reuse an older one). Then:
Render dashboard → `begg-ai-core-db` → **Networking** → remove `0.0.0.0/0` if present → add one rule:
**the sandbox egress IP I just gave you, as `/32`**. Then set secret `ODDFELLOW_DB_URL` and tell me
"allowlisted" — I do the dump + restore-verify, zero spend.

**Route B — you take the dump from your own machine.** Then the **phone's /32** is correct, because
your phone is the client: allowlist it, run `pg_dump` 18 against the External Connection String.

⚠️ **A phone `/32` with Route A is the one combination that cannot work** — the sandbox is the client
there, so the database would still refuse it. This card said "your phone's /32" for both routes until
2026-10-15; the runbook (`oddfellow/RENDER-DB-PRESERVATION-2026-10-07.md`, Path A step 1) always said
"the sandbox's IP", and the runbook is right.

**Unblocks: the only verified backup of the operational DB.** Time: ~10 min.

## 3. Gumroad delivery check (BSI-COMMERCE-002)  🟡 revenue-readiness
Gumroad dashboard → Products → for each of the 3 listings: open → Content → confirm the delivery file is attached and looks right; check price matches ($7.00 / $4.99 / $5.00). Full checklist: `oddfellow/commerce/DELIVERY-VERIFICATION-BSI-COMMERCE-002.md`. Time: ~15 min.
Optional **decision**: a $4.99 test purchase of your own listing end-to-end (only spend on this list, your call).

## 4. Approve + post the promotion drafts  🟡 revenue-first
Drafts ready: `oddfellow/promotion/DRAFTS-2026-10-14.md` (X post + Reddit-style post per listing, all factual). Review → post from your accounts when ready. **Update 2026-10-19: the drafts point at Gumroad; the Fourthwall storefront is now live with 44 public products — consider posting storefront links too (or instead).** Time: ~10 min.

## 5. Reconnect BOTH Google integrations  🟡 blocks file verification + comms failover
Letta chat → connections → reconnect **Google Drive** AND **Gmail** together (they share one broken provisioning path; both 500 "Managed MCP server configuration is unavailable" since 02:00 UTC). **Unblocks: Drive-based asset transfer + the comms failover chain.** (The Samurai hash loop CLOSED 2026-10-15 — hero verified locally against the manifest.) Time: ~2 min of taps.

## 6. Refresh the BeggAi (Stripe) token  🟡
Same connections page → BeggAi → reconnect (refresh token invalid). Time: ~1 min.

## 7. Fourthwall dashboard session  🟡 catalog hygiene + agent unblock
The catalog is live: **44 PUBLIC products** (verified 2026-10-19 00:02 UTC). Remaining dashboard-gated items: (a) the four We Sell Stuff mug designs appear **twice each** in the catalog — if those are accidental duplicates, archive one of each; (b) per-size base costs for the Enhanced Matte Poster (still the only source — public catalog shows one $5.50 from-price); (c) the samurai-motif AS Colour tees are PUBLIC — if any uses image 01 (the calligraphy-flagged artwork), that review gate is still OPEN on our side; (d) media-library MCP tools remain `tool_not_found`, so agent-side product creation still needs one dashboard upload per design. Time: ~15 min.

## 8. Higher-resolution artwork originals  🟡 unblocks the poster range
If a higher-res original of the Samurai artwork exists (bigger than 1122×1402), upload it to the shared Drive folder. Current source caps at 5×7@200DPI / soft 8×10. Time: whatever it takes to look.

## 9. Pages toggle  ⚪ low urgency
GitHub repo → Settings → Pages → enable on canonical branch (turns the storefront page live). One toggle.

## 10. Grants — two lanes open and free; one closes with the December 2026 round  🟡 deadline-bound

**This lane was missing from this board entirely** (added 2026-11-06). It is tracked in
`GRANTS-NON-DILUTIVE-PIPELINE-2026-10-01.md` and the company file, but no card here mentioned it — so a
live $10,000 opportunity with a closing window was not on your queue.

**Verizon Small Business Digital Ready — $10,000.** Re-verified 2026-11-06 against Verizon's own page.
The window closes with the **December 2026** round: *"Applications will be reviewed monthly from June
through December 2026. Each month, 10 small businesses will be selected."* The unlock is free and it is
yours: *"Register and complete any combination of two free courses or events anytime in 2026 to unlock
the grant application."* No LLC, no SAM registration, no spend. **Once unlocked, I can draft the
application for your review** — Verizon has no rule against AI assistance.
⚠️ **Unsettled, do not assume either way:** the page says selected businesses *"complete a verification
process to confirm good financial and legal standing before funds are awarded"*, and whether a sole
proprietorship satisfies that is **not stated** (the FAQ sits behind a JavaScript accordion).

**Emergent Ventures — open, no stated deadline, but the writing must be yours.** Form live
(re-verified 2026-11-06); award size deliberately unspecified, very small grants explicitly in scope,
for-profit explicitly fine. 🔴 *"Emergent Ventures no longer accepts AI-written applications. We will
test all submissions and reject those using AI for anything other than proofreading."* **I can
proofread; I must not draft.**

**Unblocks: the only non-dilutive funding lane that is open and costs nothing.** Time: ~2–3 h of your
time for the Verizon courses; the EV proposal is a writing task of yours.

## 11. Spreadshop URL — one line from your phone  🟡 unblocks the second storefront

**Added 2026-11-07: this blocker was in `COORDINATION-STATUS.md` but not on this board**, and its owner
action there was *"sign-in in sandbox browser"* — which you cannot do from a phone. That row is fixed.

**What I need: your Spreadshop shop URL.** Open your Spreadshop sales-channel overview **in your phone
browser** and paste the address here. The shape is `SHOPNAME.myspreadshop.com` (Spreadshop's own docs),
and the shop name is shown in that overview. I will then verify it live — HTTP 200, correct shop,
products visible — and the lane unblocks. Time: ~1 min.

## 12. Four archives never received  🟡 artwork, PWA, addenda

**Added 2026-11-07: also in `COORDINATION-STATUS.md` but not on this board.** Four archives were
promised and never arrived, which blocks artwork, the PWA, and the addenda. Either **upload them to the
shared Drive folder** (from your phone — the Drive app works) or attach them here. If they no longer
exist or are superseded, say so and I will close the item rather than leave it standing. Time: varies.

---

## Verification of this queue — 2026-10-15 04:0x UTC

Every claim here that can be checked from outside was re-checked, because a stale item costs Craig a
tap. All of them hold:

| Item | Claim | Checked | Result |
|---|---|---|---|
| 1 | Gate A: two Render secrets unset | `/livez` | ✅ `ready:false`, `checks_failed` names both |
| 3 | Three Gumroad listings at $7.00 / $4.99 / $5.00 | each public listing | ✅ **$7.00 / $4.99 / $5.00** exactly |
| 3 | Three live listings | each public listing | ✅ 200, named: Paycheck Budget Starter Bundle, The 7-Day Reset Planner, Job Search Starter Bundle |
| 5 | Both Google integrations return 500 | `Google_Drive`, `Gmail` | ✅ both `500 Managed MCP server configuration is unavailable` |
| 6 | BeggAi (Stripe) refresh token invalid | `list_available_accounts_or_orgs` | ✅ `Invalid refresh token` |
| 9 | GitHub Pages disabled | Pages API + URL | ✅ API 404, URL 404 |

## Verification of the grants lane — 2026-11-06 20:0x UTC

Added because the lane was absent from this board. Both open programs were re-checked against their
own primary sources today, not against a search hit:

| Program | Claim | Checked | Result |
|---|---|---|---|
| Verizon Small Business Digital Ready | still open; $10,000; monthly review June–December 2026; two free courses unlock it | `digitalready.verizonwireless.com/grants` | ✅ all hold verbatim |
| Verizon | final decision by 2027-01-12 | same page | ✅ *"All applicants will receive a final decision by January 12, 2027."* |
| Emergent Ventures | application form still live | `mercatus.tfaforms.net/5099527` | ✅ live, 1500-word limit, no PDFs |
| Emergent Ventures | AI-written applications rejected | same form | ✅ *"…reject those using AI for anything other than proofreading."* |

**Also re-verified this cycle, unchanged:** the Fourthwall MCP surface is still **126 tools** with none
of the three media-library tools exposed — the Phase-1 launch blocker stands.

**One correction made:** item 2 read *"deadline 2026-10-27 (13 days)"*. A hand-maintained day count is
stale the next day — it was already 12 by the time this was checked. **The countdown is gone; the
absolute timestamp stays**, because a date cannot drift and a countdown always does.

---
*Agents verify each item's completion from the API side the moment you say done. Nothing else on the board needs you.*
