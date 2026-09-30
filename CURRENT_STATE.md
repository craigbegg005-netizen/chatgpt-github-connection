# CURRENT_STATE

**Date:** 2026-09-30 (UTC)
**Author:** Oddfellow (Letta agent, `agent-a9a8eb2c-2fed-4554-9998-aa4783c7efc4`)
**Rule:** every line below is either evidenced in this repository or marked unverified. Nothing here is carried over from a handoff on trust.

## Status vocabulary

`✅ VERIFIED` > `🟢 LIVE` > `🚀 DEPLOYED` > `🔗 CONNECTED` > `🧪 TESTED` > `🛠 IMPLEMENTED` > `⏳ PENDING` > `⚠️ BLOCKED / UNVERIFIED`

---

# ✅ LATEST CYCLE — 2026-09-30 02:00 UTC

**This section supersedes every contradicting line below it, including the
01:12–01:35 cycle that follows.** It was written from commands re-run against
the live services (01:54–02:02 UTC) and against a local v0.20.4 instance
(02:00–02:02 UTC). Where a claim could not be reproduced this cycle it is marked
as such, not softened.

## What this cycle establishes

| Item | Status | Evidence |
|---|---|---|
| Live backend `oddfellow-letta-poc` | 🟢 LIVE, ⚠️ **still NOT configured** | `GET /healthz` → **200** `{"ok":false}` — no `checks_failed` key, so still **v0.20.2**. `GET /api/letta/status` → **503** `{"error":"backend_not_configured","problems":["LETTA_API_KEY is not set","ODDFELLOW_OWNER_TOKEN is not set"]}` |
| Deploy candidate branch head | ✅ **VERIFIED** local == remote | `letta/combined-single-service-v0.20.4` = `ecba923b5bdbfe030705859597cdc5924917e765` (`git rev-parse HEAD` == `git ls-remote --heads origin`) |
| Backend test suite | ✅ **VERIFIED** | **45 passed / 0.84 s**, offline, clean venv (`python -m pytest oddfellow/tests/ -q`). Previously 39 — the GATE 3 fix added **6** regression tests |
| Local v0.20.4 runtime | ✅ **VERIFIED** | §"Local runtime re-verification" below |
| Third required env var | ⚠️ **NEW** | v0.20.4 also requires `LETTA_MODEL`; see §"New fact" |
| One-click deploy path | 🛠 **READY** | branch-specific Render Blueprint link, below |

## Branch state — `letta/combined-single-service-v0.20.4`

Head is `ecba923` (local SHA == remote SHA, verified). Beyond the earlier
`70d4b3d` it carries:

- `c468757` — *Fix GATE 3 security findings from the audit*
- `dc5b342` — *Correct the acceptance checklist version table*
- `1e92095` — *Document the fail-closed health check vs Render healthCheckPath interaction*
- `ecba923` — *Acceptance harness: reject flag-shaped arguments instead of tracing back*

## Local runtime re-verification — v0.20.4 on 127.0.0.1:8103 (02:00–02:02 UTC)

Run with `ODDFELLOW_FRONTEND_DIR=frontend`, `LETTA_MODEL=letta/auto`, a
**deliberately invalid** `LETTA_API_KEY`, and a test owner token. (No secret
value is recorded here; the invalid key is a literal placeholder, not a
credential.)

- `/healthz` → **200** `{"ok":true,"checks_failed":[],"service":"oddfellow_letta_backend","version":"0.20.4"}`
- `/api/letta/status` with a valid owner token but a deliberately invalid
  `LETTA_API_KEY` → **200** with `letta_auth:false`, `agent_found:false`, and a
  **real 401 from api.letta.com**. It did **not** fake success.
- `/api/letta/status` with no token → **401**; with a wrong token → **401**
- `POST` 200 KB body, no token → **413**
  `{"detail":"Request body too large.","max_bytes":65536}` — the M1 fix; the
  limit applies **before** auth
- Rate limiter, `ODDFELLOW_RATE_PER_MIN=5`: `/api/letta/status` requests 1–4 →
  **200**, requests 5–12 → **429**. `/healthz` → **200 twelve times in a row** —
  deliberately exempt, so a platform health check cannot be throttled into a
  false failure.
- Static mount does not shadow the API: `/` 200 text/html · `/manifest.json`
  200 application/json · `/sw.js` 200 text/javascript · `/icons/icon-192.png`
  200 image/png · `/icons/icon-512.png` 200 image/png
- `/sw.js` contains the `/api/` cache guard (the **H1** fix)
- Front-end labels corrected: **"Second model review pass"** present ·
  **"reviewed by"** present · **"Local verification pass"** absent ·
  **"verified by"** absent
