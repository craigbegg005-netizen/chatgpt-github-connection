# BSI COORDINATION STATUS — single source for cross-AI state

**Last verified: 2026-10-25 00:04 UTC** · canonical head **`862a375`**
**Read this file first. It is kept current on a schedule — check the timestamp above before trusting it.**

> **Path is fixed on purpose.** Other pointers in this repo have drifted three times (a
> `CURRENT_STATE` pointer, a README command, and a sync pointer). This file does not move, so
> there is nothing to drift.

---

## 1. WHAT IS BLOCKED, AND ON WHOM — the only list that matters

| # | Blocker | Owner action | Blocks |
|---|---|---|---|
| 1 | **Fourthwall media-library MCP tools not exposed** | upload artwork in the dashboard | the **entire** Phase-1 launch |
| 2 | **Google Drive: 92 tools registered, every call 500s** | disconnect + reconnect Drive | artwork transfer |
| 3 | **Four archives never received** | upload to Drive, or attach here | artwork, PWA, addenda |
| 4 | **Gate A: two Render env vars unset** | set them in Render | production readiness |
| 5 | **Render DB expires 2026-10-27** | `/32` allowlist + secret | data preservation |
| 6 | **GitHub Pages disabled** (API 404, URL 404) | one repo toggle | store + PWA hosting |
| 7 | **Spreadshop: no access path** | sign-in in sandbox browser | second storefront |
| 8 | **Gumroad delivered file unverifiable** | 2 min in seller view | closes 11-vs-12-page question |

### 🔴 Blocker 1 is the one that misleads people — read this

**The Fourthwall launch is NOT blocked on artwork.** It is blocked on a **missing tool**.

`request-media-upload-link`, `save-media-library-image` and `get-media-library-images` are
**referenced by name in sibling tool descriptions but are not exposed** — `hits=0` against the
126-tool server. `create-offers-from-products` requires `regionUrls` from that same library.

**So: delivering 51 MB of artwork does not move the launch.** One owner action in the Fourthwall
dashboard does. Correcting this expectation saves the most owner time of anything in this file.

---

## 2. VERIFIED STATE — by capability, not by assertion

