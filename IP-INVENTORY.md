# Begg AI Industries — IP inventory

Maintained by the Legal / Compliance / IP department (Oddfellow, Letta agent).
Last sweep: **2026-09-30 08:55 UTC**. **Updated 2026-10-02** (dependency-licence audit;
corrections to two stale statements — see the changelog at the foot of this file).

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

## Third-party dependency licences — **audited 2026-10-02**

**How this was verified.** A fresh virtualenv was built from the declared requirements and each
package's own installed metadata was read, not guessed:

```bash
cd oddfellow && python3 -m venv .venv && .venv/bin/pip install -q -r requirements-dev.txt
.venv/bin/python - <<'EOF'
import importlib.metadata as m
for d in sorted(m.distributions(), key=lambda x: (x.metadata['Name'] or '').lower()):
    md = d.metadata
    print(d.metadata['Name'], d.version,
          md.get('License-Expression') or md.get('License')
          or [c for c in (md.get_all('Classifier') or []) if 'License' in c])
EOF
```

The licence of each package below is also corroborated by the `LICENSE`/`LICENSE.md` file bundled
in its `.dist-info` directory in `site-packages`. **Versions are the ones resolved on 2026-10-02;
the requirements use `>=` ranges, so resolved versions will drift over time — the package's
declared licence is the stable part, the version is a snapshot.**

### Direct dependencies (declared in `oddfellow/requirements*.txt`)

| Package | Version | Licence | Where declared |
|---|---|---|---|
| `fastapi` | 0.142.2 | **MIT** | `requirements.txt` |
| `uvicorn[standard]` | 0.54.0 | **BSD-3-Clause** | `requirements.txt` |
| `httpx` | 0.28.1 | **BSD-3-Clause** | `requirements.txt` |
| `pydantic` | 2.13.5 | **MIT** | `requirements.txt` *(added 2026-10-02 — was imported but undeclared)* |
| `pytest` | 9.1.1 | **MIT** | `requirements-dev.txt` |
| `Pillow` | 12.3.0 | **MIT-CMU** (HPND-style) | `requirements-dev.txt` *(added 2026-10-02 — was imported but undeclared)* |

### Transitive dependencies (pulled in by the above; all permissive)

| Package | Version | Licence | Pulled in by |
|---|---|---|---|
| `starlette` | 1.7.0 | BSD-3-Clause | fastapi |
| `anyio` | 4.15.1 | MIT | fastapi / httpx |
| `pydantic-core` | 2.46.5 | MIT | pydantic |
| `annotated-types` | 0.8.0 | MIT | pydantic |
| `typing-inspection` | 0.4.4 | MIT | fastapi / pydantic |
| `annotated-doc` | 0.0.5 | MIT | fastapi |
| `typing_extensions` | 4.16.0 | PSF-2.0 | anyio / pydantic |
| `idna` | 3.20 | BSD-3-Clause | httpx / anyio |
| `httpcore` | 1.0.9 | BSD-3-Clause | httpx |
| `h11` | 0.16.0 | MIT | httpcore |
| `certifi` | 2026.7.22 | **MPL-2.0** | httpx |
| `click` | 8.5.0 | BSD-3-Clause | uvicorn |
| `httptools` | 0.8.0 | MIT | uvicorn[standard] |
| `uvloop` | 0.23.0 | MIT | uvicorn[standard] |
| `watchfiles` | 1.3.0 | MIT | uvicorn[standard] |
| `websockets` | 17.1 | BSD-3-Clause | uvicorn[standard] |
| `python-dotenv` | 1.2.4 | BSD-3-Clause | uvicorn[standard] |
| `PyYAML` | 6.0.3 | MIT | uvicorn[standard] |
| `opentelemetry-api` | 1.45.0 | Apache-2.0 | fastapi |
| `iniconfig` | 2.3.0 | MIT | pytest |
| `pluggy` | 1.6.0 | MIT | pytest |
| `packaging` | 26.3 | Apache-2.0 OR BSD-2-Clause | pytest |
| `Pygments` | 2.21.0 | BSD-2-Clause | pytest |

**Result:** every dependency is under a permissive licence (MIT / BSD / Apache-2.0 / PSF), with a
single exception — **`certifi` is MPL-2.0**, a *file-level* copyleft licence. That is not a
blocker: MPL-2.0 permits use as a dependency and imposes no obligation to release the consuming
code; its source-disclosure obligation attaches only to *modified* certifi files, and certifi is
used here unmodified. It is recorded explicitly because it is the one licence in the tree that is
not permissive.

**Not audited, stated rather than assumed:** the licence of the *build/runtime platform* (Render,
Cloudflare Workers) and of any base container image or system library is **not** covered here —
this audit is limited to the Python dependency tree installed from `requirements*.txt`. No
freedom-to-operate or patent analysis has been done on any dependency.

## What this lane has NOT done, and why

- ~~**No clearance search has been run.**~~ **Corrected 2026-10-02:** a public-register clearance
  search *was* run on 2026-09-30 and is recorded in
  [`IP-CLEARANCE-SEARCH-2026-09-30.md`](IP-CLEARANCE-SEARCH-2026-09-30.md) (US + Australia). That
  statement was stale when written. **The EU/UK half is still open** — see that file's addendum.
- **No filing has been made**, and none is claimed. Filing costs money and is an owner decision.
- **No freedom-to-operate analysis** on the name or on any third-party component.
- ~~**No licence audit** of dependencies.~~ **Done 2026-10-02:** the full installed dependency
  tree was audited from package metadata and is recorded under
  [Third-party dependency licences](#third-party-dependency-licences--audited-2026-10-02) above.
  All permissive except `certifi` (MPL-2.0, file-level copyleft, used unmodified).
- **No terms of service, privacy policy or app-store compliance review.** These become necessary
  before any public product launch, not before a private rehearsal.

## Standing rules for this lane

1. **Never claim a registration, filing, licence or legal approval that has not been verified.**
2. **Never publish a novel asset publicly before evaluating protection** — publication can destroy
   novelty for patents and weaken trade-secret position.
3. **Preserve human creative-direction records** for AI-assisted works.
4. **Keep the Peace Framework's IP entirely separate** from Begg AI's.
5. **Spending on legal work is an owner decision**, always.

## Changelog

### 2026-10-02 — dependency-licence audit and two corrections

- Added the **Third-party dependency licences** section: full installed tree audited from package
  metadata in a fresh venv (30 packages; all permissive except `certifi`, MPL-2.0, unmodified).
- **Corrected** the stale claim "No clearance search has been run" — the search was run
  2026-09-30 and is recorded in `IP-CLEARANCE-SEARCH-2026-09-30.md` (US + Australia; EU/UK open).
- **Corrected** "No licence audit of dependencies" — now done (see above).
- Recorded the repository's **licence posture** separately in
  [`LICENSE-STATUS.md`](LICENSE-STATUS.md): there is no licence file and no stated intent, so the
  posture is **undecided and is an owner decision**. No licence was invented.
- Added the two undeclared-but-imported dependencies to the requirements files: `pydantic` to
  `oddfellow/requirements.txt`, `Pillow` to `oddfellow/requirements-dev.txt` (see the direct-
  dependency table for licences).

**Unverified / not done:** EU and UK clearance (both registers blocked automated access — see the
clearance file's addendum); platform and system-library licences; any freedom-to-operate or
patent analysis; and any filing or registration, none of which is claimed.
