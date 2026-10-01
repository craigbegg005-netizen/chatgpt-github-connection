# [TO-CLAUDE] [TO-CHATGPT] — 2026-10-01 21:33 UTC

**From:** Oddfellow (Letta agent, `agent-a9a8eb2c-2fed-4554-9998-aa4783c7efc4`) — designated GitHub writer
**To:** Claude and ChatGPT GPT-5.6 Sol
**Branch:** `letta/combined-single-service-v0.20.4` — head `2eefe25` at time of writing (local SHA == remote SHA, verified)
**Deployed commit:** `1760892` (verified byte-for-byte 20:35 UTC; unchanged since)

---

## 1. Standing truth (verified this hour, 21:34 UTC)

- Live service: **`oddfellow-letta-backend-v0206.onrender.com`** — `/livez` → **200 in 0.15 s**:
  `{"live":true,"ready":false,"checks_failed":["LETTA_API_KEY","ODDFELLOW_OWNER_TOKEN"],"version":"0.20.6"}`
- **RUNNING, NOT READY.** The only blocker is unchanged: the two secrets on that service (Render → Environment → set `LETTA_API_KEY` + `ODDFELLOW_OWNER_TOKEN` → Save). Token values must match the vault exactly or phone access fails with a clean 401.
- Branch head `2eefe25` is ahead of the deployed `1760892` by the post-20:35 UTC commits (`b1bf3c4` front-end probe bound + "waking" state, `fa91b42` docs de-naming the dead host, `2eefe25` README cold-start note). **Agreed convention holds: no redeploy before Gate A** — these ride out with the post-secrets redeploy.
- Revenue $0. Nothing submitted, sent, charged, or deployed by me beyond branch pushes.

## 2. What changed since the 20:35 UTC handoff

Three commits on the canonical branch (parallel-session work, pulled and verified by me at 21:33 UTC):

| Commit | What |
|---|---|
| `b1bf3c4` | Front end: bounded the backend probe timeout and shows a "waking" state instead of "dead" — directly targets the free-tier cold-start misread that would have hit Craig's first phone load |
| `fa91b42` | Docs: removed the dead hostname (`oddfellow-letta-backend`) from every place a reader or tool would act on it — the identifier that caused the 20-hour blind spot |
| `2eefe25` | README: documents that four services previously called dead were only cold-starting |

Plus a new remote branch appeared: `letta/universal-connector-v0.21` (origin). I have **not** inspected it — flagging its existence so whoever owns it claims it in the next handoff. `main` also advanced `f60881b..8ddfe32`.

## 3. New on my side: BeggAi MCP server connected

My session now has a **BeggAi MCP server (10 tools)** — Stripe integration planner, Stripe API read/write/search/details, account management. Implications:

- Stripe work can now be done directly from this agent without asking Craig for keys in chat.
- Per doctrine: **zero-spend still applies** — Stripe tooling is for building the payment path, not for enabling charges. Any live-mode action needs Craig's explicit approval. I will list accounts and confirm testmode before any write.
- Not yet used. First use should be `list_available_accounts_or_orgs` to see what account(s) are attached and whether they are test or live mode.

## 4. Open items (unchanged unless noted)

1. 🔴 **Gate A — the two secrets on `oddfellow-letta-backend-v0206`.** Craig's single action. My watch fires on the `ready` flip; I then run `acceptance_check.py` + `golive_check.py` and report raw gate results.
2. 🔴 **Render service ID for `-v0206`** — still unverified; the on-record ID (`srv-dau6tgqd0e5s73egkocg`) belongs to the dead service. ChatGPT to confirm.
3. 🔴 **GitHub App repo access** — still not granted; nothing under version control proceeds beyond this repo.
4. 🧪 **Phone acceptance** — after Gate A. Phone URL = the service URL. First load may take ~30 s (free-tier cold start) — that is waking, not failing.
5. Grants lane: Arkansas verified (AEDC SBIR matching post-award only; ASBTDC free first call). Oklahoma lane void. No submissions.
6. New: whoever owns `letta/universal-connector-v0.21`, claim it.

## 5. Conventions in force

- Dated handoff files `oddfellow/HANDOFF-TO-*-YYYY-MM-DD-HHMMZ.md` with `[TO-CHATGPT]`/`[TO-CLAUDE]` commit prefix; `CURRENT_STATE.md` points to the newest.
- One AI deploys at a time; Claude is the deployer; no `RENDER_API_KEY` requests to Craig (withdrawn).
- No redeploy before Gate A.
- Status labels: VERIFIED > LIVE > DEPLOYED > CONNECTED > TESTED > IMPLEMENTED > PENDING. Never upgrade without evidence.

**No claim above outranks its evidence.**
