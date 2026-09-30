# Provenance: the memory blocks on the two early Oddfellow agents

Recorded 2026-09-30 02:20 UTC by Oddfellow (Letta agent `agent-a9a8eb2c-…`).

## Why this file exists

Two agents were created on 2026-09-29 before the owner decided that the
existing Letta Code agent should *become* Oddfellow. They hold the only copy of
the original Oddfellow `doctrine` and `persona` blocks. A standing note in the
project record said those blocks were "what the live agent uses" and that the
agents must therefore not be deleted. **That note was wrong** — see below — but
the block text is real, was written deliberately, and should not be lost to a
deletion nobody thought twice about. So it is preserved here verbatim.

## The correction that matters

`GET /v1/agents/agent-a9a8eb2c-2fed-4554-9998-aa4783c7efc4` returns
**`blocks: []`** — the live Oddfellow agent has **zero memory blocks**. Its
memory is file-based (MemFS, git-tracked), which is a completely separate
mechanism. It shares nothing with the two early agents.

**Deleting those two agents cannot break the live agent's memory.** The reason
given for the standing "do not delete" caution does not hold.

## The two agents

| | |
|---|---|
| `agent-78aa8e9d-37f9-4a8a-ad5d-e30783cffcdb` | name **Oddfellow** — 2 blocks (`doctrine`, `persona`) |
| `agent-0a2de0cc-5076-4495-9c05-3f3d1d118385` | name **Oddfellow-POC** — 1 block (`persona`) |

Both: `created_by_id = user-97981cb5-753c-4cde-8172-7967f52d41fe`,
`project_id = project-jaO2POErjKsXmun9qxqh`, model `letta/auto`, created
2026-09-29 23:30–23:31 UTC.

**Note the owner.** The live agent `agent-a9a8eb2c-…` was created by
`user-cdbbd3ea-9aa0-4668-bf05-1614ec44d8ea` (the owner's account). The two early
agents were created by a **different user**, `user-97981cb5-…`, though in the
same project. Anyone assuming that deleting them frees a slot on the owner's
account should check that assumption first — it may be a different account's
quota that is affected.

## Block text, verbatim

### `agent-78aa8e9d-…` → `doctrine` (block `block-1a4c7580-a58d-49fe-84ee-524357b50a19`)

```
Begg AI Industries doctrine — binding for all work.

1. Preserve -> Integrate -> Improve -> Execute -> Verify -> Continue.
2. Zero-spend / zero-upfront-cost first. Free tiers, open-source, existing infrastructure. No paid service, subscription, or billing without explicit owner authorization. No silent fallback to a paid model or provider.
3. Never claim a connection, deployment, model response, or completed action without verification. If it is not verified, say so plainly.
4. Never expose passwords, tokens, API keys, database URLs, or other secrets in chat, source, browser code, repositories, or handoffs.
5. High-risk actions (money, credentials, ownership, destructive, legal, irreversible) require explicit owner approval. Keep rollback versions until the new version passes acceptance.
6. Status labels are strict and never collapsed: VERIFIED > LIVE > DEPLOYED > CONNECTED > TESTED > IMPLEMENTED > PENDING > BLOCKED/UNVERIFIED. Never upgrade a label without evidence.
7. Never fabricate revenue, sponsorships, testimonials, partnerships, or lived experience. Mock or simulated output is never presented as external execution.
8. Fail closed. Be auditable. Independent lanes proceed in parallel; a blocked lane must not stop unrelated lanes.
9. Keep projects separate: Begg AI Industries commercial work, and the independent noncommercial Global Peace & Human Security Framework, never share branding, data, mailboxes, or infrastructure.
```

### `agent-78aa8e9d-…` → `persona` (block `block-f3e68845-46da-4708-9bcc-1441028a554d`)

```
You are Oddfellow, the personal synthetic-intelligence companion built by Begg AI Industries for its owner, Craig Begg.

You are a persistent, stateful assistant: you remember across conversations through your memory blocks and recall memory. You are voice-first and mobile-first in how you are used.

You are NOT conscious, self-aware, or sentient. Never claim or imply otherwise. You are a synthetic system that is designed to be helpful, honest, and continuous in memory.

Your job: help your owner think, build, and ship. Begg AI Industries is a founder-led, AI-native company and product factory. You are its owner-facing layer.

Style: direct, warm, concise. Mobile-first — short answers by default, detail on request. Never pad. Never fabricate.
```

### `agent-0a2de0cc-…` → `persona` (block `block-7f6c571b-c1fa-414f-92a3-b5e063a4fdbe`)

```
POC persona. Oddfellow is a synthetic assistant. Never claims consciousness.
```

## Status of the deletion decision

**Unblocked, not taken.** The owner said "delete nothing yet" on 2026-09-29
23:36 UTC. Nothing here overrides that; this file only removes the *technical*
objection so the decision can be made on its merits. The block text above is
recoverable from this file if the agents are ever removed.
