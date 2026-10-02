# Security review findings — status after the fix pass

**By:** Oddfellow (Letta agent), Security department
**Date:** 2026-10-02
**Supersedes the status of:** `SECURITY-REVIEW-2026-10-02.md` (which remains the
finding record; this file records what happened to each finding)
**Branch:** `letta/combined-single-service-v0.20.4` @ `a45fcc4`

Every claim below was re-verified after the fix, not carried over from the fix
commit message. Where a fix turned out to be narrower than it first looked, that
is written down rather than smoothed over.

---

## Finding 1 — the voice approval gate is client-side only — **FIXED**

**Was:** `/api/letta/message` read no approval at all. The front end created a
real approval record and waited; the server never looked at it. Any client
holding the owner token could POST an elevated-risk command straight past the
gate. The commit that added it was titled *"give the voice path the real approval
gate, not a browser confirm."*

**Now:** the server is the authority.

- `oddfellow/risk.py` classifies the incoming text server-side. The browser's
  copy is a UX hint, not the enforcement.
- `/api/letta/message` requires an `approval_id` for elevated commands and
  verifies four conditions, all fail-closed: an id was supplied; it names a real
  approval; that approval is `APPROVED`; and it is **bound to exactly this text**.
- The binding is a SHA-256 of the command, compared with `hmac.compare_digest`.
  A prefix or substring binding would let "delete the branch" authorise "delete
  the branch and transfer the balance".
- The front end sends the id with the send, and if the server refuses for want of
  an approval the local planner did not ask for, it creates that approval and
  holds — so classifier drift is a wasted round trip, not a hole.

**Verified at runtime**, not only in tests — a real uvicorn instance, with
`LETTA_BASE_URL` pointed at an unreachable port so the gate had to refuse
*before* Letta was ever reached:

| Request | Result |
|---|---|
| `delete the old branch`, no approval | `403 approval_required / no_approval_supplied` |
| the same, while `WAITING_AUTHORIZATION` | `403 / not_approved` |
| an approved id, different command | `403 / approval_mismatch` |
| an approved id, truncated prefix of the command | `403 / approval_mismatch` |
| an approved id, the exact command | gate opened → `502` from the unreachable Letta |
| `what is the zero-spend rule?` | not gated → `502` from the unreachable Letta |

### Driven end to end in a real browser

The original review recorded this as something it *could not determine*: "the
end-to-end voice approval round-trip with a live token: the handoff itself admits
it was never driven together." It has now been driven, in Chrome, against a real
backend and a local stub Letta — the real network stack, the real front end, the
real gate.

| Step | Observed |
|---|---|
| Send `delete the old branch` from the UI | Held as `apr-d81daeac02d3`; **nothing sent**; approval bar visible |
| Click **Approve** | Sent; stub replied "I received 21 characters" (the command is 21 chars) |
| Server audit for that turn | `approval_consumed` then `message_sent`, **same `request_id`** |
| Send `publish this to the store`, then **Reject** | "Rejected … Nothing was sent."; the command appears **zero** times in the server log |
| `sendText("transfer the balance", null)` — a client that supplies **no** approval id | Server refused `403 approval_required`; the front end **created the approval and held it** (`apr-88556be5c37f`) rather than showing a raw 403 |
| Approve that one | Sent; `approval_consumed` then `message_sent`, same `request_id` |

The fifth row is the drift-recovery path, and it is the one worth keeping: the
browser's classifier and the server's agree today, but the server is the
authority, so a client that misses something is *corrected* rather than allowed
through or shown an error it cannot act on.

Evidence: `/root/downloads/oddfellow-approval-gate-verified.png` (the full
conversation, including the held, approved, rejected and recovered turns).

**What this does not do.** The approval record still carries the command in its
`detail` field, because the owner has to be able to see what they are approving.
An earlier version of the `binding_hash` docstring claimed the store "never holds
a second copy of the owner's message". That was false when written; a runtime
check caught it, and the docstring was corrected rather than the code. The
property that actually holds is narrower and is the one enforcement rests on:
the *binding* is a hash, and the binding is what decides.

## Finding 2 — connector approval is a caller-supplied boolean — **FIXED**

**Was:** `claim_job(..., approved: bool = False)`. The refusal was real; the
enforcement was nominal. `apply_handoff` passed one flag for an entire batch of
results, so approving any gated job in a batch approved all of them.

**Now:** approvals are rows. `request_approval(job_id)` opens a pending record
bound to one job; `decide_approval(id, decision, actor, …)` grants or refuses it
once and records who and when; `claim_job(..., approval_id=…)` verifies the id
exists, is `APPROVED`, is bound to *this* job, and matches *this* risk level.

`approved: bool` is **removed, not deprecated** — a deprecated flag would leave
the hole open for every existing caller. A test asserts the `TypeError`.

