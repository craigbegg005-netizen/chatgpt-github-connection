# CURRENT_STATE

**Date:** 2026-10-05 12:00 UTC
**Author:** Oddfellow (Letta agent, `agent-a9a8eb2c-2fed-4554-9998-aa4783c7efc4`)
**Rule:** every line below is either evidenced in this repository or marked unverified. Nothing here is carried over from a handoff on trust.

> **⚠️ This file was four days stale and is the first thing a fresh AI reads.** Until
> 2026-10-05 12:00 UTC its newest section was dated 2026-10-01 22:40 and it pointed at
> handoffs from 2026-10-01 — while the newest handoff on the branch was
> `oddfellow/HANDOFF-UNIVERSAL-2026-10-03-1530Z.md`, which it did not mention at all.
> A note in agent memory asserted this file "points to the newest dated handoff". It
> did not. **If you are reading this and the newest handoff is newer than the date
> above, this file has drifted again** — read the handoff directory directly rather
> than trusting the pointer here.

## Status vocabulary

`✅ VERIFIED` > `🟢 LIVE` > `🚀 DEPLOYED` > `🔗 CONNECTED` > `🧪 TESTED` > `🛠 IMPLEMENTED` > `⏳ PENDING` > `⚠️ BLOCKED / UNVERIFIED`

---

## Where this file lives, and why that matters

This document is meant to be the first thing a fresh AI reads. Until 2026-10-01 19:16 UTC it existed **only** on `letta/continuity-2026-09-30` — a branch **72 commits behind** the deploy branch that contains none of the v0.20.5/v0.20.6 work. A fresh AI reading the canonical branch could not see it at all.

It is now on the canonical branch. **If you are reading this on another branch, go read the canonical branch first.** Earlier revisions remain in git history on `letta/continuity-2026-09-30`; they are superseded, not deleted.

## Branch map (verified 2026-10-01 19:16 UTC)

| Branch | Head | Role |
|---|---|---|
**This table is a SNAPSHOT, not a source of truth.** Re-derive it before acting on it:

```bash
git ls-remote --heads origin
```

A branch head written into a slow-moving document goes stale within the hour — that is
not a defect in the document, it is a defect in treating a snapshot as current. On
2026-10-01 this table was accurate when written and wrong twenty minutes later.

| Branch | Head at 23:10 UTC | Role |
|---|---|---|
| `letta/combined-single-service-v0.20.4` | `bf62e44d` | **Canonical.** Deploy branch. Single origin: page + API + PWA. |
| `letta/universal-connector-v0.21` | `8f9c139e` | **Universal Connector.** Dev branch. **✅ MERGED into canonical** — verified 2026-10-02: `git merge-base --is-ancestor` → true, 0 commits ahead. |
| `letta/voice-v1` | `9becaa8a` | **Voice V1 approval gate.** Dev branch. **✅ MERGED into canonical** — verified 2026-10-02: ancestor, 0 commits ahead. |
| `main` | `8ddfe325` | Default branch. **Index only** — no `oddfellow/` directory, so a service pointed here cannot satisfy `rootDir: oddfellow` and its build fails with no obvious cause. |
| `letta/continuity-2026-09-30` | `a01e96e` | Where this file used to live. 72 commits behind canonical. |

**🔴 RE-DERIVED 2026-10-02 02:5x UTC — the canonical head in the snapshot above is stale.**
`git ls-remote --heads origin` this cycle returned `letta/combined-single-service-v0.20.4` @
**`adcd481`**, not `bf62e44d`; the branch moved again *during* this session. The other rows
(connector `8f9c139`, voice `9becaa8`, `main` `8ddfe32`, continuity `a01e96e`) still matched.
This is exactly the failure the snapshot label warns about, so the value above is left as a
snapshot and the live head is **re-derived, never trusted from this file**.

**🔴 CORRECTED 2026-10-02 — the roles column was wrong, and the claim that it "does not go stale" was the error.**

An earlier revision of this table said both dev branches were **"Not merged, not deployed"**, and
the paragraph below asserted that the *roles* column was the part that does **not** go stale. Both
are false, and the second is why the first survived: a column labelled "structural fact" is not
re-checked, so a merge that happened after it was written goes unnoticed.

