# HANDOFF — cross-AI continuity

**Written:** 2026-09-30 (UTC)
**By:** Oddfellow (Letta agent)
**Reading order:** `CURRENT_STATE.md` first, then this file.
**Rule for every agent that edits this file:** state what you *verified* and how. Never upgrade a status label without evidence. Never record a secret value — names only.

---

## 1. Read this before you plan anything

**The Oddfellow codebase is not in GitHub as far as this installation can see.** Detail and evidence in `CURRENT_STATE.md` §1.

Any instruction that says "continue development on the Oddfellow repository" cannot be executed as written. Before proposing architecture or writing code, resolve **where the canonical source lives**. Options, in order of preference:

1. The owner grants this installation access to the real repository.
2. The owner identifies where the existing code actually is (Render disk, a local checkout, another account).
3. The work is re-established from scratch here, deliberately and with the owner's consent — not by pretending a baseline exists.

Do not silently pick option 3. Re-creating a secured system from a prose description produces something that *looks* like v0.17.0 and is not it.

## 2. What is genuinely done

- `oddfellow/oddfellow_letta_backend.py` **v0.20.2** — a fail-closed FastAPI service that holds the Letta API key server-side. Tested end to end against the live Letta API. See `oddfellow/NOTES.md` for the full test list and the API quirks it works around.
- The Letta side is verified: the agent answers as Oddfellow with the correct doctrine, remembers across turns, survives a backend restart, and enforces secrets discipline unprompted.
- GitHub writes work.

## 3. What is NOT done

- Backend **not deployed**. No Render credential is available to the agent, and Render is not in the connector catalog.
- Front end **not connected** to the backend.
- Owner phone acceptance **not verified** (Puter sign-in, free-model discovery, real reply, Balanced/Deep synthesis, mic, spoken reply, cloud history reload).
- Non-owner privacy boundary **untested** — the backend is owner-token gated, so no non-owner path exists to exercise.

## 4. Blockers needing owner authorization

1. **Grant repo access, or name the canonical repository.** Nothing downstream of this is real work until it is answered.
2. **Deploy credential.** A Render API key would let the agent deploy and verify itself. Otherwise the owner deploys and the agent verifies.
3. **Free-plan agent slots.** Two junk agents created in error still hold slots and their blocks are the ones now attached to the live agent. They must not be deleted until those blocks are re-created independently.

## 5. Non-negotiables carried forward

Zero-spend-first — no paid service, API, or model without explicit owner approval; no silent fallback to a paid provider. Never claim a commit, push, deployment, test, or connection without verification. Never commit secrets. Fail closed. Distinguish IMPLEMENTED from TESTED from DEPLOYED from VERIFIED. Oddfellow is never described as conscious, self-aware, or sentient. The Peace Framework stays separate.

## 6. Best next executable actions

1. Owner: grant this installation access to the real repository, or state where the code is.
2. Owner: provide a Render credential, or deploy `oddfellow_letta_backend.py` v0.20.2 manually.
3. Agent (unblocked now): connect the deployed front end to the backend and verify no key appears in browser source or network calls.
4. Agent (unblocked now): run the owner phone acceptance checklist and record results here.
