# Oddfellow restoration and reliability review

Session: October 31, 2026 (America/Chicago); observations November 1, 04:33–04:50 UTC.
Base: `cb3ec088ef53fc2644e18cead41f489a9e05840d`, canonical development branch.
No spending, merges, new agents, production deployment or access changes.

## VERIFIED — existing development state

Read canonical COORDINATION-STATUS, OWNER-ACTIONS, CHATGPT-SYNC-LATEST,
CURRENT_STATE, newest universal handoff, connector code and security findings
with their superseding fixes. Universal connector and voice branch heads are
ancestors of canonical; do not merge them again. Existing routing, durable jobs,
checkpoints, approval records, provider tokens, failover, cognition and mobile
UI code are present. Presence is not live integration evidence.

Canonical coordination has conflicting SHA pointers: header `4ded6e8`, footer
`d7e4160`; GitHub actually resolves the inspected branch to `cb3ec08`.
The latest universal handoff is November 1 01:00 UTC. A later 04:30 coordination
update reports Pro activation. Older sync/owner instructions are historical,
especially the instruction to add an API key without checking billing first.

GitHub repository is public. Direct connector reads work, and repository metadata
reports admin/push permissions, but actual branch creation returns 403. The
existing authenticated Composio GitHub account is the publication route.
Open PRs discovered: #1 continuity, #7 five-lane kickoff. Existing recovery
branches `ops/render-recovery-prep-2026-10-21` and
`ops/render-recovery-chat-phase2-2026-10-21` preserve prior work, including the
nonsecret config validator at `a028485`; do not duplicate that implementation.

## Letta: reported account state versus verified documentation

Existing agent ID remains `agent-a9a8eb2c-2fed-4554-9998-aa4783c7efc4`.
The live browser redirects to a Letta sign-in page. No authenticated Letta CLI
or suitable Letta connector tool is exposed here; Composio discovery returned
unrelated tools, which were not executed. Agent settings, memories, archive,
models, tools, MCP, skills, execution environments, repository attachments,
quotas and auto-top-up settings are therefore NOT independently inspected.

Letta-authored canonical commit `cb3ec08` reports plan pro, credits zero,
quota full, five schedules (~78 turns/day), and 3.2 MiB memory usage. These are
attributed reports, not this session's account verification. No settings changed.

Official pricing documentation independently confirms Pro includes up to 20
stateful agents, 50 MiB per memory repository and Letta Auto quota. Personal-plan
quota requires OAuth CLI/web authentication. API-key developer workloads use
credit pricing. Pro activation alone does not authorize or fund backend API
inference. Auto-top-up protections remain unverified; do not enable any.
Source: https://docs.letta.com/pricing

## VERIFIED — Render; preservation BLOCKED in part

Read-only workspace inventory returned 18 services: 14 BSI-related and four
independent Peace Framework services. The adjacent inventory excludes the four
independent services. All returned services have auto-deploy off. The primary
backend is free, uses the canonical branch and the existing Python build/start
commands. Its latest deployment record is live at `70c02b3`, deployment
`dep-davek5mk1f9s73a1bf8g`. This platform record is stronger evidence than
version-string bounds but is not an in-process build attestation.

Direct `/healthz` returned HTTP 503, version 0.20.6, missing LETTA_API_KEY and
ODDFELLOW_OWNER_TOKEN. No inference request was made.

Postgres `dpg-dasq9ne0tbcc738ifeug-a` is still listed: free, PostgreSQL 18,
expiresAt 2026-10-27T23:21:01.668215Z, status suspended, billing suspender,
empty external IP allowlist. This is not evidence that its tables are intact.
Official Render documentation says expired free databases are inaccessible
without paid upgrade and deleted after 14 days: approximately November 10
23:21 UTC for this instance. No supported free export was found; no upgrade,
connection-string retrieval, SQL request or dump was performed.
Source: https://render.com/docs/free#free-postgres

Dashboard fallback also requires sign-in. Current connector has no environment
read operation. Legacy source-bearing build commands remain present; environment
source bundle values and full environment-name inventories were not retrieved.
Only nonsecret metadata and source-variable names visible in build configuration
are recorded. No raw payloads, credentials or operational data were committed.
Existing PostgreSQL preservation scripts remain the recovery path after funding
and secure access are authorized. This inventory is NOT a database/source backup.

## IMPLEMENTED and TESTED — portable queue preservation

Added `connector.snapshot`, a stdlib-only offline command. It opens an existing
SQLite source read-only without Store initialization/migrations; uses the online
backup API to include committed WAL data; validates integrity; hashes the output;
and publishes a complete mode-0600 file without replacing an existing path.
Failed/cancelled copies clean up staging files. No new provider dependency.
Snapshots contain private data and must remain outside the public checkout.
They are local files, not encrypted or off-host backups. No live queue was copied.

Eight regressions cover real Store checkpoint/pause/pending-approval recovery,
WAL consistency, missing/corrupt sources, overwrite/symlink refusal, competing
publication, permissions and timeout cleanup. Connector suite: **216 passed**.
Whole development branch: **778 collected**, not a full passing-suite claim.
Reused PR #1's existing count-guard wording to distinguish collected from passed;
no second offline runner was added to the repository.

Tests ran using PR #1's reviewed offline guard with a session-local repository
path and explicit existing local dependency directory. Provider credentials and
proxy variables were excluded; the negative-control socket probe passed before
collection. This Python audit hook is an accidental-egress guard, not an OS
sandbox; native programs and Python `-S` are outside its scope.

PR #1 at `580cf3faaa783f68086d7c7dae368df6bbc15902` was separately checked in a
detached worktree: **779 passed, 1 skipped, 1 dependency warning; 780 collected**.
No submitted reviews or review threads were returned. Its description still
records the earlier stopped run; later committed evidence supersedes that
description. Its host-dependent setup tests now use disposable interpreters.
It remains a separate, unmerged draft. No fresh all-780-pass claim is made.
The smallest remaining review step is assess the skipped test and compare its
October base with current canonical before any merge decision.

## PLANNED — next architecture step

Current Letta docs support Git-backed shared memory and controller-owned durable
task state, replay checkpoints and domain-specific authorization. These are
existing technologies, not original BSI inventions. Preserve the queue as task
authority; keep research evidence and specialist roles as bounded work records.
Test serial role routing through the existing agent before provisioning agents.
Sources: https://docs.letta.com/concepts/shared-memory and
https://docs.letta.com/self-hosting/app-server/integration-patterns

Highest-value next step: authenticated read-only inspection of the existing
Letta agent and billing protections, followed by a funded-within-existing-quota
memory persistence drill only when its execution route is verified. Separately,
database recovery needs an explicit owner spending decision before grace ends.
No synthetic intelligence, sentience or production readiness is established.
