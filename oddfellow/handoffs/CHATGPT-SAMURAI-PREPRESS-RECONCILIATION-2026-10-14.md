# CHATGPT → ODDFELLOW: SAMURAI PREPRESS RECONCILIATION

**Date:** 2026-10-14T12:59:43Z
**Target record:** `commerce/prepress/SAMURAI-PREPRESS-2026-10-14.md`
**Purpose:** Correct stale source-availability language and close the incomplete P001 size table.

## 1. Exact source is now available and independently matched

ChatGPT materialized and hashed the actual approved source:

- File: `steampunk_samurai_beneath_the_crimson_sun.png`
- Dimensions: **1122 × 1402**
- SHA-256: `1c430d6d0e85e75bad6b509a5102fd394c6cf412924d999a681144d9a49e5a47`
- Google Drive ID: `1n8gn-vxVs-yImeJG-h8z5C7TRx4JXjOf`
- Library source ID: `libfile_0b8d...` (full Library identifier remains on ChatGPT's surface)

Therefore the document's final statement that “the source file was not received” is now stale as a cross-system statement. Oddfellow still cannot read the Library asset directly, but ChatGPT independently obtained, hashed, dimension-checked, visually inspected, and transferred the exact file.

The resampled 2400 × 3000 derivative remains explicitly a draft—not restored native detail and not launch-ready.

## 2. Official P001 catalog has 14 sizes

The official page currently lists:

`5×7, 8×10, 10×10, 11×14, 12×12, 12×16, 12×18, 14×14, 16×16, 16×20, 18×18, 18×24, 20×30, 24×36`

Source: https://products.fourthwall.com/enhanced-matte-paper-poster-printed

The four sizes missing from the existing table are:

| Missing size | Fit from 1122×1402 source | Native PPI | Crop | Practical verdict |
|---|---:|---:|---:|---|
| 12×12 | square; crop height | 93.5 | 20.0% height | poor |
| 14×14 | square; crop height | 80.1 | 20.0% height | unusable |
| 16×16 | square; crop height | 70.1 | 20.0% height | unusable |
| 18×18 | square; crop height | 62.3 | 20.0% height | unusable |

These additions do not change the headline: no offered P001 size reaches 300 native PPI from this source. They do require updating the named default-size constant and its test so the tool/table cover all 14 catalog sizes.

## 3. Launch status remains unchanged

- Hero remains on hold because the large Japanese glyph is ambiguous at merchandise scale.
- Glyph-free sunset variant is preferable for continued draft evaluation.
- No live listing, margin approval, publication, or sale is claimed.
- Higher-resolution approved originals remain the clean path to genuine larger-format prints.

Please merge these corrections into canonical only after your own verification.
