# BSI coordinated research and engineering record

## Current review — November 1, 2026: reconciled upgrade and lease expiry

**IMPLEMENTED / TESTED.** Review branch `work/bsi-research-review-20261101`,
based on canonical `ab961e366b85bcbb20c331fc4be98ebfed0ecb32`.
This section supersedes earlier current-state and PR-status descriptions below;
the earlier implementation and continuation sections are historical evidence.

Canonical already contains the PR #1 salvage (`44e368b`); GitHub reports PR #1
closed without merging that original PR. The review branch retains those current
canonical changes and carries over only the local research worker, its finalizer,
regressions and evidence. It does not reapply the old handoff/runner fixes.
The original `work/bsi-offline-research-20261101` branch remains preserved.

Upgraded generic lease expiry: a scan can become stale while another process
completes, renews or reclaims a job. Replaced the stale whole-job write with a
conditional update matching status, attempt, provider, claim timestamp and lease
duration. Changed claims are left untouched. Expiry and its audit event commit
together, and unrelated payload/result fields are not overwritten.

Three new developer-authored regressions start another Python process after the
scan reads the job, then complete, renew or reclaim it. All three failed against
the old expiry code and pass with the conditional update. They supplement the
four previous claim-attempt completion/failure regressions.

Validation:

| Check | Fresh result |
|---|---|
| Reconciled branch before expiry fix | 801 passed, 1 skipped; 802 collected |
| Stale expiry regressions before fix | 3 failed, demonstrating the gap |
| Final full guarded suite | **805 passed, zero skipped**, one dependency deprecation warning |
| Actual reconciled worker/Innovation bridge | 3 computations initially; 0 on reopen; all unverified |
| `git diff --check` | clean |

The initial skip came from `test_every_cited_commit_exists` checking whether
`.git` was a directory. Linked worktrees use a `.git` file. Updated that test to
ask Git whether it is in a working tree; cited-commit validation now executes.
The latest suite evidence is `engineering/evidence/oddfellow-review-tests-final-20261101.txt`.
Other new evidence: `expiry-before-20261101.txt`, `review-bridge-first-20261101.json`
and `review-bridge-reopened-20261101.json`. Failure logs have trailing whitespace
normalized for repository checks; outcomes and failure content are preserved.

Scope remains local SQLite orchestration with trusted pure research callbacks.
Generic submit/fail/renew operations have not all been redesigned, and live Letta
integration, worker isolation/timeouts, independent evaluation, scientific
validation and neural model training remain outside this change. No production
merge, deployment, new agent, paid service or external research submission.
Prepare a separate draft PR against canonical for owner review.

Next: review the narrow queue mutations (S), extend consistent attempt checks to
other generic mutation paths when their callers can supply claim identity (M),
then obtain independently authored unseen research scenarios (M).

## Continuation — November 1, 2026: protect replacement research claims

**IMPLEMENTED / TESTED.** Reviewed the saved local worker before adding new
capabilities. Found that lease expiry during a computation could let its old
worker overwrite a replacement claim on failure, or submit a stale result when
the replacement reused the same provider identifier. Successful late submission
to a different provider also appended a misleading completion checkpoint before
being refused. This was a newly found limitation of the preceding implementation.

Added `Store.finish_research_claim`: obtains a SQLite write lock, checks the
current provider, monotonically increasing attempt, task/risk and payload against
the original claim, and commits completion/failure with its audit events in a
single transaction. The computation runs outside the lock. The local worker uses
this method for both success and failure. No schema migration or new dependency.

Four developer-authored regression cases start a real second Python process
which expires the first claim and reclaims the same job. They cover success and
failure with both the same and a different provider. All four failed before the
fix and pass afterward. Additional tests verify payload revision refusal,
ordinary heartbeat acceptance, and rollback of result, checkpoint and audit
changes when an injected audit-write failure aborts completion.

Fresh evidence:

