# Spreadshop — state, access gap, and Marketplace findings

**Date:** 2026-10-13 · **Lane:** BSI commerce (second storefront) · **Owner report:** Spreadshop
account created.

## 🔴 I have no access to the Spreadshop account

The directive asks me to "obtain and verify the exact Spreadshop URL from the authenticated
sales-channel dashboard". **I cannot do that, and I will not guess it.** Evidence:

| Check | Result |
|---|---|
| Spreadshop MCP server | **none** — only `BeggAi` (Stripe) and `Fourthwall` are available |
| Spreadshop in the Letta integration catalog | **no matches** for `spreadshop`, `print on demand merch`, or `ecommerce storefront` |
| Spreadshop / Spreadshirt anywhere in memory or repo | **zero references** — this is its first mention |

Probing plausible shop names would be **guessing**, and a wrong guess resolves to somebody
else's real storefront. That is exactly the kind of unevidenced claim the doctrine forbids, so
the URL stays unverified until there is a real source for it.

**Two ways to unblock, both zero-cost:**
- **A —** Tell me the URL and I will verify it live (HTTP 200, products visible, correct shop).
- **B —** Sign into the sandbox browser once (`[Open computer]`); I can then read the sales-channel
  overview directly, which is the authoritative source the directive names.

Spreadshop's own docs give the URL shape — `SHOPNAME.myspreadshop.com` — and say the shop name
is shown **in the overview of your sales channels**. That is the field I need to read.

## ✅ Fourthwall — verified this session (nothing lost)

The three prepared products are **intact**. Re-verified live:

```
ecommerce_get-offers        → totalElements: 0        (still nothing created)
ecommerce_get-current-shop  → status: COMING_SOON, lastLiveAt: null
```

**Storefront URL (verified, from `get-current-shop`):**

- **Primary domain: `https://wesellstuff-ymn-shop.fourthwall.com`**
- Shop id `sh_b24e7c60-65fe-4cf1-bc63-bc0642248746`, name `Wesellstuff`
- Custom domains configured: `wesellstuff.com`, `www.wesellstuff.com` — but the Free plan's
  `domains: limit 0` means only the `*.fourthwall.com` host actually serves
- Currencies: USD + 16 others · Payment providers: Stripe, PayPal
- Payouts ACTIVE (Stripe connected 2026-10-13T01:18Z) — **but no products, so no sales to pay out**

⚠️ **Note:** the shop's own description is Fourthwall's generic default — *"The official website
and shop of Wesellstuff. Find the latest content, buy merch, and support your favorite
creator."* It is unedited boilerplate, not real copy, and should be replaced before launch.

## Spreadshirt Marketplace — it is NOT automatic

The owner's caution is correct, and the docs confirm it. **Marketplace and Spreadshop are two
separate sales channels**, and publication is an explicit choice, not a side effect:

> *"You can now decide where a design should be published — either on Marketplace, Spreadshop
> or both — before you create the design or product."* — Spreadshirt, sales-channels announcement

Practical consequences:

1. **Publishing is per-design.** The Marketplace path is *Designs & products → My designs →
   "Publish on the Marketplace"*. It is not enabled by having a shop.
2. **No extra fee** to publish on the Marketplace — *"you don't need to pay anything to publish
   your designs on the marketplace."*
3. **A single-channel account gets routed automatically**, but that routing decision is made
   from what the account is set up as. A new Spreadshop account should **not** be assumed to
   carry Marketplace exposure.
4. **This is a known confusion point.** Multiple users in the comments report being unable to
   enable Marketplace for existing designs, and one asks specifically about selling on both
   simultaneously. So the setting must be **verified in the dashboard**, not inferred.
5. **Marketplace is discovery, not a guarantee.** It exposes designs to Marketplace browsers
   (~140 product types available); it does not create demand. Do not count it as traffic we have.

**Conclusion: treat Marketplace as a second, separately-activated channel that must be
confirmed per design. Do not report it as live until the dashboard shows it.**

## Margins on Spreadshop are NOT yet known

Spreadshop's model is base cost deducted from retail — no monthly fee, no minimum — with monthly
payouts by direct deposit or PayPal. **But I have no Spreadshop base-price data**, and base
prices differ from Fourthwall's. The owner's gates (> $5 net contribution, > 25% margin) apply
to every product on every storefront, so **no Spreadshop product can be approved until its own
base costs are read from the dashboard.** Fourthwall margins do not transfer.

## Not claimed

- No Spreadshop URL verified. No Spreadshop account registered (owner said not to duplicate).
- No products created, listed, or published on either storefront.
- No Marketplace exposure claimed. No traffic claimed. No revenue, no sales, no payouts.
- No spend. No paid service, ad, sample, inventory, or seller-funded fulfilment.