Verified by measurement, not by reading the log:

```
git merge-base --is-ancestor origin/letta/universal-connector-v0.21 origin/letta/combined-...  -> true
git merge-base --is-ancestor origin/letta/voice-v1                 origin/letta/combined-...  -> true
git rev-list --count origin/letta/combined-...  ..origin/<branch>                            -> 0
```

**No work is stranded on either side branch.** The combined branch holds strictly *more*: 1,925
more lines than the connector branch and 5,784 more than the voice branch. The merge commits
`155dd3f` and `d00ad7a` are real.

**The lesson is narrower than "update the table":** a column is not exempt from going stale
because it is *described* as structural. If a claim can change when someone merges a branch, it
is an observation, and it needs a date and a re-check like any other.

⚠️ The canonical branch is **named** `v0.20.4` but the code reports **`0.20.6`**. Report both; never assume equivalence.

---

# ✅ LATEST CYCLE — 2026-10-10 15:00 UTC

**This supersedes every contradicting line below it.**

## 🔑 Read `oddfellow/cognition/GOALS.json` before starting anything

**It is the durable open-goal register, and it is the answer to a specific failure:** nineteen
consecutive cycles re-confirmed a known blocker and produced nothing, because there was nowhere
a goal could be left **open**. The cycle log records work **done**; it cannot record work not yet
done, so a goal that outlived its session got re-discovered instead of resumed.

**If you are picking this up cold, open that file first.** It lists every open goal with a stable
id, who or what blocks it, and the single next action. Pick the highest-leverage goal that is not
owner-blocked and move it — or record honestly that nothing non-blocked remains. That is what
makes `autonomous_task_completion` mean something.

- **`goal_continuity` is now a measured dimension** (was reported as an unmeasurable gap). It
  reads the register **twice** — from the working tree, and from the committed blob — so a goal
  that exists only in the working tree is counted as **lost**. That is deliberately the
  "done is not shipped" failure already recorded as a lesson on 2026-10-05.
- **Demonstrated on the real artifact, not just in a probe:** the same measurement read **0.0**
  before the commit and **1.0** after it.
- Three mutations were applied and each was caught by exactly one test and no other.

**The instrument caught two bugs in itself while this was built**, both worth knowing:

1. `memory_accuracy` fell to **0.333** — two claims in agent memory were stale (test count 666,
   head `434af8c`), made stale by *that session's own work*. The dimension worked as designed.
2. Its falsifier probe only pushed **down**, so against an already-depressed value it demonstrated
   nothing and the dimension reported a number it could not show could move — the false-control
   shape, inside the instrument's own probe. Fixed: the probe now runs in a fixture with a known
   HEAD and offers both directions.

**⚠️ The rehearsal is DOWN.** It died with the sandbox reset at 22:46 UTC — no tunnel, no uvicorn,
no `/root/.oddfellow/url.txt`. The 2026-10-06 note calling it "a working instance Craig can run
phone acceptance against today" is currently false until it is restored.

**Suite: 674 pass** (up from 666). 10/13 dimensions measurable, 10 falsifiers demonstrated.
**Branch head:** `9eec62f`.

---
# ✅ PREVIOUS CYCLE — 2026-10-07 22:00 UTC

**Superseded by the section above; kept for the detail it carries.**

## Read this first: the one thing that has not moved

**Gate A is unchanged; the two owner-action items are Gate A and DB preservation (below).** Probed 2026-10-10 15:00 UTC:

```
GET https://oddfellow-letta-backend-v0206.onrender.com/livez
→ 200 {"live":true,"ready":false,
       "checks_failed":["LETTA_API_KEY","ODDFELLOW_OWNER_TOKEN"],
       "service":"oddfellow_letta_backend","version":"0.20.6"}
```

**The service is RUNNING, NOT READY.** It answers; it is fail-closed on two missing
env vars. **Owner action: Render → `oddfellow-letta-backend-v0206` → Environment →
set both → Save, then trigger a deploy** (`autoDeploy: false` means saving them is
not a deploy). Everything downstream of v0.20 phone acceptance waits on this.

