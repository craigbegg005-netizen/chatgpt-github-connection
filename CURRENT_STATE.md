# CURRENT_STATE

**Date:** 2026-10-01 19:50 UTC
**Author:** Oddfellow (Letta agent, `agent-a9a8eb2c-2fed-4554-9998-aa4783c7efc4`)
**Rule:** every line below is either evidenced in this repository or marked unverified. Nothing here is carried over from a handoff on trust.

## Status vocabulary

`✅ VERIFIED` > `🟢 LIVE` > `🚀 DEPLOYED` > `🔗 CONNECTED` > `🧪 TESTED` > `🛠 IMPLEMENTED` > `⏳ PENDING` > `⚠️ BLOCKED / UNVERIFIED`

---

## Where this file lives, and why that matters

This document is meant to be the first thing a fresh AI reads. Until 2026-10-01 19:16 UTC it existed **only** on `letta/continuity-2026-09-30` — a branch **72 commits behind** the deploy branch that contains none of the v0.20.5/v0.20.6 work. A fresh AI reading the canonical branch could not see it at all.

It is now on the canonical branch. **If you are reading this on another branch, go read the canonical branch first.** Earlier revisions remain in git history on `letta/continuity-2026-09-30`; they are superseded, not deleted.

## Branch map (verified 2026-10-01 19:16 UTC)

| Branch | Head | Role |
|---|---|---|
| `letta/combined-single-service-v0.20.4` | `cff1f7c` | **Canonical.** Deploy branch. Single origin: page + API + PWA. |
| `main` | `8ddfe32` | Default branch. **Index only** — no `oddfellow/` directory, so a service pointed here cannot satisfy `rootDir: oddfellow` and its build fails with no obvious cause. |
| `letta/continuity-2026-09-30` | `a01e96e` | Where this file used to live. 72 commits behind canonical. |

⚠️ The canonical branch is **named** `v0.20.4` but the code reports **`0.20.6`**. Report both; never assume equivalence.

---

# ✅ LATEST CYCLE — 2026-10-01 19:50 UTC

**This supersedes every contradicting line below it.**

## The redeploy landed — verified by artifact, not by identifier

ChatGPT deployed the canonical branch to `oddfellow-letta-backend-v0206` at ~19:40 UTC. I did not accept that from the deployment identifier. `b253905` is the oldest of the 14 commits that were missing from the previously-running `11b3901`, and it adds `command.html`:

```
GET /command.html                   -> 200, 9610 B   (absent from 11b3901)
GET /definitely-not-a-real-path-xyz -> 404           (control: the 200 is not a catch-all)
```

**So the running code is newer than `11b3901`: the 14-commit drift is closed.** I cannot prove from outside that it is exactly `1760892` — every commit between them changes only files the service does not serve — so treat that as consistent-with-evidence, not verified.

## The phone path is already complete

Single origin, and every PWA prerequisite answers:

| Path | Result |
|---|---|
| `/` | 200, 29,513 B, `<title>Oddfellow Synthetic v0.20</title>` |
| `/manifest.json` | 200, 672 B, `start_url: "/"`, `display: standalone` |
| `/sw.js` | 200, 1,963 B — **the fixed version** (refuses `/api/`, refuses `X-Owner-Token`, refuses non-GET) |
| `/icons/icon-192.png`, `icon-512.png`, `apple-touch-icon.png` | 200, correct `image/png` |

**The phone URL is the service URL: `https://oddfellow-letta-backend-v0206.onrender.com`.** No separate front-end service, so no CORS configuration can be wrong.

⚠️ **Cold start:** the first request after an idle period timed out at 30 s; warm requests answer in 0.15 s. The owner's first phone load may appear to hang. That is Render free-tier cold start, not a failure.

The service-worker vulnerability documented in `oddfellow/SECURITY-2026-09-30.md` is **no longer what is deployed** — that finding can be closed for this service.

## The critical path moved, and the cause was a wrong service name

For roughly twenty hours this document recorded `oddfellow-letta-backend` as returning no HTTP response, and inferred *"service exists, no healthy instance."* **That service is indeed dead** — re-probed 19:14 UTC, `/livez` → `000`. But it was never the only deploy target, and the inference was applied to the whole deployment.

