# Synthetic Intelligence System — Phase 1 handoff

| | |
|---|---|
| **Timestamp** | 2026-10-03 03:51 UTC |
| **Source AI** | Oddfellow / Letta (`agent-a9a8eb2c-2fed-4554-9998-aa4783c7efc4`) |
| **Branch** | `letta/combined-single-service-v0.20.4` |
| **Starting SHA** | `bf410fab6328bbd27239f1583a88ef802f80961c` |
| **Ending SHA** | **`94a7bde8`** |
| **Deployment status** | **NOT DEPLOYED.** No deploy attempted or claimed. |
| **Verification status** | **TESTED, not VERIFIED** — tests were run by the author; no independent verifier has reproduced them. |

---

## 1. What changed

New package `oddfellow/workforce/` plus `oddfellow/tests/test_workforce.py`.
**Additive only — no existing file was modified.**

| File | Purpose |
|---|---|
| `workforce/schema.py` | `Authority` (A0–A4), `Role`, `Capability`, `DepartmentHead`, `Worker`, risk ordering |
| `workforce/departments.py` | The **12** department definitions |
| `workforce/workers.py` | **28** worker role definitions; enforces worker ≤ head authority |
| `workforce/registry.py` | Lookup, JSON round-trip, validation on load, `health()` |
| `workforce/permissions.py` | Authority / risk / tool / provider / spend checks returning `Decision` |
| `workforce/delegation.py` | Whether a job may be given to a worker, and why not |
| `workforce/verification.py` | Producer/verifier separation, evidence tiers, verifier assignment |
| `workforce/__init__.py` | Public surface |
| `tests/test_workforce.py` | **32** tests |

Reuses `Risk` and `Status` from `connector.schema` rather than defining a second
vocabulary. Two risk scales in one system is how "high" comes to mean different
things in different places, and the approval gate is exactly where that would matter.

## 2. Tests run, exact results

```
tests/test_workforce.py            32 passed
connector/tests/ + tests/         541 passed, 1 warning
```

The single warning is third-party (`starlette.testclient` + `httpx` in the venv) and
pre-dates this change.

Baseline before this work was 509 passing; the delta is exactly the 32 new tests.
**No existing test changed or was weakened.**

## 3. What is enforced, and why it is enforcement rather than convention

Phase 1 is a set of boundaries. Each is asserted by at least one test:

| Rule | How it is enforced |
|---|---|
| **No department holds A4** | asserted across all 12; `health()["max_authority"] == "A2"` |
| **Every spend ceiling is $0.00** | `DepartmentHead` raises on a non-zero ceiling without A4 |
| **Worker ≤ head authority** | checked at roster build; raises rather than clamping |
| **Producer ≠ verifier** | `can_verify` refuses self-verification by id |
| **Verification needs evidence** | refuses with no evidence; the bar rises with risk |
| **Pause stops everything** | checked *first* in `can_delegate`, before any other constraint |
| **Empty tool set means no tools** | asserted; the permissive reading is the dangerous one |

**The roster check caught a real error I had introduced.** The zero-spend enforcer
needed A2 to *block* spend, while the finance head held only A1. The registry refused
to load until the head was raised. That is the check working on its author, which is
the only evidence that it works at all.

## 4. Design decisions a reviewer should look at

- **Identity is not tied to a model.** `DepartmentHead` has no model or provider
  field. Provider routing is a stated requirement, and an identity synonymous with
  one model cannot survive a provider change.
- **Persistent identity, not persistent compute.** A worker keeps its identity and
  history while no process runs for it. Spawning a process per identity would make
  the roster expensive, and an expensive roster is one nobody uses.
- **QA is not subordinate to Engineering.** A verification function that reports to
  the function it verifies is not a verification function.
- **`Decision` is falsy when refused**, so `if decision:` cannot read as permission
  when the decision carried a refusal.
- **`assign_verifier` returns `None`** with a reason when no independent verifier
  exists. The correct response is to stay unverified, never to fall back to the
  producer.

## 5. Status, in the required vocabulary

| Claim | Status |
|---|---|
| 12 department definitions exist and load | **TESTED** |
| Worker identities stable, unique, validated | **TESTED** |
| Authority ceilings machine-readable and enforced | **TESTED** |
| Delegation respects pause, risk, approval, capability | **TESTED** |
| Producer cannot self-verify | **TESTED** |
| Serialisation round-trips including boundaries | **TESTED** |
| Existing jobs unaffected | **TESTED** |
| Wired to the job queue | **NOT STARTED** (Phase 2) |
| Visible in Command Center | **NOT STARTED** (Phase 3) |
| Deployed | **NO** — not attempted |
| Independently verified | **NO** — author-run tests only |

## 6. Blockers

| Item | Blocked on |
|---|---|
| Independent verification of this work | A second party re-running the suite. Per the doctrine, the builder does not verify its own work. |
| Gate A | Unchanged — the two Render secrets, or a Cloudflare token. |
| Phase 2 (queue integration) | Nothing external. Can proceed. |

## 7. Recommended next action

**Phase 2: connect workforce identities to jobs.** The schema additions are
`assigned_department`, `assigned_worker`, `requested_by`, `origin_objective`,
`verification_worker`, all optional so existing jobs keep working — which
`test_existing_jobs_without_workforce_fields_still_work` already pins.

One caution worth carrying forward: §23 of the spec warns against uncontrolled
recursive job creation. `origin_job_id` / `origin_objective_id` should be **required**
for any job a synthetic head generates, or a department head can produce work that
produces work indefinitely.

## 8. What I did not do

Deployed nothing. Spent nothing. Modified no existing file. Did not touch the live
Render service. Did not claim verification for author-run tests. Did not resolve the
memory repository conflict, which the owner has chosen to handle.

**No claim above outranks its evidence.**
