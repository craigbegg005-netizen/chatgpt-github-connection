# Universal connector — Phase 1 capability discovery

**Date:** 2026-10-14 01:30 UTC · **Directive:** expand the connector to multi-channel
**Method:** live probes only. Nothing here is inferred from a connection list.

---

## HEADLINE: the failover chain has exactly ONE working link

The directive's Phase 3 defines a three-tier failover. **Two of the three tiers do not work.**

| Tier | Channel | Status |
|---|---|---|
| Preferred | **GitHub** | ✅ **read + write VERIFIED** |
| Secondary | **Google Drive** | ❌ **registered, every call fails** |
| Notification | **Gmail** | ❌ **NOT CONNECTED** |

**There is no redundancy.** If GitHub fails, the coordination system has no fallback at all — and
the directive's premise, that agents can exchange tasks "through whichever verified channel is
available", currently reads *"through GitHub, or not at all."*

**Building phases 2–6 on top of this would produce a failover design that cannot fail over.**

---

## Channel-by-channel, with evidence

### 1. GitHub — ✅ the only fully working channel

| Capability | Status | Evidence |
|---|---|---|
| Read | ✅ **VERIFIED** | `git fetch`/`ls-remote` throughout this session |
| Write | ✅ **VERIFIED** | commits `019c5899`, `10868ede`, `2cf682f7`; remote read-back each time |
| Branch create | ✅ VERIFIED | `coordination/oddfellow-chatgpt-sync` |
| Read-back after write | ✅ VERIFIED | remote head compared to local every push |

⚠️ **ChatGPT's GitHub write is 403 (token scope).** It reads; it cannot write. So today **one agent
has write access to the shared record.**

### 2. Google Drive — ❌ registered but non-functional

```
GOOGLEDRIVE_LIST_CHILDREN_V2   → 500 {"error":"Managed MCP server configuration is unavailable"}
GOOGLEDRIVE_FIND_FOLDER        → same
GOOGLEDRIVE_LIST_SHARED_DRIVES → same
```

**Three different tools, identical failure → server-level, not tool-level.** Earlier tested 3× for
transience; identical every time. **No call reaches Google**, so this is not a sharing, folder-ID
or permission problem — and it means **the artwork's presence in the folder is still UNKNOWN.**

**Read: not testable. Write: not testable. Neither is "denied" — the channel does not respond.**

### 3. Gmail — ❌ not connected

The catalog has it (`id: gmail`, `"Connect Gmail"`) and it is **not** in my server list. **0 tools.
No read, no search, no send.**

---

## Phase 2 — proposed structure (ready, but cannot be built yet)

Both proposals below are **sound and blocked**, not rejected. They need channels that answer.

**Drive folder:** `BSI-Coordination/`
- `inbox/` `outbox/` `archive/` `tasks/` `acks/`
- one JSON file per message — `{task_id}-{sender}-{utc}.json`

**Gmail:** a dedicated label `BSI-Coordination` with filters on a subject prefix
`[BSI-<task_id>]`, so agent mail is separable from the owner's real inbox.

**Message schema** (the directive's fields, made concrete):

```json
{
  "task_id": "BSI-2026-10-14-001",
  "sender": "oddfellow",
  "recipient": "chatgpt",
  "utc": "2026-10-14T01:30:00Z",
  "priority": "P1",
  "status": "OPEN|ACK|DONE|BLOCKED",
  "required_action": "...",
  "file_refs": [{"channel":"github","path":"...","sha":"..."}],
  "authorization": "none|owner_required",
  "evidence": ["probe output", "commit sha"],
  "idempotency_key": "BSI-2026-10-14-001-oddfellow-1"
}
```

**Why an idempotency key:** this session already produced a **duplicate schedule** because a 520
told me "no schedule was created" when it had been. **Retried creates duplicate.** Any
message-based channel must dedupe on a key, not on arrival.

## Phase 3 — revised failover, honestly stated

```
GitHub          ✅ works        → use it
Google Drive    ❌ non-functional → cannot be secondary yet
Gmail           ❌ not connected  → cannot be notification yet
```

**Current recommendation: keep GitHub as the sole channel and say so**, rather than documenting a
chain that silently degrades. **A documented fallback that does not work is worse than a
documented single point of failure**, because the first breeds false confidence.

## Phase 4 — polling: not yet justified

Polling exists to detect *new* messages. **With one working channel that already notifies on
commit, polling Drive (15 min) and Gmail (30 min) would burn quota watching two channels that
cannot receive anything.**

**Recommendation:** the existing GitHub-side schedules already cover this:
- rehearsal check — hourly
- lane sweep — every 4 h
- **coordination status refresh — every 2 h** (new; keeps `COORDINATION-STATUS.md` current)

**Add Drive/Gmail polling only when those channels actually answer.**

## Phase 5 — the round-trip test that is possible today

**GitHub round-trip is already demonstrated** — not proposed, *done*: I write a commit, read the
remote head back, and compare. Every push in this session did exactly that.

**Drive round-trip: IMPOSSIBLE.** ❌ Not because the test is risky, but because **the channel does
not respond.** A read-only check was attempted first, as the directive asks — that is how the
failure was found.

## Phase 6 — integration: one blocker to preserve

Whatever is built must keep **one authoritative task state**. Today that is GitHub, and it works.
**Do not replicate task state into Drive until Drive works**, or there will be two records with no
guarantee of agreement — the exact drift problem this repo has already hit three times with
pointers.

---

## REPORT — as the directive requests

| Asked for | Answer |
|---|---|
| **Available connections** | GitHub ✅ · Google Drive ⚠️ registered-but-dead · Gmail ❌ absent |
| **Verified permissions** | GitHub read+write. That is the complete list. |
| **Missing permissions** | ChatGPT GitHub write (403). Drive read/write (unavailable). Gmail read/send (not connected). |
| **Recommended channel** | **GitHub, alone.** It is the only one that answers. |
| **Safe next test** | Nothing new — the GitHub round-trip already ran. Drive needs a **reconnect** before any test is meaningful. |
| **Implementation status** | Phase 1 **COMPLETE**. Phases 2–6 **BLOCKED on channels**, structures drafted above. |

## Owner actions, in order

1. **Reconnect Google Drive.** It is registered with 92 tools and answers nothing; a reconnect re-runs provisioning. Cheapest single fix available.
2. **Connect Gmail** if the notification tier is wanted (card below).
3. Optionally: give ChatGPT's integration write scope, so the shared record has two writers.

## Not claimed

No Drive read. No Drive write. No Gmail access. No round trip. **No channel described as
available that was not probed in this session.**
