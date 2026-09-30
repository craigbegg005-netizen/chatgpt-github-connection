# Oddfellow backend on Cloudflare Workers

**The same API as `../oddfellow_letta_backend.py`, on a second runtime.**

## Why this exists

The Python backend is canonical and stays canonical. This was built because the
Render deploy could not be completed: it needed a credential held by another
operator, and every deploy attempt failed for a reason that had nothing to do
with the code (see `../HANDOFF-2026-09-30-0242Z.md` §6). A Worker is a deploy
target this agent can drive end to end.

It is **not** a new product and **not** a fork of the contract. Every route,
status code, and response shape is the one the Python backend serves, and the
**same acceptance harness** (`../acceptance_check.py`) verifies both.

## What it fixes, beyond the credential

- **No cold start.** A Worker answers immediately; the free Render tier sleeps.
- **No health check that can fail a deploy.** Render treats a non-200
  `healthCheckPath` as a failed deploy, so a missing secret used to read as a
  build failure. `/livez` is always 200 here too, so the same protection applies.
- **One origin.** The front end is served from the same Worker, so page, API and
  PWA share an origin and CORS does not apply at all.

## Deploying

One command does the deploy, sets both secrets, waits for the new revision, and
runs the acceptance harness against the live URL:

```bash
cd oddfellow/cloudflare
LETTA_API_KEY=... ODDFELLOW_OWNER_TOKEN=... ./deploy.sh deploy
```

Secrets are read from the environment and piped to `wrangler secret put` over
stdin, so they never appear in argv, shell history, or a process listing.

The individual steps, if you would rather run them yourself:

```bash
npx wrangler deploy
npx wrangler secret put LETTA_API_KEY
npx wrangler secret put ODDFELLOW_OWNER_TOKEN
```

`LETTA_MODEL`, `ODDFELLOW_AGENT_ID`, `ODDFELLOW_RATE_PER_MIN` and
`ALLOWED_ORIGIN` are non-secret and already set in `wrangler.toml`.

The secrets can be set before or after the first deploy — nothing fails closed at
deploy time, so the order does not matter.

## Verifying

```bash
python ../acceptance_check.py https://<worker-url> --owner-token "$ODDFELLOW_OWNER_TOKEN"
```

Local, with no Cloudflare account at all — this starts the Worker, waits for it,
runs the harness, and cleans up after itself:

```bash
printf 'LETTA_API_KEY=...\nODDFELLOW_OWNER_TOKEN=...\n' > .dev.vars   # gitignored
./deploy.sh verify
```

Gate 1 needs a **working** Letta key. With a placeholder in `.dev.vars`, gate 1
is expected to fail — and it must fail by reporting the real 401 from
`api.letta.com`, never by inventing a reply. Gates 0, 2 and 3 must all pass.

## Status of this component

| | |
|---|---|
| 🛠 IMPLEMENTED | `worker.js` |
| ✅ VERIFIED with a real key | **2026-09-30 04:04 UTC — every gate passed, including gate 1, with a real Letta reply.** Run locally via `./deploy.sh verify` against a real `LETTA_API_KEY`. `/api/letta/status` returned `runtime: cloudflare-worker`, `letta_auth: true`, `agent_found: true`, `agent_name: "Oddfellow"`. A real reply came back in 3.0 s: *"I'm Oddfellow, and I confirm the zero-spend rule: no paid service, subscription, or billing without your explicit authorization."* History held both turns, `new-session` produced a distinct empty conversation, and gate 3 scanned 41 strings with no key-shaped value. The earlier "never served a real Letta reply" caveat is now closed. |
| ⏳ PENDING | **Not deployed.** Needs a Cloudflare account connection. Everything above is local. |
| ⚠️ NOT VERIFIED | Never served a request from the public internet, and never run with the owner's own Letta key (the sandbox key was used). |

## The one behavioural difference, stated plainly

**The rate limiter is per-isolate.** A Worker runs many isolates across many
colos, so the limit is approximate rather than global: it stops a runaway client
hitting one isolate, not a distributed one. The Python backend's limiter is exact
because it is a single process. For a single-owner backend behind a secret token
this is an acceptable trade — but it is a real difference and is written down
rather than glossed over.

Two smaller differences, both deliberate:

- **The Command Center is deliberately absent, and must not be ported here as-is.**
  It holds approvals and the pause flag in memory. Because state is per-isolate
  (see above), an approval created on one isolate would be invisible on another,
  and the pause switch would stop a fraction of requests while *appearing* to work.
  An emergency stop that stops some traffic is worse than one that is absent,
  because it is trusted. The Command Center therefore requires a single-instance
  host. This Worker remains a fallback for the **API contract**, not for the owner
  console — and if it ever needs the console, the state has to move to durable
  storage first. The route-parity test lists these paths as a dated exclusion for
  the same reason.
- The Worker **never creates an agent**. `ODDFELLOW_AGENT_ID` is required; if it
  is unset the Worker returns 503 rather than searching or creating. Agent
  creation stays in the Python backend, where the free-plan limit handling lives.
- The Worker resolves the agent **by id only**. `POST /v1/agents/search` and
  `GET /v1/agents/{id}` return disjoint sets (verified 2026-09-30), so search
  cannot be used to decide whether the pinned agent exists.