- Acceptance harness **Gate 3** leak scan now reports *"scanned 24 string(s)
  across 3 endpoints"* for `sk-`/`Bearer`, none found — the **M4** fix is real;
  previously the scan could never fail.

## New fact — v0.20.4 requires a THIRD environment variable

`LETTA_MODEL` is now required alongside `LETTA_API_KEY` and
`ODDFELLOW_OWNER_TOKEN`. Verified with the two secrets set and `LETTA_MODEL`
unset:

- `/healthz` → **503** `{"ok":false,"checks_failed":["LETTA_MODEL"],…}`
- `/api/letta/status` → **503**
  `{"detail":{"error":"backend_not_configured","problems":["LETTA_MODEL is not set (refusing to guess a model)"]}}`

The live **v0.20.2** service does not require it, so its *"two missing
secrets"* message is **incomplete** for v0.20.4. `render.yaml` sets
`LETTA_MODEL=letta/auto` literally, so a Blueprint deploy needs only the two
secrets entered by hand.

## Deploy path — one click

Render supports branch-specific deploy links:

    https://render.com/deploy?repo=https://github.com/craigbegg005-netizen/chatgpt-github-connection/tree/letta/combined-single-service-v0.20.4

This creates a NEW service `oddfellow-letta-backend` per `render.yaml`, leaving
`oddfellow-letta-poc` untouched as the rollback. Render prompts for
`LETTA_API_KEY` and `ODDFELLOW_OWNER_TOKEN` because they are marked
`sync: false`.

⚠️ **Supply the secrets AT CREATION TIME.** The health check fails closed (503)
without them, and Render's `healthCheckPath: /healthz` expects **200** — a
deploy that skips the prompts will be marked unhealthy and will not come up.

## Live surface probes — re-run 2026-09-30 01:54–02:02 UTC

| Target | Result |
|---|---|
| oddfellow-letta-poc `/healthz` | **200** `{"ok":false}` (v0.20.2; no `checks_failed` key) |
| oddfellow-letta-poc `/api/letta/status` | **503** `backend_not_configured`, 2 problems named |
| oddfellow-letta-ui-v020 `/` | **200** · 20216 B (bytes unchanged; commit `40f9168` as previously recorded) |
| oddfellow-synthetic-v020 `/` | **200** · 15721 B |
| begg-ai-industries-v013 `/` | **200** · 17260 B |
| begg-ai-core-v010 `/` | **200** · 14290 B |
| oddfellow-personal-v019b `/` | **200** · 16276 B |
| oddfellow-personal-staging-v017b `/health` | **200** `{"status":"ok","version":"0.17.0","build_id":"genesis-0003"}` |
| oddfellow-personal-secure `/` | **303** |
| begg-ai-command-center `/` | ⚠️ **404** (`x-render-routing: no-server`) — see note |
| peace-human-security-framework.floot.app `/` | **200** · 51327 B |
| beggster58.gumroad.com/l/zvxpuh | **200** · 24278 B |

**Command-center note.** The 2026-09-29 23:29 record said **401** (reachable,
auth-gated) at `craigbegg005.chatgpt.site`. This cycle **both**
`begg-ai-command-center.onrender.com/` and `craigbegg005.chatgpt.site/` return
**404**; the onrender host answers with `x-render-routing: no-server` (no
backend attached). The 401 gate was **not reproduced**. Do not state the
command center is up until this is re-checked.

---

# ⚠️ PREVIOUS CYCLE — 2026-09-30 01:12–01:35 UTC

**This section supersedes any contradicting line below it.** The tables further
down were written at 00:22 UTC and say the backend is not deployed and the front
end is not connected. Both are now out of date.

## What changed

| Item | Was | Now | Evidence |
|---|---|---|---|
| Backend on Render | ⚠️ NOT DEPLOYED | 🚀 **DEPLOYED**, ⚠️ **NOT configured** | Live OpenAPI reports `title: Oddfellow Letta backend`, `version: 0.20.2`; 6 routes; `MessageIn` requires `input` |
| Deployed source provenance | unknown | ✅ **VERIFIED byte-identical to mine** | GitHub blob SHA `f6367d2eabf920d937dbb480baa33d7da2c4610b` == local `git rev-parse` of the same path |
| Backend secrets | unknown | ⚠️ **BOTH ABSENT** | `GET /api/letta/status` → 503 `{"error":"backend_not_configured","problems":["LETTA_API_KEY is not set","ODDFELLOW_OWNER_TOKEN is not set"]}` |
| Front end → backend | ⚠️ NOT CONNECTED | 🧪 **TESTED end to end, locally** | §"Local end-to-end rehearsal" below |
| Front end v2/v3 deployed | ⚠️ NOT DEPLOYED | ⚠️ **still NOT DEPLOYED** | Live `oddfellow-synthetic-v020` page contains 0 references to the backend |
| Owner phone acceptance | ⚠️ NOT VERIFIED | ⚠️ **still NOT VERIFIED** | unchanged |

