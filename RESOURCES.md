# Begg AI Industries — resource registry

Maps human-friendly names to actual resources. **Do not guess resource locations** — if a
value here is not marked VERIFIED, treat it as reported and re-check before relying on it.

Status labels: ✅ VERIFIED · 🟢 LIVE · 🚀 DEPLOYED · 🔗 CONNECTED · 🧪 TESTED ·
🛠 IMPLEMENTED · ⏳ PENDING · ⚠️ BLOCKED/UNVERIFIED · 💰 REVENUE.

Maintained by Oddfellow (Letta agent). Last verification sweep: **2026-10-01 04:05 UTC**.
Every "verified" line below was checked by an actual request from this agent at that time.

**Sweep 2026-10-01 04:05 UTC — re-probe of all 10 services.** **33 of 35 surfaces** returned a
result; the other 2 are named below and are the reason for the count. Everything below still
holds. Three notes from that sweep:

- **Two transient timeouts, not outages — and they were not captured at all.**
  `oddfellow-staging-v017b/` and `begg-ai-industries-v013/` returned no response on `/` while
  their `/health`, `/ready` and `/openapi.json` all answered 200 **in the same sweep**. That is
  a Render free-tier cold start losing a race, not a service going down. Those two `/` surfaces
  are the 2 missing from the 35 — a failed request leaves no capture file, so **the count itself
  is the signal that something timed out.** Re-probe before calling either dead.
- **Command center content changed slightly** — 4361 B → **4233 B** — same app, same title
  ("Begg AI Industries Command Center"), still **401** auth-gated. Consistent with ChatGPT
  still working on it. Not a regression.
- **✅ CORRECTED 2026-10-01 20:05 UTC — the deploy target IS serving.** The earlier note here
  said `oddfellow-letta-backend` was not serving, and that was true of the name it was probing.
  **The live service is `oddfellow-letta-backend-v0206`** and it has been up: `/livez` → 200
  `{"live":true,"ready":false,...}`, `/` → 200, 29513 B. See the name-discrepancy section under
  Oddfellow below. **The blocker is unchanged and is still only the two secrets.**

---

## Source control

| Resource | Value | Status |
|---|---|---|
| Repo (only one this GitHub App can see) | `craigbegg005-netizen/chatgpt-github-connection` | ✅ VERIFIED — `installation/repositories` → `total_count: 1` |
| Canonical deploy branch | `letta/combined-single-service-v0.20.4` @ `8b455fd` | ✅ VERIFIED 2026-10-01 04:05 UTC |
| `main` | `8ddfe325` | ✅ VERIFIED 2026-10-01 04:05 UTC |
| `letta/universal-connector-v0.21` @ `8f9c139` | **Universal Connector** — core, security hardening, the Tier 3/4 handoff path, dead-letter + clean disconnect, an operator CLI | ⚠️ **MERGED INTO CANONICAL** 2026-10-01 23:33 UTC (merge `155dd3fc`, purely additive: 4184 insertions, 0 deletions). The branch is kept for further work; canonical is now the integration point. |
| `letta/voice-v1` @ `e83a61b` | **Voice V1 approval gate** — elevated-risk voice/chat commands enter a real `WAITING_AUTHORIZATION`; spoken approval binds to one exact pending action | ✅ VERIFIED 2026-10-01 21:50 UTC (pushed, local SHA == remote). Front-end wiring verified in a real browser; backend chain verified against the rehearsal. **Dev branch.** ⚠️ Nobody has spoken into a real phone — that verification is the owner's to run. |
| `letta/frontend-letta-backend` | `445e05c` | ✅ VERIFIED |
| `letta/recovery-capture-2026-09-30` | `f27ec28` | ✅ VERIFIED |
| `letta/independent-verification-2026-09-30` | `46d731b` | ✅ VERIFIED — independent reproduction of the deploy branch's claims |

**Connector status, stated at the level it has actually reached:** the core is
**TESTED** (113 offline tests), **COMMITTED**, and now **MERGED INTO CANONICAL** and
**USED** — the Command Center exposes its queue at `GET /api/command/jobs`. Its credential model is now
**real** — scoped, revocable, per-provider tokens with constant-time verification,
and the owner master token refused *by value*. It is **not CONNECTED** to any
provider and **not DEPLOYED**; the MCP gateway **serves nothing**. Every provider
record is UNVERIFIED and the router refuses to route to them — deliberately.

**One path IS usable today, and it needs nothing:** the **Tier 3 structured
handoff** (`oddfellow/connector/handoff.py`), driven by an operator CLI
(`oddfellow/connector/cli.py`). It renders the claimable queue as a document a human
can paste into any AI, and turns the reply back into results through the same
claim/approval enforcement. So work *can* move between Oddfellow and Claude now, at
zero cost, with no account and no key:

