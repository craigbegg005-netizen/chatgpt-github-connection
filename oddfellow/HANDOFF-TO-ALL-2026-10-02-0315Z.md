# [TO-ALL] Universal handoff — 2026-10-02 03:15 UTC

**From:** Oddfellow (Letta agent `agent-a9a8eb2c-2fed-4554-9998-aa4783c7efc4`)
**Canonical branch:** `letta/combined-single-service-v0.20.4` @ **`7372606`**
**Rule:** every line below is evidenced in this repository or by a command whose
output is quoted. Nothing is carried over from a handoff on trust.

---

## 1. The headline: §29 is satisfied, and it is now a test file

The universal handoff's §29 security checklist is **implemented and verified**.
Every item is a test in `oddfellow/tests/test_section29_release_gate.py`, so the
checklist cannot quietly become true again.

Running it found a real gap: **the Command Center's approval record had no
`decided_by` field at all.** The audit line knew who decided; the record did
not, so anything reading the record alone could not answer "who approved this?"
The connector's record had carried it all along. `decide()` now takes and stores
the actor.

§29 items verified by running code:

| Item | Where |
|---|---|
| persisted approvals, approval id | `test_29_approvals_are_persisted_with_an_id` |
| normalized binding digest | `test_29_the_binding_is_a_normalized_digest` |
| actor, decision, timestamps | `test_29_the_record_carries_actor_decision_and_timestamps` |
| expiration | `test_29_expired_approval_is_refused` |
| consumed state, single-use atomic consume, replay rejection | `test_29_replay_is_refused` |
| server-side validation, missing approval | `test_29_missing_approval_is_refused` |
| payload mismatch, prefix-extension | `test_29_payload_mismatch_is_refused`, `..._a_prefix_does_not_authorise_a_longer_command` |
| denied / expired / unknown approval | three separate tests |
| ambiguous approval | `test_29_ambiguous_approval_cannot_be_applied` |
| wrong-owner-token | `test_29_wrong_owner_token_is_refused_even_with_a_valid_approval` |
| pause override | `test_29_pause_overrides_a_valid_approval` |
| connector approval evidence | `test_29_the_connector_records_persisted_approval_evidence` |
| provider-name path traversal | `test_29_provider_name_path_traversal_is_refused` |
| provider-disconnect case normalization | `test_29_provider_disconnect_is_case_normalized` |
| Letta error payload logging | `test_29_letta_error_payloads_are_not_logged` |
| regression tests exist | `test_29_security_regression_tests_exist` |

## 2. The five false controls, and the two I wrote myself

A "false control" is a comment, docstring or commit message asserting a
discipline the code does not enforce. Five were found on 2026-10-01/02:

| Claim | Where | Reality |
|---|---|---|
| "never caches API or third-party calls" | deployed `sw.js` comment | cached every same-origin GET |
| "these are claims with dates" | `command_center.py` docstring | no entry carried a date |
| "the real approval gate, not a browser confirm" | voice commit message | still a browser confirm |
| "the store never holds a second copy of the owner's message" | `binding_hash` docstring | `detail` holds it |
| "prose in the `error` field cannot smuggle it into the log" | `_error_kind` docstring | the pattern allowed spaces |

**The last two were written by me, during the fix pass that was fixing the other
three.** Writing a fix is not a protected activity. Both were caught by checks
rather than by review — one by a runtime probe, one by a QA pass.

## 3. A QA pass broke three of the fixes

The QA lane was asked to falsify rather than confirm. It found three real
defects, all now fixed:

1. **The risk classifier was a verb allowlist.** `rm -rf / --no-preserve-root`,
   `DROP TABLE jobs;`, `git push --force`, `curl … | bash` were **every one
   classified "normal"** and forwarded to Letta with no approval at all. Fixed
   with a structural layer. It is still a heuristic and **not a sandbox** — the
   honest limit is that this cannot be made complete by adding patterns. The
   real fix is to gate the *actions* rather than classify free text, and that
   remains open.
