# 🔴 P1 — the agent's configured model has been RETIRED; chat is dead

**Found:** 2026-11-07 04:08 UTC · **Severity:** P1 — the product's core function fails
**Status:** ROOT-CAUSED, fix identified, **not applied** (needs an owner decision on which model)

---

## Symptom

The acceptance harness began failing — reproducibly, on the first failure of the hour:

```
[FAIL] message: real reply                    HTTP 502 in 0.8s | None
[FAIL] history: the turn we just took is in it  HTTP 200 | 0 message(s)
```

**Not a transient and not self-inflicted.** I waited 70s for the rate-limit window to clear and
re-ran: identical failure. The *first* 502 (04:03:27) also predates any rate-limit event.

## Root cause — verified three independent ways

Calling the endpoint directly with the correct auth header (`X-Owner-Token`, **not**
`Authorization: Bearer`) returns the real error:

```json
{"detail":{"error":"letta_message_failed","status":400,
 "detail":{"error":"letta/auto is no longer available. Select a hosted model using
 credits or connect an external provider.",
 "reasons":["model-retired"]}}}
```

**1. The model list no longer contains it.** `GET /v1/models/` returns **89 handles**;
`letta/auto` is **not among them**. Available Letta-hosted handles include `letta/auto-fast`,
`letta/echo`, `letta/glm`.

**2. The agent's own `llm_config` is the retired handle:**

```json
{"model":"auto","provider_name":"letta","handle":"letta/auto","context_window":180000}
```

**3. A per-request `llm_config` override does NOT work.** I tried `openai/gpt-4o-mini` and
`letta/echo` as explicit overrides — **both returned the identical `letta/auto` error.** The
agent's stored config wins, so the fix must be applied to the agent, not the request.

## Impact

| Surface | Effect |
|---|---|
| Rehearsal harness | **FAILS** — message + history gates |
| Rehearsal product (phone path) | **Chat is dead** — any turn fails |
| **The agent itself** | Its stored `llm_config` is a retired handle |
| Render production | **Insulated only by accident** — it 503s `backend_not_configured` on Gate A, so it never reaches the model call. **It will fail identically the moment Gate A is resolved.** |

⚠️ **The last row is the important one.** This does not look like a rehearsal-only problem. It is
latent in production and will surface at the worst moment — right after the env vars are finally
set and someone tries the phone for the first time.

## The fix

**Change the agent's `llm_config` handle from `letta/auto` to a currently-available model**
(`PATCH /v1/agents/{id}`), or arrange for the backend to supply an explicit `llm_config` that
actually takes effect.

**Also update `LETTA_MODEL` in `rehearsal.sh` / `rehearsal_watchdog.sh`** (both hardcode
`letta/auto`) and any Render env var carrying the same value.

## 🔴 Why I did NOT apply it

**Choosing the model is a spend and quality decision, and the zero-spend doctrine forbids me
guessing at it.** The options differ in ways I cannot resolve alone:

- `letta/auto-fast` — Letta-hosted, but I have **not verified whether it consumes credits**.
- `letta/echo` — likely zero-cost, but it is an **echo** model: it would satisfy the harness's
  "reply present" assertion **without producing a real reply**, which would make the gate pass
  while the product stays useless. **That is exactly the vacuous-check failure mode this
  codebase has already been burned by twice** (the history check that "always passed" on an empty
  conversation; the leak scan that matched a fixed string). I will not introduce a third.
- `openai/*` and others — require a provider key or credits.

**Recommendation: `letta/auto-fast`**, pending confirmation it is covered — it is the closest
like-for-like replacement for the retired auto handle and keeps the harness meaningful.

## Quota and credits — verified 2026-11-07 08:0x UTC, and it changes the recommendation's status

`letta usage` (read-only) returns:

```
Current plan: pro
Usage Credits (non-BYOK models)   Balance: 12763 credits
Usage Quota (`letta/*` models)    Bucket: empty (daily: empty)
                                  Quota Window End: 2026-11-07T12:00:00Z
                                  Daily Quota Window End: 2026-11-08T00:00:00Z
```

**Two things follow, and the first is not in the recommendation above.**

1. 🔴 **`letta/auto-fast` would ALSO fail right now.** It is a `letta/*` model, and the `letta/*`
   quota bucket is **empty** until **2026-11-07T12:00:00Z**. So the recommended fix is sound but
   **timing-dependent** — switching to it before the window resets would swap one failure for another,
   and the new failure would look like a bad model choice rather than an exhausted bucket. Verify the
   bucket is non-empty *at the moment of the change*.

2. **The credits balance is no longer 0** — it is **12,763**, where agent memory recorded 0 on
   2026-11-01. Credits cover **non-BYOK** models; `letta/*` models draw on the quota instead. So the
   two pools are separate, and a non-empty credit balance does **not** mean a `letta/*` model will work.

**A third option the report did not weigh: an external-provider model.** This agent's own configured
model is now `deepseek/deepseek-v4.1-flash` (provider type `openrouter`) — i.e. the agent itself was
already moved off `letta/auto` and onto an external provider, which sidesteps both the retirement and
the quota bucket. That is the configuration known to be working right now, and it is worth considering
for `rehearsal.sh` rather than assuming a `letta/*` handle is the only replacement.

## What is NOT claimed

- **Not fixed.** The rehearsal chat path is still broken as of this report.
- **Not a rate-limit artifact.** Ruled out by the 70s wait and by timestamp ordering.
- **Not Render's fault.** Production never reaches the model call — it 503s earlier.
- No spend, no config change, no secret touched.