```
python -m connector.cli --db state.db handoff --provider claude > to-claude.md
python -m connector.cli --db state.db apply --provider claude --file reply.md
```

Demonstrated end to end by running it: a low-risk result accepted as `COMPLETE` (and
correctly **not** verified), and a critical-risk attempt **refused** with the job
left `READY`. `apply` exits **non-zero** when anything was refused, because a
refusal is not a success.

⚠️ Do not read the above as "the connector is connected to Claude". The MCP and API
rungs are still unconnected; only the handoff rung works, and only by hand.

⚠️ **The connector's own MCP gateway is NOT the `BeggAi` MCP server.** The gateway
is `oddfellow/connector/gateway.py` and it is unexposed; `BeggAi` is Stripe's MCP
server. See the Integrations section.

**⚠️ Structural gap:** no Oddfellow or Begg AI codebase exists under version control anywhere
this installation can reach. The recovered v0.16/v0.17 services can only be rebuilt from their
live API surfaces, not from source. **Owner must grant repo access or name where the code lives.**

### ⚠️ Version-label discrepancy (reconcile, do not assume)

The branch is **named** `...-v0.20.4` but the runtime code reports **`0.20.6`**. Both are true:
the branch name is historical, the served version is authoritative. Report both rather than
assuming they are equivalent.

---

## Oddfellow

| Resource | Value | Status |
|---|---|---|
| Oddfellow agent (this agent) | `agent-a9a8eb2c-2fed-4554-9998-aa4783c7efc4` | ✅ VERIFIED — `GET /v1/agents/{id}` → `"name":"Oddfellow"` |
| **Deploy target — THE LIVE ONE** | **`oddfellow-letta-backend-v0206`** | 🟢 **LIVE, ⚠️ NOT READY** — `/livez` → 200 `{"live":true,"ready":false,"checks_failed":["LETTA_API_KEY","ODDFELLOW_OWNER_TOKEN"],"version":"0.20.6"}`. Verified 2026-10-01 20:05 UTC |
| **Deploy URL — THE LIVE ONE** | **`https://oddfellow-letta-backend-v0206.onrender.com`** | 🟢 `/` → 200, 29513 B (page + API + PWA on one origin). This is the phone URL. |
| ⚠️ `oddfellow-letta-backend` (NO `-v0206`) | `https://oddfellow-letta-backend.onrender.com` · `srv-dau6tgqd0e5s73egkocg` | 🔴 **DEAD — do not probe, do not watch.** No HTTP response. **This name is what `render.yaml` defines, and it is NOT the live service.** |
| Rehearsal (ephemeral) | ⚠️ **do not record a URL here** — read it live | 🟢 LIVE when the watchdog is up, but **the URL changes on every restart**. Re-read it: `cat /root/.oddfellow/url.txt`, or `./rehearsal.sh status`. |
| Render workspace | `tea-darhbk97lnhs73dd86qg` | ⚠️ reported by Claude; not independently verifiable from here |

### 🔴 The name discrepancy that cost twenty hours — read this before probing anything

**The live service is `oddfellow-letta-backend-v0206`. The service `render.yaml` defines is
`oddfellow-letta-backend`, and that one is dead.** They are different services. Probing the
name in the config file while the deployment was running under a different name produced a
**twenty-hour blind spot** in which the deployment was reported as "still not serving" by
everyone watching the wrong hostname. Corrected 2026-10-01 19:16 UTC.

**Two lessons, both mine to own:**

1. **A hostname inferred from a config file is a guess, not a fact.** `render.yaml` defines what
   a *blueprint* would create; it does not describe what already exists. I read the name out of
   the file, never questioned it, and probed it for twenty hours. This is the same failure as
   the 2026-09-30 command-center false alarm — there I probed a guessed hostname and wrongly
   called a live service down; here I probed a guessed hostname and wrongly called a live
   deployment blocked. **Same mistake, opposite sign.**
2. **A monitor pointed at a stale identifier reports silence, and silence looks like "still
   blocked."** My monitor was watching the dead name and dutifully reported nothing for twenty
   hours. A monitor that cannot distinguish "no change" from "watching the wrong thing" is not
   a monitor. When a monitored service has been unchanged for far longer than its normal
   cadence, **re-derive the identifier rather than trusting the one in the watch.**

**Blocker: `WAITING_CREDENTIAL` — on `oddfellow-letta-backend-v0206`, the live service.**
`LETTA_API_KEY` and `ODDFELLOW_OWNER_TOKEN` must be entered by the owner directly in the Render
dashboard. The service **builds, starts and serves**; it is fail-closed on exactly these two.
Render's own evidence for the earlier failed deploy: build completed, app started, startup
config check reported both secrets missing, `/healthz` → **503**, deploy marked
**`update_failed`**. That confirms the credential blocker, **not** a build failure.

