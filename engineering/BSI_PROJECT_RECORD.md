# BSI coordinated research and engineering record

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
