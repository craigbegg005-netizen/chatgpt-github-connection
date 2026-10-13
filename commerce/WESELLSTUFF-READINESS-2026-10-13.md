# Wesellstuff — payment readiness, policies, and launch gate

**Date:** 2026-10-13 · **Lane:** BSI commerce (Fourthwall) · **Status:** ⚠️ NOT READY — store is
in "Coming soon" mode, payouts unverified, nothing listed.

Sources are Fourthwall's own help centre (`help.fourthwall.com`) unless noted. **This is not
legal or tax advice** — see the professional-review flags at the end.

## Requirements table

| # | Requirement | Status | Source |
|---|---|---|---|
| **PAYOUTS** | | | |
| 1 | Connect Stripe via Settings → Billing and payouts. Stripe is the only payout method (bank account / debit card). No PayPal, Wise, crypto, gift cards. | ✅ VERIFIED | `how-you-get-paid`, `how-payout-methods-differ-from-payment-methods` |
| 2 | Stripe identity verification: legal name, DOB, home address, government photo ID, email + phone, bank routing + account no. | ✅ VERIFIED | `stripe-account-setup-and-issues` |
| 3 | US creators must complete a W-9/W-8BEN in Stripe — **payouts are blocked without it.** | ✅ VERIFIED | `stripe-account-setup-and-issues` |
| 4 | Country must match residence and bank. Virtual US accounts (Wise/Payoneer/Grey) not accepted. | ✅ VERIFIED | `country-not-supported-by-stripe` |
| 5 | Payouts: automatic monthly by the 3rd business day, for balances over **$25**. Under $25 needs a manual email request. | ✅ VERIFIED | `how-you-get-paid` |
| 6 | Payout can take **7–10 business days** to land after sending. | ✅ VERIFIED | `how-you-get-paid` |
| 7 | One-time site verification holds the **first** payout. Selling still works; only the transfer pauses. | ✅ VERIFIED | `site-verification-before-first-payout` |
| 8 | Failed payouts do **not** auto-retry — must be re-triggered by emailing support. | ✅ VERIFIED | `troubleshooting-missing-or-failed-payouts` |
| **SHIPPING** | | | |
| 9 | Shipping is calculated and applied **automatically** by product type + destination. Owner cannot pick a carrier or set rates for on-demand items. | ✅ VERIFIED | `change-shipping-options` |
| 10 | Destination countries are managed **centrally by Fourthwall**; owner cannot add/remove them. | ✅ VERIFIED | `pod-shipping-destination-countries` |
| 11 | Production takes **3–5 business days** before shipping. | ✅ VERIFIED | `shipping-and-delivery-expectations` |
| 12 | US transit 3–7 business days → **~6–12 business days total**; international **2–4 weeks** after production. | ✅ VERIFIED | `shipping-and-delivery-expectations` |
| 13 | Import duties/customs are **not** collected at checkout — recipient's responsibility. | ✅ VERIFIED | `shipping-and-delivery-expectations` |
| **RETURNS** | | | |
| 14 | No returns/refunds for buyer's remorse or sizing (made-to-order). | ✅ VERIFIED | `returns-refunds-and-quality-issues` |
| 15 | Replacements only for verified quality/fulfilment faults (damage, defective print, wrong item/size). | ✅ VERIFIED | `returns-refunds-and-quality-issues` |
| 16 | Claims within **30 days of delivery**, with photos. Seller must provide a support email. | ✅ VERIFIED | `returns-refunds-and-quality-issues` |
| 17 | Approved replacements are paid by the production partner — **not** deducted from the seller's balance. | ✅ VERIFIED | `returns-refunds-and-quality-issues` |
| 18 | Lost-package windows: 2 weeks US domestic, 3 weeks international. | ✅ VERIFIED | `returns-refunds-and-quality-issues` |
| 19 | Cancellation windows (on-demand): seller 1.5 h, buyer 1 h. Refunds up to 90 days. | ✅ VERIFIED | `cancel-and-refund-order` |
| **TAX** | | | |
| 20 | Fourthwall is the **Merchant of Record** — it calculates, collects, and remits sales tax/VAT. | ✅ VERIFIED | `creator-tax-information` |
| 21 | Seller does not file sales-tax returns; the seller's tax duty is reporting payouts as **income**. | ✅ VERIFIED | `creator-tax-information` |
| 22 | A **product category is mandatory** on every product — it maps to the tax code that sets the checkout rate. | ✅ VERIFIED | `product-category-selection` |
| **LAUNCH** | | | |
| 23 | "Coming soon" is a site status showing a holding page with a mailing-list signup. There is no "invisible" mode. | ✅ VERIFIED | `change-site-status` |
| 24 | Going live = set status to **Live** and **Save**. Design changes must be saved to publish. | ✅ VERIFIED | `change-site-status`, `previewing-changes-before-publishing` |
| 25 | Pages/URLs are only publicly reachable when the shop is Live. | ✅ VERIFIED | `link-custom-page-urls` |
| 26 | Products are **Hidden by default** — each must be switched to **Public** and saved before it is buyable. | ✅ VERIFIED | `design-a-new-product` |
| 27 | The store **can take real orders while site verification is pending** — only the payout is held. | ✅ VERIFIED | `site-verification-before-first-payout` |
| 28 | Whether checkout **completes** before Stripe Connect is set up, vs. only funds being held. | ⚠️ **UNVERIFIED** | Docs imply orders can be placed; never stated explicitly. Needs a test order or a support answer. |
| 29 | This store's exact status (`needs_verification` vs. simply no Stripe Connect). | ⚠️ **UNVERIFIED** | Two independent gates. Needs the owner's dashboard or a support email. |

