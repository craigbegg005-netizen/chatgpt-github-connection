# BSI-COMMERCE-002 — Gumroad delivery-verification checklist (one owner dashboard session)

**Purpose:** before any promotion starts, verify that a buyer who pays actually receives what they paid for. Sales/delivery/payout status is NOT publicly verifiable (confirmed 2026-10-14) — only the seller dashboard shows it. This is the one session that closes that gap.
**Time:** ~15–20 minutes on a phone browser (gumroad.com → Sign in → Dashboard). Everything below is taps; no desktop needed except item 5 (file upload) IF a file turns out missing.
**Rule:** check first, fix second — go through all items and record pass/fail before changing anything, so the fixes are one batch.

---

## Item 1 — Delivery file attached (all 3 listings)
Dashboard → Products → open each product → check the "Files"/content section:

| Product | Price | What buyers should receive |
|---|---|---|
| Paycheck Budget Starter Bundle (`/l/oavkpq`) | $7.00 | The budget bundle file(s) |
| The 7-Day Reset Planner (`/l/zvxpuh`) | $4.99 | The 11-page printable PDF |
| Job Search Starter Bundle (`/l/troynk`) | $5.00 | Resume + cover letter + tracker file(s) |

**Pass:** each product has at least one file attached, and the file is the right product (names should make that obvious).
**Fail:** any product with 0 files = buyers pay and receive nothing. Record which; do NOT promote until fixed.

## Item 2 — Spot-check the file content
Download/open each attached file from the dashboard. **Pass:** opens cleanly, contains what the listing promises (11 pages for the Reset Planner; budget categories for the Paycheck bundle; resume + cover letter + tracker for the Job bundle). **Fail:** wrong file, corrupt file, placeholder.

## Item 3 — Price sanity
Each product page in the dashboard shows its price: $7.00 / $4.99 / $5.00. **Pass:** all three match. **Fail:** any mismatch (e.g., a draft price left over) — note it.

## Item 4 — Payout readiness
Dashboard → Payouts (or Settings → Payment). **Pass:** a payout method is connected and not showing an error banner. **Fail:** Stripe/bank disconnected, "action required" banner, or identity-verification prompt — money would sit unclaimed. Note exactly what the banner says (one line is enough for me to act on it).

## Item 5 — Fixes (only for items that failed)
- Missing/wrong file → upload the correct file from the dashboard (easiest on a desktop; if phone-only, Gumroad's mobile browser upload usually works — try it, and if it fights you, that's a desktop session).
- Price wrong → edit, save.
- Payout banner → follow whatever it asks (usually re-link Stripe or confirm identity).

## Item 6 — The $4.99 decision (only if items 1–4 all pass)
A real test purchase is the only end-to-end proof: buy the 7-Day Reset Planner with your own card, confirm the download email arrives and the file opens, then refund yourself (Gumroad allows creator refunds; the fee loss is ~$0.60–$1).
**This is a spend decision — yours to make, not mine.** Everything above is free; this item costs under a dollar and is the only true buyer-side verification.

## What to send back (one line per item is enough)
`1: pass/pass/pass · 2: pass · 3: pass · 4: pass · 6: done/skipped`
I will record the result, and the promotion drafts (`oddfellow/promotion/DRAFTS-2026-10-14.md`) unlock the moment 1–4 pass.
