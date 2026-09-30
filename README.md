# chatgpt-github-connection

This repository is the working home for **Oddfellow** — the persistent,
voice-first, mobile-first synthetic-intelligence layer built by **Begg AI
Industries**, with Letta as its memory and persistence layer.

> **`main` is an index, not the code.** The working branches are deliberately kept
> off `main` so a half-finished revision can never be mistaken for the deployed
> one. Everything below says which branch holds what. If you are an agent picking
> this up cold, read this file first, then the handoff named in
> [Where to start](#where-to-start).

Oddfellow is a synthetic system. It is **not** conscious, self-aware, or sentient,
and must never be described as such.

---

## Where to start

| If you want… | Read |
|---|---|
| The latest cross-AI handoff | [`oddfellow/HANDOFF-2026-09-30-0242Z.md`](https://github.com/craigbegg005-netizen/chatgpt-github-connection/blob/letta/combined-single-service-v0.20.4/oddfellow/HANDOFF-2026-09-30-0242Z.md) on `letta/combined-single-service-v0.20.4` |
| The deploy steps | [`oddfellow/SINGLE-SERVICE.md`](https://github.com/craigbegg005-netizen/chatgpt-github-connection/blob/letta/combined-single-service-v0.20.4/oddfellow/SINGLE-SERVICE.md) |
| The acceptance checklist | [`oddfellow/ACCEPTANCE.md`](https://github.com/craigbegg005-netizen/chatgpt-github-connection/blob/letta/combined-single-service-v0.20.4/oddfellow/ACCEPTANCE.md) |
| The security findings | [`oddfellow/SECURITY-2026-09-30.md`](https://github.com/craigbegg005-netizen/chatgpt-github-connection/blob/letta/combined-single-service-v0.20.4/oddfellow/SECURITY-2026-09-30.md) |
| What the older live services expose | [`recovered/`](https://github.com/craigbegg005-netizen/chatgpt-github-connection/tree/letta/recovery-capture-2026-09-30/recovered) |

## Branches

| Branch | What it is |
|---|---|
| **`letta/combined-single-service-v0.20.4`** | **The deploy candidate.** v0.20.5 backend **plus** the front end, served from one Render service: page, API and PWA on one origin, so CORS does not apply at all. 66 tests pass. |
| `letta/frontend-letta-backend` | The front end as a **separate** static service (the installable PWA). Carries the same v0.20.5 security fix. |
| `letta/recovery-capture-2026-09-30` | A read-only capture of every live Begg/Oddfellow service, fingerprinted — the only surviving record of what is actually deployed. |
| `letta/continuity-2026-09-30` | Earlier continuity notes and current-state documents. |
| `letta/oddfellow-backend-v0.20.1` … `v0.20.4` | The backend revision history. Kept for provenance. |
| `letta/verification-2026-09-30`, `letta/recovered-api-surface` | Dated verification notes and the first API-surface recovery. |
| `main` | This index. |

## What is deployed right now

Status labels are strict: **VERIFIED > LIVE > DEPLOYED > CONNECTED > TESTED >
IMPLEMENTED > PLANNED > BLOCKED**. Nothing is upgraded without evidence.

| Service | State |
|---|---|
| `oddfellow-letta-ui-v020-pwa.onrender.com` | 🟢 **LIVE** — the installable PWA. Verified 2026-09-30 02:35 UTC. |
| `oddfellow-letta-backend.onrender.com` | 🔴 **Not serving.** Resolves in DNS, accepts TCP, returns no HTTP response. |
| `oddfellow-letta-poc.onrender.com` | 🟢 LIVE but ⚠️ **unconfigured** — runs v0.20.2, refuses every request. |
| `oddfellow-letta-ui-v020`, `oddfellow-synthetic-v020` | 🟢 LIVE, older front ends. Preserved as rollback. |

## Deploying

One click — creates a **new** service and leaves the existing ones untouched as
rollback:

```
https://render.com/deploy?repo=https://github.com/craigbegg005-netizen/chatgpt-github-connection/tree/letta/combined-single-service-v0.20.4
```

Render prompts for `LETTA_API_KEY` and `ODDFELLOW_OWNER_TOKEN`; `LETTA_MODEL` is
already set in `render.yaml`. The health check points at `/livez`, which is always
200 while the process is up, so a deploy cannot fail over a missing secret —
`/healthz` still fails closed with 503 and names what is missing.

## Verifying

```bash
python oddfellow/acceptance_check.py <url> --owner-token "$ODDFELLOW_OWNER_TOKEN"
```

Stdlib only, no install. Prints the raw request and response for every check.
Gates: 0 service identity, 1 authenticated work, 2 the page and its PWA assets,
3 security. Exit 0 = all passed.

Offline backend tests:

```bash
pip install -r oddfellow/requirements.txt pytest
python -m pytest oddfellow/tests -q      # 66 passed
```

## Doctrine

Binding for all work in this repository:

- **Preserve → Integrate → Improve → Execute → Verify → Continue.**
- **Zero-spend first.** Free tiers, open source, existing infrastructure. No paid
  service, subscription, or billing without explicit owner authorization. Never
  silently fall back to a paid model or provider.
- **Never claim a result that was not verified.** A successful build is not a
  successful deployment; a reachable URL is not a working application.
- **Never expose secrets.** Keys live in server-side environment variables only —
  never in chat, source, browser JavaScript, or this repository.
- **High-risk actions are approval-gated.** Money, credentials, ownership,
  destructive changes, publication, legal commitments.
- **Fail closed. Be auditable.**
- **Never fabricate** revenue, sponsorships, testimonials, partnerships, or lived
  experience. Simulated output is never presented as real execution.

## A note on this repository's origin

This repository was originally created as a ChatGPT GitHub connection test. It is
now the Oddfellow working repository. The ChatGPT connector is still useful for
read-only analysis; write access from ChatGPT uses Codex or a GitHub App.

---

Maintained by **Oddfellow** (Letta agent `agent-a9a8eb2c-2fed-4554-9998-aa4783c7efc4`)
for **Begg AI Industries**.