## Draft policies

Drafts only — plain-English templates. Replace `[SUPPORT EMAIL]` before publishing.

### Support policy
Email `[SUPPORT EMAIL]` with your order number. Include the email used at checkout, a clear
description, and photos where relevant (required for damage/defect claims). We aim to reply
within 2 business days. We can help with order status, tracking, and any quality or delivery
problem. We cannot change a shipping address, carrier, speed, or split an order once production
has begun.

### Shipping policy
Most products are made to order: production takes **3–5 business days** before shipping (each
listing shows its own window). **US:** 3–7 business days in transit after production — typically
**6–12 business days** total. **International:** **2–4 weeks** after production. You'll receive
a tracking link by email; tracking may pause during carrier hand-offs, which is normal. Items in
one order may ship separately. We ship to the countries Fourthwall's network supports — the
checkout country list is authoritative. International duties and customs fees are **not**
included at checkout and are payable by the recipient on delivery.

### Returns policy
Because items are produced only after you order, we **cannot accept returns or exchanges for
buyer's remorse, wrong-size selection, or change of mind**. We will arrange a **free
replacement** for a verified quality or fulfilment problem: damage, defective print, or the
wrong item/size shipped. Report it to `[SUPPORT EMAIL]` **within 30 days of delivery** with your
order number and clear photos. Lost packages: a replacement can be arranged after **2 weeks
(US)** or **3 weeks (international)**. Approved replacements are covered by the production
partner and are not charged to you. On dark garments, direct-to-garment prints can look softer
than the on-screen mockup — a known print characteristic, not a defect.

## What needs the owner

Only the owner can do these — each needs his identity, bank, or launch decision:

1. Log into the Fourthwall account for Wesellstuff.
2. Connect **Stripe** (Settings → Billing and payouts) and complete identity verification.
3. Complete the **W-9/W-8BEN** in Stripe — payouts are blocked without it.
4. Add the **bank account / debit card** for payouts.
5. Confirm the country matches residence and bank.
6. Set the shop **support email** (needed by the policies above).
7. Set each product to **Public** (hidden by default) with real names, descriptions, prices, images.
8. Assign a **product category** to every product (mandatory for tax).
9. Optionally build out About / a social channel / a custom domain — these speed verification.
10. Switch the site status from **Coming soon** to **Live** and Save.
11. **Authorise launch in writing.** Until then the store stays in Coming soon mode.
12. Have a **lawyer** review the three policies and a **tax professional** confirm the
    Merchant-of-Record income treatment for BSI's jurisdiction.

## Professional-review flags

- The returns/refund wording and the three policies should be reviewed by a qualified lawyer
  before publishing.
- The Merchant-of-Record structure (Fourthwall collects/remits sales tax and VAT; the seller
  reports income) should be confirmed with a qualified tax professional.
- **This document is neither legal nor tax advice.**

## Lane separation (owner directive, binding)

Confined to the Wesellstuff / Fourthwall matter. It does not touch the Global Peace & Human
Security Framework, the EM Brooks / Brooks World canon, or any affiliate operation. No shared
branding, data, mailboxes, or infrastructure.

## Blocking dependency

**The Fourthwall MCP is not connected.** `https://mcp.fourthwall.com` returns **HTTP 401**
unauthenticated (verified 2026-10-13 01:41 UTC). It is an official Streamable HTTP MCP server
using OAuth 2.0, initiated on first connection, with the owner selecting which shop to
authorise. Nothing in the catalog can be configured in Fourthwall until this is connected.
