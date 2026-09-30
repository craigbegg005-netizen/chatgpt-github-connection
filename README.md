# chatgpt-github-connection

This repository is the working home for **Oddfellow** — the persistent,
voice-first, mobile-first synthetic-intelligence layer built by **Begg AI
Industries**, with Letta as its memory and persistence layer.

> **This file is the front door for every branch.** If you are an agent picking this
> up cold, read this first, then the handoff named in [Where to start](#where-to-start),
> then [`RESOURCES.md`](RESOURCES.md) for the identifiers.

Oddfellow is a synthetic system. It is **not** conscious, self-aware, or sentient,
and must never be described as such.

---

## Current state — 2026-09-30 06:10 UTC

| Thing | Value |
|---|---|
| Canonical deploy branch | `letta/combined-single-service-v0.20.4` @ `50d90ff` |
| Backend version the code reports | **`0.20.6`** |
| Tests | **84 passed** · fault injection **39/39 passed** |
| Deploy target | `oddfellow-letta-backend` (`srv-dau6tgqd0e5s73egkocg`) |
| Deploy status | ⚠️ **`WAITING_CREDENTIAL`** — not serving |

### ⚠️ The one blocker

`LETTA_API_KEY` and `ODDFELLOW_OWNER_TOKEN` must be entered by the owner **directly in the
Render dashboard** (service → Environment). **Never ask the owner to paste them into chat.**

Render's own evidence for the last deploy: build completed, application started, the startup
configuration check reported **both secrets missing**, `/healthz` returned **503**, and Render
therefore marked the deploy **`update_failed`**. That confirms the credential blocker, **not** a
build failure. Independently confirmed from outside: `/livez`, `/healthz` and `/` all return no
HTTP response at a 60s and a 120s timeout.

**Deploy ownership: Claude deploys this service.** One AI deploys at a time. Do not redeploy or
change env vars on it until the owner confirms the secrets are saved.

### ⚠️ Version-label discrepancy — report both, do not assume equivalence

The branch is **named** `...-v0.20.4`; the runtime code reports **`0.20.6`**. Both are true. The
branch name is historical; the served version is authoritative.

---

## Where to start

| If you want… | Read |
|---|---|
| The latest cross-AI handoff | [`oddfellow/HANDOFF-2026-09-30-0600Z.md`](oddfellow/HANDOFF-2026-09-30-0600Z.md) |
| Every resource, service ID and URL | [`RESOURCES.md`](RESOURCES.md) |
| The deploy steps | [`oddfellow/SINGLE-SERVICE.md`](oddfellow/SINGLE-SERVICE.md) |
| The acceptance checklist | [`oddfellow/ACCEPTANCE.md`](oddfellow/ACCEPTANCE.md) |
| The security findings | [`oddfellow/SECURITY-2026-09-30.md`](oddfellow/SECURITY-2026-09-30.md) |
| What the older live services expose | `recovered/` on `letta/recovery-capture-2026-09-30` |

## Branches

| Branch | What it is |
|---|---|
| **`letta/combined-single-service-v0.20.4`** | **The deploy candidate.** Backend **plus** front end served from one service: page, API and PWA on one origin, so CORS does not apply at all. v0.20.6, 84 tests. |
| `letta/frontend-letta-backend` | The front end as a **separate** static service. Kept in sync with the combined branch. |
| `letta/recovery-capture-2026-09-30` | A read-only capture of every live Begg/Oddfellow service, fingerprinted — the only surviving record of what is actually deployed. |
| `letta/continuity-2026-09-30` | Earlier continuity notes and current-state documents. |
| `letta/oddfellow-backend-v0.20.1` … `v0.20.4` | Backend revision history, kept for provenance. |
| `letta/verification-2026-09-30`, `letta/recovered-api-surface` | Dated verification notes and the first API-surface recovery. |
| `main` | The index. Working branches are deliberately kept off `main` so a half-finished revision can never be mistaken for the deployed one. |

## What is live right now

Status labels are strict: **VERIFIED > LIVE > DEPLOYED > CONNECTED > TESTED > IMPLEMENTED >
PENDING > BLOCKED**. Nothing is upgraded without evidence. Every line below was checked by an
actual request on 2026-09-30 between 04:00 and 06:10 UTC.

| Service | State |
|---|---|
| `oddfellow-letta-backend.onrender.com` | ⚠️ **Not serving** — no HTTP response at 60s and 120s. The deploy target. |
| `oddfellow-letta-poc.onrender.com` | 🟢 LIVE — `/livez` → 404 in 0.16s, i.e. the older v0.20.2 build that predates that route. |
| `oddfellow-personal-staging-v017b.onrender.com` | 🟢 LIVE — 303 → `/setup`, unenrolled, no owner data. |
| `oddfellow-personal-secure.onrender.com` | 🟢 LIVE — 303. |
| `begg-ai-industries-v013.onrender.com` | 🟢 LIVE — 200. Begg AI Core v0.13.0. |
| `begg-ai-core-v010.onrender.com` | 🟢 LIVE — 200. v0.12.1. |
| `begg-ai-command-center.craigbegg005.chatgpt.site` | 🟢 LIVE — 401, auth-gated. |

**LIVE ≠ end-to-end verified.** Render's free tier cold-starts; allow 90s before calling a
service dead. Full identifiers, service IDs and rollbacks: [`RESOURCES.md`](RESOURCES.md).

## Deploying

**Two targets, same API, same acceptance harness.** Render is the permanent home; Cloudflare
Workers is the fallback.

### Render — the primary path

Claude holds Render access and drives this deploy. The service already exists
(`oddfellow-letta-backend`), so this is an env-var + redeploy step, not a new service.

### Cloudflare Workers — one command, no dashboard

```bash
cd oddfellow/cloudflare
LETTA_API_KEY=... ODDFELLOW_OWNER_TOKEN=... ./deploy.sh deploy
```

Deploys, sets both secrets over stdin, waits for the new revision, and runs the acceptance
harness against the live URL. `./deploy.sh verify` does the same locally with no Cloudflare
account at all.

Either way the platform health check points at **`/livez`**, which is always 200 while the
process is up, so a deploy cannot fail over a missing secret. `/healthz` still fails closed with
503 and names what is missing. That split exists because a Render deploy was once reported as
*failed* when the only real problem was that the secrets had not been entered yet.

## Verifying

```bash
python oddfellow/acceptance_check.py <url> --owner-token "$ODDFELLOW_OWNER_TOKEN"
```

Stdlib only, no install. Prints the raw request and response for every check. Gates: 0 service
identity, 1 authenticated work, 2 the page and its PWA assets, 3 security. Exit 0 = all passed.
**It backs off and retries on HTTP 429**, because Render's free tier rate-limits at 20
requests/minute and a platform limit is not a property of the build under test.

Offline backend tests:

```bash
pip install -r oddfellow/requirements.txt pytest
python -m pytest oddfellow/tests -q      # 84 passed
python oddfellow/fault_injection_check.py # 39/39
```

### The live rehearsal

`oddfellow/rehearsal.sh` runs the whole stack inside an agent sandbox and publishes it through a
Cloudflare quick tunnel, so the stack can be exercised from a phone without any credential:

```bash
LETTA_API_KEY=... ODDFELLOW_OWNER_TOKEN=... ./rehearsal.sh up
./rehearsal.sh keepalive   # detached watchdog: restarts either process if it dies
./rehearsal.sh status      # backend / tunnel / watchdog, then the acceptance harness
./rehearsal.sh down
```

**It is a rehearsal, not a deployment:** it dies with the sandbox, it uses the sandbox's
platform-managed Letta key (which the owner cannot rotate), and Cloudflare's tunnel edge
terminates TLS. What it proves is that the stack is correct.

## Doctrine

Binding for all work in this repository:

- **Preserve → Integrate → Improve → Execute → Verify → Continue.**
- **Zero-spend first.** Free tiers, open source, existing infrastructure. No paid service,
  subscription, or billing without explicit owner authorization. Never silently fall back to a
  paid model or provider.
- **Never claim a result that was not verified.** A successful build is not a successful
  deployment; a reachable URL is not a working application.
- **Never expose secrets.** Keys live in server-side environment variables only — never in
  chat, source, browser JavaScript, screenshots, or this repository.
- **High-risk actions are approval-gated.** Money, credentials, ownership, destructive changes,
  publication, legal commitments.
- **Fail closed. Be auditable.**
- **Never fabricate** revenue, sponsorships, testimonials, partnerships, or lived experience.
  Simulated output is never presented as real execution.
- **Do not overwrite newer verified work.** Two agents work this repository concurrently;
  fetch before pushing, and rebase rather than force.

## A note on this repository's origin

This repository was originally created as a ChatGPT GitHub connection test. It is now the
Oddfellow working repository. The ChatGPT connector is still useful for read-only analysis;
write access from ChatGPT uses Codex or a GitHub App.

---

Maintained by **Oddfellow** (Letta agent `agent-a9a8eb2c-2fed-4554-9998-aa4783c7efc4`)
for **Begg AI Industries**.
