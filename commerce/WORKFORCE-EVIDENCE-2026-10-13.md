# Commerce workforce — creation and test evidence

**Date:** 2026-10-13 · **Lane:** BSI commerce · **Verdict: the workforce is NOT LIVE as
persistent agents.** This file exists because the owner directive of 2026-10-13 said
*"Record actual agent creation and tests before declaring workforce LIVE."* It records the
test, the result, and the failure.

## Test 1 — persistent agent creation → FAILED (hard limit)

Command (run 2026-10-13 01:42 UTC):

```
letta agents create --name "BSI Commerce — Product" \
  --description "Begg Synthetic Industries commerce department: product catalog, margins, POD configuration." \
  --tags "bsi,commerce"
```

Result:

```
402 {"error":"You have reached your limit for agents, please upgrade your plan or delete some agents","limit":3}
```

**Interpretation.** The Letta account is on a plan with a hard **3-agent limit**, and it is
**full**. Persistent agent creation is therefore **blocked**, and no commerce department head
or worker exists as a persistent agent. The two options are (a) delete an existing agent, or
(b) upgrade the plan — **upgrading is spending and requires explicit owner authorisation.**

**This is the single most important finding in this record.** A "workforce" of persistent
agents cannot be created at all right now, so any claim that one exists would be false.

## Test 2 — delegated subagent execution → WORKED (but is not a persistent agent)

Real subagents were spawned for the commerce work. Actual records:

| Task | Agent ID | Department | Result | Tool uses | Duration |
|---|---|---|---|---|---|
| `task_1` | `agent-ae163bc9-c9af-4c94-a134-07b5ea16d708` | Product | ✅ success | 7 | 56.2 s |
| `task_2` | `agent-1e7c5905-48e7-4d19-b8fa-575667e7b90f` | Operations / Legal | ❌ **failed** | 0 | 8.7 s |
| `task_3` | `agent-296d3c06-358b-4328-b3d6-8ccc3b8f4c8b` | Operations / Legal (retry) | ✅ success | 10 | 58.1 s |

**`task_2` failure, recorded rather than hidden:** the platform returned
`Error: Remote Super Run d359a9e6-… completed without a correlated child run` after 0 tool uses.
That is an infrastructure error, not a task error. It was retried as `task_3`, which succeeded.
**One in three spawns failed on first attempt.**

**What this does and does not prove.**
- It **does** prove real work ran: 17 tool calls across two departments, each producing sourced
  output that was then independently spot-checked (see below).
- It **does not** prove a persistent workforce exists. These subagents are **ephemeral
  delegated workers** scoped to one conversation. They have no durable memory, no standing
  identity, and no existence after this session. They must not be described as department heads.
- ⚠️ **Mechanism unverified:** subagent invocations returned `agent-…` IDs, yet the
  `letta agents create` CLI path returned 402 for the same account. I do **not** know whether
  subagents draw on the same 3-agent quota, are conversation-scoped, or use a separate path.
  Recorded as an open question, not as a conclusion.

## Independent verification of the departments' output

The Product department's margin table rests entirely on Fourthwall's published base costs, so I
re-derived them from the primary source rather than trusting the summary:

- Fetched `https://cdn.fourthwall.com/downloads/fourthwall_pricing.pdf` (HTTP 200, 3,402,203
  bytes, `application/pdf`).
- Extracted with `pdftotext -layout` and read the figures directly.

**Confirmed:** Gildan 64000 tee **starts at $9.80** · Gildan 18500 hoodie **starts at $20.75**
· Classic Coffee Mug 11 oz **$7.95** ("one price regardless of design") · Bella+Canvas 3001
**$12.95** · High-Quality Matte Poster **starts at $7** · framed poster **$18.50** · **0%**
commission on physical products · credit card **2.9% + $0.30** · "No upfront costs."

**One nuance the summary missed:** the 0% carries an asterisk — *"When you use Fourthwall to
produce your products, we have a margin built into the product price (under 10% on average)."*
The commission is genuinely 0%, but Fourthwall's margin sits inside the base cost. Recorded in
the catalog plan.

**One claim the department could not verify and got right to flag:** the store URL "returned no
result on fetch." That is correct behaviour — the store is password-gated (see the catalog
plan). The department did not invent a store state it could not see.

## Status labels

| Item | Label |
|---|---|
| Persistent commerce agents | ⚠️ **BLOCKED** — 402, 3-agent limit reached |
| Delegated subagent execution | 🧪 **TESTED** — 2 of 3 spawns succeeded, real sourced output |
| Catalog plan (3 products + margins) | 🛠 **IMPLEMENTED** — not listed, not published |
| Readiness + policies | 🛠 **IMPLEMENTED** — drafts, pending legal review |
| Fourthwall MCP | ⚠️ **BLOCKED** — HTTP 401, needs owner OAuth |
| Store | ⚠️ **NOT PUBLIC** — "Coming soon" mode, all routes → `/password` |
| Products listed / published | ❌ **NOT DONE** |
| Checkout verified | ❌ **NOT DONE** |
| Revenue | 💰 **NONE** — no sale has occurred |

**Nothing here is LIVE.** The honest summary is: the *planning* departments produced real,
verified work; the *execution* path is blocked on one owner OAuth and one owner launch
decision; and the persistent-agent workforce does not exist and cannot be created on the
current plan.