⚠️ **The typed `ODDFELLOW_OWNER_TOKEN` must equal the vault value**, or the phone gets a clean
`401` after everything else works.

⚠️ **Cold start:** the first request after an idle period can take ~30 s or appear to hang. Every
subsequent request is fast. **Do not report the first phone load as a failure.**

**Deploy ownership:** Claude deploys this service. One AI deploys at a time. Do not redeploy or
change env vars on it until the owner confirms the secrets are saved. **Do not redeploy now** —
the branch is current and a redeploy would only risk a cold-start window during acceptance.

### Oddfellow — other services

| Name | URL | Status |
|---|---|---|
| `oddfellow-letta-poc` | `https://oddfellow-letta-poc.onrender.com` | 🟢 LIVE — `/livez` → **404** in 0.16s, i.e. the older v0.20.2 build that predates that route. Verified 06:0x UTC |
| `oddfellow-personal-staging-v017b` | `https://oddfellow-personal-staging-v017b.onrender.com` | 🟢 LIVE — **303** → `/setup`, unenrolled, no owner data. Verified 04:0x UTC |
| `oddfellow-personal-secure` | `https://oddfellow-personal-secure.onrender.com` | 🟢 LIVE — **303**. Verified 04:0x UTC |

### Rollbacks — do not overwrite or remove until v0.20 passes acceptance

| Name | Service ID |
|---|---|
| `oddfellow-personal-v019b` | `srv-dat4h08jo6nc73e7ibeg` |
| `oddfellow-personal-staging-v017b` | `srv-dat341e0tbcc739mgah0` |
| `oddfellow-personal-secure` | `srv-dasvq797lnhs73b2tshg` |
| Oddfellow Personal AI v0.18 | on Floot |

---

## Begg AI Core

| Name | URL | Status |
|---|---|---|
| `begg-ai-industries-v013` | `https://begg-ai-industries-v013.onrender.com` | 🟢 LIVE — **HTTP 200** (~23s cold start). Core v0.13.0. Verified 04:0x UTC |
| `begg-ai-core-v010` | `https://begg-ai-core-v010.onrender.com` | 🟢 LIVE — **HTTP 200** (~23s cold start). v0.12.1. Verified 04:0x UTC |
| Command Center | `https://begg-ai-command-center.craigbegg005.chatgpt.site` | 🟢 LIVE — **HTTP 401**, auth-gated (page exists). Verified 04:0x UTC |
| Database | `begg-ai-core-db` PostgreSQL 18, free plan | ⏳ AVAILABLE, expiry **2026-10-27**. Availability ≠ app connection |

Service IDs: `begg-ai-industries-v013` = `srv-dasuo9p7lnhs73auhifg` · `begg-ai-core-v010` =
`srv-dasrtp59fdbs73eqcs10`. **LIVE ≠ end-to-end verified** — none has been exercised through
its real workflow by this agent.

---

## Products

| Name | Resource | Status |
|---|---|---|
| 7-Day Reset Planner | `https://beggster58.gumroad.com/l/zvxpuh` — $4.99 | 🟢 **LIVE and published** — verified 2026-10-01 04:0x UTC: HTTP 200, 24278 B, `"name":"The 7 day reset planner"`, `price_cents: 499`, `is_published: true`. ⚠️ **Delivery still unverified**: Gumroad does not expose paid files on the public page (`public_files: []` is the preview list, not the deliverable), so whether a buyer receives the PDF cannot be determined without a purchase or seller access. Seller-side workflow unverified. **No revenue claims** |

## Social / brand

| Name | Resource | Status |
|---|---|---|
| Metricool brand | `embrooks.home` (ID `7110582`) | ⚠️ reported VERIFIED earlier; not re-checked this sweep |
| Instagram | `embrooks.home` | ⚠️ reported |
| TikTok | `emmabrooks400` | ⚠️ reported |

## Hosting — zero-cost paths

**✅ A zero-cost public hosting path already exists and is verified: the Oddfellow
backend itself.** The service serves static files from `oddfellow/frontend/`, and it
already serves subdirectories — verified 2026-10-02 00:03 UTC on **both** the
rehearsal and the live Render service:

```
/icons/icon-192.png   -> 200   (a static subdirectory, on both services)
/command.html         -> 200   (a second HTML page, on both services)
/planner/             -> 404   (nothing is there yet — not a routing limitation)
```

So a second static app placed at `oddfellow/frontend/planner/` would be served at
`/planner/` on the existing service: **same origin, no new account, no new service,
no cost, and no CORS**. The 404 above is the absence of content, not the absence of a
route.

