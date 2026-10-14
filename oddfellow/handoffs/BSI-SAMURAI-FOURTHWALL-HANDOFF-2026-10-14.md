# BSI Samurai Fourthwall Launch Handoff

**Task ID:** BSI-SAMURAI-FOURTHWALL-003  
**Date:** 2026-10-14  
**Status:** RESAMPLED_DRAFT_ASSET_NOT_LAUNCH_READY  
**Spend:** $0  
**Live commerce changes:** None

## Reconciliation basis

Reconciled against canonical branch head `129c2364ccff882484fcf8364439f45c6a94622e`, including:
- `commerce/prepress/SAMURAI-PREPRESS-2026-10-14.md`
- `commerce/WESELLSTUFF-INVENTORY-2026-10-13.md`
- `commerce/WESELLSTUFF-READINESS-2026-10-13.md`

## Preserve

- Hero source `SAM-POST-01`: `steampunk_samurai_beneath_the_crimson_sun.png`, 1122×1402, SHA-256 `1c430d6d0e85e75bad6b509a5102fd394c6cf412924d999a681144d9a49e5a47`.
- Approved variant `SAM-POST-02`: `watercolor_steampunk_samurai_at_sunset.png`, 1122×1402, SHA-256 `49ca79e3f7c3c38dc3d61cb316bb8fe1604680e64776b1a49f23973abc5c7a27`.
- The similarly titled image with SHA prefix `471303` is a different file and must not replace the canonical hero.

## QA decision

- Hold `SAM-POST-01`: independent review found its large stylized glyph broadly resembles `侍` at full resolution but is ambiguous at thumbnail/merch scale. Do not market it as exact Japanese typography without corrected, independently reviewed glyph treatment.
- Use the owner-approved, glyph-free `SAM-POST-02` only for further hidden-draft evaluation.

## Resampled draft asset

- File: `SAM-POST-02_8x10_300dpi_PREPRESS.png`
- Dimensions: 2400×3000 px, sRGB, 4:5.
- SHA-256: `1e6442002d40fd19df22465a8759826ca4e32cb49cab7ed99cb170144205c596`.
- Method: deterministic Lanczos resize from the canonical source; no generative redraw or added content.
- Independent pixel/visual QA: no visible crop, distortion, clipping, seams, halos, corruption, or additions; normalized correlation 0.994078.
- Critical limitation: this is a resample, not restored native detail. The 1122×1402 source supplies about 140 native PPI at 8×10. Do not describe the asset as native 300-PPI art or treat dimension compliance as proof of print quality.
- Library ID: `libfile_82c1890aad6c819186852c824a2ad16f`.
- Drive ID: `1FUIsr4BUD-VEOGOF2QifcCTY4RolWB5F`.
- Drive folder: https://drive.google.com/drive/folders/1a6Wer2z3HRYQqQ4T7cGRl1c3rKuDuogP
- Drive file is private/not shared; connected-account access only.

## Fourthwall facts re-derived

- Public shop redirects to Coming Soon/password: https://wesellstuff-ymn-shop.fourthwall.com/password
- The most recent canonical live MCP inventory (2026-10-13) reports **0 offers**, not three existing products. Three product concepts were prepared but not created.
- Candidate POD product: Allcolor P001 Enhanced Matte Paper Poster.
- 8×10 matches the art's 4:5 ratio, but native detail is only about 140 PPI.
- 5×7 is about 200 native PPI and requires roughly 10.7% width crop.
- No available poster size reaches 300 native PPI from this source.
- Public catalog lists the poster from $5.50; exact design/size cost remains unverified until a design exists.
- Official catalog: https://products.fourthwall.com/enhanced-matte-paper-poster-printed
- Official artwork guidance: https://help.fourthwall.com/create-and-sell-products/best-practices/artwork-best-practices

## Remaining gates

1. Authenticate to the Fourthwall creator dashboard and confirm current offer count/status against the 2026-10-13 MCP evidence.
2. Check for a genuinely higher-resolution approved original before accepting a soft print.
3. If no higher-resolution original exists, create only a hidden draft for mockup/quality-indicator review; do not publish.
4. Confirm exact base cost, processing-fee impact, payout setup, and non-negative margin using dashboard values.
5. Obtain independent review of the hidden draft crop/bleed/mockups and the print-quality limitation.
6. Keep the shop in Coming Soon and products Hidden until owner launch authority, payout readiness, support email, policy review, and print-quality gate are satisfied.
7. Preserve $0 spend; do not order samples, subscribe to Pro, or enable paid features.

No product was created, published, repriced, ordered, or advertised in this task.