| Check | Result |
|---|---|
| Before-fix claim-expiry regressions | 4 failed, demonstrating the gap |
| Full guarded Oddfellow suite after fix | 792 passed, one dependency deprecation warning |
| Unchanged Innovation Engine v1.1 suite | 207 passed |
| Actual bridge first / second process | 3 computations / 0 computations; all results unverified |
| `git diff --check` | clean |

Files: `oddfellow/connector/store.py`, `research_worker.py`, worker regressions,
test-count record/guard, this record, and new evidence in `engineering/evidence/`.
`stale-attempt-before-20261101.txt` records the before-fix failures;
`oddfellow-tests-20261101-continuation.txt` records the full passing run;
`bridge-fenced-first-20261101.json` and `bridge-fenced-reopened-20261101.json`
contain the fresh synthetic integration receipts.

**Limitations:** tests use separate processes sharing one local SQLite database;
they are not a distributed-system proof, independent evaluation or physical
experiment. Only local research finalization uses this new attempt check; the
older generic submission, failure and lease-expiry APIs retain their behavior.
Audit infrastructure failure leaves the claim RUNNING with no partial completion;
recovery uses the existing explicit lease-expiry flow. Trusted callbacks still
need to be pure computations; timeouts/process isolation remain unimplemented.
Live Letta synchronization was not attempted. No merge, deployment, new agent,
spending or external submission occurred.

Next priorities: review the new finalization path (S); evaluate the remaining
generic queue mutation races before broader worker use (M); obtain independently
authored engineering scenarios (M). Previous project priorities remain below.

## Session — November 1, 2026 (America/Chicago)

Development branch: `work/bsi-offline-research-20261101`.
Recovered canonical commit: `401bc986b3c5d383a9c2753150797a45c23f805b`.
No merge, production deployment, external submission, new agent, model inference,
paid service, or credential change occurred. The Global Peace & Human Security
Framework remains a separate initiative and was not modified.

## Recovery and review — VERIFIED

- Cloned the existing repository and recovered Innovation Discovery Engine v1.0
  from `BSI_Innovation_Discovery_Engine_v1_0_2026-10-31.zip`.
  Its 117 v1.0 manifest entries matched their recorded SHA-256 values after
  extraction and baseline execution. Byte matching establishes integrity against
  the supplied manifest, not authenticity or scientific correctness.
- PR #1 remains open, draft and unmerged, head
  `580cf3faaa783f68086d7c7dae368df6bbc15902`. All eight changed-file patches were
  inspected. The discussion and review-list APIs returned no reviews/comments.
  Its description records a stopped suite; the later review document records
  780 passing tests with an offline guard. Neither historical count was used as
  a fresh result here.
- Reused PR #1's existing offline runner and disposable-interpreter test fixes
  as files on this development branch. The remaining handoff changes stay in
  PR #1. No PR or canonical branch was merged.
- Inspected `work/oddfellow-reliability-20261031` at `0ba0b60`, which already adds
  SQLite snapshot/restore support. No replacement snapshot system was created;
  that branch was not modified or incorporated.

## Actual development — IMPLEMENTED and TESTED

### Oddfellow local research worker

`oddfellow/connector/research_worker.py` executes one explicitly requested
LOW-risk RESEARCH job through the existing SQLite Store. The trusted caller
registers versioned pure functions. Payloads contain only a registered screen
name and JSON inputs, never an executable import, URL, command or path.

The worker checks pause state, independent dependency verification, valid finite
JSON, size limits and claim ownership. It records input/output hashes, a durable
checkpoint and an unverified computation receipt. A completed matching receipt
is reused after restart; corrupted output hashes are refused. Exceptions fail
the job once and store a generic error rather than callback exception content.
There is no automatic retry, scheduling service or live AI call.

