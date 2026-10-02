# Universal Connector

Provider-independent job coordination for Oddfellow. It lets authorised AIs work
against one canonical queue without exposing anyone's private memory, and it is
built so that the safe answer is always the default answer.

## The transport ladder

Routing prefers, in order: **MCP → provider API → structured handoff → durable
queue**. Only the third rung works today, and that is a fact about credentials, not
about the code.

## What actually works right now

The **structured handoff**. It needs no API key, no MCP exposure, no account and no
public endpoint — so it is usable with Claude, ChatGPT, Gemini or Grok today.

```bash
python -m connector.cli --db state.db handoff --provider claude > to-claude.md
# ... paste to-claude.md into the AI, save its reply ...
python -m connector.cli --db state.db apply --provider claude --file reply.md
```

`apply` exits **non-zero** when anything was refused. A refusal is a normal outcome
but it is not a success, and a script must be able to tell "done" from "the gate said
no".

## Running the queue on a schedule

```bash
python -m connector.cli --db state.db tick --provider claude --out /var/oddfellow
```

The tick renders a handoff when there is work and **does nothing when there is not**.
It is idempotent: it fingerprints the ready set and records it, so a second run with
no change reports *"identical to the last handoff; not rewritten"* instead of
rewriting the same document forever.

**On cadence — the deliberate decision, recorded because it looks like an omission.**
This is *not* given its own hourly schedule. An idle queue would make most runs report
"no ready jobs", and each run costs tokens. Zero-spend applies to tokens as well as
dollars. The tick is instead run as part of the existing scheduled sweeps, where it
costs nothing extra:

```bash
python -m connector.cli --db "$ODDFELLOW_QUEUE_DB" tick --provider claude --out /root/.oddfellow
```

If the queue ever carries real work at a rate that needs its own cadence, give it one
then — not before.

## What the tick will not do

It renders. It does not **claim, approve, submit, or requeue**, and it refuses to
prepare work while the emergency pause is set. A background job is exactly the wrong
place to loosen a gate, so a critical-risk job is handed over and *still* cannot be
claimed without approval.

## The two rules that matter most

**`COMPLETE` is not `VERIFIED`.** A submitted result is COMPLETE. Verification is a
separate act, requires evidence, and cannot be performed by the provider that
submitted it. Never promote company state from an unevidenced AI claim.

**Provider output is untrusted input.** A returned result is parsed defensively and
then passes through the same claim, ownership and approval enforcement as any other
transport. It cannot steal a job, bypass approval, or verify itself.

## Operator commands

| Command | Does |
|---|---|
| `jobs` | list the queue |
| `handoff` | render a handoff for a provider |
| `apply` | apply a provider's reply |
| `tick` | one idempotent queue pass |
| `dead-letters` | jobs that exhausted their retries |
| `requeue` | revive one, with a stated reason |
| `connect` / `tokens` / `disconnect` | provider credentials, scopes, revocation |
| `audit` | the audit trail |

`connect` prints a token **once**. It is not recoverable — a lost token is reissued,
not restored. `tokens` lists metadata and never a value.

## Status

🧪 **TESTED** — offline and deterministic · 🛠 **IMPLEMENTED** · ⏳ **NOT CONNECTED**
to any provider · ⏳ **NOT DEPLOYED** as public MCP.

Every provider record is **UNVERIFIED** and the router refuses to route to them,
because no capability probe has been run against a real provider. One probe *has* been
run against a real MCP server (Stripe's), which proves the detection mechanism works —
it does not make any target provider verified.
