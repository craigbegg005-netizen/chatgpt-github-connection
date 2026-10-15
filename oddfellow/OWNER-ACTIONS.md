# Owner actions — the whole queue, tap-sized (updated 2026-10-14 19:00 UTC)

Everything currently blocked on Craig, one card per action, phone-first. Each card: what, where to tap, time, what it unblocks. Nothing here spends money except the two items marked **decision**.

## 1. Gate A — two Render secrets  🔴 blocks Oddfellow v0.20 acceptance
Render dashboard → service **oddfellow-letta-backend-v0206** → Environment → add:
- `LETTA_API_KEY` (from letta.com dashboard → API keys)
- `ODDFELLOW_OWNER_TOKEN` (any long random string; must match what the app stores)
Save → service redeploys (~2 min). **Unblocks: the whole acceptance sequence.** Time: ~5 min.

## 2. Render DB preservation — deadline **2026-10-27T23:21:01Z**  🔴 data loss risk
Either: Render dashboard → `begg-ai-core-db` → Networking → allowlist **your phone's /32** → tell me "allowlisted" and set secret `ODDFELLOW_DB_URL` (I do the dump+restore, zero spend).
Or: run the dump from your own machine (`pg_dump` 18 against the External Connection String).
**Unblocks: the only verified backup of the operational DB.** Time: ~10 min.

## 3. Gumroad delivery check (BSI-COMMERCE-002)  🟡 revenue-readiness
Gumroad dashboard → Products → for each of the 3 listings: open → Content → confirm the delivery file is attached and looks right; check price matches ($7.00 / $4.99 / $5.00). Full checklist: `oddfellow/commerce/DELIVERY-VERIFICATION-BSI-COMMERCE-002.md`. Time: ~15 min.
Optional **decision**: a $4.99 test purchase of your own listing end-to-end (only spend on this list, your call).

## 4. Approve + post the promotion drafts  🟡 revenue-first
Drafts ready: `oddfellow/promotion/DRAFTS-2026-10-14.md` (X post + Reddit-style post per listing, all factual). Review → post from your accounts when ready. Time: ~10 min.

## 5. Reconnect BOTH Google integrations  🟡 blocks file verification + comms failover
Letta chat → connections → reconnect **Google Drive** AND **Gmail** together (they share one broken provisioning path; both 500 "Managed MCP server configuration is unavailable" since 02:00 UTC). **Unblocks: Samurai source-file hash verification, Drive-based asset transfer, the comms failover chain.** Time: ~2 min of taps.

## 6. Refresh the BeggAi (Stripe) token  🟡
Same connections page → BeggAi → reconnect (refresh token invalid). Time: ~1 min.

## 7. Fourthwall dashboard session  🟡 unblocks poster launch decisions
Fourthwall creator dashboard (phone browser works): confirm 0 offers; check payout/support-email readiness; get **per-size base costs** for the Enhanced Matte Poster (the only source — public catalog shows one $5.50 from-price). Do NOT create public products — shop is **LIVE and empty**; anything public is immediately visible. Time: ~15 min.

## 8. Higher-resolution artwork originals  🟡 unblocks the poster range
If a higher-res original of the Samurai artwork exists (bigger than 1122×1402), upload it to the shared Drive folder. Current source caps at 5×7@200DPI / soft 8×10. Time: whatever it takes to look.

## 9. Pages toggle  ⚪ low urgency
GitHub repo → Settings → Pages → enable on canonical branch (turns the storefront page live). One toggle.

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

**One correction made:** item 2 read *"deadline 2026-10-27 (13 days)"*. A hand-maintained day count is
stale the next day — it was already 12 by the time this was checked. **The countdown is gone; the
absolute timestamp stays**, because a date cannot drift and a countdown always does.

---
*Agents verify each item's completion from the API side the moment you say done. Nothing else on the board needs you.*