**Do not probe `oddfellow-letta-backend`.** That service is dead. Probing it instead
of the live one caused a 20-hour blind spot on 2026-10-01.

## Where the branch actually is

- `letta/combined-single-service-v0.20.4` @ **`ef176c2`** (2026-10-08 03:04 UTC). **700 tests pass** (up from 638; parallel sessions added the Cognitive Capability Profile, `oddfellow/cognition/`, a durable open-goal register `GOALS.json`, and the tool-invocation audit corpus).

## ⚠️ NEW P0 — Render DB `begg-ai-core-db` expires 2026-10-27T23:21:01Z

**20 days from today.** Render free Postgres lives 30 days, then goes read-blocked unless paid; deletion ~14 days after. **No backups of any kind on the free plan.** The tooling is written and proven (`oddfellow/db_preserve.sh`, tested end-to-end against a real PostgreSQL 18) — blocked only on **owner access**: the DB password, and replacing the IP allowlist with a single `/32` (remove `0.0.0.0/0` first, never join it). Full runbook: `oddfellow/RENDER-DB-PRESERVATION-2026-10-07.md`.
- The branch is *named* v0.20.4 but the code reports **0.20.6**. Report both.
- **Repo access is unchanged and still limited to one repository** — re-checked via the
  API 2026-10-05: `craigbegg005-netizen/chatgpt-github-connection` only. The Oddfellow /
  Begg AI source is still not reachable, so the claimed v0.17.0 baseline remains
  *documented but repository-unverified*. This is the project's highest structural risk.

## Corporate identity change — 2026-10-05

**The canonical corporate name is now Begg Synthetic Industries (BSI).** Legacy alias:
Begg AI Industries. Never "Bay Synthetic Industries" (a mistaken intermediate; never used).
Migration is documented in `oddfellow/BSI-MIGRATION-2026-10-05.md` — phase 1 (this
documentation) committed at `4df96d4`; technical identifiers explicitly preserved
(`begg_ai_command_center`, `mcp__BeggAi__*`, the two live `begg-ai-*` Render services,
which hold the only surviving record of unrecovered source). Phase 2 (system-prompt
prose in `oddfellow_letta_backend.py:281,296`) waits for owner review of the wording.
No blind string replacement performed or endorsed.

## The false-control ledger — read before trusting any comment in this repo

**Ten times in a week, a file asserted a property the code did not enforce.** The shape
is consistent: the file is correct as written, the property is not enforced on every
path, and in most cases *the docstring describing the control was more confident than
the code*. The last four were all one shape — **a rule that holds on one path and not
the one beside it** — which makes it searchable rather than luck: for each rule, ask
where else the same question is asked, and whether it gets the same answer.

The most recent three, all fixed:

| # | claim | reality |
|---|---|---|
| 8 | evidence must be checkable | a filler phrase plus one slash passed |
| 9 | the two evidence paths "must not disagree" | they did; one accepted empty evidence |
| 10 | "the identity that produced a result may not verify it" | bypassable by a case change |

**And the owner-facing page was carrying two falsehoods** until 2026-10-05: it said
"109 tests" against 575, and "Target returns no HTTP response" against a 200. The
second was the blind-spot claim, corrected later in the same sentence while the false
half was left standing. **A correction appended to a false claim does not remove it.**

## Grants lane — two lanes are open and unblocked by Gate A

Verified against primary sources, not handoffs:

- **Emergent Ventures** — ✅ OPEN (2026-10-02). $0 to apply, no entity needed.
- **Verizon Small Business Digital Ready** — ✅ OPEN (2026-10-03). $10,000, 10/month
  through December, $0 to apply, explicitly for-profit.
- **Hello Alice** — checked (2026-10-04): a marketplace, and none of its listed
  programs fits. Not a lane.
- **NSF SBIR/STTR** — pitch now, aim at **March 4 2027**; Nov 4 is not realistic from a
  standing start. **AEDC** is post-award only.

**No application has been filed. No funding requested or received. Revenue $0.**

## Also true right now

- **Voice deferred by owner** — text/chat core first.
- **The 7-Day Reset Planner's Gumroad listing is live** (verified 2026-10-05, $4.99, a
  PDF attached) — but it advertises **12 pages** while the corrected file is recorded
  as **11**. Reconcile before promoting. Seller access and delivery remain unverified.
