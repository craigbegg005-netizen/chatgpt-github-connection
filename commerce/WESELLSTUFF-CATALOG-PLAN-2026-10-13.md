# Wesellstuff — catalog plan and unit margins

**Date:** 2026-10-13 · **Lane:** BSI commerce (Fourthwall) · **Status:** 🛠 PLANNED — nothing is
listed, published, or selling. No revenue has occurred.

Store: `https://wesellstuff-ymn-shop.fourthwall.com` — **canonical, per owner directive
2026-10-13. Do not create a duplicate storefront.**

> **A listing is not a sale; a suggested margin is not profit.** Carried forward from
> `oddfellow/HANDOFF-UNIVERSAL-2026-10-05-1955Z.md`.

## Verified store state (probed 2026-10-13 01:41 UTC)

| Check | Result |
|---|---|
| `GET /` | HTTP 200 → **redirects to `/password`** |
| `GET /products`, `/collections/all`, `/about` | HTTP 200 → **all redirect to `/password`** |
| Page title | `Coming soon \| Wesellstuff` |
| Page body | email signup only — "Coming soon · Join our mailing list" |
| Payouts | **NOT VERIFIED** (owner-reported) |

So the store is in Fourthwall's **"Coming soon" site status**, not merely "no products yet".
Nothing is publicly reachable. Per Fourthwall's own docs, pages and URLs are only publicly
reachable once the shop is set to **Live**.

## Verified POD base costs (primary source)

All figures read from Fourthwall's own pricing PDF —
`https://cdn.fourthwall.com/downloads/fourthwall_pricing.pdf` — extracted with `pdftotext` and
read directly, not taken from a summary. **Independently re-verified 2026-10-13.**

| Product | Base cost | Note |
|---|---|---|
| Gildan Classic T-shirt (Gildan 64000) | **Starts at $9.80** (range $9.29–$19.29) | +$3.90 per additional print area |
| Bella + Canvas Supersoft (3001) | Starts at $12.95 | |
| Gildan Classic Hoodie (18500) | **Starts at $20.75** (range $20.35–$32.75) | |
| High-Quality Matte Poster (8×10–24×36) | **Starts at $7** | "Price varies by size of poster" |
| High-Quality Framed Poster | Starts at $18.50 | |
| Classic Coffee Mug, 11 oz ceramic | **$7.95** | "One price regardless of design" |
| Large Coffee Mug, 15 oz | see PDF | |
| Eco-Friendly Tote (Econscious EC8000) | Starts at $14.95 | |
| Kiss-Cut Stickers (Allcolor 5493) | From $2.29 | |

**Fees, verified from the same PDF:**
- **0% commission on physical products**, 3% on digital.
- Credit card rate **2.9% + $0.30**.
- "No upfront costs."
- ⚠️ **Nuance worth recording:** the 0% carries an asterisk — *"When you use Fourthwall to
  produce your products, we have a margin built into the product price (under 10% on
  average)."* The commission is genuinely 0%, but Fourthwall's margin is already inside the
  base cost. This does not change the arithmetic below (base cost is what we pay), but it
  should not be described as "Fourthwall takes nothing".

⚠️ **Base cost is "starts at".** The exact figure for our chosen blank/colour/size is shown
only inside the logged-in product designer. Every margin below must be **re-confirmed in the
designer** before a price is set. Treat these as close estimates, not final.

## The three proposed products

All three are original work authored by us. No third-party IP, no logos, no real-brand marks,
no people or likenesses, no certifications we do not hold.

### 1. Apparel — "Extrusion Die Blueprint" heavyweight tee
- **Concept:** original blueprint-style line illustration of a generic industrial
  plastics-extrusion die, with invented dimension callouts and part numbers.
- **Base cost:** $9.80 (Gildan 64000, printed on-demand)
- **Retail:** $28.00 → **gross margin $18.20 (65.0%)**
- **Net per unit after card processing:** 28.00 − 9.80 − (28.00 × 0.029 + 0.30) = **$17.09**

### 2. Wall art — "Interference No. 4" matte poster
- **Concept:** original generative artwork — a concentric-ring interference/moiré pattern
  computed from a mathematical function, printed as a matte poster.
- **Base cost:** starts at $7.00 (entry size; varies by size — **UNVERIFIED for our size**)
- **Retail:** $25.00 → **gross margin $18.00 (72.0%)** at the entry size
- **Net per unit after card processing:** 25.00 − 7.00 − 1.03 = **$16.98**

### 3. Accessory — "Batch No. 004" 11 oz ceramic mug
- **Concept:** original typographic "material batch" label — fictional lot number, fictional
  test-spec grid, our own type system.
- **Base cost:** $7.95 (Classic Coffee Mug, 11 oz)
- **Retail:** $18.00 → **gross margin $10.05 (55.8%)**
- **Net per unit after card processing:** 18.00 − 7.95 − 0.82 = **$9.23**
- ⚠️ This is the thinnest of the three and sits at the edge of Fourthwall's $10-profit
  guidance. **$20.00 retail** would net **$11.23** — recommended if the design justifies it.

### Margin summary

| Product | Base | Retail | GM $ | GM % | Net/unit after fees |
|---|---|---|---|---|---|
| Extrusion Die Blueprint Tee | $9.80 | $28.00 | $18.20 | 65.0% | $17.09 |
| Interference No. 4 Poster | $7.00 | $25.00 | $18.00 | 72.0% | $16.98 |
| Batch No. 004 Mug | $7.95 | $18.00 | $10.05 | 55.8% | $9.23 |

**Break-even is 0 units** for all three — POD carries no upfront or fixed cost, so there is no
investment to recover. Any unit sold at these prices clears base cost and processing. This is
**not** a profitability claim: with no traffic and no sales, expected revenue is $0.

## What is NOT verified

- Exact base cost for our specific blank/colour/size — needs the logged-in product designer.
- Poster base cost for the size we would actually list.
- Whether the design concepts would pass Fourthwall's Acceptable Use review — nothing submitted.
- **Demand.** No sourced sales, traffic, or market-size data exists. None is claimed.
- Payment-processing basis (whether 2.9% + $0.30 applies to shipping too) — unconfirmed.

## Lane separation (owner directive, binding)

These products sit entirely in BSI's own lane. They use no EM Brooks / Brooks World canon
(Emma Brooks, Mia Vale, Jordan Blake, Ma & Pa), no Global Peace & Human Security Framework
material, and no affiliate content. Branding, data, and infrastructure stay separate.