A cross-AI handoff (ChatGPT, 2026-10-01 19:02 UTC) named a service this repository's `render.yaml` does **not** define: **`oddfellow-letta-backend-v0206`**. Probed directly at 19:14 UTC:

```
GET https://oddfellow-letta-backend-v0206.onrender.com/livez
→ 200 {"live":true,"ready":false,
       "checks_failed":["LETTA_API_KEY","ODDFELLOW_OWNER_TOKEN"],
       "service":"oddfellow_letta_backend","version":"0.20.6"}
```

**The application builds, starts, and serves at v0.20.6.** It is fail-closed on two missing environment variables. The twenty-hour conclusion was correct about the service it named and wrong about the deployment as a whole.

| Service | `/livez` | Reading |
|---|---|---|
| `oddfellow-letta-backend-v0206` | **200** | 🛠 **RUNNING**, ⚠️ **NOT READY** — `checks_failed: LETTA_API_KEY, ODDFELLOW_OWNER_TOKEN`; v0.20.6 |
| `oddfellow-letta-backend` | `000` | 🔴 no HTTP response (the old target; still dead) |
| `oddfellow-letta-poc` | `404` | 🟢 LIVE, v0.20.2 (no `/livez` route), still unconfigured |
| `oddfellow-letta-ui-v020` | `404` | 🟢 LIVE static site (no `/livez` route) |
| `oddfellow-letta-ui-v020-pwa` | `404` | 🟢 LIVE static site (no `/livez` route) |

Note the handoff labelled `-v0206` "🟢 LIVE". **`/livez` → 200 with `ready:false` is not ready.** It is running and refusing to serve authenticated traffic, which is the correct fail-closed behaviour.

## The single owner action

Render → **`oddfellow-letta-backend-v0206`** → Environment → set `LETTA_API_KEY` and `ODDFELLOW_OWNER_TOKEN` → Save. Render restarts the service on an env change, so this step needs no separate deploy click.

⚠️ **Token-matching risk:** the value typed must equal the vault `ODDFELLOW_OWNER_TOKEN`, or phone access fails with a clean `401` after everything else works.

## Second, smaller action: 14 commits of drift

The running commit is `11b3901`, verified to be a real ancestor of the canonical branch and **14 commits behind** `cff1f7c`. The drift is documentation, the Command Center diagnosis correction, and Command Center code fixes — **not** security-critical: the service-worker fix (`c468757`) **is** present at `11b3901`, verified with `git merge-base --is-ancestor`. After the secrets are in, "Deploy latest commit" brings it current.

## Corrections to claims in this file's own history

- **"Ruled out: the secrets were not saved on the wrong service."** That conclusion was reached by testing only the services then known. It is **not established**. The new service's own fail-closed check names both secrets as missing, which is consistent with the secrets having been saved on a *different* service. The question is open, and it is answered by the Render dashboard, not by probing.
- **"The 502 is noise / the service exists with no healthy instance."** True of `oddfellow-letta-backend`. It was over-generalised to the entire deployment.
- **"A 502 is not a credential problem: the app starts with both secrets empty, so the fault is in the build or start."** Withdrawn — see `oddfellow/CORRECTION-502-CAUSE-2026-09-30.md`. The app starts *with* both secrets empty and reports exactly that; the fault was never in the build.

## Read these for detail

- `oddfellow/HANDOFF-TO-CHATGPT-2026-10-01-1950Z.md` — **newest handoff** (`[TO-CHATGPT]` convention)
- `oddfellow/HANDOFF-2026-10-01-1916Z.md` — the 19:16 UTC handoff
- `RESOURCES.md` — resource registry, re-verified 2026-10-01 04:05 UTC
- `oddfellow/CORRECTION-502-CAUSE-2026-09-30.md` — the 502 cause
- `oddfellow/SECURITY-2026-09-30.md` — service-worker finding (deployed but latent)
- `IP-CLEARANCE-SEARCH-2026-09-30.md`, `IP-INVENTORY.md` — name is crowded; register clear in Classes 9/42
- `oddfellow/CORRELATION-2026-09-30.md` — what each AI did, chronologically
- `GRANTS-NON-DILUTIVE-PIPELINE-2026-10-01.md` — grants / non-dilutive lane (leads, not findings)
