# Gumroad delivered-file verification — the zero-cost path does not exist

**Date:** 2026-10-14 · **Question:** is the buyer-delivered PDF the corrected **11-page** file, or
does the **12-page** legacy version still sit behind the listing?

## Answer: not verifiable at zero cost. Recorded so nobody retries it.

The listing's **copy** is verifiable and **is correct**. The **delivered file** is not.

| Claim | Status | Evidence |
|---|---|---|
| Listing copy says 11 pages | ✅ **VERIFIED** | **10 occurrences** of `11-page` in the rendered page; **zero** occurrences of `12-page` |
| Listing copy free of the old typo | ✅ **VERIFIED** | 0 occurrences of `oil`; meta description and `og:description` both read "an 11-page printable PDF" |
| **Delivered PDF is the 11-page file** | ❌ **UNVERIFIED** | no route exists |

## Routes I checked, and why each fails

1. **Page preview / sample** — the listing exposes **no** preview, sample or content URL. The
   assets on the page are Gumroad's own JS bundles, not product content.
2. **File metadata** — the page carries an internal `file.external_id` (the asset reference) but
   **no filename, page count or size**, and the asset itself is not fetchable without a purchase.
3. **Purchase** — would answer it definitively and is **excluded by zero-spend.**
4. **Seller dashboard** — the real answer, and **requires owner account access**, which is the
   same blocked condition as every other publishing lane.

## What this means

**An 11-page listing selling a 12-page file is a real customer-facing defect** — the customer
receives more than described, which is usually harmless but is still a mismatch, and the
corrected file was the point of the repair. It is worth checking, and it **cannot be checked from
outside the seller account.**

**Owner action, two minutes in the Gumroad dashboard:** open the product → the attached file's
name/page count is visible on the seller side. If it says 12, re-attach the 11-page file.

## Not claimed

The delivered file is **not** known to be wrong. It is **unknown**. `NOT CHECKED` and `BROKEN` are
different states, and this is the former.
