# SAM-POST-01 prepress analysis — the launch constraint is resolution, not authentication

**Date:** 2026-10-14 02:55 UTC · **Source:** `steampunk_samurai_beneath_the_crimson_sun.png`, **1122 × 1402 px**
**Sizes tested:** Fourthwall Enhanced Matte Paper Poster (P001), all **14** available sizes, read live from the catalog.

## 🔴 The headline

**At 300 DPI this artwork supports 3.74 × 4.67 inches — smaller than Fourthwall's SMALLEST poster (5×7).**

There is **no size** at which this source produces a 300-DPI print. The best available outcome is
**5×7 at 200 DPI**, with a 10.7% width crop.

**So the Samurai launch cannot be a "matte art print" range. It is a 5×7 small print, and arguably
an 8×10 that is soft.** That is a product decision the owner has to make, and it is invisible from
the authentication work currently in progress.

## Measured, size by size (fit, no upscaling)

| Size | Aspect | vs source (0.800) | Real DPI | Crop | Verdict |
|---|---|---|---|---|---|
| **5×7** | 0.714 | crop width | **200** | 10.7% | ✅ **viable** |
| **8×10** | 0.800 | **EXACT** | **140** | 0% | ⚠️ soft |
| 11×14 | 0.786 | crop width | 100 | 1.8% | ❌ poor |
| 10×10 | 1.000 | crop height | 112 | 20.0% | ❌ poor |
| 12×16 | 0.750 | crop width | 88 | 6.3% | ❌ unusable |
| 12×18 | 0.667 | crop width | 78 | 16.7% | ❌ unusable |
| **16×20** | 0.800 | **EXACT** | **70** | 0% | ❌ unusable |
| 18×24 | 0.750 | crop width | 58 | 6.3% | ❌ unusable |
| 20×30 | 0.667 | crop width | 47 | 16.7% | ❌ unusable |
| 24×36 | 0.667 | crop width | 39 | 16.7% | ❌ unusable |

**8×10 and 16×20 share the source's exact 4:5 aspect** — so they need no crop, which is why they
look attractive. But 8×10 is only 140 DPI and 16×20 is 70.

## Why upscaling is not the answer

| Target | Pixels needed at 300 DPI | Linear upscale required | Real detail behind it |
|---|---|---|---|
| 8×10 | 2400 × 3000 | **2.1×** | 140 DPI |
| 16×20 | 4800 × 6000 | **4.3×** | 70 DPI |
| 24×36 | 7200 × 10800 | **7.7×** | 39 DPI |

**Corrected 2026-10-14:** this row read **6.4×**. That is the *width* ratio (7200/1122); the
*height* ratio governs, and 10800/1402 = **7.7×**. The row already reported 39 DPI, which is the
height-limited figure, so it contradicted itself. 8×10 and 16×20 are exact 4:5 matches and so are
unaffected — both dimensions scale equally. **The correction makes the point stronger, not weaker.**
Found by `prepress_check.py`, which reproduces this table in `oddfellow/tests/test_prepress_check.py`.

**A resampled file is a bigger number, not more detail.** The handoff already says this — *"an
upscaled file is not proof of restored original detail"* — and the numbers show why: at 24×36 you
would be inventing **7.7× more pixels than exist.**

## The one question that could change everything

**Is there a higher-resolution original?** The source is 1122×1402. If this was AI-generated, the
generator's native output may be larger, or a higher-res export may exist in the ChatGPT Library
alongside it. **That is the only path to a genuine large-format print** — and it is worth checking
BEFORE accepting a 5×7-only launch.

**Do not regenerate the artwork to fake it.** The owner has said so explicitly, and a regenerated
piece is not the approved piece.

## Pricing at the sizes that work

Fourthwall lists this poster `priceFrom: 5.50` (the 5×7 end of the range). Against the owner's
gates (**≥ $5 contribution, ≥ 25% margin**):

| Size | Est. base | Retail | Margin | Margin % | Gates |
|---|---|---|---|---|---|
| 5×7 | ~$5.50 | **$14.99** | $9.49 | 63% | ✅ pass |
| 5×7 | ~$5.50 | $10.50 | $5.00 | 48% | ✅ exactly at the floor |
| 5×7 | ~$5.50 | $9.99 | $4.49 | 45% | ❌ fails $5 |
| 8×10 | ~$7-8 | $18.00 | ~$10 | ~56% | ✅ if the 140 DPI is accepted |

⚠️ **Base costs here are inferred from `priceFrom`/`priceTo`, not the per-size quote.** The exact
per-size base is only available through `get-customization-pricing`, which needs a
`customizationId`, which needs a design, which is the blocked media-library path. **Treat the
prices above as illustrative, not as the margin gate passing.**

## Recommendation

1. **Check for a higher-resolution original first.** If one exists, this whole constraint dissolves.
2. **If not: launch at 5×7 only**, priced ~$14.99, and describe it accurately as a small print. Do not offer larger sizes that the file cannot support.
3. **Do not upscale and call it a poster.** It would pass a size check and fail a customer.
4. **Apply the same analysis to every other collection before launch.** If the Samurai master is 1122×1402, the others likely are too — which would mean **the entire Phase-1 wall-art plan is affected, not just this SKU.**

**Point 4 is the one to act on.** One SKU is a product decision; all six collections sharing the
limit is a strategy problem.

## Not claimed

The source file was **not received** — dimensions come from the handoff, and the SHA256
`1c430d6d…a49e5a47` matches nothing in this repository. **No prepress was performed on the actual
file.** This is a dimensional analysis of the stated source, and it should be re-run the moment the
real file arrives.
