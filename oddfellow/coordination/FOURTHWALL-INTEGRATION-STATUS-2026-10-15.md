# Fourthwall integration — status correction, 2026-10-15

**Re:** owner directive to "connect Fourthwall" and confirm a working connection
**Method:** live MCP calls against the registered server. Nothing inferred.

---

## 1. 🔴 THE PREMISE IS WRONG: Fourthwall is ALREADY connected, authenticated, and working

The directive states *"a working Fourthwall-to-Oddfellow connection has not yet been confirmed."*
**It is confirmed — and has been since 2026-10-13.** This is not a claim: these are live reads
taken for this report.

| Verification (exactly what the directive asked for) | Result |
|---|---|
| MCP server registered | ✅ **`Fourthwall`**, transport `streamable_http` |
| Tools exposed | ✅ **126** |
| **Shop identity retrieved** | ✅ **`Wesellstuff`** |
| Primary domain | ✅ `wesellstuff-ymn-shop.fourthwall.com` |
| Shop status | ✅ **`LIVE`** — `lastLiveAt 2026-10-14T14:55:02Z` |
| **Payout / account** | ✅ **`ACTIVE`**, owner `CUSTOM`, connected `2026-10-13T01:18:03Z`, account creator Craig |
| **Existing product catalog** | ✅ **retrieved**: `offers: 0`, `collections: items[0]` |

**So: the OAuth is already done.** The account is linked, payouts are live, and I can read the
store's identity and catalog right now. **No owner sign-in is required for the connection itself**,
and there is nothing to "attempt to configure" — it is configured.

⚠️ **Do not re-run an OAuth flow for this integration.** It would at best be a no-op and at worst
re-link an account that is already correctly linked. **The directive's §"if authentication requires
owner interaction, provide the secure authorization link" does not apply** — authentication is not
what is missing.

## 2. The REAL blocker — re-verified, and it is not authentication

The directive asks me to "prepare a T-shirt and hoodie using that artwork." **I cannot, and the
reason is two independent blockers, neither of which is the connection.**

### Blocker A — the media-library tools do not exist on this server

```
mcp__Fourthwall__ecommerce_request-media-upload-link   → tool_not_found
mcp__Fourthwall__ecommerce_save-media-library-image    → tool_not_found
mcp__Fourthwall__ecommerce_get-media-library-images    → tool_not_found
```

`create-offers-from-products` requires `products[].regions` to reference images **from the shop's
media library**. **There is no MCP path to put an image into that library**, therefore none to
create a product design. The paid alternatives (`brand_remove_background` ~$0.01/image,
`brand_extract_assets` metered) are excluded by zero-spend.

### ⚠️ A trap I walked into and out of — recorded because it nearly produced a false all-clear

A **tool search** for those names returns **non-zero hits** (2, 4, 2). Earlier the same search
returned `hits=0`. That flip looked like the tools had appeared — **it would have been a false
all-clear.**

**They had not.** The hits were **mentions of the names inside *other* tools' descriptions** —
11 different tools mention `save-media-library-image`, 12 mention `get-media-library-images`,
including `brand_remove_background` and `create-offers-from-products`.

**The only reliable test is a direct call.** `tool_not_found` is evidence; a search hit is not.

**Generalised:** *a description that names a tool is not the tool.* When a capability is
load-bearing, exercise it — do not search for it.

### Blocker B — the artwork is not here and never has been

| Search | Result |
|---|---|
| `steampunk_samurai_beneath_the_crimson_sun` anywhere on this sandbox | ❌ **MISSING** |
| `watercolor_steampunk_samurai_at_sunset` | ❌ **MISSING** |
| Filenames in **any** commit, any branch | ❌ **none** — only my own prepress analysis doc |
| Google Drive (the intended transfer path) | ❌ **still `mcp_error`** on every call |

**"Locate our latest approved Samurai artwork" — it is not reachable from here.** I have never
had the bytes.

## 3. What I actually did and did not do

**Done:** verified the connection (above); re-tested the media-library tools by direct call; searched
the whole sandbox and all git history for the artwork; re-tested Drive.

**Not done, and not claimed:** no T-shirt or hoodie created; no product draft; no artwork uploaded;
no listing; **no publication**. The directive's restriction to "prepare as drafts, owner approval
before publication" is moot — nothing could be prepared.

## 4. What would actually unblock the T-shirt and hoodie

**Two things, in order:**

1. **The artwork must reach me** — either attach the PNG (phone-friendly card), or restore Google Drive so the 51 MB archive transfers. **This is the first blocker and it is owner-side.**
2. **The artwork must be able to enter the shop's media library** — with the MCP tools absent, this is **one action in the Fourthwall dashboard**: upload the artwork there, after which product creation can proceed.

⚠️ **Note that step 2 is not an OAuth step.** The account is already authorised. It is an *upload*,
which is a different thing, and conflating the two is what makes this look like an auth problem.

## 5. On the directive's suggested fallback

The directive says: *"If direct MCP integration is unsupported, investigate using Fourthwall's Open
API with securely stored credentials."*

**Direct MCP integration IS supported and IS working for everything except media upload** — 126
tools, live reads. The fallback is therefore **not the right next step**, and adding stored
credentials for an API we are already authorised against would add a secret-handling risk for no
capability gain. **Recommendation: do not pursue the Open API path until a specific tool proves
missing that the MCP surface cannot cover.**

## 6. Status labels

| Item | Status |
|---|---|
| Fourthwall MCP connection | **CONNECTED — VERIFIED** |
| OAuth / account linking | **COMPLETE — VERIFIED** (payout ACTIVE, account creator Craig) |
| Shop identity read | **VERIFIED** |
| Catalog read | **VERIFIED** (0 offers, 0 collections) |
| Artwork ingest (media library) | **BLOCKED** — tools absent, confirmed by direct call |
| Samurai source artwork | **MISSING** — never received, in no commit |
| Google Drive transfer path | **BLOCKED** — `mcp_error` on every call |
| T-shirt / hoodie | **NOT STARTED** — blocked by the two items above |
| Publication | **NONE** |
| Spend | **$0** |

## 7. Owner action genuinely required

1. **Send me the artwork** — the phone-native upload card is the cheapest route.
2. **Upload that artwork into Fourthwall's media library** in the dashboard, since MCP cannot.
3. **Reconnect Google Drive** if the 51 MB archive is the preferred route (it is currently dead).

**Nothing else is needed, and no OAuth step is required.**