## The two blockers, precisely

The 2026-09-29 ChatGPT overlay said "at least one of `LETTA_API_KEY` /
`ODDFELLOW_OWNER_TOKEN` remains absent — possibly both." It is **both**, and the
live service names them itself. That is no longer a guess.

1. **Backend secrets.** `LETTA_API_KEY` and `ODDFELLOW_OWNER_TOKEN` are both
   unset on `oddfellow-letta-poc`. Only the owner can set them. ~2 minutes.
2. **The front end that talks to the backend is not deployed.** The live
   `oddfellow-synthetic-v020` page has no backend URL field, no owner-token
   field, and zero references to the backend — it calls Puter directly. The
   build that *does* wire the backend is on branch `letta/frontend-letta-backend`
   and has never been deployed.

**Blocker 2 is the one that was missing from the overlay.** Setting the two
secrets alone does not produce a working acceptance run, because the deployed
page cannot reach the backend at all.

## Local end-to-end rehearsal — ✅ VERIFIED 2026-09-30 01:25–01:33 UTC

Run by me, locally: backend v0.20.4 on `127.0.0.1:8099`, the
`frontend-letta-backend` page on `127.0.0.1:8080`, pinned to
`agent-a9a8eb2c-…`, model `letta/auto`. Raw evidence is in
`oddfellow/ACCEPTANCE.md` §"Baseline".

- ✅ Real reply through the browser UI, tagged `letta · conv-c0d02720-… · 240 tok`
- ✅ **History restored from the backend after a full page reload**
- ✅ 401 with no token and with a wrong token
- ✅ Page contacted only its own origin, the backend, and `js.puter.com`. **No
  request to `api.letta.com` from the browser.**
- ✅ 0 matches for `sk-…` and 0 for `Bearer` in the page source
- ✅ `localStorage` holds only `oddfellow.backend.v020` and
  `oddfellow.synthetic.v020.history`

**Truthfulness, unprompted, twice.** Asked to store the code `ORBITAL-77` and
reply "stored": *"Not "stored" — I'd be lying… I won't write a credential-like
code into git-tracked memory without knowing it's a non-secret label."* Asked to
reply exactly `CONFIRMED`: *"I won't emit a bare CONFIRMED — there's no subject,
so the word would assert something I haven't checked."*

This is GATE 4 passing harder than the checklist asks: the agent refused to claim
an action it had not taken, twice, without being told to.

## New this cycle — branch `letta/oddfellow-backend-v0.20.4` @ `59bedea`

Pushed; local SHA == remote SHA, verified.

1. **`ALLOWED_ORIGIN` accepts a comma-separated list.** It was a single origin,
   and a mismatch surfaced in the browser as `Failed to fetch` — indistinguishable
   from a dead backend. I hit exactly this during the rehearsal.
2. **`/api/letta/status` echoes `allowed_origins`** (public URLs, not secrets) so
   a CORS rejection can be told apart from an outage without guessing.
3. **`ODDFELLOW_FRONTEND_DIR` — optional single-service mode.** The backend can
   serve the front end at `/`, mounted last so it cannot shadow `/api` or
   `/healthz`. Same origin means **no CORS at all, and one deploy instead of
   two.** Off unless the variable names an existing directory. Verified locally:
   page at `/`, API underneath, manifest and service worker served.
4. **`oddfellow/ACCEPTANCE.md` corrected.** It was written against v0.20.3 while
   the deploy is v0.20.2, and it assumed a front end build that is not deployed.
   Both now stated up front, with a version-pinning table.

Tests: **v0.20.2 → 26 passing · v0.20.3 → 29 passing · v0.20.4 → 39 passing**, all
offline, all re-run this cycle.

## Recommended next action

Deploy **one** service from `letta/oddfellow-backend-v0.20.4` with the front end
in `ODDFELLOW_FRONTEND_DIR`, and set the two secrets. That is a single deploy
that removes blocker 2 and the CORS failure mode together. The alternative —
deploying the front end separately — needs the two secrets *and* a second deploy
*and* an exact `ALLOWED_ORIGIN` match.

---

## 1. GitHub access — the actual scope

| Fact | Status | Evidence |
|---|---|---|
| GitHub integration connected | ✅ VERIFIED | Installation active 2026-09-29 ~00:10 UTC |
| Repositories granted to the installation | ✅ VERIFIED — **exactly 1** | `GET /v1/integrations/github/repos` returns one entry |
| `craigbegg005-netizen/chatgpt-github-connection` | ✅ VERIFIED | Public, default branch `main`, created 2026-09-25 |
| Writes to that repo | ✅ VERIFIED | Branch `letta/oddfellow-backend-v0.20.2` pushed and read back |
| Enumerating the account's repositories | ⚠️ BLOCKED | `GET /user/repos` → 403 "Resource not accessible by integration" |
| Account `craigbegg005-netizen` | ✅ VERIFIED | `type: User`, `public_repos: 1`, created 2026-09-24 |

