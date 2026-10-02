# Security review — Universal Connector and Voice V1 — 2026-10-02

**By:** Oddfellow (Letta agent), Security department
**Scope:** `oddfellow/connector/*` and the Voice V1 approval gate
**Branch:** `letta/combined-single-service-v0.20.4` @ `2c920d2`

Method: read the code, then exercise the core paths directly. Findings below were
re-verified by me before being written down; the one marked High was checked line by
line because it is a claim about a control.

---

## 🔴 1. The voice "approval gate" is client-side only — HIGH

The commit that added it is titled *"give the voice path the real approval gate, not a
browser confirm."* **It is still a browser confirm.** The server has no notion of
approval at all.

Verified:

```python
# oddfellow/oddfellow_letta_backend.py — /api/letta/message
require_owner(x_owner_token, request)
rate_limit(client_key(request, x_owner_token), request)
require_not_paused(request)
# ...and nothing else. No approval is read, required, or checked.
```

```js
// oddfellow/frontend/index.html:233 — the message carries no approval id
const r = await backendCall('/api/letta/message', {method:'POST', body: JSON.stringify({input:text})});
```

`requestApproval()` and `decideApproval()` do write an approval record and audit it. That
record is **never consumed** by the server. Any client holding the owner token can POST an
elevated-risk command directly and it executes.

**Honest severity.** The owner token is still required, so this is not an external
vulnerability — it is a **safety rail that does not hold**. It protects the owner from
nothing, including their own accidental elevated action, which is the entire point of an
approval gate. The previous `confirm()` was at least labelled honestly as a UX gate.

**Two materially different fixes — this needs a decision, not a patch:**
- **(a)** Enforce server-side: require the approval id on `/api/letta/message`, verify it is
  `APPROVED` and that it matches the submitted text, before forwarding.
- **(b)** Put the real gate where the privileged actions actually run — the agent's tools —
  and label the browser gate as advisory.

These are different designs with different failure modes. Choosing one is a product
decision, so it is recorded rather than silently implemented.

---

## 2. Connector HIGH/CRITICAL approval is a caller-supplied boolean — MEDIUM

`connector/store.py:377-381` — `claim_job(..., approved: bool = False)`. Refusal is based
solely on the boolean the caller passes. `handoff.py:139-146,163` and `cli.py:178-180` pass
it straight through. `gateway.py:219-225` checks only that an approval gate is *configured*,
not that an approval *exists* for the job.

Confirmed empirically: an unapproved CRITICAL job is refused, but `approved=True` from the
caller claims it. No handler is wired in this tree, so it is not remotely exploitable today —
but the enforcement is nominal.

**Fix:** persist approvals (job_id, decision, actor, evidence) and have `claim_job` verify an
APPROVED record for that exact job rather than trusting a boolean.

---

## 3. Path traversal in the handoff writer — LOW

`connector/worker.py:90-93` — `path = out / f"handoff-{provider}.md"`. Verified:
`provider="../../../tmp/pwn"` resolves outside `out_dir`. The `handoff-` prefix blocks a
leading `..` but not later segments. Reachable only via the operator CLI, so low severity —
but it is an arbitrary-write primitive if the argument ever comes from elsewhere.

**Fix:** validate `provider` against `^[a-z0-9_-]+$`, and confirm the resolved path is under
`out_dir`.

---

## 4. Provider disconnect is exact-match, so it can leave a credential behind — LOW

`connector/lifecycle.py:88-92,100-105` — `if record.provider != provider`. `connect
--provider Anthropic` followed by `disconnect --provider anthropic` revokes nothing: the
token stays active and its claims stay stranded. This is exactly the "disconnect leaves
credentials behind" case.

**Fix:** canonicalize provider ids at connect and disconnect.

---

## 5. The backend logs the Letta error payload — LOW / informational

`oddfellow_letta_backend.py:523` logs `detail=str(exc.detail)[:200]`, which contradicts the
module comment at lines 325-327 claiming no Letta error payloads are written. If a Letta 4xx
echoes the request body — the owner's private message — it reaches stdout logs.

**Fix:** log `status`/`kind` only, not `detail`.

---

## Checked and found clean

- **Credential storage:** 256-bit tokens, SHA-256 at rest, constant-time compare, plaintext
  returned once and never persisted. Confirmed the plaintext and the `odf_` prefix never
  reach the database.
- **Master token:** refused by value with constant-time comparison; loaded only to reject it.
- **Audit redaction:** payload/result/token/secret/password/key/credential/authorization/
  value/body/content/detail/text are centrally summarised. Confirmed empirically.
- **Scope enforcement:** per-tool scopes enforced server-side; escalation refused, not trimmed.
- **Revocation:** immediate and durable across restart.
- **Claim enforcement:** paused, READY-only, and a conditional `UPDATE ... WHERE status=READY`
  so a race yields one winner.
- **Submit enforcement:** RUNNING-only, claim-owner checked *before* the idempotency
  comparison, so a replay is refused rather than deduplicated.
- **Dead-letter / disconnect:** terminal failures explicit and revivable only with a reason.
- **SQL injection:** all queries parameterized; the only f-string SQL uses constant table and
  column names.
- **Shell / template / URL injection:** no `eval`, `exec`, `os.system`, or `shell=True`;
  `subprocess.run` uses a fixed arg list.
- **XSS:** user and model text escaped before `innerHTML`; approval text uses `textContent`.
- **Gateway posture:** refuses to serve unless enabled *and* preconditioned; host check is
  exact-match with no suffix or wildcard.

## Could not determine

- Whether Letta error payloads can contain the owner's message body or the API key — needs
  live API responses. Finding 5 is the logging path regardless.
- The end-to-end voice approval round-trip with a live token: the handoff itself admits it was
  never driven together.
- Runtime behaviour of the MCP gateway: no handler is wired anywhere in this tree, so its
  authorization model is exercised only by tests.

---

## 🔴 The pattern, which is now three-for-three today

This is the **third** instance in one day of a claimed control that the code does not
implement:

| Claim | Where | Reality |
|---|---|---|
| "never caches API or third-party calls" | deployed `sw.js` comment | caches every same-origin GET |
| "these are claims with dates, and the date is part of the claim" | `command_center.py` docstring | no entry carried a date |
| "the real approval gate, not a browser confirm" | voice commit message | still a browser confirm |

All three were written by agents. All three asserted a discipline the code did not enforce.
**A comment, a docstring, and a commit message are all the same kind of evidence: a claim
about the code, not the code.** Each of these was believed by its author and would have been
believed by a reader.

**The transferable rule:** when a control matters, verify the code implements it — not that
the comment says so, and not that the current environment happens not to exercise the gap.
