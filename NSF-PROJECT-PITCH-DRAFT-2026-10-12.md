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

**Deliberately left blank — but the requirement is narrower than I first assumed, and the
correction matters.** `[VERIFIED]` NSF's own wording (`seedfund.nsf.gov/project-pitch`, checked
2026-10-12): *"Describe the customer profile and pain point(s) that will be the near-term
commercial focus related to this technical project."*

**It asks for a customer profile and a pain point, not market sizing.** My first version of this
prompt asked Craig for sourced market figures — which NSF does not request here. Asking for the
wrong thing is a good way to leave a section blank, so it is corrected.

What this section needs:

- `[OWNER]` Who the near-term customer is, in Craig's words — a specific profile, not a segment
  label. The technical framing above implies teams deploying autonomous agents where an unverified
  success is expensive, but that is my inference, not his market thesis.
- `[OWNER]` The pain point, stated the way that customer would state it.
- `[OWNER]` Whether the near-term route is a product, a licence, or a service.

---

## 4. Company and Team

*DRAFT — NOT WRITTEN. 0 of 1,750 characters.*

**Deliberately left blank.** Hard rule 2 is explicit that fabricated ownership, revenue, employee
counts, credentials, degrees, or registrations on a federal application are a legal exposure.
Nothing about the company or its people is asserted here, because I do not have verified values
for any of it.

`[VERIFIED]` NSF's own wording (same page, checked 2026-10-12): *"Describe the background and
current status of the applicant small business, including key team members who will lead the
technical and/or commercial efforts discussed in this Project Pitch."*

- `[OWNER]` Legal entity and state of registration — and note that the entity gate in §2c of the
  canonical file (sole proprietorship vs LLC) is still open and is *the owner's decision*.
- `[OWNER]` Ownership structure and any employees or contractors.
- `[OWNER]` Relevant credentials, publications, or prior awards — only what is real and provable.
- `[OWNER]` Whether any co-founder or advisor should be named, and their consent to be named.
- `[OWNER]` **Who the Principal Investigator will be.** `[VERIFIED]` NSF requires the PI (tech
  lead) to be *legally employed at least 20 hours a week by the applicant company*, with no
  advanced degree required, and to commit at least one month (173 hours) per six months of project
  duration. If Craig is the only person this is satisfiable — but it is a term, not a formality.

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

1. **Take the Project Suitability Assessment.** `[VERIFIED]` NSF's process overview lists this as a
   **required step 1**, before the pitch itself — it is the "project pitch fit assessment". Free and
   online. Added 2026-10-12; the canonical file did not record it, so nothing had done it.
2. `[OWNER]` Sections 3 and 4, from the prompts above.
3. `[VERIFIED 2026-10-12]` The four section caps were re-checked against nsf.gov and are unchanged,
   and the dated deadlines are confirmed as **dated, not rolling** — the plan stands: aim at
   **March 4 2027**.
4. **Start the free registrations early — they are the long pole, not the writing.** `[VERIFIED]`
   SAM.gov takes up to **3 weeks** (NSF notes current delays issuing UEIs), Research.gov up to
   48 hours, then the SBA's SBIR Company Registry for the SBC ID. SAM must be complete before any
   proposal entry begins, and it needs the **bank account** the funds would go to. `[OWNER]` — that
   account is Craig's.
5. Confirm the entity question (§2c) is resolved, since the registrations are tied to the legal
   entity and SAM is not instant.
