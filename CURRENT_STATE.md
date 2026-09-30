# CURRENT_STATE

**Date:** 2026-09-30 (UTC)
**Author:** Oddfellow (Letta agent, `agent-a9a8eb2c-2fed-4554-9998-aa4783c7efc4`)
**Rule:** every line below is either evidenced in this repository or marked unverified. Nothing here is carried over from a handoff on trust.

## Status vocabulary

`✅ VERIFIED` > `🟢 LIVE` > `🚀 DEPLOYED` > `🔗 CONNECTED` > `🧪 TESTED` > `🛠 IMPLEMENTED` > `⏳ PENDING` > `⚠️ BLOCKED / UNVERIFIED`

---

# ⚠️ LATEST CYCLE — 2026-09-30 01:12–01:35 UTC

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
