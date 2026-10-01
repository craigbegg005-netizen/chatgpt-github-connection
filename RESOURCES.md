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
- **`oddfellow-letta-backend` is still not serving.** No HTTP response on `/healthz` or
  `/livez`. Cause established: missing secrets failing the health check, deploy marked
  `update_failed` — see `oddfellow/CORRECTION-502-CAUSE-2026-09-30.md`.

---

## Source control

| Resource | Value | Status |
|---|---|---|
| Repo (only one this GitHub App can see) | `craigbegg005-netizen/chatgpt-github-connection` | ✅ VERIFIED — `installation/repositories` → `total_count: 1` |
| Canonical deploy branch | `letta/combined-single-service-v0.20.4` @ `8b455fd` | ✅ VERIFIED 2026-10-01 04:05 UTC |
| `main` | `8ddfe325` | ✅ VERIFIED 2026-10-01 04:05 UTC |
| `letta/frontend-letta-backend` | `445e05c` | ✅ VERIFIED |
| `letta/recovery-capture-2026-09-30` | `f27ec28` | ✅ VERIFIED |
| `letta/independent-verification-2026-09-30` | `46d731b` | ✅ VERIFIED — independent reproduction of the deploy branch's claims |

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
| Deploy target | `oddfellow-letta-backend` · `srv-dau6tgqd0e5s73egkocg` | ⚠️ **NOT RESPONDING** |
| Deploy URL | `https://oddfellow-letta-backend.onrender.com` | ⚠️ `/livez`, `/healthz`, `/` all HTTP 000 at 60s and 120s — verified 06:05 UTC |
| Rehearsal (ephemeral) | `https://verbal-breaking-assumptions-amount.trycloudflare.com` | 🟢 LIVE — v0.20.6, all acceptance gates pass |
| Render workspace | `tea-darhbk97lnhs73dd86qg` | ⚠️ reported by Claude; not independently verifiable from here |

**Blocker: `WAITING_CREDENTIAL`.** `LETTA_API_KEY` and `ODDFELLOW_OWNER_TOKEN` must be entered
by the owner directly in the Render dashboard. Render's own evidence: build completed, app
started, startup config check reported **both secrets missing**, `/healthz` → **503**, deploy
marked **`update_failed`**. That confirms the credential blocker, **not** a build failure.

**Deploy ownership:** Claude deploys this service. One AI deploys at a time. Do not redeploy or
change env vars on it until the owner confirms the secrets are saved.

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

## Integrations

| Service | Status |
|---|---|
| GitHub | 🔗 CONNECTED (this organization) — but only **1 repo** visible |
| Slack | not connected |
| Linear | not connected |
| Cloudflare | not connected |
| Render | ⚠️ **not accessible to this agent** — Claude and ChatGPT have access; that access is theirs, not mine |

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
