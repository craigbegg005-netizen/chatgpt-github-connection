# The Cloudflare Worker passes Gate 0. One credential would clear Gate A.

**Verified 2026-10-02 00:58 UTC by running it**, not by reading about it.

## What was found

The Cloudflare Worker implementation is **present on canonical and fully working**:
`oddfellow/cloudflare/{worker.js,wrangler.toml,deploy.sh}`. It was built, per its own
README, precisely because *"the Render deploy could not be completed: it needed a
credential held by another operator."* Its README makes a claim worth re-reading:

> **A Worker is a deploy target this agent can drive end to end.**

That claim was never tested in this session. It is correct.

## The evidence

`./deploy.sh verify` starts the Worker locally and runs the **real acceptance harness**
against it. Result, with a **deliberately dummy** `LETTA_API_KEY` in `.dev.vars`
(24 chars; the real key is 107 — compared by value, never printed):

| Gate | Result |
|---|---|
| **Gate 0** | ✅ **ALL PASS** — `/livez` 200 **`ready:true`** `checks_failed:[]`, `/healthz` **`ok:true`**, build current, all OpenAPI routes present, message schema correct |
| **Gate 1** | ❌ fails — and **correctly**: a real `401` from `api.letta.com`, because the key is a dummy. It reports the true error rather than inventing a reply. |
| **Gate 2** | ✅ ALL PASS — front end served, static mount does not shadow `/api`, manifest icons declared and resolving, service worker served |
| **Gate 3** | ✅ ALL PASS — no token → 401, wrong token → 401, no key-shaped string in 50 scanned strings |

**15 of 17 checks pass with a key that cannot work.** The two failures are exactly the
two that require a valid Letta key.

## Why this matters — the comparison that counts

| | Render `oddfellow-letta-backend-v0206` | Cloudflare Worker |
|---|---|---|
| `/livez` | 200 | 200 |
| **`ready`** | **`false`** | **`true`** |
| **`/healthz`** | **503 fail-closed** | **200 `ok:true`** |
| Secrets supplied by | **the owner, typing into a dashboard** | **`deploy.sh`, from the environment** |

`deploy.sh deploy` sets both secrets itself via `wrangler secret put`, taking
`LETTA_API_KEY` and `ODDFELLOW_OWNER_TOKEN` **from the environment**. Both are already
available to this agent. **No human needs to type either value anywhere.**

## The blocker, stated exactly

**One credential: Cloudflare authentication for `wrangler`.** That is a
`CLOUDFLARE_API_TOKEN` (plus the account id). Checked and confirmed absent: no
`CLOUDFLARE*` or `CF_*` environment variable, and the `Cloudflare` MCP server registered
to this agent has an **empty URL and 0 tools** — a placeholder, not a connection.

Everything else is already in place: `node` v22.23.3, `npx`, `workers_dev = true`, the
front end wired in as assets, and the deploy script that sets the secrets and runs the
harness.

## What is NOT claimed

- **Not deployed.** Nothing was published. `verify` runs locally on `127.0.0.1:8799`.
- **Not a substitute for the Render decision.** The Python backend stays canonical; this
  is a second runtime for the same contract.
- **Gate 1 is not proven end-to-end.** A dummy key was used by design. With a real key
  the expectation is 17/17, but that is an expectation, not an observation.
- **The phone still has to be tested by the owner.**

## If the owner supplies a Cloudflare API token

```
cd oddfellow/cloudflare
CLOUDFLARE_API_TOKEN=... LETTA_API_KEY=... ODDFELLOW_OWNER_TOKEN=... ./deploy.sh deploy
```

That one command deploys, sets both secrets, waits for the new revision, and runs the
acceptance harness against the live URL — then reports the raw results.

**This is the shortest path to a genuinely authenticated Oddfellow that currently
exists, and it does not require anyone to handle the two secret values by hand.**