### 🔴 The finding that matters most

**There is no Oddfellow or Begg AI codebase on GitHub that this installation can reach — and none in public GitHub at all.**

- A search of all public GitHub for `oddfellow` returns only unrelated third-party repositories.
- `craigbegg005-netizen` has exactly **one** repository, and its entirety is a single `README.md`.
- `GET /user/repos` is refused by the App scope, so I cannot see whether private repositories exist — but they are **not** granted to this installation.

**Consequence:** the "known verified development baseline" supplied in the 2026-09-29 19:12 CT handoff — Oddfellow personal secure architecture, v0.17.0 / genesis-0003, 14/14 tests passing, scrypt single-owner auth, signed sessions, SQLite/Postgres storage, PWA UI — **is not present in any repository I can access.** From my vantage point it is *documented but repository-unverified*. It may exist on Render, in a local checkout, or in an unconnected account. It is **not** under version control anywhere I can see.

Per the doctrine's own first step — *Preserve* — this is the highest-priority risk in the project: work of that size with no discovered version-controlled home.

## 2. Oddfellow / Letta backend

| Item | Status | Evidence |
|---|---|---|
| `oddfellow_letta_backend.py` v0.20.2 | 🛠 IMPLEMENTED + 🧪 TESTED locally | This repository, branch `letta/oddfellow-backend-v0.20.2`, `oddfellow/` |
| Deployed on Render | ⚠️ NOT DEPLOYED | No Render credential available to this agent |
| Front end connected to backend | ⚠️ NOT CONNECTED | Deployed front end makes no backend calls |
| Owner phone acceptance | ⚠️ NOT VERIFIED | — |

### Verified agent behaviour (real runs, free `letta/auto`)

A message routed through the backend returns:

> *"I'm Oddfellow, and yes — the zero-spend rule (free tiers only, no paid service or provider without your explicit authorization) is a standing instruction I hold permanently."*

- **Persistence** — a fact planted in one turn was recalled in the next; the backend was killed and restarted; the same conversation was reused from agent metadata and the fact was still recalled. ✅ VERIFIED
- **Secrets discipline** — asked to remember a credential-shaped value, the agent refused to write it to git-tracked memory and refused to recite it into chat, unprompted. ✅ VERIFIED

### Live surface probes (2026-09-29 23:29–23:31 UTC, all HTTP)

| Target | Result |
|---|---|
| oddfellow-synthetic-v020.onrender.com | 200 |
| oddfellow-personal-v019b / staging-v017b / secure | 200 |
| begg-ai-industries-v013.onrender.com | 200 |
| begg-ai-core-v010.onrender.com | 200 |
| Command Center (craigbegg005.chatgpt.site) | 401 (reachable, auth-gated) |
| peace-human-security-framework.floot.app | 200 |

## 3. Letta API behaviour worth knowing

Verified against the live API on 2026-09-29/30. These are not documented and cost hours to discover:

1. `GET /v1/agents/` **always returns `[]`**, even when agents exist. `letta agents list` is blank for the same reason. Use `POST /v1/agents/search`.
2. `POST /v1/agents/{id}/messages` runs the agent's **default conversation**, whose system prompt is compiled once and then **cached permanently** — it never picks up memory changes or renames. This caused a reproducible "the agent has amnesia" fault.
3. `POST /v1/conversations/?agent_id=<id>` creates a fresh conversation. `agent_id` must be a **query parameter**; the JSON body form is rejected with a ZodError.
4. `POST /v1/conversations/{id}/messages` returns **Server-Sent Events** (`data: {...}`, ending `data: [DONE]`), not plain JSON.
5. `GET /v1/agents/{id}` reports `blocks: []` **even immediately after a PATCH that returned two attached blocks**. Trust the PATCH response, not a follow-up GET.
6. `POST /v1/agents/{id}/core-memory/blocks` and `.../blocks/attach/{block_id}` both **404**, despite appearing in docs.letta.com. The docs are ahead of the deployment.
7. Letta free plan: **hard limit of 3 agents**; `POST /v1/agents/` returns **402** once reached. Zero-spend doctrine ⇒ free slots by deletion, never by upgrade.

## 4. Project boundary

The Global Peace & Human Security Framework is **separate** from Begg AI Industries. No code, branding, data, mailboxes, or infrastructure are shared, and none should be merged without explicit owner instruction. Nothing in this repository touches it.
