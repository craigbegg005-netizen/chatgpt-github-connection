# First end-to-end acceptance pass — 2026-09-30 03:17–03:21 UTC

**Status: 🧪 TESTED — the full chain works. ⚠️ NOT a deployment.**

## What ran

The v0.20.5 backend (`oddfellow_letta_backend.py` @ `d68988d`) was run inside the
agent sandbox with the front end mounted, and published through a Cloudflare
quick tunnel (`trycloudflare.com`, no account) so it could be reached from a
phone. The sandbox's own Letta key was used — **the key never left the sandbox**;
the tunnel only exposes the HTTP port.

## Result — every gate passed

```
GATE 0  livez / healthz / openapi version / routes / MessageIn schema      all PASS
GATE 1  auth + agent resolved / real reply / new session / history / agent all PASS
GATE 2  page served / mount does not shadow /api / 3 icons resolve / sw.js all PASS
GATE 3  no token 401 / wrong token 401 / no key-shaped string              all PASS
RESULT: all checks passed
```

The reply was real, not simulated:

> "I'm Oddfellow — and yes, the zero-spend rule holds: no paid service,
> subscription, or billing without your explicit authorization."

and, from the browser:

> "I'm Oddfellow — Craig's persistent Letta-based agent for Begg AI Industries,
> holding continuity across sessions — and my spend ceiling is zero: free tiers
> only, no paid service or billing without your explicit approval."
> `letta · conv-be3a4d7c-bca6-44af-ab8f-8eba5a2ee1bd · 92 tok`

Evidence: [`evidence/live-acceptance-2026-09-30.png`](evidence/live-acceptance-2026-09-30.png)

## PWA installability — checked as the browser sees it, not inferred

Gate 2 previously only proved the files *return 200*. That is weaker than
"installable". Read back from the live page:

```
service worker   registered: true   active: true   state: "activated"
manifest         name ✓  start_url "/" ✓  scope "/" ✓  display "standalone" ✓
icons            192x192 ✓   512x512 ✓   maskable ✓
```

Every criterion Chrome checks for installability is met.

## Re-running it

```bash
LETTA_API_KEY=... ODDFELLOW_OWNER_TOKEN=... ./rehearsal.sh up
./rehearsal.sh status     # is it up, and what does the harness say
./rehearsal.sh down
```

`status` validates candidate URLs against a live `/livez` rather than trusting a
log line, because a quick-tunnel URL is unrecoverable any other way and an old
log holds a URL that is now dead.

## Why this is a rehearsal and not a deployment

1. **It is not persistent.** The tunnel and the backend run inside an ephemeral
   sandbox. When the sandbox stops, the URL dies. A real deployment is the
   Cloudflare Worker (`cloudflare/`) or Render — both still need a credential.
2. **It uses the sandbox's Letta key**, which is platform-managed and cannot be
   rotated by the owner. Fine for a rehearsal; wrong for a product.
3. **Traffic passes through Cloudflare's tunnel edge**, which terminates TLS.

## What it does prove

- The v0.20.5 backend authenticates, resolves the pinned Oddfellow agent, creates
  and reuses conversations, and returns real replies.
- The front end, the API and the PWA work from one origin with no CORS at all.
- The owner token, the fail-closed paths, and the leak scan all behave.
- **The stack is correct.** The only thing missing is a permanent home for it.
