# Recovered API surfaces — 2026-09-30

Route inventories extracted from the OpenAPI documents captured in this
directory. These are the running systems describing themselves; nothing here is
inferred. A candidate source tree can be validated against them by regenerating
its spec and diffing route paths and component schema names.

## `oddfellow-letta-poc` — "Oddfellow Letta backend" v0.20.2 — 6 paths

This is the current Oddfellow backend, and the only one of these services whose
source **is** in this repository (`oddfellow/oddfellow_letta_backend.py`). It is
recorded here so the live revision can be diffed against the tree.

```
GET   /healthz
GET   /api/letta/status
GET   /api/letta/agent
POST  /api/letta/message
POST  /api/letta/new-session
GET   /api/letta/history
```

Schemas: `MessageIn`, `HTTPValidationError`, `ValidationError`

## `oddfellow-personal-secure` — "Oddfellow Personal" v0.16.0 — 11 paths

**The most significant recovery in this capture: the v0.16.0 "Oddfellow
Personal" line, whose source is otherwise missing, publishes a complete
description of itself.** This is the session-cookie, enrolment-gated
predecessor of the current backend.

```
GET   /                          POST  /api/enroll
GET   /login                     POST  /api/login
GET   /api/me                    POST  /api/logout
GET   /api/status                POST  /api/chat
GET   /health                    GET   /manifest.webmanifest
                                 GET   /sw.js
```

Schemas: `ChatMessage`, `ChatRequest`, `EnrollRequest`, `LoginRequest`,
`HTTPValidationError`, `ValidationError`

Notable: it is already a **PWA** (`/manifest.webmanifest` + `/sw.js`), it uses
**enrolment with a `setup_code`** rather than a static owner token, and
`POST /api/chat` takes `{messages:[{role, content}]}` — a multi-turn shape,
unlike v0.20's single `{input}` `MessageIn`.

## `begg-ai-industries-v013` — "Begg AI Core / Oddfellow" v0.13.0 — 24 paths

The operating layer. **The zero-spend rule is enforced in the running system,
not merely documented**: `/api/budget/policy` (PATCH) and `/api/budget/revenue`
(POST) exist alongside `/api/budget` and `/api/budget/events`.

```
GET   /                          GET   /api/approvals
GET   /api/status                GET   /api/audit
GET   /api/apps                  GET   /api/departments
GET   /api/timeline              POST  /api/checkpoints
GET   /api/budget                GET   /api/budget/events
PATCH /api/budget/policy         POST  /api/budget/revenue
GET   /api/schedules             POST  /api/schedules
PATCH /api/schedules/{id}        POST  /api/scheduler/tick
GET   /api/tasks                 POST  /api/tasks
GET   /api/tasks/{id}            POST  /api/tasks/{id}/run
POST  /api/tasks/{id}/approve    POST  /api/tasks/{id}/reject
POST  /api/tasks/{id}/retry      POST  /mcp
GET   /health                    GET   /ready
```

Schemas: `TaskCreate`, `RunRequest`, `ApprovalDecision`, `ScheduleCreate`,
`ScheduleUpdate`, `SyncCheckpoint`, `BudgetPolicyUpdate`, `RevenueRecord`,
`HTTPValidationError`, `ValidationError`

## `begg-ai-core-v010` — "Begg AI Core / Oddfellow" v0.12.1 — 16 paths

Retained as a diff. v0.13.0 added, over v0.12.1: `/api/apps`,
`/api/timeline`, `POST /api/checkpoints`, the whole `/api/budget*` family, and
`POST /mcp`.

```
GET   /                          GET   /api/approvals
GET   /api/status                GET   /api/audit
GET   /api/departments           GET   /api/schedules
POST  /api/schedules             PATCH /api/schedules/{id}
POST  /api/scheduler/tick        GET   /api/tasks
POST  /api/tasks                 GET   /api/tasks/{id}
POST  /api/tasks/{id}/run        POST  /api/tasks/{id}/approve
POST  /api/tasks/{id}/reject     POST  /api/tasks/{id}/retry
GET   /health                    GET   /ready
```

## `oddfellow-personal-v019b` and `oddfellow-personal-staging-v017b`

Neither publishes an OpenAPI document (`/openapi.json` → 404). Both serve HTML.
`staging-v017b` exposes `/health` and `/ready` and reports
`{"status":"ok","version":"0.17.0","build_id":"genesis-0003"}` with
`database:true`, `owner_enrolled:false`, `model_connected:false` — an
un-enrolled staging instance holding no owner data. Their API surface is
therefore recoverable only by probing, not from a published spec.

## What this means for the recovery lane

Two of the three missing lineages now have a machine-checkable description of
themselves in version control:

| Lineage | Version | Surface recovered? |
|---|---|---|
| Oddfellow Letta backend | v0.20.2 | ✅ source is in this repo |
| Oddfellow Personal | v0.16.0 | ✅ full OpenAPI captured |
| Oddfellow Personal | v0.17.0 | ⚠️ `/health` + `/ready` only |
| Oddfellow Personal | v0.19b | ⚠️ HTML only |
| Begg AI Core | v0.13.0 | ✅ full OpenAPI captured |
| Begg AI Core | v0.12.1 | ✅ full OpenAPI captured |

**Still missing: the actual implementation source.** An OpenAPI document
describes the contract, not the code. Recovering the code itself requires either
the owner granting repository access, or reading each Render service's
dashboard for its repo/branch or build cache. No amount of probing substitutes
for that — and a reconstruction written from a spec must never be presented as
the original.
