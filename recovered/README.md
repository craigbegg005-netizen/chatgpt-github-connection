# Recovered API surface — the older Oddfellow services are still RUNNING

**Discovered 2026-09-30 00:56 UTC by Oddfellow (Letta agent), by probing the live
Render services.**

## Why this matters

A handoff stated that the earlier Oddfellow secure architecture
(`v0.17.0 / genesis-0003`, scrypt owner auth, signed sessions, SQLite/Postgres)
was **documented but repository-unverified** — no source anywhere in GitHub that
the Letta GitHub App can reach.

That is still true about the **source**. But the systems are **alive**, and their
running API surfaces are fully recoverable. That is a very different starting
point from "we have nothing": the shapes, the auth model, and the exact endpoint
set are now evidence rather than prose.

This directory preserves that evidence.

## Evidence (raw, unedited)

### `oddfellow-personal-staging-v017b.onrender.com` — v0.17.0 / genesis-0003

```
GET /health  -> 200 {"status":"ok","version":"0.17.0","build_id":"genesis-0003"}
GET /ready   -> 200 {"ready":true,"database":true,"owner_enrolled":false,"model_connected":false}
GET /        -> 303 (redirect; unenrolled instance routes to /setup)
GET /login   -> 303
GET /setup   -> 200  (setup page renders)
GET /api/history -> 401 {"error":"Sign in required"}
GET /sw.js   -> 200
```

Note `owner_enrolled: false` and `model_connected: false`. This instance is a
**staging instance that has never been enrolled** — it is not in production use
and holds no owner data. `database: true` means its Postgres is connected.

### `oddfellow-personal-secure.onrender.com` — v0.16.0

Serves a complete OpenAPI document (saved here as
`oddfellow-personal-v0.16-openapi.json`):

| Method | Path | Notes |
|---|---|---|
| GET  | `/` | app shell |
| GET  | `/login` | sign-in page |
| POST | `/api/enroll` | body `{setup_code, name, password}` — one-time owner setup |
| POST | `/api/login` | body `{owner_record, password}` |
| POST | `/api/logout` | |
| GET  | `/api/me` | |
| GET  | `/api/status` | returns 401 "Sign in required" unauthenticated |
| POST | `/api/chat` | body `{messages: [{role, content}]}` |
| GET  | `/health` | `{"ok":true,"service":"oddfellow-personal-secure","version":"0.16.0"}` |
| GET  | `/manifest.webmanifest` | PWA |
| GET  | `/sw.js` | service worker |

Auth model, read straight off the spec: a **session cookie** named
`oddfellow_session`, an **enrolment gate** (`/api/enroll` takes a `setup_code`,
so a fresh deployment cannot be claimed without it), and a separate `owner_record`
identifier at login. `/docs` and `/redoc` are disabled in production — good
practice, and it is why v0.17 exposes no OpenAPI document.

### `begg-ai-industries-v013.onrender.com` — Begg AI Core **v0.13.0**

Title `Begg AI Core / Oddfellow`. Serves a complete OpenAPI document (24 paths),
saved here as `begg-core-v0.13.0-openapi.json`:

| Area | Endpoints |
|---|---|
| Job / task queue | `POST,GET /api/tasks`, `GET /api/tasks/{id}`, `POST /api/tasks/{id}/run`, `/approve`, `/reject`, `/retry` |
| Scheduler | `POST,GET /api/schedules`, `PATCH /api/schedules/{id}`, `POST /api/scheduler/tick` |
| Audit | `GET /api/audit`, `GET /api/timeline` |
| Approvals | `GET /api/approvals` |
| Departments | `GET /api/departments` |
| Budget / zero-spend | `GET /api/budget`, `GET /api/budget/events`, `PATCH /api/budget/policy`, `POST /api/budget/revenue` |
| Misc | `GET /api/apps`, `POST /api/checkpoints`, `GET /api/status`, `GET /health`, `GET /ready`, `POST /mcp` |

Note `/api/budget/policy` — the zero-spend rule is **enforced in the running
system**, not just documented in a handoff. And there is an MCP endpoint.

### `begg-ai-core-v010.onrender.com` — Begg AI Core **v0.12.1**

The same service one minor version earlier: 16 paths (no budget, apps,
timeline, or checkpoints; no `/mcp`). Saved as
`begg-core-v0.12.1-openapi.json`. Useful as a diff to show what v0.13.0 added.

## What this does and does not give us

**Does give:** the exact endpoint set, the request body shapes, the
authentication model, the version/build identifiers, and a fingerprint to match
any local checkout against.

**Does not give:** the source code, the database contents, or the deployment
configuration.

## How to actually recover the source

This directory is evidence, not recovery. In rough order of likelihood:

1. **Render's build logs or build cache** for these services may contain the
   uploaded source or the commands that produced it.
2. **The Render dashboard** for each service shows its repo/branch (or, as with
   `oddfellow-letta-poc`, whether the source is materialised from an environment
   variable). Worth reading before assuming the code is gone.
3. **A local checkout on the owner's machine.**
4. **Another GitHub account or organisation.**

Fingerprints to match against a candidate checkout — all verified above:

- `/health` on v0.17 must return `build_id: genesis-0003`
- `/ready` on v0.17 must return the keys `ready`, `database`, `owner_enrolled`,
  `model_connected`
- v0.16 must expose exactly the 11 paths in the table, with schema names
  `ChatMessage`, `ChatRequest`, `EnrollRequest`, `LoginRequest`
- the session cookie must be named `oddfellow_session`

A checkout that does not reproduce those is **not** the original. Do not present
a reconstruction as the recovered original.
