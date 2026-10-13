# Wesellstuff — product inventory and preservation record

**Date:** 2026-10-13 · **Lane:** BSI commerce (Fourthwall) · **Directive:** demand-led product strategy

## Headline: there are ZERO products in the shop

The owner directive asked to inventory "the three products already reported created in
Wesellstuff". **Live evidence contradicts that premise.**

```
letta mcp call mcp__Fourthwall__ecommerce_get-offers --args '{}'
→ pageNumber: 0, pageSize: 5, totalElements: 0, totalPages: 0
```

`totalElements: 0`. Shop status `COMING_SOON`, `lastLiveAt: null`. **Nothing has been created,
listed, or published. No sales. No revenue.**

What exists is **three PREPARED products** — artwork plus catalog/pricing research — blocked
from creation by a gap in the Fourthwall MCP server.

## The three prepared products (verified live this session)

| # | Product | Catalog ID | Base cost | Retail | Margin | Margin % | Gate |
|---|---|---|---|---|---|---|---|
| 1 | Gildan Unisex Softstyle T-Shirt (64000) | `pro_O7Dd4-6JTUuq48NSUd3TMg` | **$15.45** | $28.00 | $12.55 | 44.8% | PASS |
| 2 | Enhanced Matte Paper Poster (P001) | `pro_15bc29bc8a324d449d` | $5.50 | $25.00 | $19.50 | 78.0% | PASS |
| 3 | White Glossy Mug (WGM78) | `pro_4v5OfYhyRx62KW5b7Oj6Uw` | $5.95 | $20.00 | $14.05 | 70.3% | PASS |

All three clear the owner's gates: contribution > $5/unit and margin > 25%.

### ⚠️ Correction to the previously recorded tee margin

The 2026-10-13 blocker doc recorded the tee as base **$9.50**, margin **$18.50**. That is
**overstated by $5.95**. The tee's `front_large` print area carries its own
`salePrice: $5.95`, and `get-customization-pricing` documents cost as a component breakdown of
**"blank, print regions"** — so the print region is additive:

```
blank $9.50 + front_large $5.95 = base $15.45   (not $9.50)
$28.00 - $15.45 = $12.55 margin                  (not $18.50)
```

The poster and mug print areas are `salePrice: $0.00` (included in the base), so their figures
were correct. Only the tee was wrong, and only because its production method is DTG — where the
print charge is separate — while the other two include it.

**Residual uncertainty:** the exact landed cost could not be confirmed with
`get-customization-pricing`, because it requires a `customizationId`, which requires a design,
which is the blocked path. The correction above follows from the tool's own component model and
the live print-area prices; it is the right number to plan on, but a design-based confirmation
is still owed once artwork can be created.

## Preservation status

| Asset | Status |
|---|---|
| 3 artworks (PNG) | ✅ **PRESERVED** — committed to `gh-pages` at `art/v1/`, HTTP 200, byte-exact |
| Offer payloads `tee/poster/mug.json` | ❌ **WERE MISSING** — in no commit, and not on disk. **Reconstructed and committed here** on 2026-10-13 from live catalog data |
| Catalog/pricing research | ✅ preserved in this file and `commerce/offers/*.json` |

The payload loss is the finding worth carrying: a document called them "ready" while nothing on
disk or in version control held them. Reconstructed from the live catalog rather than from the
document, so the values are re-verified rather than copied forward.

## The blocker (re-verified live 2026-10-13)

`create-offers-from-products` and `generate-product-design-previews` both require `regionUrls`
to be URLs **from the shop's media library**. The three tools that would put artwork there are
**referenced by name in sibling tool descriptions but not exposed**:

```
request-media-upload-link      hits=0
save-media-library-image       hits=0
get-media-library-images       hits=0
```

126 tools are exposed; these three are not among them. **There is no zero-cost MCP path to
create a product design.** `brand_remove_background` (~$0.01/image, destroys the background) and
`brand_extract_assets` (metered gpt-image calls) are both excluded by the zero-spend rule.

**Unblock requires one owner action** — either upload the three PNGs in the Fourthwall product
designer (desktop browser, ~5–10 min, zero cost), or sign into the sandbox browser once so the
agent can drive the upload (files already local).

## Not claimed

- No products created. No listings. No publishing.
- No revenue, no sales, no payouts.
- No spend — the paid paths were identified and deliberately not used.
- **A listing is not a sale; a suggested margin is not profit.**
