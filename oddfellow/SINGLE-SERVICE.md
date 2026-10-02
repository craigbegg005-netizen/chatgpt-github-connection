# Single-service deploy option — one URL serves the page and the API

Status: 🚀 **DEPLOYED** (as `oddfellow-letta-backend-v0206`) · 🧪 TESTED · ⚠️ NOT READY
Branch: `letta/combined-single-service-v0.20.4`
Verified by: Oddfellow (Letta agent), 2026-09-30 01:40–01:45 UTC

> **Updated 2026-10-02 02:5x UTC.** The status line above previously read
> "🛠 IMPLEMENTED · 🧪 TESTED LOCALLY · ⚠️ NOT DEPLOYED". **That is no longer true:** this
> single-service build *is* deployed, as **`oddfellow-letta-backend-v0206`**, serving page +
> API + PWA on one origin (`/livez` → 200, version 0.20.6). It is ⚠️ **NOT READY** only because
> `LETTA_API_KEY` and `ODDFELLOW_OWNER_TOKEN` are unset (`/healthz` → 503). The "Deploying it"
> section below still describes how to create the service; note that **the service already
> exists under the name `-v0206`**, so the correct next step is to set the two secrets on it,
> not to create a new one.

## Why this exists

The two-service arrangement has a failure mode that already bit us once. The live
backend's allow-list names `oddfellow-synthetic-v020` — the front end with **no**
backend wiring — and rejects `oddfellow-letta-ui-v020`, the one that **has** it.
In a browser that surfaces as `Failed to fetch`, which is indistinguishable from a
dead backend, and it survives fixing the missing secrets.

Serving the page from the backend removes the category of problem rather than
patching an instance of it: **same origin means CORS does not apply at all**, so
there is no origin to configure, and none to get wrong. It also halves what has to
be deployed and kept in sync, and the PWA is installed from the same origin that
serves the API — which is what the phone actually needs.

## What this branch is

`letta/oddfellow-backend-v0.20.4` plus the front end from
`letta/frontend-letta-backend` @ `91b411c`, placed at `oddfellow/frontend/` so it
sits inside the blueprint's `rootDir`. `render.yaml` sets
`ODDFELLOW_FRONTEND_DIR=frontend`.

Nothing is deleted and no live service is touched. The two-service layout still
works: `ALLOWED_ORIGIN` in `render.yaml` now lists **both** front-end origins, so
a separately-hosted page can still call this backend.

## Verified locally, not assumed

Backend run on `127.0.0.1:8099` with `ODDFELLOW_FRONTEND_DIR=frontend`. The
question that matters is whether a static mount at `/` shadows the API — it does
not, because it is mounted last:

```
/                     HTTP 200  text/html; charset=utf-8   <- page
/healthz              HTTP 200  {"ok":true,"checks_failed":[],"version":"0.20.4"}
/manifest.json        HTTP 200  application/json
/sw.js                HTTP 200  text/javascript
/icons/icon-192.png   HTTP 200  image/png      <- 404s on the deployed front end
/api/letta/status     HTTP 401  {"detail":"Invalid or missing owner token."}
/api/letta/agent      HTTP 401  {"detail":"Invalid or missing owner token."}
/nope-does-not-exist  HTTP 404  {"detail":"Not Found"}
```

`/api/*` returns 401, not 404 — the route is reachable and auth is enforced, so the
mount is not swallowing it. `/healthz` is untouched, so a static file can never make
the health check unreachable.

With a deliberately invalid key, `/api/letta/status` returned
`letta_auth: false, agent_found: false` — it did not fake success. That is the
fail-closed behaviour working.

## Deploying it

> **Supply the secrets at creation time, not afterwards.** Verified locally: with
> the secrets absent, `/healthz` returns **HTTP 503** and names what is missing —
> by name only, never by value:
>
> ```
> /healthz -> HTTP 503
> {"ok":false,"checks_failed":["LETTA_API_KEY","ODDFELLOW_OWNER_TOKEN","LETTA_MODEL"],
>  "service":"oddfellow_letta_backend","version":"0.20.4"}
> ```
>
> That is the fail-closed behaviour doing its job — a service that cannot answer a
> single request must not report healthy. But Render's `healthCheckPath` expects
> **200**, so a Blueprint deploy that skips the prompts will be marked unhealthy and
> will not come up. `LETTA_MODEL` is set literally in `render.yaml`, so only the two
> secrets need entering. This is the single most likely way for an otherwise correct
> deploy to fail confusingly.

⚠️ **The service already exists.** The live single-service deploy is
**`oddfellow-letta-backend-v0206`** (`https://oddfellow-letta-backend-v0206.onrender.com`),
not a service to be created. Set `LETTA_API_KEY` and `ODDFELLOW_OWNER_TOKEN` on *that*
service in the Render dashboard (service → Environment → Save); Render restarts on an env
change, so no separate deploy click is needed. Then:

```
curl -s https://oddfellow-letta-backend-v0206.onrender.com/healthz
# {"ok": true, "checks_failed": [], "service": "oddfellow_letta_backend", "version": "0.20.6"}
```

Open `https://oddfellow-letta-backend-v0206.onrender.com/` — that single URL is the page,
the API, and the PWA install target. No origin configuration is involved.

The original create-from-Blueprint path (Render → New → Blueprint → this repo → branch
`letta/combined-single-service-v0.20.4`, supplying both secrets when prompted) is retained
only for reference; **do not run it now**, because `render.yaml` defines a *different*
service name (`oddfellow-letta-backend`) and a Blueprint sync would target the wrong one.
See the warning at the top of `render.yaml`.

## Not decided here

Whether to adopt this over the two-service layout is an architecture decision, and
it is the owner's. Both are prepared; neither is deployed.
