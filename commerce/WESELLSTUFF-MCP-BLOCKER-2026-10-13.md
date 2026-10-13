# Wesellstuff — MCP blocker: artwork cannot enter the media library

**Date:** 2026-10-13 · **Lane:** BSI commerce (Fourthwall) · **Status:** ⚠️ BLOCKED on a gap in
the Fourthwall MCP server. Nothing has been listed. No revenue.

## What is verified working

| Item | Evidence |
|---|---|
| Fourthwall MCP connected | 126 tools available; `ecommerce_get-current-shop` returns live data |
| Shop identity | `Wesellstuff`, id `sh_b24e7c60-65fe-4cf1-bc63-bc0642248746` |
| My access level | `ecommerce_get-shop-permissions` → `groups: OWNER` |
| Plan | Free (`subpln_m6Z_V0csTKeYFXOLAMDasg`), `pro: false` |
| Offer capacity | `offers: limit 50, usage 0` — capacity is not the constraint |
| Payouts | `ecommerce_get-payout-info` → **status ACTIVE**, owner `CUSTOM`, connected 2026-10-13T01:18:03Z |
| Payment providers | `allowedPaymentProviders: PayPal, Stripe` |
| Support email | `customerSupportEmail: craigbegg005@gmail.com` (already set) |
| Site status | `COMING_SOON`; `lastLiveAt: null` — never been live |
| Custom domain | `wesellstuff.com` / `www.wesellstuff.com` configured, but **Free plan `domains: limit 0`** |
| Original artwork | 3 designs generated, visually inspected, hosted at public URLs (see below) |

## The blocker, with the exact evidence

`ecommerce_create-offers-from-products` requires each `regionUrls` entry to be an image that is
**already in the shop's media library**. Three probes establish this precisely:

1. **External URL** (`https://raw.githubusercontent.com/.../tee-extrusion-blueprint.png`):
   > `Asset URI ... does not point to a managed or trusted GCS bucket.`

2. **Gateway bucket URI** (`gs://popshopprod-mcp-gateway-assets/sh_b24e7c60-.../probe.png`):
   > `Region artwork is not in this shop's media library: [...]. Save each image to the media
   > library first and pass the url it returns.`

   The error **changed**, which proves the gateway bucket *is* trusted — the bucket check passes.
   Only the media-library registration is missing.

3. **The tools needed to register it are not exposed.** The server's own tool descriptions
   reference three tools that do not exist in its tool list:

   | Tool the docs require | Exposed? |
   |---|---|
   | `ecommerce_request-media-upload-link` | ❌ **not available** |
   | `ecommerce_save-media-library-image` | ❌ **not available** |
   | `ecommerce_get-media-library-images` | ❌ **not available** |

   `ecommerce_generate-product-design-previews` states verbatim:
   *"regionUrls MUST be URLs from the shop's media library (use get-media-library-images, or
   upload via request-media-upload-link → PUT file → save-media-library-image)."*
   `ecommerce_edit-design` likewise: *"Every replace-image / add-image href must be the exact CDN
   url returned by ecommerce_save-media-library-image."*

**Conclusion: there is no MCP path to get artwork into the media library, and therefore no MCP
path to create a product design.** The 126 exposed tools are internally inconsistent — three
tools are referenced by name in their siblings' descriptions but are absent from the server.

This is a defect in the Fourthwall MCP server, not in our configuration. Worth reporting to
Fourthwall.

## Paths that do NOT work

- **`brand_extract_assets`** — extracts *individual elements* (wordmark, illustration, notes
  block, grid) from an analysed sheet, not the composed design. Wrong output, and its own
  description says to confirm before spending image-gen calls.
- **`brand_remove_background`** — costs **~$0.01/image** (Ideogram) and *removes the
  background*, which would destroy all three designs (the tee and mug are built on solid
  backgrounds; the poster is full-bleed). Wrong on cost and wrong on output.
- **Upgrading to Pro ($19/mo)** — would raise limits but does not add the missing tools.
  **Spending, and not a fix.**

## What is ready to go the moment artwork is in

- 3 original artworks, inspected and defect-corrected, at
  `https://raw.githubusercontent.com/craigbegg005-netizen/chatgpt-github-connection/gh-pages/art/v1/`
  (`tee-extrusion-blueprint.png` 285,700 B · `poster-interference-4.png` 6,585,238 B ·
  `mug-batch-004.png` 116,621 B) — all verified `HTTP 200 image/png`.
- Validated offer payloads for all three products, with exact catalog IDs, verbatim size strings
  and profit margins: `tee.json`, `poster.json`, `mug.json`.
- Margin basis re-derived from the live catalog (authoritative, and **lower** than the pricing
  PDF's "starts at" figures):

| Product | Catalog ID | Base from | Profit margin | Retail at entry size |
|---|---|---|---|---|
| Gildan Unisex Softstyle Tee (64000) | `pro_O7Dd4-6JTUuq48NSUd3TMg` | $9.50 | $18.50 | **$28.00** |
| Enhanced Matte Paper Poster (P001) | `pro_15bc29bc8a324d449d` | $5.50 | $19.50 | **$25.00** |
| White Glossy Mug (WGM78) | `pro_4v5OfYhyRx62KW5b7Oj6Uw` | $5.95 | $14.05 | **$20.00** |

## Two ways to unblock

**A — Owner uploads the three PNGs in the product designer** (documented Fourthwall path;
desktop browser required). Products → Create New Product → Design Something New → choose the
catalog product → Upload image. ~5–10 minutes total. Zero cost.

**B — Owner signs into the sandbox browser once; the agent drives the upload.** The artwork
files already sit locally in this sandbox, so no download step is needed. After sign-in the
agent can create all three products, set prices, and publish. One owner action, then hands-off.

## Honesty notes

- **Nothing is listed, published, or live.** The shop is still `COMING_SOON` and `lastLiveAt`
  is `null`.
- **No revenue.** No sale has occurred.
- **No spend.** No paid tool has been invoked; the ~$0.01/image path was identified and
  deliberately not used.
- The Free plan's `domains: limit 0` means `wesellstuff.com` will not serve on the current
  plan — the `*.fourthwall.com` subdomain is what works.