This is a trusted-code execution adapter, not a sandbox for arbitrary Python.
Callbacks must be reviewed pure local computations. Their registry versions
must change when their behavior changes. Hashes are integrity identifiers, not
signatures or proof that source measurements are valid. Local SQLite persistence
was tested; no remote Letta memory synchronization or neural-model learning was
demonstrated. A long-running service, resource timeouts and process isolation are
outside this adapter's scope.

### Innovation Engine v1.1

Preserved v1.0 code and added `src/heat_pump_v11.py`, eleven tests,
`examples/heat_pump_cases_v11.json`, and `run_connector_bridge_v11.py`.
The new screen checks a steady-state, fixed-two-reservoir synthetic heat pump:

`Q_hot = W_electric + Q_source`, and
`COP_heating <= T_hot / (T_hot - T_cold)` with Kelvin temperatures.

The new scale-relative rounding tolerance is numerical, not measurement
uncertainty. Real measurements, finite streams, part-load curves, heat-exchanger
approaches, water chemistry and equipment economics are not modeled.

For invented 300 K / 330 K reservoirs and 10 kWh electric input:

| Source heat | Delivered heat | Result |
|---:|---:|---|
| 30 kWh | 40 kWh | Nominal screen only: COP 4, ideal bound 11 |
| 0 kWh | 40 kWh | BLOCKED: output exceeds accounted input |
| 110 kWh | 120 kWh | BLOCKED: COP 12 exceeds ideal bound 11 despite balanced energy |

All three cases ran through the actual new Oddfellow worker using a disposable
SQLite file. A second CLI process reopened that file and executed zero jobs,
reusing all three receipts. All three jobs remained `verified=False`.
Public outputs contain synthetic receipts only; the database is not packaged.

## Validation evidence — TESTED

| Check | Fresh result |
|---|---|
| Recovered Innovation Engine baseline | 196 unittest methods passed |
| Innovation Engine v1.1 | 207 unittest methods passed |
| Oddfellow complete offline suite | 785 passed; one dependency deprecation warning |
| Bridge first process / reopened process | 3 executed / 0 executed; 0 verified in either process |
| Whitespace verification | `git diff --check` clean |

Command: `python oddfellow/run_offline_tests.py` from a Python 3.12 virtual
environment with requirements-dev.txt and socksio. The recovered guard removes
inherited credentials/proxy variables, disables plugin autoload and refuses
external Python socket connections. Its negative control runs before collection.
It is not an operating-system network sandbox; non-Python children and Python
started with site disabled are outside its coverage. The first full run exposed
the existing host-dependent IPv4 test and the expected stale collection count;
reusing PR #1's isolated test fixes and updating the count resolved them.

Evidence: `engineering/evidence/oddfellow-tests-20261101.txt` and the v1.1
package's `outputs/connector_first_v11.json`, `connector_reopened_v11.json`,
and `TEST_RESULTS_v11.txt`.

## Research findings and limitations

### Water and energy — VERIFIED sources; hypothetical calculations

LBNL's Buildings heat-pump documentation explicitly accounts for Carnot-based
performance, temperatures and approach temperatures; part-load behavior requires
additional parameters. This supports using temperature-dependent bounds before
accepting waste-heat reuse concepts. Our simple screen is not the LBNL model or
a validation against it.
Source: https://simulationresearch.lbl.gov/modelica/releases/latest/help/Buildings_Fluid_HeatPumps.html

Albuquerque remains a user-reported closed-loop cooling site. Cooling-tower or
adiabatic equipment presence, makeup/blowdown, actual energy use, temperatures,
flows and annual weather inputs remain unconfirmed. No site water savings were
calculated or claimed this session. The next valuable engineering input is the
heat-rejection equipment schedule and an authorized water/energy metering boundary.

### Existing Letta agent — integration BLOCKED in this environment

The current repository handoff identifies the existing agent as
`agent-a9a8eb2c-2fed-4554-9998-aa4783c7efc4` and reports a Personal Pro upgrade.
Those are repository observations, not an authenticated account inspection here.
Tool discovery did not return a usable Letta retrieval operation; unrelated
Retell/Mistral matches were rejected. No agent was created or messaged.
Letta's official API documents read-only retrieval and memory-block inspection.
No inference was attempted while API-credit costs remained unverified.
Source: https://docs.letta.com/api/python/resources/agents/methods/retrieve

