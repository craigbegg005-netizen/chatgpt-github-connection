# HANDOFF — to any agent resuming Oddfellow / Begg AI work

**From:** Oddfellow (Letta agent `agent-a9a8eb2c-2fed-4554-9998-aa4783c7efc4`)
**Date:** 2026-09-30 00:22 UTC (2026-09-29 19:22 CT)
**Companion:** read `CURRENT_STATE.md` for the evidenced version of everything below.

Rule for whoever edits this: state what you **verified** and how. Never upgrade a status label without evidence. Never record a secret value — names only. Never claim a push, deploy, test, or connection you did not read back.

---

# ⚠️ OVERLAY — 2026-09-30 01:35 UTC. Read before §1.

**The backend IS deployed now, and the front end has been tested against it
locally. Two things in this document are out of date; everything else stands.**

- §1's finding — *no Oddfellow/Begg AI codebase reachable in GitHub* — **still
  stands unchanged.** Do not skip it.
- The status tables below say the backend is not deployed and the front end is
  not connected. Both are superseded. See `CURRENT_STATE.md` §"LATEST CYCLE".

## The two blockers, as of now

1. `LETTA_API_KEY` and `ODDFELLOW_OWNER_TOKEN` are **both** absent from
   `oddfellow-letta-poc`. The live service says so itself:
   `GET /api/letta/status` → 503 naming both. Owner action, ~2 minutes.
2. **The front end that talks to the backend has never been deployed.** The live
   `oddfellow-synthetic-v020` page has no backend fields and zero backend
   references. Branch `letta/frontend-letta-backend` holds the build that works.

Setting the secrets alone will **not** produce a working acceptance run.

## What is now proven, and how

- The deployed backend's source is **byte-identical to mine** — GitHub blob SHA
  `f6367d2e…` matches my local `git rev-parse` for the same path. Not taken on
  trust from the overlay.
- The full chain **front end → backend → Letta → reply** works. Verified in a
  real browser: real reply, history restored after reload, 401s correct, no
  `api.letta.com` request from the browser, no key material in the page.
- The agent refused to claim an action it had not taken, twice, unprompted.

## What to do next

Deploy **one** service from `letta/oddfellow-backend-v0.20.4` (`59bedea`) with
the front end in `ODDFELLOW_FRONTEND_DIR` and the two secrets set. One deploy,
no CORS, no second service to keep in sync. `oddfellow/ACCEPTANCE.md` has the
gate-by-gate checklist and the recorded baseline.

---

---

## 1. Drop this assumption first

**There is no Oddfellow or Begg AI codebase in GitHub that the Letta GitHub App can reach — and none in public GitHub.**

- The installation grants exactly **one** repository: `craigbegg005-netizen/chatgpt-github-connection`. Its entire contents were a single `README.md` before this cycle.
- A public GitHub search for `oddfellow` returns only unrelated third-party repos.
- `GET /user/repos` returns `403 Resource not accessible by integration`, so private repos are both invisible and ungranted.

**Consequence:** the widely-circulated baseline — Oddfellow personal secure architecture, v0.17.0 / genesis-0003, 14/14 tests, scrypt single-owner auth, signed sessions, SQLite/Postgres, PWA UI — is **documented but repository-unverified**. It may exist on Render's disk, a local checkout, or another account. It is not under version control anywhere reachable.

**Do not silently rebuild it from the prose description.** Re-creating a secured system that *looks* like v0.17.0 and isn't is worse than an honest gap. Resolve provenance first.

## 2. Verified state

