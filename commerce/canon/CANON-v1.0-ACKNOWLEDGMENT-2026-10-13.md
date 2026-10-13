# BSI Commerce Canon v1.0 — acknowledgment and receipt report

**Date:** 2026-10-13 · **Directive:** accept BSI Commerce Canon v1.0 · **Status:** acknowledged,
with a **material receipt gap** recorded below.

## 1. Files actually received: NONE

The directive designates two files as authoritative:

| File named in the directive | Received? |
|---|---|
| `BSI_COMMERCE_CANONICAL_LETTA_HANDOFF_v1.txt` | ❌ **not received** |
| `EXACT_ORIGINAL_ART_MANIFEST_SHA256.json` | ❌ **not received** |

Verified by searching the whole sandbox (`find /`), not just the usual drop point:

- `/root/downloads/` contains only files from **2026-09-30 and 2026-10-01** — screenshots and
  an owner-token file. Nothing from 2026-10-13.
- No file matching either name exists anywhere on disk.
- No upload arrived in this session.

**I am not able to read the letter's contents or import an archive that is not here.** The
directive's own summary of the canon is recorded below as *the owner's description*, which is
not the same thing as having read the letter — and I will not paraphrase a document I have not
seen, or treat a summary as its text.

**To unblock:** attach both files.

<action type="request-file-upload" message="Attach the Canon v1.0 letter and the art manifest" multiple="true"></action>

## 2. Artwork: three files exist, six collections were described

The directive says to import the existing original artwork archive and preserve **six separate
collections**. What is actually present is **three files**:

| File | Bytes | SHA256 |
|---|---|---|
| `tee-extrusion-blueprint.png` | 285,700 | `25063a854bea02c8e2ddc82128954401d35833e08f77f57b8dfaed6bf86848d9` |
| `poster-interference-4.png` | 6,585,238 | `c7c17e8f31a96969bb021596a2f4990ea47aabc3a604faa3ff736d25208e7799` |
| `mug-batch-004.png` | 116,621 | `51cc7e4d5984ab8ec0be9c42d3b5e374943fbc63e55aa9d5244657afc1229421` |

All three live in `gh-pages` at `art/v1/` and were re-downloaded and hashed **from the live
files** on 2026-10-13. Hashes are committed alongside this file as
`ART-BASELINE-SHA256-2026-10-13.json`.

**This is a baseline, not the manifest.** The owner-named manifest would let me verify that
these three are the approved versions. Without it, these hashes are simply *what is here now* —
recorded so that any future substitution is detectable.

**Named collections that are absent.** The directive names two of six and their specifics:
Art Deco Samurai (Japanese watercolour + subtle steampunk) and Retro Future Noir (slim
glowing-eye cybernetic card shark, cigarette, dirigible-style spaceships, Alley Ambush scene).
**No artwork matching either exists in this sandbox.** The remaining four collections are not
named in the directive text I received, so I cannot even inventory them by title.

**I will not generate substitutes.** The directive is explicit, and it matches the doctrine: do
not replace refined, owner-approved pieces with invented visuals.

## 3. Verified current status (re-checked this session, not carried forward)

| Item | Verified state |
|---|---|
| Fourthwall storefront | ✅ **`https://wesellstuff-ymn-shop.fourthwall.com`** — matches the directive exactly |
| Shop status | `COMING_SOON`, `lastLiveAt: null` |
| Offers | **0** (`totalElements: 0`) — three prepared products intact, nothing created |
| Prepared products | tee / poster / mug with corrected margins (44.8% / 78.0% / 70.3%) |
| Artwork creation | 🔴 **blocked** — the three media-library MCP tools are still not exposed |
| Spreadshop | 🔴 **no access** — no MCP server, no integration-catalog entry. Account id `401329032` is new information from this directive and is recorded; it is not a substitute for access |
| Public-facing BSI branding | none published — the shop's description is Fourthwall's unedited default boilerplate, not BSI copy |
| Revenue / sales / payouts | **none. Zero.** |

## 4. Gates the directive restates — current standing

- **≥ $5 contribution / ≥ 25% margin:** the three prepared products pass *on Fourthwall pricing*.
  Spreadshop base costs are **unknown**, so no Spreadshop product can be assessed yet.
- **No seller-funded charges:** no paid tool, ad, sample, inventory or fulfilment invoked. The
  one paid path identified (~$0.01/image background removal) was deliberately not used.
- **Print resolution:** **not verified** for any of the three files against their intended print
  sizes. The poster is 6.5 MB and the tee 285 KB; actual pixel dimensions against the catalog
  print areas have not been checked. Recorded as an open gate, not a pass.
- **Legal / payout / account:** open, as previously recorded.
- **Publish:** nothing published, and nothing will be until the gates pass.

## 5. What I need from the owner

1. **The two files** — letter and manifest (upload card above).
2. **The six collections' artwork**, or confirmation that only three pieces exist.
3. **Spreadshop access** — the URL, or a browser sign-in, so the account can be verified at all.
4. **Fourthwall artwork upload** — one action unblocks the three prepared products.

## 6. Versioning

Per the directive: later owner decisions are to be dated and appended as **new canonical
versions** rather than edited into this one. This file is the v1.0 receipt. It is not itself the
canon — the canon text was not received.