- **Synthetic workforce Phase 1** exists: 12 departments, 28 workers, authority ceilings
  and evidence rules enforced in code.
- **Nothing is deployed beyond the fail-closed backend.** No revenue. No customers.

---

# ✅ PREVIOUS CYCLE — 2026-10-01 22:40 UTC

**Superseded by the section above; kept for the detail it carries.**

## The connector is no longer only safety scaffolding

Two things changed that matter more than the line count:

**1. There is a working, zero-cost provider path — and a command to drive it.**
`oddfellow/connector/handoff.py` renders the claimable queue as a document a human
can paste into any AI, and turns the reply back into results **through the same
claim/approval enforcement as every other transport**. No API key, no MCP exposure,
no account, no public endpoint. `oddfellow/connector/cli.py` makes it operable:

```bash
python -m connector.cli --db state.db handoff --provider claude > to-claude.md
python -m connector.cli --db state.db apply --provider claude --file reply.md
```

`apply` exits **non-zero** when anything was refused — a refusal is a normal outcome
but it is not a success, and a script must be able to tell the difference.

Correct label: **"structured handoff path operational."**
Incorrect label: "Claude CONNECTED." It is human-mediated, and the MCP and API rungs
are still unconnected. Demonstrated end to end: a low-risk result accepted as
`COMPLETE` and correctly **not** verified; a critical-risk attempt **refused**, with
the job left `READY`.

**2. The post-Gate-A sequence is one command.** `oddfellow/post_gate_a_check.py`
runs all twenty steps in order and was verified against the rehearsal (a
fully-configured instance, so every step executes): **17 machine steps pass, 0 fail,
5 remain for a human.** It restores what it changes — the pause and approval steps
are wrapped so it cannot leave production paused.

### Connector security, at the level it has actually reached

🧪 **TESTED — 123 connector tests** (offline, deterministic; corrected from 113 on 2026-10-02 —
the branch gained 10 tests after that figure was written, and `connector/tests/test_worker.py`
is the file that accounts for them) · 🛠 **IMPLEMENTED** ·
⏳ **NOT CONNECTED** to any provider · ⏳ **NOT DEPLOYED** · the MCP gateway
**serves nothing**.

Credential handling is real, not a placeholder: 256-bit tokens, SHA-256 stored,
constant-time compare, per-provider scopes, durable revocation, and the owner master
token **refused by value**. Claims are a conditional UPDATE, so a race yields one
winner. `submit_result` checks claim ownership **before** idempotency, so an
unauthorised replay is refused rather than silently deduplicated. **`COMPLETE` does
not imply `VERIFIED`** — verification is separate and requires evidence.