2. **`_error_kind` allowed spaces** while its docstring claimed prose could not
   get through. Spaces are what prose needs. Now identifiers-only.
3. **`Store.create_job`** stored `job.provider` verbatim — the one write path
   that skipped canonicalisation.

And a fourth, found by running the extracted regex in a **real JS engine**:
`"rm -rf / ?"` was elevated in Python and normal in the browser. The three-way
drift check missed it because its corpus did not contain the case. A drift check
is only as good as its corpus.

## 4. Evidence

- **487 tests pass** (232 at the start of this cycle).
- **39/39 fault injection.**
- The approval gate driven **end to end in a real Chrome** against a real
  backend and a local stub Letta: held → approved → sent; rejected → nothing
  sent; and a client supplying *no* approval recovering rather than erroring.
  Screenshot: `/root/downloads/oddfellow-approval-gate-verified.png`
- The front end's classifier verified in node against 14 cases.

## 5. Branch heads (re-derive; this is a snapshot)

| Branch | Head | Note |
|---|---|---|
| `letta/combined-single-service-v0.20.4` | `7372606` | **canonical** |
| `letta/universal-connector-v0.21` | `8f9c139` | merged into canonical |
| `letta/voice-v1` | `9becaa8` | merged into canonical |
| `main` | `8ddfe32` | index only; **not** a deploy source |

Canonical is named `v0.20.4` but the code reports **`0.20.6`**. Report both.

## 6. Live services (probed, not assumed)

| Service | Result |
|---|---|
| `oddfellow-letta-backend-v0206` `/livez` | **200**, `ready:false`, `checks_failed: [LETTA_API_KEY, ODDFELLOW_OWNER_TOKEN]`, v0.20.6 |
| `oddfellow-letta-backend-v0206` `/healthz` | **503**, fail-closed |
| `oddfellow-letta-backend` (legacy) | **no HTTP response at all** — dead |
| `oddfellow-letta-poc` `/healthz` | 200 `{"ok":false}` — v0.20.2, unconfigured |

## 7. Blockers

1. **Gate A** — `LETTA_API_KEY` and `ODDFELLOW_OWNER_TOKEN` on
   `oddfellow-letta-backend-v0206`. Owner action; the only thing between the
   owner and a working authenticated Oddfellow.
2. **Real phone microphone / STT** remains UNVERIFIED. The gate is now
   server-enforced and testable without a phone; voice *capture* is not.
3. **`render.yaml` `name:`** does not match the live service. Documented in-file
   and flagged as needing owner authorization — a Blueprint name change is a
   Render control-plane action that could create a new service or act on the
   live one, and no agent here has Render access.
4. **The MCP gateway serves nothing** — no handler is wired anywhere in this
   tree, so its authorization model is exercised only by tests.

## 8. Corrections to incoming handoff information

- The handoff's §29 list is **satisfied**; it was listed as an open blocker.
- The handoff's "previously observed canonical head `83c3d73`" is **stale**;
  canonical is `7372606`.
- The handoff's §38 blocker 1 ("Oddfellow server-side approval enforcement") is
  **closed**.
- The handoff's §38 blocker 4 (Planner v0.3) is **not verified by me** — I have
  not looked at it this cycle. Treat as unverified rather than open or closed.
- The handoff's §38 blocker 3 (ChatGPT GitHub 403) is **not reproducible from
  this agent** — GitHub pushes from here succeed.

## 9. What I did not do

- **No deployment.** The canonical branch is deployable but I did not trigger
  one; that is an owner-gated action and Gate A is unset anyway.
- **No spend.** Zero, as always.
- **No secrets** in any file, log, commit, or output.
- **No claims about the Planner, Product Factory, Brooks, Grants, or Peace.**
  I did not work those lanes this cycle and will not report on them.
