# BSI COORDINATION STATUS — single source for cross-AI state

**Last verified: 2026-11-07 02:04 UTC** · canonical head **`592c2c0`**
**Read this file first. It is kept current on a schedule — check the timestamp above before trusting it.**

> **Path is fixed on purpose.** Other pointers in this repo have drifted three times (a
> `CURRENT_STATE` pointer, a README command, and a sync pointer). This file does not move, so
> there is nothing to drift.

---

## 1. WHAT IS BLOCKED, AND ON WHOM — the only list that matters

| # | Blocker | Owner action | Blocks |
|---|---|---|---|
| 1 | **Fourthwall media-library MCP tools not exposed** | upload artwork in the dashboard | the **entire** Phase-1 launch |
| 2 | **Google Drive: 92 tools registered, calls fail 403 insufficient scopes** (was 500) | disconnect + reconnect Drive | artwork transfer |
| 3 | **Four archives never received** | upload to Drive, or attach here | artwork, PWA, addenda |
| 4 | **Gate A: two Render env vars unset** | set them in Render | production readiness |
| ~~5~~ | **RESOLVED 2026-11-01 06:44 UTC — DB preservation complete; the DB was EMPTY.** Owner set `ODDFELLOW_DB_URL` and allowlisted the sandbox egress (`170.9.15.3/32` — note: egress changed from the old `170.9.4.232` with a sandbox cycle; always re-verify at action time). Full runbook path passed against the real server: recon → dump → verify (1,379 B, `pg_restore --list` parses) → restore-verify (row counts match exactly). **Contents: 0 user tables, 7,686 kB (virgin Postgres size) — nothing was ever stored; the "Command Center may use it" signal was a false alarm.** Artifacts: `/root/oddfellow-db-backups/begg-ai-core-db-20261101T064404Z.dump` (+ `.sql.gz`) + delivered to owner downloads. Owner may now delete/downgrade the DB — deletion is verified zero-loss. **Also settled:** the silent-close was the allowlist the whole time, not the expired plan — diagnosis probe: TLS handshake completes, startup message gets a clean close with no FATAL. | none — closed | data preservation |
| 6 | **GitHub Pages disabled** (API 404, URL 404) | one repo toggle | store + PWA hosting |
| 7 | **Spreadshop: no access path** | **tell me your shop URL** (from your phone — see the note below) | second storefront |
| 8 | **Gumroad delivered file unverifiable** | 2 min in seller view | closes 11-vs-12-page question |

### 🔴 Blocker 7's owner action was wrong — corrected 2026-11-07

It read *"sign-in in sandbox browser"*, which **Craig cannot do**: he works from a mobile phone, and a
remote desktop has no touch affordances. That is a known hard constraint, and this row asked him to do
the one thing it rules out.

**The mobile-native path already existed in the lane's own doc** and was not carried here.
`commerce/SPREADSHOP-STATE-2026-10-13.md` lists two ways to unblock, and only the second is impossible:

- **A — tell me the URL.** Spreadshop's own docs give the shape `SHOPNAME.myspreadshop.com`, and the
  shop name is shown in the sales-channel overview. **Craig can read that off his phone and paste it.**
  This is the path to use.
- **B — sign into the sandbox browser.** ❌ **Not phone-doable. Do not ask for it.**

**The general rule, which this row violated:** before writing an owner action, ask *"can this be done on
a phone with taps and no mouse?"* If not, find another path or say plainly that it is desktop-only.

### 🔴 Blocker 2 is HALF-RESOLVED — Gmail works again, Drive does not (2026-11-10)

The blocker read *"Google Drive: 92 tools registered, calls fail 403 insufficient scopes (was 500)"* and
the owner action was *"disconnect + reconnect Drive"*. **Re-probed 2026-11-10 and the two Google
integrations have diverged:**

- ✅ **Gmail is WORKING.** `GMAIL_GET_PROFILE` returned `successful: true` with real account data
  (message and thread totals), and a malformed call returned a **400 validation error** — not the
  `500 Managed MCP server configuration is unavailable` this file recorded. **The Gmail half of the
  owner action is no longer needed.**
- ⛔ **Drive is still broken**, and with the same cause as before: `403 ACCESS_TOKEN_SCOPE_INSUFFICIENT`
  on `drive/v3/about`. **Reconnecting Drive is still the right action.**

**Also corrected: the server name.** This file wrote `Google_Drive`; the server is registered as
**`Google Drive`** (with a space), and its tools are double-prefixed
(`mcp__Google_Drive__mcp__Google_Drive__GOOGLEDRIVE_*`). A call using the underscore form returns
`server_not_found`, which reads like the server is missing when it is only misnamed. The tool count is
**108**, not the 92 recorded here.