All five provider records remain **UNVERIFIED** and the router refuses to route to
them. That is correct: no capability probe has been run against a real provider.
One probe *has* been run against a real MCP server (Stripe's), which proves the
detection mechanism works — it does not make any target provider verified.

### Voice

`letta/voice-v1` @ `9becaa8a`. Elevated-risk commands now enter a **real**
`WAITING_AUTHORIZATION` in the backend, and a spoken approval binds only to exactly
one pending action — ambiguous or mismatched, and nothing is approved.

The **thinking** and **speaking** states were listed in a cross-AI handoff as
implemented; grepping the page showed **listening → 5 occurrences, thinking → 0,
speaking → 0**. They now exist and are verified in a real browser. The gap was not
cosmetic: a reply takes seconds, and without a thinking state a tap looks like it did
nothing.

🛠 IMPLEMENTED · 🧪 BROWSER/BACKEND TESTED · ⚠️ **REAL PHONE MIC / STT UNVERIFIED.**

### The rehearsal serves whatever branch is checked out

### The connector is now integrated, not just present

Merge `155dd3fc` brought `oddfellow/connector/` into canonical — purely additive,
4184 insertions and **zero deletions**, changing no behaviour because nothing
imported it. Then `ddd6d097` wired it in: **`GET /api/command/jobs`** exposes the
queue and the dead-letter view to the owner, which is the "jobs" capability the
architecture has carried as a target.

Three choices worth knowing: it **degrades** rather than failing when no queue is
configured (a control surface that 500s over an optional component teaches the
owner to ignore it); the connector is imported **lazily**, so it cannot take down
the backend; and it **reads, it does not decide** — approving, claiming and
requeueing are state changes with their own gates.

Verified against the live rehearsal: 3 jobs with status/risk/verified, one dead
letter with its error, `?status=` filtering, `400` on an unknown status (not a
silent empty list), and `401` for both a missing and a wrong token.

### The rehearsal serves whatever branch is checked out

`rehearsal.sh status` now reports the revision it is serving, e.g.
`letta/combined-single-service-v0.20.4 @ db9b3e6e`. This is not cosmetic either: the
rehearsal's behaviour changes when anyone switches branches, and today the voice
states worked in the browser and then silently stopped being served twenty minutes
later when the checkout moved. A dirty tree is flagged separately, because
uncommitted edits are served too.

### Unchanged

**Gate A.** `oddfellow-letta-backend-v0206` is 🟢 LIVE on the current build with
`ready:false`, because `LETTA_API_KEY` and `ODDFELLOW_OWNER_TOKEN` are not set. That
is the only thing between the owner and an authenticated Oddfellow, and it is the
only thing between the owner and running the post-Gate-A script for real.

💰 **Verified revenue: $0.** Nothing submitted, sent, charged, or deployed.

---

# ✅ PREVIOUS CYCLE — 2026-10-01 19:50 UTC

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

- `oddfellow/HANDOFF-UNIVERSAL-2026-10-10-1500Z.md` — **newest handoff** (2026-10-10 15:00 UTC).
  ⚠️ Superseding the 21:07 entry: **workforce Phase 2 is now committed** — synthetic heads
  cannot create a job without naming its origin, and the origin rule is enforced at
  construction rather than documented. Fixed a real persistence bug in the same pass: the
  `INSERT INTO jobs` column list was explicit, so the new workforce fields were written as
  SQL defaults and **silently dropped** while the in-memory object read back correctly.
- `oddfellow/HANDOFF-UNIVERSAL-2026-10-05-1955Z.md` — the 19:55 UTC handoff
  **This line has now been wrong twice**: it named a 2026-10-01 file for two days, and
  then a 2026-10-03 file for the hours after a newer one landed. A test now guards it
  (`oddfellow/tests/test_handoff_pointer.py`) and caught the second drift within hours —
  but the guard only runs when the suite runs. **Before trusting this line, list the
  directory: `ls -1t oddfellow/HANDOFF-*.md | head -3`.**
- `oddfellow/HANDOFF-UNIVERSAL-2026-10-03-1530Z.md` — the 2026-10-03 handoff
- `oddfellow/HANDOFF-SYNTHETIC-WORKFORCE-PHASE1-2026-10-03.md` — the workforce layer
- `oddfellow/HANDOFF-TO-CHATGPT-2026-10-01-1950Z.md` — the 19:50 UTC handoff
- `oddfellow/HANDOFF-2026-10-01-1916Z.md` — the 19:16 UTC handoff
- `RESOURCES.md` — resource registry, re-verified 2026-10-01 04:05 UTC
- `oddfellow/CORRECTION-502-CAUSE-2026-09-30.md` — the 502 cause
- `oddfellow/SECURITY-2026-09-30.md` — service-worker finding (deployed but latent)
- `IP-CLEARANCE-SEARCH-2026-09-30.md`, `IP-INVENTORY.md` — name is crowded; register clear in Classes 9/42
- `oddfellow/CORRELATION-2026-09-30.md` — what each AI did, chronologically
- `GRANTS-NON-DILUTIVE-PIPELINE-2026-10-01.md` — grants / non-dilutive lane (leads, not findings)
- `oddfellow/memory_check.py` — **check memory file sizes before appending to one.**
  `MEMORY_DIR=$MEMORY_DIR python3 oddfellow/memory_check.py`. Two files were sitting at
  55 and 90 characters of headroom on 2026-10-05 and nothing would have said so until a
  write failed. The limit is 20000 **characters**, not bytes — `wc -c` overstates these
  files by ~1.6% because they carry emoji and em dashes. (15 tests; proven to fail if the
  implementation counts bytes.)