| Item | State | Evidence |
|---|---|---|
| Letta GitHub read/write | ✅ **VERIFIED** | commits `10868ede`, `2cf682f7`; remote read-back |
| ChatGPT GitHub read | ✅ **VERIFIED** | its own independent read-back of `5accc01f` |
| ChatGPT GitHub write | ⛔ **403 — token scope** | its own diagnosis |
| Work / Grok / Gemini / Claude write | **UNVERIFIED** | never tested |
| **My MCP surface** | `Fourthwall` (126) · `BeggAi` (10) · `Gmail` (61, **non-functional**) · `Google_Drive` (92, **non-functional**) · `Sentry` (0) · `Cloudflare` (0) | `letta mcp list` |
| Fourthwall shop | **`LIVE`** — `lastLiveAt: 2026-10-14T14:55:02Z` (was `COMING_SOON`) | `get-current-shop` |
| Fourthwall offers | **`totalElements: 50`** — **PUBLIC offers exist and are purchasable** (2026-10-21 sweeps count 44 PUBLIC · 4 HIDDEN · 2 ARCHIVED; first page of 5 is now 4 HIDDEN digital drafts $6.99–$29.99 created 2026-10-20 — the shop's first digital products — + 1 PUBLIC tee; `get-offers` still ignores `pageNumber` — do not generalize from any single page) | `get-offers`, `get-offers-by-ids` |
| Fourthwall collections | **`items[7]`** — Norse/Nordic (1, first recorded 2026-10-22) · Mugs & Home (17) · Celtic (5) · Christian & Biblical (12) · Samurai & Japanese Art (8) · Trail Forge Outfitters Comfort Colors (17) + AS Colour (22) — all `PUBLIC` | `get-collections` |
| Fourthwall payouts | API says **ACTIVE** — PUBLIC offers now live; still zero sales | `get-payout-info` |
| Gumroad | **3 live listings**, all HTTP 200 | public probe |
| Rehearsal | **LIVE but ephemeral** — dies with the sandbox | sandbox cycled again; restored `up`+keepalive 2026-10-25 00:03 UTC, tunnel answers 200 |
| Render `-v0206` | **LIVE, NOT READY** | `/livez` 200, `/healthz` `ok:false` |
| Deployed SHA | **NOT VERIFIABLE** — no build endpoint | **lower bound `7c33404` (2026-09-30 04:21:57 UTC)** — see the note below |
| Persistent workforce | **NOT PROVISIONED** | `letta agents create` → **402, `"limit":3`** |
| Test suite | **770 passed** | re-run at `862a375` |
| **Revenue / orders / payouts** | **NONE, on every platform** | — |

### ⚠️ The deployed-SHA bound, corrected 2026-10-14

This row previously read *"bounded ≤ 2026-10-05 08:07:56 UTC"*. The version evidence does not
support an upper bound, and what it does support is a **lower** one:

- The deployed build reports `"version": "0.20.6"` on `/livez` and `/healthz`.
- The version string became `0.20.6` at **`7c33404` (2026-09-30 04:21:57 UTC)**, where it was
  hardcoded in the responses.
- `5d500e4` (2026-10-05 08:07:56) did not change the version — it **refactored** the hardcoded
  literals into a `VERSION` constant whose value was already `0.20.6`. That is why a search for
  `VERSION = "0.20.6"` lands there and a search for the bare string lands at `7c33404`.

So the deployed commit is **at least as new as `7c33404`**, and no upper bound has been
established: `/readyz` and `/version` returning 404 on the deployed build is consistent with those
routes never having existed, which bounds nothing. **The honest statement is "≥ 2026-09-30
04:21:57, upper bound unknown"** — not "≤ 2026-10-05". Anyone comparing head to production should
use the lower bound.

### ⚠️ A tool that silently shows 5 of 255 — verified 2026-10-14

`ecommerce_get-catalog-products` **ignores `pageNumber` and `pageSize`**. Asked for
`{"pageNumber":1,"pageSize":50}` it returns `pageNumber: 0, pageSize: 5` and the *same* first five
products as page 0, every time. There is also no text-search parameter.

So the Fourthwall catalog is readable through this tool to a depth of **five products out of 255**,
and the poster is not among them. This is why an earlier pass could not resolve the poster's size
list, and it is worth knowing before any claim rests on "the catalog":

- **Do not conclude a product is absent because this tool does not show it.** Absence here means
  "not in the first five".
- **The public product API works and is the way through:**
  `https://api.fourthwall.com/api/products/<product_id>` returns the full record — its `variants`
  array carries `size` per variant. That is how the poster's 14 sizes were confirmed, and the count
  and the list were then checked against `prepress_check.py`'s constant (exact match, 14/14).
- Where this file says something was *"reconstructed from the live catalog"*, check which route was
  used before trusting the completeness of the reconstruction.

### ⚠️ Registrations that are not capabilities

Four connections exist on paper and do not work. **Do not report these as available:**

- **Gmail** — server listed, 61 tools, **calls return `500 Managed MCP server configuration is unavailable`** (probed 2026-10-21)
- **Google Drive** — server listed, 92 tools, **every call returns `500 Managed MCP server configuration is unavailable`** (3/3 retries, two different tools)
- **Stripe** — MCP connection present, **`Invalid refresh token`**
- **Fourthwall payouts** — reads **ACTIVE** (setup state only) — **no sales have occurred**; do not report it as revenue

---

## 3. ALREADY REPAIRED — do not redo

- **Gumroad listing typo gone.** "Inside the oil" no longer exists; listing reads **11-page** (10 occurrences, zero "12-page"). **Listing copy VERIFIED; delivered file UNVERIFIED** — different claims.
- **Tee margin is $12.55, not $18.50** — base $15.45; the DTG print charge is additive.
- **README's handoff-finder command** — was wrong (alphabetical sort). Fixed with a tested replacement.
- **The DB allowlist verdict** — re-corrected. **A TCP probe gives a FALSE POSITIVE:** Render's proxy accepts TCP and completes TLS *before* the allowlist check, then closes silently.
- **`tee/poster/mug.json`** — were in no commit; reconstructed from the live catalog.

---

## 4. UNRECEIVED — exists elsewhere, has no copy here

| Asset | Status |
|---|---|
| `BSI_LETTA_CANON_PLUS_ALL_6_COLLECTIONS_2026-10-13.zip` (~51 MB) | ❌ missing |
| `seven-day-reset-planner-pwa-mvp.zip` | ❌ missing |
| `15-Minute-Home-Rescue-Cards.pdf` (6pp), `No-Reply-Follow-Up-Kit.pdf` (6pp), `Service-Quote-Builder.pdf` (4pp) | ❌ missing |
| `BSI_COMMERCE_CANON_ADDENDUM_v1.1 / v1.2` | ❌ missing |
| `BSI_ENTERPRISE_DELEGATION_AND_CONTINUITY_ADDENDUM` | ❌ missing |

**These exist in exactly one place each, with no committed copy.** The offer payloads had the same
shape and had to be rebuilt from a live catalog; **these cannot be.**

---

## 5. PREPARED GATES — ready to run when files arrive

- **Canva licence gate** (`commerce/micro-earnings/CANVA-LICENCE-GATE-2026-10-14.md`) — 5 checks, cited terms. **One is sharp:** Canva templates containing Pro Content **may not be sold as PDFs at all**, "whether flattened or not."
- **Micro-earnings lane** (`commerce/micro-earnings/LANE-2026-10-13.md`) — three PDFs, gates 1–5.
- **Render DB probe** (`oddfellow/preservation/RENDER-DB-PROBE-2026-10-13.md`).

---

## 6. RULES THAT HAVE COST REAL TIME HERE

1. **Re-fetch before acting.** Canonical moved ~11 commits under one session on 2026-10-13 alone.
2. **Registrations are not capabilities.** See §2.
3. **`NOT CHECKED` ≠ `BLOCKED`.** No evidence either way = the former.
4. **Never describe a manifest as running.**
5. **A pointer that nothing maintains drifts.** Sort the *timestamp*, not the string.
6. **`COMPLETE` is not `VERIFIED`. A listing is not a sale. A margin is not profit.**
7. **Zero spend.** No purchase, ad, upgrade, sample or metered tool without explicit owner approval.
8. **Never write a secret into a repo file.** Count matches; never print them.

---

## 7. CURRENT HEAD

`letta/combined-single-service-v0.20.4` @ **`862a375`** · coordination branch
`coordination/oddfellow-chatgpt-sync` @ **`62e2be3`**