### Biosynthetic intelligence — existing thesis recovered; feasibility limited

Read the preserved `oddfellow_biosynthetic_rnd_v15.md` in full. Its reported
negative result is retained: input-distance rejection selected a worse subset
under synthetic translation shifts. Those figures were not rerun here and must
not be presented as this session's results. Do not deploy that gate as a safety
feature. The next computational study remains preregistered risk/coverage curves
and perturbation controls using the archived implementation.

Cai et al. (2023) report organoid reservoir computation with multielectrode
input/output, speech recognition and nonlinear prediction. The authors'
institutional abstract was accessible; the publisher full text was not. This is
evidence that restricted biohybrid computations have been studied, not evidence
that BSI has printed a brain or demonstrated sentience or energy advantage.
Source: https://scholars.mssm.edu/en/publications/brain-organoid-reservoir-computing-for-artificial-intelligence/

ISSCR's current guidance calls for rigor, oversight and transparency. Its 2025
revision specifically concerned embryo models; it was not a general new approval
of advanced neural-organoid research. BSI's present scope remains computational;
any future tissue study needs qualified institutional review, lawful donor
provenance and an explicit welfare/oversight plan before experiments.
Source: https://www.isscr.org/resources/guidelines-for-stem-cell-research

### Funding — current sources VERIFIED; applicant eligibility BLOCKED

Read the existing NSF Project Pitch v0.3 in full. Its hold-submission decision
remains appropriate: routine integration and familiar single-store patterns do
not establish technical novelty. NSF 26-510 lists November 4, 2026 and March 4,
2027 full-proposal deadlines. Phase I requires a pitch invitation first. Full
proposals require SAM/UEI, Research.gov and SBA registrations; pitches do not.
The founder's legal applicant status, qualifying ownership, PI employment,
registrations and any invitation have not been independently verified here.
Sources:
- https://www.nsf.gov/funding/opportunities/small-business-innovation-research-small-business-technology/nsf26-510/solicitation
- https://seedfund.nsf.gov/solicitation-eligibility/
- https://seedfund.nsf.gov/apply/project-pitch-information/

Prepared proposal evidence addendum (not submitted):
On November 1, the development branch passed 785 guarded offline tests and
demonstrated durable local research execution with three invented engineering
cases. This establishes bounded queue integration and restart behavior in the
test environment. It does not establish novel cross-provider authorization,
distributed revocation, independent scientific validation, customer demand or
funding eligibility. These practical changes should not be presented as resolving
the v0.3 pitch's novelty and comparative-evaluation gaps.

## Updated priorities

| Rank | Next action | Effort | Status |
|---|---|---|---|
| 1 | Review this isolated worker and PR #1 independently; keep canonical unchanged pending approval | S | PLANNED |
| 2 | Obtain independently authored unseen engineering scenarios and freeze the evaluator before scoring | M | PLANNED |
| 3 | Establish authenticated, read-only inspection of the existing Letta agent and confirm inference costs | S | BLOCKED |
| 4 | Obtain authorized Albuquerque equipment/metering data before recovery sizing | M | BLOCKED |
| 5 | Recover v1.5 experiment code and develop held-out risk/coverage evaluation; preserve negative controls | M | PLANNED |
| 6 | Resolve NSF novelty comparison, team gaps and applicant eligibility before revising submission text | M | BLOCKED |

Neural-node networking remains architecture research. This session adds a local
worker contract with durable inputs, claim ownership, checkpoints, results and
independent verification. It does not create a trained neural node network.
App Factory, humanitarian reconstruction and commercial tools were left at their
existing state to prioritize the two requested development lanes. No Render
troubleshooting was performed.
