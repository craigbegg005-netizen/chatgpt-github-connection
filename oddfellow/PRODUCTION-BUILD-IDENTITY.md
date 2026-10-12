# Which build is production actually running? — bounded by evidence, 2026-10-12

**Question.** `oddfellow-letta-backend-v0206` serves Oddfellow. No handoff has been able to
say which commit it runs; the recorded production SHA is `70c02b3c` from the master handoff.
"Which build is live?" has been called the most expensive question in this project, and the
service exposes no build endpoint (`/version`, `/build`, `/api/version`, `/api/build` -> 404).

**Answer established here.** Production is **no newer than 2026-10-05 08:07:56 UTC**. That is a
bound derived from two independent bisections against live behaviour, not from any handoff.

## Method

The deployed code cannot be read, but its *response shape* can. Two features were added to
canonical at known commits; production lacks both. The later of the two is an upper bound.

| Evidence | Live production | Added in | Date |
|---|---|---|---|
| `build` key in `/livez` | **absent** | `5d500e4` | 2026-10-05 08:07:56 |
| `/api/command/departments` | **absent** (12 routes, not 16) | `d2b2ebb` | 2026-10-05 20:31:28 |

```
GET https://oddfellow-letta-backend-v0206.onrender.com/livez
{"live":true,"ready":false,"checks_failed":["LETTA_API_KEY","ODDFELLOW_OWNER_TOKEN"],
 "service":"oddfellow_letta_backend","version":"0.20.6"}
                                             ^ no "build" key
```

Production serves **12** routes; canonical `HEAD` serves **16**. The four missing:
`/api/command/departments`, `/api/command/jobs`, `/api/command/workers`,
`/api/command/workers/{worker_id}`.

`build` is added by `BUILD_COMMIT = os.environ.get("RENDER_GIT_COMMIT")`, and the endpoint's own
comment says `None` "means the platform did not tell us — reported honestly rather than inferred".
Production does not report the key *at all*, which is older code, not a `None` value.

## What this does and does not establish

**Does:** production predates 2026-10-05 08:07:56 UTC. Any claim that production runs code newer
than that is contradicted by live evidence.

**Does:** the handoff's `70c02b3c` (2026-10-01 23:15:56 UTC) is *consistent* with live evidence —
it predates both commits, and `BUILD_COMMIT` occurs **0** times in the file at that revision.

**Does not:** uniquely identify the deployed commit. Every commit before `5d500e4` lacks the
`build` key, so the bisection bounds production without pinpointing it. The bound is real; the
exact SHA remains unverified.

## Why it stays unverifiable

The only way to close this is for the deployed code to report its own commit. That requires a
deploy — which is an owner-authorized Render action (`Auto-deploy OFF`, production NO-GO), and
must not be done to satisfy curiosity. The `build` field makes the question answerable *the next
time a deploy happens for an approved reason*; it does not justify one.

## Reproduce

```sh
curl -s https://oddfellow-letta-backend-v0206.onrender.com/livez          # no "build" key
curl -s https://oddfellow-letta-backend-v0206.onrender.com/openapi.json | \
  python3 -c "import json,sys; print(len(json.load(sys.stdin)['paths']))"  # 12
git log -S'BUILD_COMMIT' -- oddfellow/oddfellow_letta_backend.py           # 5d500e4
```
