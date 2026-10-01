# Oddfellow Voice V1 — status report, 2026-10-01 21:50 UTC

**From:** Oddfellow (Letta agent, `agent-a9a8eb2c-2fed-4554-9998-aa4783c7efc4`)
**Branch:** `letta/voice-v1` @ **`783ddddc`** (pushed, local SHA == remote SHA)
**Base:** `letta/combined-single-service-v0.20.4` @ `ac9ad156` — deploy branch untouched

---

## Status, in the required vocabulary

| Requirement | State | Evidence |
|---|---|---|
| Mic button, tap to speak | **IMPLEMENTED** (pre-existing) | `#mic` toggle in `setupVoice()`; verified present in a real browser |
| Speech → text | **IMPLEMENTED** (pre-existing) | `SpeechRecognition` / `webkitSpeechRecognition` |
| Text reaches the command path | **IMPLEMENTED** (pre-existing) | `send()` → `lettaReply()` → `/api/letta/message` |
| Transcript shows both sides | **VERIFIED** | rendered exchange visible in the browser capture |
| Response read aloud | **IMPLEMENTED** (pre-existing) | `speak()` via `speechSynthesis` |
| Stop / cancel | **IMPLEMENTED** (pre-existing) | `#stopvoice` → `speechSynthesis.cancel()` |
| **HIGH/CRITICAL → WAITING_AUTHORIZATION** | **VERIFIED** | see below |
| **Approval bound to the exact pending action** | **VERIFIED** | see below |
| Audit events recorded | **VERIFIED** | `command_approval_created`, `command_approval_decided` |

**Not verified, and stated rather than implied:** speech-to-text and speech-to-text
*quality* on a real phone. Both use the browser's own engine, which needs a real
device and a real microphone — neither exists here. The code path is implemented
and the browser reports `Voice: ready`; nobody has yet spoken into it.

## What was actually missing, and what changed

Voice V1 was already ~80% present. The two genuinely missing pieces were the ones
the handoff is most specific about.

**Before:** the elevated-risk path called `confirm()`. Its own comment read *"a UX
gate, NOT a security boundary: anything that talks to the API directly bypasses
it."* That was honest, and it meant the planner's risk chip implied a consequence
that did not exist.

**Now:** with a backend configured, an elevated-risk command creates a **real
approval** in the command centre (`POST /api/command/approvals`, `risk=high`) and
**stops**. It runs only once that exact approval is decided. This reuses the
existing orchestrator, approval gate and audit log rather than adding a parallel
one, as the handoff required.

**Spoken approval is deliberately hard to get wrong.** It is accepted only when
the backend reports **exactly one** pending approval *and* its id matches the one
being held. Two pending, or a mismatch, and nothing is approved — because
approving the wrong action silently is the precise failure this gate exists to
prevent. **Everything fails closed:** if the approval cannot be recorded, the
action does not run.

Without a backend, it falls back to `confirm()`, now labelled in the transcript as
a local confirmation only.

## Verification performed

**Front-end wiring, in a real browser against the live rehearsal**, with
`backendCall` stubbed so no credential ever touches a command line:

| # | Test | Result |
|---|---|---|
| 1 | elevated risk gates and sends nothing | `sent=0`, bar shown |
| 2 | approve → `decide('approve')` → then send | `decided=approve`, `sent=[...]` |
| 3 | spoken approval, two pending → refuses | `sent=0`, still pending |
| 4 | spoken approval, one matching → approves | `decided=approve`, `sent=[...]` |
| 5 | spoken approval, mismatched → refuses | `decided=none`, `sent=0` |

**Backend chain, directly against the live rehearsal:**

```
create -> apr-5947995c54e3  state=WAITING_AUTHORIZATION  risk=high
list   -> present in ?state=WAITING_AUTHORIZATION
decide -> state=REJECTED  decision=reject
audit  -> command_approval_created  approval_id=apr-5947995c54e3  risk=high
          command_approval_decided  approval_id=apr-5947995c54e3  decision=reject
```

**Both halves are verified. They have not been driven together with a live token**,
because doing so would put the owner token into a command line. Said plainly
rather than glossed: the integration point is the same `backendCall` the page
already uses for every other command, so this is an untested *join*, not an
untested mechanism.

## Deliberately not done

No avatar, waveform, animation, or visual effects — per the handoff's instruction
not to block V1 on them. No wake word, no barge-in, no selectable voices; those
are named as future phases.

## Blockers

| Item | Blocked on |
|---|---|
| Phone verification (mic, STT quality, TTS aloud, PWA install) | A real device. Only the owner can run it. |
| End-to-end voice → real approval with a live token | The owner token, entered on the device — not in chat, not in a command line. |
| Gate A (Oddfellow readiness) | `LETTA_API_KEY` + `ODDFELLOW_OWNER_TOKEN` on `oddfellow-letta-backend-v0206`. **Unchanged.** |

**No claim above outranks its evidence.**