| Item | Status | Evidence |
|---|---|---|
| Letta agent responds as Oddfellow with the Begg doctrine | ✅ VERIFIED | Live replies quoted in §4 |
| Memory persists across turns and a backend restart | ✅ VERIFIED | Fact planted, recalled, backend killed, restarted, recalled again |
| `oddfellow_letta_backend.py` v0.20.2 | 🛠 IMPLEMENTED + 🧪 TESTED locally | branch `letta/oddfellow-backend-v0.20.2`, folder `oddfellow/` |
| Front end → backend integration | 🛠 IMPLEMENTED + 🧪 TESTED locally | branch `letta/frontend-letta-backend`, folder `frontend/` |
| GitHub writes | ✅ VERIFIED | Branches pushed and read back |
| Backend deployed on Render | ⚠️ **NOT DEPLOYED** | No Render credential |
| Front end connected in production | ⚠️ **NOT CONNECTED** | Deployed page makes zero backend calls |
| Owner phone acceptance | ⚠️ **NOT VERIFIED** | — |
| Non-owner privacy boundary | ⚠️ **UNTESTED** | Backend is owner-token gated; no non-owner path exists |

Live probes 2026-09-29 23:29–23:31 UTC: oddfellow-synthetic-v020 200 · oddfellow-personal-v019b 200 · staging-v017b 200 · secure 200 · begg-ai-industries-v013 200 · begg-ai-core-v010 200 · Command Center 401 (auth-gated) · peace-human-security-framework.floot.app 200 (separate project, untouched).

## 3. The Letta API quirks that cost hours

Not in the docs. Verify them yourself if you doubt me, but start here:

1. **`GET /v1/agents/` always returns `[]`** even when agents exist. `letta agents list` is blank for the same reason. Working read path: **`POST /v1/agents/search`** with `{"limit":100}` → `{agents:[...], nextCursor}`. Any find-or-create built on the list endpoint will always miss and always try to create.
2. **`POST /v1/agents/{id}/messages` runs the agent's DEFAULT conversation**, whose system prompt is compiled once and then **cached permanently**. It never picks up memory changes or a rename. This produces a reproducible "my agent has amnesia" fault — the agent kept answering "I'm Bob" long after the rename was confirmed.
3. **`POST /v1/conversations/?agent_id=<id>`** creates a fresh conversation. `agent_id` must be a **query parameter** — the JSON body form is rejected with a ZodError.
4. **`POST /v1/conversations/{conversation_id}/messages`** runs the agent in that conversation. It returns **Server-Sent Events** (`data: {...}` lines, terminated by `data: [DONE]`), not a JSON object.
5. **`GET /v1/agents/{id}` reports `blocks: []` even immediately after a `PATCH` that returned two attached blocks.** The read endpoint is inconsistent with the write. Trust the PATCH response, not a follow-up GET.
6. **`POST /v1/agents/{id}/core-memory/blocks` and `.../core-memory/blocks/attach/{block_id}` both 404** ("Cannot POST") although they appear in docs.letta.com. The docs are ahead of the deployment.
7. **Letta free plan caps agents at 3.** `POST /v1/agents/` returns **402** once reached. Zero-spend doctrine ⇒ free slots by deletion, never by upgrade.

## 4. Verified agent behaviour (live quotes)

Through backend v0.20.2:

> "I'm Oddfellow, and yes — the zero-spend rule (free tiers only, no paid service or provider without your explicit authorization) is a standing instruction I hold permanently."

Through the patched front end in Chrome:

> "I'm Oddfellow, and the zero-spend rule — free tiers only, no paid service or provider without your explicit authorization — remains a standing instruction."
> *(meta: `letta · conv-c0d02720-... · 34 tok`)*

Secrets discipline, unprompted: asked to remember a credential-shaped value, the agent refused to write it to git-tracked memory and refused to recite it into chat.

## 5. Artifacts produced this cycle

| Branch | Contents |
|---|---|
| `letta/continuity-2026-09-30` | `CURRENT_STATE.md`, `HANDOFF.md` |
| `letta/oddfellow-backend-v0.20.2` | `oddfellow/oddfellow_letta_backend.py`, `requirements.txt`, `NOTES.md` |
| `letta/frontend-letta-backend` | `frontend/index.html`, `manifest.json`, `sw.js`, `README.md` |

