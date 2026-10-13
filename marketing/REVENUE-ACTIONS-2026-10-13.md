# Revenue actions — 2026-10-13

Owner-driven revenue plan. Written 2026-10-13 00:50 UTC. Every claim below was probed
from this sandbox at that time; nothing here is carried over from an earlier handoff
without re-verification.

## Verified state (2026-10-13 00:45–00:50 UTC)

**Purchasable today — 2 live products on Gumroad** (`beggster58.gumroad.com`, both HTTP 200,
in stock, not sales-limited, both `native_type: digital`):

| Product | Price | URL | Ratings |
|---|---|---|---|
| The 7 day reset planner | $4.99 | `https://beggster58.gumroad.com/l/zvxpuh` | 0 |
| Paycheck Budget Starter Bundle | $7.00 | `https://beggster58.gumroad.com/l/oavkpq` | 0 |

- The bundle was **not** in project memory before this probe — it is new.
- Both listings carry valid `application/ld+json` Product structured data.
- **Sales counts are not visible from outside the seller account.** Zero ratings is the only
  public signal; no revenue is claimed here. 💰 requires transaction evidence.

**Live but with no payment path — 7 free apps** (all HTTP 200, probed 2026-10-13 00:45 UTC):

`household-task-board` · `pantry-first` · `service-mile` · `renewal-watch` ·
`small-business-starter` · `ready-card` · `home-ledger` — all at
`https://{slug}.craigbegg005.chatgpt.site`

Seven slugs do **not** resolve: `7-day-reset-planner`, `reset-planner`, `everyday-tools`,
`keep-the-receipt`, `opportunity-exchange`, `agency-sales-dashboard`, `pixelbloom`.
Note the first: **the planner's own app subdomain is 404** while the PDF sells.

**Broken:** the Stripe MCP connection returns `Invalid refresh token` from
`list_available_accounts_or_orgs`. Stripe is unusable until re-authenticated, and was
sandbox-only (`livemode=false`) before that.

## The diagnosis

The bottleneck is **traffic, not product**. Two finished, priced, live products and no
verified buyers. Nothing done to the products earns a dollar until someone sees them.
So the work that matters is distribution.

## Action 1 — Enable GitHub Pages (owner, one toggle, ~20 seconds)

A store landing page is **built, verified and pushed** to the `gh-pages` branch of
`craigbegg005-netizen/chatgpt-github-connection`. The GitHub App token cannot enable Pages
(`403 Resource not accessible by integration` — needs repo admin), so this is the one step
that needs the owner.

**Settings → Pages → Source: Deploy from a branch → Branch: `gh-pages` → `/ (root)` → Save**

https://github.com/craigbegg005-netizen/chatgpt-github-connection/settings/pages

Live URL once enabled: `https://craigbegg005-netizen.github.io/chatgpt-github-connection/`

The page routes to both Gumroad listings, surfaces the seven free tools, and carries
Product structured data for search. It loads no third-party scripts, sets no cookies, and
contacts exactly two origins (its own and `public-files.gumroad.com` for cover images), so
it adds no tracking or secret-leak surface.

## Action 2 — Two Gumroad listing fixes (owner, ~2 minutes)

**2a. Fix a customer-visible typo.** The planner's description currently reads:

> The 7 day reset plan is a simple guided plan to help clear your mind and reset. It helps
> you pause, rewind, and reset. Inside the **oil** find a 7-Day reset...

"Inside the oil" should be "Inside you'll". This string is the listing's meta description,
its `og:description`, and its JSON-LD description — so the typo appears in Google results
and in every social share preview, not just on the page.

**2b. Consider a bundle.** $4.99 + $7.00 = $11.99 separately; a combined listing at ~$9.99
raises average order value and gives one link to promote instead of two. Optional — it is a
pricing decision, not a defect.

## Action 3 — Brooks World promotion (ready to post)

The fastest path to a first sale is an audience that already exists. Emma Brooks' content
theme is resets; the 7-Day Reset Planner *is* a reset planner. That is a direct
content-to-product fit at zero spend.

**This lane is ChatGPT's per the operating protocol — these drafts are for handoff, not for
this agent to publish.** Follower counts on `embrooks.home` are unverified from here.

Three posts, written to the brand's voice. No fabricated testimonials, no invented scarcity,
no revenue claims. AIGC disclosure flags to be applied per the existing Brooks World rule.

**Post 1 — the reset hook (IG/TikTok, pairs with a 15s video of a cluttered → clear surface)**

> The 7-day reset that actually gets finished.
>
> Most reset plans are 40 pages you abandon by Wednesday. This one is seven days, one page
> each. Clear your head, then move on with your week.
>
> Link in bio → 7-Day Reset Planner ($4.99, instant download).

**Post 2 — the "pause, rewind, reset" framing (carousel: 3 slides)**

> Slide 1: Pause. → Slide 2: Rewind. → Slide 3: Reset.
>
> That's the whole idea. Seven days, a page a day, space to let go of what isn't serving
> you. Printable, so it works on paper like you actually plan.
>
> 7-Day Reset Planner — link in bio.

**Post 3 — the money pairing (for a Monday/payday slot)**

> Reset your week. Then reset your paycheck.
>
> Two printables: a 7-day reset to clear your head, and a paycheck plan to organise your
> money. Both instant downloads, no subscription, no app to learn.
>
> Links in bio.

**What NOT to do:** no "limited time", no invented customer quotes, no "thousands of
downloads". There is no evidence for any of those, and the doctrine forbids them.

## Action 4 — Turn on live Stripe (owner decision + account work)

Seven live apps with no way to take payment is a monetisation surface that is built and
switched off. Stripe is currently sandbox-only **and** its connection is broken
(`Invalid refresh token`). This is the larger ceiling than the two PDFs, and it is
owner-gated: it needs live-mode activation and a pricing decision.

## Ranked by (impact ÷ effort)

1. **Enable Pages** — one toggle, gives the products a real URL to point at.
2. **Brooks World posts** — existing audience, exact theme fit, zero spend.
3. **Fix the typo** — two minutes, removes a credibility defect from every search result.
4. **Live Stripe** — biggest ceiling, most owner work.
5. **Bundle the two products** — pricing optimisation, do after there is traffic.

## What this agent can still do without the owner

- Keep the landing page current as products/prices change.
- Draft further Brooks World copy on request.
- Build the planner's own web app (the repo holds only a `noindex` placeholder at
  `oddfellow/frontend/planner/index.html`) as a free-tier funnel into the paid PDF.

## Standing honesty note

No revenue has been verified. 💰 is reserved for transaction evidence. Zero ratings is not
zero sales — it is the absence of a public signal either way.
