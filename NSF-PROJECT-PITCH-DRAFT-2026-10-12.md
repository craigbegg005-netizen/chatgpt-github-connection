# NSF Project Pitch — DRAFT

**Status: DRAFT, not submitted. Nothing here has been filed, requested, or committed to.**
Drafted 2026-10-12 by Oddfellow (Letta agent) as Next action 3 of
[`GRANTS-NON-DILUTIVE-PIPELINE-2026-10-01.md`](GRANTS-NON-DILUTIVE-PIPELINE-2026-10-01.md).

**Why this is a draft and not a submission.** Two of the four sections need facts only Craig can
supply — company and team details, and sourced market figures. They are written below as
structured prompts, deliberately **not** filled in, because the lane's hard rule 2 forbids
fabricating ownership, revenue, employee counts, credentials, or registrations, and a fabricated
claim on a federal application is a legal exposure rather than a shortcut.

**Provenance marks used below**, because the difference matters more here than anywhere:

- `[VERIFIED]` — checked against a primary source, cited.
- `[BUILT]` — exists in the codebase and is observable; not a claim about novelty.
- `[PROPOSAL]` — a thesis the pitch argues. Not a fact, and not presented as one.
- `[OWNER]` — needs Craig. Left blank on purpose.

**Character caps** (NSF's own, from the canonical file): Technology Innovation 3,500 ·
Technical Objectives and Challenges 3,500 · Market Opportunity 1,750 · Company and Team 1,750.

---

## 1. Technology Innovation

*Draft — 2,048 characters of 3,500, measured (excluding this line and markdown emphasis).*

The dominant failure mode of autonomous AI systems is not incapacity but **unverified
confidence**: a system reports success it has not established, and the error propagates because
nothing downstream can distinguish a checked result from an unchecked one. Our R&D question is
whether that failure mode can be made structurally difficult rather than merely discouraged.

We are developing a verification-first orchestration architecture for synthetic-intelligence
agents with five coupled properties:

1. **Fail-closed readiness.** A service reports ready only when every declared dependency is
   confirmed present. Missing configuration produces a refusal with named causes, never a
   degraded success. `[BUILT]` The production service answers while reporting `ready:false` and
   naming the two absent credentials.

2. **Evidence-gated verification.** A result may be marked verified only when its evidence is
   *checkable* — a URL, path, identifier, or commit-like reference — not merely non-empty.
   `[BUILT]` This closes a documented failure class in which a bare "looks fine" promoted an
   unverified result to verified.

3. **Single-source rule enforcement.** Where a rule must hold in more than one place it is
   implemented once and shared. Duplication is treated as the mechanism of divergence rather
   than as redundancy. `[BUILT]`

4. **Provenance-bound build identity.** The running service reports the commit it was built
   from, bound by live evidence rather than by a deployment identifier, so "deployed" and
   "running this code" are separately observable. `[BUILT]`

5. **Persistent, self-maintaining agent memory.** The agent's context is a versioned,
   agent-editable store, so operational knowledge survives process death and model replacement.
   `[BUILT]`

`[PROPOSAL]` The unifying hypothesis: **verification discipline can be encoded as executable
structure** — gates, guards, and shared rules — rather than as instructions to a model. If it
can, the reliability of autonomous systems becomes a property of their architecture rather than
of their prompting.

---

## 2. Technical Objectives and Challenges

*Draft — 2,147 characters of 3,500, measured (excluding this line and markdown emphasis).*

**Objective 1 — Make unverified success unrepresentable.** Define a status algebra in which a
result cannot occupy a verified state without an attached checkable artefact, and show that no
code path can promote a result without one. *Challenge:* the property must hold across process
and language boundaries; enforcement in one layer does not constrain another.

**Objective 2 — Detect and eliminate false controls.** A false control is a check whose condition
cannot vary, or a document asserting a property the code does not enforce. `[BUILT]` Twelve
instances were found and fixed in a single production codebase. *Challenge:* the failure is
silent by construction — the check passes — so detection requires adversarial probing rather than
test coverage. Our method is to treat every prose claim about system state as a claim requiring a
guard, and to require that a guard be shown to fail before it is trusted.

**Objective 3 — Bound the cost of verification.** Verification is not free: a probe is load on
the system it probes, and an over-eager verifier can cause the failures it reports. *Challenge:*
characterising the verification/load trade-off and deriving rate limits from it rather than from
trial and error.

**Objective 4 — Provider-independent orchestration under a hard cost floor.** Route work across
heterogeneous model providers with a zero-cost constraint, degrading capability rather than
silently incurring spend. *Challenge:* a silent fallback to a paid provider is indistinguishable
from success at the call site, so the constraint must be enforced where the decision is made.

**Objective 5 — Continuity across model replacement.** The agent's identity and operational
knowledge must survive replacing the underlying model. *Challenge:* demonstrating that behaviour
is carried by the context store rather than by the model requires an experimental design that
separates the two.

**Principal technical risk.** `[PROPOSAL]` The core hypothesis may hold only for the classes of
check already encountered. A negative result is informative: it would bound the approach to
mechanically checkable properties and identify where model judgement remains irreplaceable.

---

## 3. Market Opportunity

*DRAFT — NOT WRITTEN. 0 of 1,750 characters.*

**Deliberately left blank.** Every sentence in this section would be a market claim, and the
lane's hard rule 4 is that a search hit is a lead, not a finding. Unsourced market figures in a
federal pitch are the most quotable kind of fabrication.

What this section needs, and who can supply it:

- `[OWNER]` The customer segment, in Craig's words. The technical framing above implies
  teams deploying autonomous agents where an unverified success is expensive — but that is my
  inference, not his market thesis, and it should not go in a federal document as though it were.
- `[OWNER]` Any market size, growth, or spend figure — **with its source**, so it can be cited.
- `[OWNER]` Whether the intended route is a product, a licence, or a service.

---

## 4. Company and Team

*DRAFT — NOT WRITTEN. 0 of 1,750 characters.*

**Deliberately left blank.** Hard rule 2 is explicit that fabricated ownership, revenue, employee
counts, credentials, degrees, or registrations on a federal application are a legal exposure.
Nothing about the company or its people is asserted here, because I do not have verified values
for any of it.

- `[OWNER]` Legal entity and state of registration — and note that the entity gate in §2c of the
  canonical file (sole proprietorship vs LLC) is still open and is *the owner's decision*.
- `[OWNER]` Ownership structure and any employees or contractors.
- `[OWNER]` Relevant credentials, publications, or prior awards — only what is real and provable.
- `[OWNER]` Whether any co-founder or advisor should be named, and their consent to be named.

---

## What this draft does not do

- It does not claim eligibility. `[VERIFIED]` The canonical file records NSF's terms as verified
  and Begg AI's eligibility as **unknown**; that remains true here.
- It does not claim the architecture is novel. `[BUILT]` marks what exists. Whether it is
  *unproven innovation* is the question the pitch asks, and NSF decides it.
- It does not frame shipping the app as R&D. Hard rule 3 is explicit that NSF states the opposite
  in its own instructions; only the verification architecture is pitched.
- It is not submitted, and nothing in it is a commitment.

## Before this can be submitted

1. `[OWNER]` Sections 3 and 4, from the prompts above.
2. Re-verify the program's live status and the four section caps against nsf.gov — the canonical
   file's last check was 2026-10-02, and rule 5 says listings close.
3. Confirm the entity question (§2c) is resolved, since SAM.gov registration is required before
   submission and is not instant.