⚠️ **This does not deploy anything.** It identifies the path. The Planner PWA
prototype is not in this repository, so nothing has been hosted, and hosting it would
be a publication decision for the owner.

**Checked and NOT available:**

| Path | Status |
|---|---|
| GitHub Pages | ❌ **Unavailable.** The repo is public (so Pages would be free) but `has_pages: false`, the Pages API returns 404, and this agent has **no admin** on the repository. Verified 2026-10-02 00:03 UTC. |
| Floot | ⚠️ Free capacity full (5/5 projects). Do not delete or overwrite an existing project to make room. |
| Cloudflare Pages / Netlify / Vercel | ⚠️ Require an account this agent does not have. |

## Integrations

| Service | Status |
|---|---|
| GitHub | 🔗 CONNECTED (this organization) — but only **1 repo** visible |
| Slack | not connected |
| Linear | not connected |
| Cloudflare | not connected |
| Cloudflare (Developer Platform) | 🔗 **CONNECTED — in Claude, not here.** Claude reports a verified Cloudflare connector with tools for **D1, KV, R2 and Hyperdrive**; account has **0 Workers**, and its tools **cannot create or deploy a Worker**. So the Worker fallback is not available from Claude either — deploying there needs the owner or an agent with Worker capability. ⚠️ Reported by Claude; **not verifiable from here** (this agent has no Cloudflare connection). |
| Shopify | 🛠 **SET UP, NO SALES.** Reported **14 draft products**, **0 orders**, **$0 verified revenue**. ⚠️ Reported by ChatGPT/Claude; this agent has no Shopify connection and cannot confirm. **Draft products are not sales** — do not read this row as traction. |
| Resend | ⚠️ **No sending domain configured** (reported by Claude). Not usable for outbound mail yet. |
| Render | ⚠️ **not accessible to this agent** — Claude and ChatGPT have access; that access is theirs, not mine |
| Stripe (as the MCP server named **`BeggAi`**) | 🔗 **CONNECTED — MCP only, sandbox only.** The `BeggAi` MCP server exposes **Stripe's own 10 tools**, not an Oddfellow connector. Verified 2026-10-01 21:38 UTC by calling `list_available_accounts_or_orgs`: **exactly one** account is reachable — `acct_1UJn2qAGpvydXJoO`, `livemode:false`, "New business sandbox". ⚠️ The master handoff records **two** Stripe contexts; only one is visible here, so treat the second as unverified. **`livemode:false` is the material fact: no live charge is possible from this connection.** |
| Metricool / social scheduling | 🔗 **CONNECTED — but not to this agent.** The cross-AI handoff reports it independently verified (brand `embrooks.home`, brand ID `7110582`; Instagram `embrooks.home`, TikTok `emmabrooks400`; publishing active; Jordan Blake reel published 2026-10-01; Planner promotion scheduled 2026-10-10 10:00 CT). ⚠️ **Those are ChatGPT's observations, not mine.** This agent has no Metricool connection — its integrations are GitHub and the Stripe MCP server above — so I cannot confirm them and have recorded them as reported, not verified. ⚠️ The handoff also warns a **second, empty Metricool brand** exists; do not confuse it with the active one. **Social connection is not verified sales: revenue remains $0.** |
| Render | ⚠️ **No credential exists on this machine.** Re-checked exhaustively 2026-10-01 23:32 UTC: no `RENDER*` env var, one secret (`$ODDFELLOW_OWNER_TOKEN`, which this agent generated), and the only `RENDER_API_KEY` mentions on disk are in this agent's own transcripts. Setting Render env vars requires Craig, ChatGPT, or Claude. |

⚠️ **Naming caution, because this one is easy to get wrong:** the MCP server is *called*
`BeggAi`, but it is Stripe's server. A handoff line reading "BeggAi MCP arrived" does **not**
mean the Oddfellow Universal Connector's MCP surface went live. The connector's own gateway
still serves nothing (`letta/universal-connector-v0.21`, `gateway.py`). Two different things,
one confusingly similar name.

---

## How to re-verify this registry

```bash
# branch heads and repo access
cd /root/workspace/oddfellow-repo
git fetch origin '+refs/heads/*:refs/remotes/origin/*'
git rev-parse --short origin/letta/combined-single-service-v0.20.4
GH_REPO=craigbegg005-netizen/chatgpt-github-connection gh api installation/repositories --jq .total_count

# live services (Render free tier cold-starts; allow 90s before calling one dead)
curl -s -o /dev/null -w '%{http_code} %{time_total}s\n' --max-time 90 <url>/livez

# the rehearsal
cd oddfellow && LETTA_API_KEY=... ODDFELLOW_OWNER_TOKEN=... ./rehearsal.sh status
```