**What this unblocks:** the comms failover chain was listed as blocked on Gmail. That half is now open.

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
| **My MCP surface** | `Fourthwall` (126) · `BeggAi` (10) · **`Gmail` (61) — ✅ WORKING, re-verified
2026-11-10** · `Google Drive` (108 tools, **still 403 insufficient scopes**) · `Sentry` (0) · `Cloudflare` (0) |
`letta mcp list`; `GMAIL_GET_PROFILE` returned `successful: true` |
| Fourthwall shop | **`LIVE`** — `lastLiveAt: 2026-10-14T14:55:02Z` (was `COMING_SOON`) | `get-current-shop` |
| Fourthwall offers | **`totalElements: 55`** — **PUBLIC offers exist and are purchasable** (2026-10-21 sweeps counted 44 PUBLIC · 4 HIDDEN · 2 ARCHIVED; 2026-11-05 23:42 UTC added 3 HIDDEN candle offers — Grace/Joy/Faith Soy Wax Candle; **2026-11-06 00:20–00:24 UTC added 2 more HIDDEN offers — Trailforge Gildan Classic Hoodie + Heavy Blend Zip Hoodie — and repriced the Grace candle $23→$17.99 (00:25 UTC)** — implying 44 PUBLIC · 9 HIDDEN · 2 ARCHIVED; page 0 now leads with those 2 HIDDEN hoodies, then the 3 HIDDEN candles; `get-offers` still ignores `pageNumber` — do not generalize from any single page) | `get-offers`, `get-offers-by-ids` |
| Fourthwall collections | **`items[7]`** — Norse/Nordic (1, first recorded 2026-10-22) · Mugs & Home (17) · Celtic (5) · Christian & Biblical (12) · Samurai & Japanese Art (8) · Trail Forge Outfitters Comfort Colors (17) + AS Colour (22) — all `PUBLIC` | `get-collections` |
| Fourthwall payouts | API says **ACTIVE** — PUBLIC offers now live; still zero sales | `get-payout-info` |
| Gumroad | **3 live listings**, all HTTP 200 | public probe |
| Rehearsal | **LIVE but ephemeral** — dies with the sandbox | cycled again after the 00:02 UTC restore; restored `up`+keepalive 2026-11-07 02:03 UTC, tunnel answers 200 (`live:true, ready:true`), watchdog pid 1864, suite 780 re-verified this cycle |
| Render `-v0206` | **LIVE, NOT READY** | `/livez` 200, `/healthz` `ok:false` |
| Render census — **all 20 services documented** (owner screenshots 07:38 UTC + probes) | **14 LIVE · DB Available-but-verified-empty · 5 NOT SERVING** (cleanup candidates: `begg-ai-core`, `global-peace-human-security-framework`, old `oddfellow-letta-backend`, `oddfellow-personal-staging-v017`, `oddfellow-letta-poc`). **PgHero instance is wired to the rescued DB (401, auth-gated) — deleting the DB orphans it; delete both.** `oddfellow-personal-v019` proves "Failed deploy" can still serve (200). 3 Command Center variants, none match repo | dashboard + probes 2026-11-01 07:45 UTC; recovery doc addendum `a2115a6` on `letta/recovery-render-census-2026-11-01` |
| Deployed SHA | **NOT VERIFIABLE** — no build endpoint | **lower bound `7c33404` (2026-09-30 04:21:57 UTC)** — see the note below |
| Persistent workforce | **NOT PROVISIONED — limit lifted, creation untested** | account upgraded to **Personal Pro 2026-11-01** (`letta usage`: plan `pro`); docs: **up to 20 stateful agents** (was 3); no new agents created — owner has not authorized any |
| Test suite | **805 passed on canonical** | re-verified 2026-11-09; the count had drifted to 780 here while the suite grew, because this file was outside the count guard's coverage — now inside it |
| **Revenue / orders / payouts** | **NONE, on every platform** | — |

### 🟢 Plan change 2026-11-01 — Letta account upgraded to Personal Pro

Verified via `letta usage` at 04:25 UTC: plan **`pro`**; `letta/*` quota bucket **full** (daily:
full), window end 2026-11-01T08:00Z, daily reset 2026-11-02T00:00Z; **credits balance 0**.
Per docs.letta.com/pricing, Pro includes: Letta Auto weekly + monthly quota · **up to 20
stateful agents** (free was 3 — the 402 blocker is lifted per docs, untested) · **50 MiB per
memory repository** (free was 5; current use 3.2 MiB) · pay-as-you-go overage **requires
purchasing credits** (balance 0 — none will be purchased without owner authorization).

**Two cautions for every AI reading this:**
1. Personal-plan quota requires OAuth (CLI/web). **API-key-authenticated usage draws credits,
   not quota** — so the Render backend's `LETTA_API_KEY` calls may bill credits once Gate A is
   set. Unverified until Gate A lands; do not assume the backend runs on Pro quota.
2. The 5 active schedules total ~78 agent turns/day. Quota is currently full and resets daily,
   so nothing is being exhausted — but consolidation (5 → 3 schedules) is recommended and
   pending owner approval. Do not add new schedules without checking for overlap.

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
- **Google Drive** — server listed, 92 tools, **calls now execute but fail `403 Request had insufficient authentication scopes`** (`ACCESS_TOKEN_SCOPE_INSUFFICIENT`, DriveFiles.List; probed 2026-10-31, re-probed unchanged 2026-11-06). Was `500 Managed MCP server configuration is unavailable` through 2026-10-26. Disconnect + reconnect still the owner action — the token needs the scopes re-granted.
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

`letta/combined-single-service-v0.20.4` @ **`592c2c0`** · coordination branch
`coordination/oddfellow-chatgpt-sync` @ **`62e2be3`**