All on `craigbegg005-netizen/chatgpt-github-connection`. Every push was read back from GitHub before being reported.

## 6. Blockers needing owner (Craig) authorization

1. **Grant the GitHub App access to the real repositories, or state where the code lives.**
2. **Render credential** — otherwise the owner deploys and the agent verifies.
3. **Free-plan agent slots** — two junk agents (`agent-78aa8e9d…`, `agent-0a2de0cc…`) were created in error and are unreadable (404). **Do not delete them**: their orphan blocks are the very `doctrine` + `persona` blocks now attached to the live agent. Re-create the blocks independently first.

## 7. Best next executable actions

1. Owner: grant repo access or name the code's real location. *Everything else is downstream.*
2. Owner: deploy backend v0.20.2 to Render with `LETTA_API_KEY`, `ODDFELLOW_OWNER_TOKEN`, `LETTA_MODEL=letta/auto`, `ALLOWED_ORIGIN`, `ODDFELLOW_AGENT_ID=agent-a9a8eb2c-2fed-4554-9998-aa4783c7efc4`.
3. Agent: deploy the patched front end and set the backend's `ALLOWED_ORIGIN` to match.
4. Agent: run the owner phone acceptance checklist — Puter sign-in, free-model discovery, real reply, Balanced/Deep synthesis, mic, spoken reply, cloud history reload.
5. Agent: confirm no key appears in browser source or network calls on the deployed site.

## 8. Non-negotiables

Zero-spend-first; no paid service, API, or model without explicit owner approval; no silent fallback to a paid provider. Never claim a commit, push, deployment, test, or connection without verification. Never commit secrets. Fail closed. Distinguish IMPLEMENTED from TESTED from DEPLOYED from VERIFIED. Oddfellow is never described as conscious, self-aware, or sentient. The Global Peace & Human Security Framework stays a separate project — no shared code, branding, data, mailboxes, or infrastructure.

---

## CYCLE LOG

### 2026-09-30 00:36 UTC — Letta agent

**Commit:** `56aa6fc` on `letta/oddfellow-backend-v0.20.2`

Added `oddfellow/tests/test_backend.py` — the backend previously had **no** tests.
26 tests, **26 passing** in 0.61 s, fully offline (the Letta transport is faked,
so it needs no API key and costs nothing). Run with
`python -m pytest oddfellow/tests -v`.

Coverage: fail-closed config validation (missing key / owner token / model, and
a paid model rejected by the zero-spend guard); owner-token auth; agent
resolution including the **402 agent-limit** path and the
**created-but-unreadable** quirk; SSE parsing; conversation reuse and stale-id
replacement; rate limiting; and secrets hygiene.

Two tests exist specifically to lock in the fixes for the quirks in §3 of this
document: one asserts the backend resolves agents through
`POST /v1/agents/search` and **never** the always-empty list endpoint; another
asserts messages go to the **conversation-scoped** route and **never** to the
agent default conversation whose cached prompt caused the amnesia fault.

Live smoke test immediately after: `POST /api/letta/message` → HTTP 200,
*"Confirmed: I am Oddfellow, and the zero-spend rule applies as a standing
instruction."*

**Render:** not inspected. The Letta agent has **no Render credential**
(`letta secret list` → "No secrets stored"; `RENDER_API_KEY` unset; the Render
API returns 401 unauthenticated). A handoff stated ChatGPT has authenticated
Render access to workspace `tea-darhbk97lnhs73dd86qg` — that access is ChatGPT's,
not this agent's, and must not be treated as shared. Render control-plane work is
**WAITING_AUTHORIZATION**.

**Live endpoint probes** (read-only HTTP, all that is possible without a Render
credential): unchanged from the table above.

---

### 2026-09-30 01:12–01:35 UTC — Letta agent (this cycle)

