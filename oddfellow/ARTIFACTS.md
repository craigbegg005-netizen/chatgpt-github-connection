# Oddfellow Artifact Registry

**Purpose:** A durable, verified record of what Oddfellow has built, shipped, or verified.
**Rule:** Nothing appears here without evidence. An idea is not an artifact. A draft is not shipped.

---

## 2026-09-29 — Oddfellow Letta Backend v0.20.0

**Artifact:** `oddfellow/oddfellow_letta_backend.py`
**Status:** ✅ VERIFIED (running on Render, pass-through tested)
**Evidence:**
- Render service `oddfellow-letta-backend-v0206` live at `https://oddfellow-letta-backend-v0206.onrender.com`
- `/livez` returns 200 with version string
- `/healthz` returns 200 (database healthy)
- Pass-through to Letta API tested with real agent ID

**What it does:**
- Single FastAPI service: auth gate + Letta pass-through + Command Center + front end
- Owner-token authentication on all `/api/*` routes
- Command Center at `/command.html` (owner-only, auth-gated)
- Front end at `/` (owner-facing chat UI)

---

## 2026-09-30 — Command Center v0.20.1

**Artifact:** `oddfellow/command_center.py` + `oddfellow/frontend/command.html`
**Status:** ✅ VERIFIED (auth-gated, approval matrix, emergency pause)
**Evidence:**
- Manual browser test: `/command.html` returns 401 without token
- Approval creation tested via API
- Pause toggle tested
- Audit trail written to `audit.log`

**What it does:**
- Owner-facing control surface for approvals, pause, and audit
- Mobile-first PWA layout
- Real-time status polling

---

## 2026-10-01 — Approval Gate v0.20.2

**Artifact:** `oddfellow/command_center.py` (approval enforcement)
**Status:** ✅ VERIFIED (live-HTTP test: approval created → decided → consumed → replay refused 403)
**Evidence:**
- Live HTTP test against rehearsal instance: valid approval passes gate exactly once
- Replay of consumed approval returns 403 `not_approved`
- Expired approvals refused with state EXPIRED

**What it does:**
- Elevated-risk commands require a real APPROVED approval bound to exact payload
- Approvals are single-use (atomic consume)
- 15-minute TTL from decision
- Journal persistence via `ODDFELLOW_APPROVAL_JOURNAL`

---

## 2026-10-02 — §29 Security Gate v0.20.4

**Artifact:** `oddfellow/tests/test_section29_release_gate.py`
**Status:** ✅ VERIFIED (194 tests pass in §29 suite; 490 total)
**Evidence:**
- Full suite run: 490 passed, 39/39 fault injection
- §29 gate file exercises every claim: persisted approvals, ID, binding, expiration, consume, replay rejection, payload mismatch, denied/missing/expired/wrong-token refusals

**What it does:**
- Every security claim from the §29 checklist is now a test
- Regressions fail the build; the gate cannot quietly become false again

---

## 2026-10-02 — Evidence Verification Gate v0.20.5

**Artifact:** `oddfellow/connector/store.py` (`verify_result` with checkable evidence)
**Status:** ✅ VERIFIED (live test: bare "looks fine" refused; real URL accepted; self-verify refused)
**Evidence:**
- Live test: "looks fine" → 403 "evidence must be checkable"
- Live test: "https://evidence.example/run/1" → accepted
- Live test: submitter as verifier → refused "cannot verify own work"

**What it does:**
- Verification evidence must name something checkable (URL, path, commit hash, identifier)
- A phrase that restates the claim is not evidence
- Self-verification refused
- This was the seventh false control — docstring claimed "bare 'looks fine' is refused", code only refused *empty* evidence

---

## 2026-10-03 — Workforce Layer v0.20.6

**Artifact:** `oddfellow/workforce/` (registry, departments, workers, verification)
**Status:** ✅ VERIFIED (12 departments, 28 workers, 3 verifiers, authority ceilings enforced)
**Evidence:**
- Live test: `WorkforceRegistry` loads, `can_verify` enforces independence, spend ceilings $0.00
- Authority ceiling: no worker holds more authority than its head (fixed at `eaecddc` after sixth false control)
- Health check: `{'departments': 12, 'workers': 28, 'verifiers': 3, 'max_authority': 'A2', 'non_zero_spend_ceilings': []}`

**What it does:**
- Synthetic organization: 12 department heads, 28 specialized workers
- Authority hierarchy enforced at construction time (not just for the built-in roster)
- Spend ceilings: $0.00 across all workers by default
- Verification independence: producer cannot verify own work

---

## 2026-10-03 — Provider Capability Registry

**Artifact:** `oddfellow/connector/providers.py`
**Status:** ✅ VERIFIED (declared vs verified separation, cost-aware routing)
**Evidence:**
- Provider records exist for: letta, openai, anthropic, google, xai
- Each separates `declared` (from docs) from `verified` (from probing)
- `paid` field visible to router → zero-spend rule enforced at routing level
- `supports()` returns True only for *verified* transports

**What it does:**
- Declared capabilities are leads, not findings
- Routing trusts only verified capabilities
- Cost is a first-class capability — paid providers ineligible without owner approval

---

## 2026-10-05 — BSI Migration Documentation

**Artifact:** `oddfellow/BSI-MIGRATION-2026-10-05.md`
**Status:** ✅ VERIFIED (grep inventory of every 'begg' occurrence, each classified)
**Evidence:**
- Verified preservation of: `begg_ai_command_center`, `mcp__BeggAi__*`, the two live `begg-ai-*` Render services
- Phase 2 (system-prompt prose) explicitly waits for owner review
- No blind string replacement performed

**What it does:**
- Canonical corporate name: Begg Synthetic Industries (BSI)
- Legacy alias: Begg AI Industries
- Forbidden: "Bay Synthetic Industries"
- Technical identifiers preserved until phase 5

---

## Not Yet Artifacts (ideas, drafts, planned)

- Voice interface (deferred by owner, not implemented)
- Planner PWA v0.3 (bundle not in repo, placeholder only)
- Zero-inventory commerce (documented strategy, no listings live)
- Grants applications (drafts only, nothing submitted)

---

**This file is the record. Nothing ships without appearing here with evidence.**