`apply_handoff` now takes `approval_ids: dict[job_id, approval_id]`; the CLI takes
a repeatable `--approval-id JOB_ID=APR_ID`.

**Verified end to end** through the CLI: create → `request-approval` →
`decide-approval` → `apply --approval-id`, accepted as `COMPLETE` and correctly
**not** `VERIFIED`, with the whole chain visible in `audit`.

`router.route`'s `approved` is renamed `approval_granted` and documented as a
**planning input, not enforcement** — the function is pure and has no store, so it
can only be told. Callers derive it from `Store.approval_state_for_job()`, and
`claim_job` re-checks the record itself.

## Finding 3 — path traversal in the handoff writer — **FIXED**

`canonical_provider()` now rejects anything that is not `^[a-z0-9][a-z0-9_-]{0,63}$`,
and `_handoff_path` additionally asserts the resolved path's parent *is* the
output directory. Rejection rather than sanitisation is deliberate: a silently
rewritten provider id is a *different* provider, and the caller would never learn
that its disconnect targeted something else.

## Finding 4 — provider disconnect is exact-match — **FIXED, and wider than reported**

The review described this as a connect/disconnect problem. It was not: provider
ids are stored in **four** places, and canonicalising only at connect and
disconnect would have left the bug alive. `claim_job` stores the provider too, so
a job claimed by `Anthropic` stayed invisible to `disconnect_provider("anthropic")`
— the token was revoked, no claims were released, and the disconnect reported
itself clean while the work sat stranded in `RUNNING`.

The fix is at every **write** (token issue, claim, submit, verify), which is what
makes every later comparison correct rather than patching each comparison in turn.
A test asserts the claim-release case specifically, because that is the half the
original review did not name.

## Finding 5 — the backend logs the Letta error payload — **FIXED**

`audit("letta_error", …)` logged `detail`, contradicting the module comment
promising no Letta error payloads. A Letta 4xx can echo the request body — the
owner's private message — into stdout, which on Render's ephemeral disk is the
only durable record.

It now logs the status and a sanitised error *kind*. **Verified at runtime:** the
log carries `kind: letta_transport_error` and no payload; grepping the log for the
owner's message text and for the provider URL both return zero matches.

---

## Two tests were asserting things that were true and no longer load-bearing

Both were rewritten rather than deleted, and both are worth reading as evidence
of how a green test can hide a live defect.

**`test_hostile_provider_name_is_just_a_string`** passed
`"../../etc/passwd; DROP TABLE jobs"` through `claim_job` and asserted it
round-tripped intact. True while the only consumer was parameterised SQL; false
once the handoff writer interpolated the same value into a filename. It kept
passing because it tested the one consumer that was already safe.

**`test_the_approval_store_never_holds_the_command_text`** asserted the command
appeared nowhere in the record. A runtime check showed `detail` carries it. The
docstring was the thing that was wrong, not the code.

**`test_high_risk_cannot_be_claimed_before_approval`** asserted that
`claim_job(..., approved=True)` claims a CRITICAL job — the finding, written down
as the expected behaviour.

## The pattern, now four-for-four

| Claim | Where | Reality |
|---|---|---|
| "never caches API or third-party calls" | deployed `sw.js` comment | cached every same-origin GET |
| "these are claims with dates, and the date is part of the claim" | `command_center.py` docstring | no entry carried a date |
| "the real approval gate, not a browser confirm" | voice commit message | still a browser confirm |
| "the store never holds a second copy of the owner's message" | `binding_hash` docstring, written today | `detail` holds it |

All four were written by agents. All four asserted a discipline the code did not
enforce. **A comment, a docstring, and a commit message are the same kind of
evidence: a claim about the code, not the code.** The fourth one is the useful
one — it was written *during this fix*, by me, and caught by a runtime check
rather than by review.

## Evidence

- **354 tests pass** (was 232 at the branch base; +122).
- **39/39 fault injection.**
- Runtime verification of the gate over HTTP (table above).
- Runtime verification of the audit-log redaction.
- Three-way classifier drift check: `tests/test_risk.py` extracts the browser's
  regexes out of `index.html` and the Worker's out of `worker.js`, runs one
  corpus through all three, and asserts they agree — with a companion test that
  proves the extraction is reading real patterns rather than an empty function.

## Still open

- **The Worker refuses elevated commands outright** rather than gating them. It
  cannot hold an approval durably (per-isolate state), so this is the correct
  fail-closed behaviour, not a gap to close by porting. If the Worker ever needs
  to gate rather than refuse, the state has to move to durable storage first.
- **Real phone microphone / STT behaviour remains UNVERIFIED.** The gate is now
  enforced server-side, which is testable without a phone; the voice *capture*
  path is not.
- **The MCP gateway still serves nothing** — no handler is wired anywhere in this
  tree, so its authorization model is exercised only by tests.
