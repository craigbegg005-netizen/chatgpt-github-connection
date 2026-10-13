# Release readiness — 2026-10-13

**Purpose.** Priority 1 of the 2026-10-12 master handoff asks for a deployment plan gated on
evidence. This file records what is actually verified at exact head, what is not, and the two
defects found while checking. **No deploy. Nothing here authorizes one.**

**Exact head when written:** `0c9a992667c53f96db3eb2939e8fc7a55aae821b`
**Deployed commit:** `70c02b3cc9452b10ac49502ccd389d5137c7ab59`
**Gap:** 254 ahead, 0 behind — re-derived, matching the handoff's snapshot.

---

## Verified at exact head

| Item | Evidence |
|---|---|
| Suite | **727 passed, 0 failed, 0 skipped** at `0c9a992`, run from the repo root |
| Count guard | Binds and passes — prose `727` == constant == collected. A scoped run reports `3 passed, 1 skipped`, which is the documented trap, not a pass |
| Approval persistence | `test_section29_release_gate.py` — **21 passed**, and it uses real `subprocess` restarts (`test_29_an_approved_approval_survives_a_real_restart`), not mocks. Producer and verifier are separate identities |
| Health route exists | `/livez` is a real route (`oddfellow_letta_backend.py:993`) |
| Preserved API surfaces | All three `recovered/` captures hash-identical to live (independently re-verified 2026-10-13) |
| Workforce registry | 12 departments · 28 workers · 3 verifiers · max authority A2 · spend ceiling $0.00 · no permitted external provider |
| Gate A | `/livez` → 200, `ready:false`, `checks_failed:[LETTA_API_KEY, ODDFELLOW_OWNER_TOKEN]`, v0.20.6 |

## Two defects found

### 1. The live service is not governed by `render.yaml`, so it has no health check

`render.yaml` declares `healthCheckPath: /livez` and `autoDeploy: false` — but it defines a
service named **`oddfellow-letta-backend`**, while production is
**`oddfellow-letta-backend-v0206`**. The blueprint does not describe the service that is running.

So the handoff's observation that the live health-check path is **empty** is not a
misconfiguration to fix in the repo — the repo is already correct. **The blueprint is simply not
applied to that service.** Two consequences:

- Render has no health check on production, so a deploy that starts but never becomes ready is
  not detected by the platform.
- Any future edit to `render.yaml` will not affect production. Editing it and expecting a change
  would be a silent no-op — the same shape as the pointer that was "advanced" by a replace that
  matched nothing.

**Owner action:** set the health-check path to `/livez` on the service itself, in the dashboard.
The route already exists and answers 200 whenever the process is up.

### 2. Dependencies are unpinned, so builds are not reproducible

`oddfellow/requirements.txt` declares four dependencies, all with open lower bounds:

```
fastapi>=0.115   uvicorn[standard]>=0.30   httpx>=0.27   pydantic>=2
```

The installed set at head is `fastapi 0.143.0`, `uvicorn 0.54.0`, `httpx 0.28.1`,
`pydantic 2.14.1`, `starlette 1.7.0`. Those are far newer than the floors, so the resolved set
is whatever pip chose on the day the image was built.

With `autoDeploy: false` the deployed artifact is frozen, which is why nothing has broken. But
**any future deploy resolves fresh versions**, so the same commit can produce a different
runtime. A deploy that fails would then be unattributable between "the code changed" and "a
dependency changed underneath it" — which is exactly the two-variables-at-once problem the
deploy-hold decision already exists to avoid.

**Not fixed here**, deliberately: pinning is a real change with its own test burden, and doing it
in the same pass as a deploy would recreate the problem it is meant to prevent. It belongs in its
own commit, before any deploy, with the suite re-run.

## Preconditions before any deploy

1. Gate A closed — both env vars set, `/livez` reports `ready:true`.
2. Health-check path set on the service (defect 1).
3. Dependencies pinned and the suite re-run at the pinned set (defect 2).
4. A restorable database backup exists — **currently none.** See
   `RENDER-DB-PRESERVATION-2026-10-07.md`.
5. Rollback target identified and rehearsed.
6. Explicit owner authorization.

**A deploy is not proposed here.** Items 1, 2, 4 and 6 are owner actions; 3 and 5 are mine.