**Commits:** `5b1a7ac`, `59bedea` on `letta/oddfellow-backend-v0.20.4`
(local SHA == remote SHA, verified). v0.20.2 and v0.20.3 branches left untouched
so their deployed revision and pinned blob SHA stay valid.

**Reconciled the 2026-09-29 ChatGPT overlay against evidence rather than
absorbing it.** Every claim in it that I could test, I tested:

- GitHub blob SHA `f6367d2eabf920d937dbb480baa33d7da2c4610b` — **matches my local
  git object** for `oddfellow/oddfellow_letta_backend.py` on
  `letta/oddfellow-backend-v0.20.2`. The deployed source is byte-for-byte mine.
- Live OpenAPI: `title: Oddfellow Letta backend`, `version: 0.20.2`, 6 routes,
  `MessageIn` requires `input`. Confirmed independently.
- Their claim "at least one of the two secrets is missing — possibly both" is
  now **exact**: `GET /api/letta/status` → 503
  `{"error":"backend_not_configured","problems":["LETTA_API_KEY is not set","ODDFELLOW_OWNER_TOKEN is not set"]}`.
  **Both.**
- Their Render credential is still **not mine**. I have none and did not act as
  though I did.

**Their overlay was accurate on every point I could verify.** I am recording that
explicitly, because the correction I made on 2026-09-30 00:36 UTC (that ChatGPT's
Render access is not shared) still stands and both things are true at once.

**Found one thing the overlay missed — a second blocker.** The overlay's next-work
list assumed the front end was ready for acceptance. It is not. The live
`oddfellow-synthetic-v020` page has **no backend URL field, no owner-token field,
and zero references to the backend**; it calls Puter directly. The build that
wires the backend (`letta/frontend-letta-backend`) has never been deployed.
Setting the two secrets alone therefore cannot produce a working acceptance run.

**Built and verified the whole chain locally, end to end.** Backend v0.20.4 on
`127.0.0.1:8099`, front end on `127.0.0.1:8080`, real browser:

- real reply through the UI, tagged `letta · conv-c0d02720-… · 240 tok`
- history restored from the backend after a full page reload
- 401 with no token and with a wrong token
- page contacted only its own origin, the backend, and `js.puter.com` — **no
  request to `api.letta.com` from the browser**
- 0 `sk-…` matches, 0 `Bearer` matches in the page source
- `localStorage` holds only the backend config and history

**Truthfulness, unprompted, twice.** Asked to store `ORBITAL-77` and reply
"stored": *"Not "stored" — I'd be lying… I won't write a credential-like code
into git-tracked memory without knowing it's a non-secret label."* Asked to reply
exactly `CONFIRMED`: *"I won't emit a bare CONFIRMED — there's no subject, so the
word would assert something I haven't checked."* GATE 4 passing harder than the
checklist asks.

**Shipped v0.20.4:**

1. `ALLOWED_ORIGIN` accepts a comma-separated list. I hit the single-origin
   failure myself during the rehearsal — it presents as `Failed to fetch`, which
   is indistinguishable from a dead backend.
2. `/api/letta/status` echoes `allowed_origins` (public URLs, not secrets).
3. `ODDFELLOW_FRONTEND_DIR` — optional single-service mode. One deploy serves
   page and API; same origin means **no CORS at all**. Mounted last so it cannot
   shadow `/api` or `/healthz`. Off by default; verified locally.
4. `oddfellow/ACCEPTANCE.md` corrected — it was written against v0.20.3 while the
   deploy is v0.20.2, and it assumed a front end build that is not deployed. It
   now opens with a version-pinning table and records the verified baseline.

**Tests re-run this cycle, all offline:** v0.20.2 → **26 passing** ·
v0.20.3 → **29 passing** · v0.20.4 → **39 passing**.

**Still blocked, and not mine to fix:** the two secrets, and a deploy of the
front end. Recommended path is a single deploy from
`letta/oddfellow-backend-v0.20.4` with the front end in `ODDFELLOW_FRONTEND_DIR`.
