# Begg AI Industries — IP inventory

Maintained by the Legal / Compliance / IP department (Oddfellow, Letta agent).
Last sweep: **2026-09-30 08:55 UTC**.

**This is not legal advice, and nothing here is a registration.** No trademark, patent,
copyright registration, licence or filing is claimed to exist for any Begg AI asset unless a
line below says VERIFIED and names the register. Anything unmarked is **UNKNOWN — not checked**.

The protocol's rule for this lane is explicit: *do not falsely state that a patent, trademark,
copyright registration, license, filing, or legal approval exists unless verified.* This document
exists so that rule has somewhere to live.

---

## ⚠️ Finding of the first sweep: the name "Oddfellow" is crowded

A public search on 2026-09-30 found **multiple third parties using "Oddfellow" / "Oddfellows"
commercially**, including two live US registrations. None is in the class an AI product would
occupy, but the name is not clear.

| Mark | Owner | Class / goods | Status | Source |
|---|---|---|---|---|
| ODDFELLOWS | 316 W Seventh LP (Dallas, TX) | **Class 043** — cafe-restaurants | **REGISTERED AND RENEWED** (Reg. 3935909, filed 2010, renewed 2021-01-08) | USPTO serial 85070017 |
| ODDFELLOWS ICE CREAM CO. | Oddfellows Management LLC → Oddfellows Holding Company LLC (New York, NY) | **Class 030** — ice cream and frozen desserts | **SECTION 8 & 15 ACCEPTED** (Reg. 5706838, registered 2019-03-26) | USPTO serial 87624527 |
| ODDFELLOWS | Oddfellows Pty Ltd (NSW, Australia) | **Class 035** — advertising, marketing, PR, business management | **REMOVED — not renewed** (filed 2013) | IP Australia 1587873 |
| Oddfellows (studio) | Oddfellows, Portland OR | Motion design / creative studio, trading actively | In commercial use | oddfellows.tv |

**What this does and does not mean.** Both live US registrations sit in classes unrelated to
software or AI services, and trademark rights are class-specific — so this is **not** a
statement that the name is unavailable. It **is** a statement that the name is in active use by
several businesses, that a clearance search is required before any filing, and that the risk of
confusion is a real question rather than a hypothetical one.

**Zero-cost next step:** a proper clearance search in the classes an AI product would occupy
(typically 009 for software and 042 for SaaS/technology services), by class and by jurisdiction,
before any filing or any significant spend on the name. Free public registers — USPTO TESS,
EUIPO, IP Australia, UK IPO — cover most of it. A paid attorney opinion is the only way to get
certainty, and that is a spending decision for the owner.

---

## Asset inventory

| Asset | Type | Protectable? | Registration status |
|---|---|---|---|
| **Oddfellow** (product name) | Word mark | Possibly — but see the finding above | **UNKNOWN.** No filing by Begg AI. Name is in third-party use. |
| **Begg AI Industries** (company name) | Word mark | Possibly | **UNKNOWN.** Not checked. |
| **Global Peace & Human Security Framework** | Copyright in a literary work | Yes, automatically on fixation | **SEPARATE PROJECT — tracked separately, never merged with Begg AI records.** |
| Oddfellow source code (`oddfellow/` in this repo) | Copyright in a literary work | Yes, automatically on creation | **UNKNOWN** ownership position. Written by AI agents under the owner's direction; see the note below. |
| Oddfellow front end, PWA, icons | Copyright / design | Yes | **UNKNOWN.** |
| `RESOURCES.md`, handoffs, cycle logs, this document | Copyright | Yes | **UNKNOWN.** |
| 7-Day Reset Planner (PDF, listing) | Copyright in a literary/artistic work | Yes | **UNKNOWN.** Listing exists on Gumroad; no registration claimed. |
| Brooks World characters (Emma Brooks, Mia Vale, Jordan Blake, Ma, Pa) | Copyright; possibly trade mark | Yes | **UNKNOWN.** Names are generic personal names, which are weak marks. |
| Small Business Marketing Kit (Canva) | Copyright / design | Yes | **UNKNOWN.** |
| App Factory concepts (Everyday Tools, Household Task Board, Pantry First, Service Mile, Keep the Receipt, Renewal Watch, Small Business Starter, Ready Card, Home Ledger, Opportunity Exchange) | Names; some may be descriptive | Weak to unknown | **UNKNOWN.** Several are descriptive and would be hard to protect as marks. |
| Domain names | — | — | **UNKNOWN.** None verified as owned. |

### The AI-authorship question, stated rather than assumed

A large part of this repository was written by AI agents. In several jurisdictions, purely
machine-generated output may not attract copyright at all, and the position is unsettled and
jurisdiction-specific. **The practical mitigation is already the doctrine**: preserve records of
human creative direction — the owner's instructions, decisions and review — because that is what
establishes the human contribution. This repository's commit history, handoffs and cycle logs are
exactly that record, which is a second reason to keep them.

---

## Trade secrets

| Asset | Treatment |
|---|---|
| `ODDFELLOW_OWNER_TOKEN`, `LETTA_API_KEY` and any future credential | **Trade secret / confidential.** Server-side environment variables only. Never in chat, source, screenshots, handoffs or logs. Verified clean by a repo-wide scan on 2026-09-30 (0 matches across seven key-shaped patterns). |
| The recovered API surfaces (`recovered/`) | Public information — they were fetched from public endpoints. **Not** a trade secret. |
| The rehearsal tunnel URL | Ephemeral and unauthenticated at the edge; the owner token is the actual control. Not a secret in itself, but not to be treated as private either. |

---

## What this lane has NOT done, and why

- **No clearance search has been run.** That is the next step and it is free at the public-register
  level.
- **No filing has been made**, and none is claimed. Filing costs money and is an owner decision.
- **No freedom-to-operate analysis** on the name or on any third-party component.
- **No licence audit** of dependencies. `requirements.txt` is small (fastapi, uvicorn, httpx) and
  the harnesses are stdlib-only, but that is an observation, not an audit.
- **No terms of service, privacy policy or app-store compliance review.** These become necessary
  before any public product launch, not before a private rehearsal.

## Standing rules for this lane

1. **Never claim a registration, filing, licence or legal approval that has not been verified.**
2. **Never publish a novel asset publicly before evaluating protection** — publication can destroy
   novelty for patents and weaken trade-secret position.
3. **Preserve human creative-direction records** for AI-assisted works.
4. **Keep the Peace Framework's IP entirely separate** from Begg AI's.
5. **Spending on legal work is an owner decision**, always.
