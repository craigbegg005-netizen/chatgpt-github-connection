# BSI Migration — Begg Synthetic Industries

**Status: IMPLEMENTED (this document) / PLANNED (phases 2–5). Not deployed anywhere.**
**Canonical corporate name: Begg Synthetic Industries (BSI). Legacy alias: Begg AI Industries.**
**Do NOT use "Bay Synthetic Industries" — a mistaken intermediate name. Never used.**

This document is the migration's durable record. ChatGPT drafted it 2026-10-05 but its
GitHub integration is read-only (403 on write), so it asked any authorized writer to
commit it. This is that commit, expanded with a verified inventory of where the legacy
name actually lives.

## Architecture

```
OWNER
  ↓
BSI (Begg Synthetic Industries)
  ↓
ODDFELLOW (synthetic operating/orchestration layer)
  ↓
SYNTHETIC DEPARTMENT HEADS
  ↓
AI / SYNTHETIC WORKERS
  ↓
SPECIALIZED AGENTS / PROVIDER ADAPTERS / TOOLS
```

Oddfellow is a persistent synthetic-intelligence operating layer, not a chatbot wrapper.
No claims of consciousness or sentience — about Oddfellow or any worker.

## Compatibility rule

Do not rename technical identifiers merely for cosmetic consistency. Preserved
unchanged in this migration (verified by grep, 2026-10-05):

- `begg_ai_command_center` — the Command Center's `service` identifier string
  (`oddfellow/command_center.py:436`). Changing it would break anything matching on
  it, including tests and any external probe.
- `mcp__BeggAi__*` — the MCP server tool namespace (`connector/verify_capabilities.py`).
  Named by the harness, not by us.
- `begg-ai-industries-v013`, `begg-ai-core-v010` — live Render services whose API
  surfaces are the only surviving record of source code that exists nowhere in version
  control. Renaming a live service risks losing that record. **Do not touch.**
- The workforce layer already says "Begg Synthetic Intelligence System" — ahead of
  this migration, not behind it.

## Consumer-brand rule

BSI is the parent/owner. Products, apps, games, storefronts and ventures retain
independent customer-facing identities — "BSI" is not placed on every product.
Brooks / EM Brooks Home remains a separate consumer brand; BSI internal infrastructure
is never exposed inside ordinary Brooks consumer content.

## Verified inventory of the legacy name (2026-10-05, grep of code + docs)

| Where | Type | Action |
|---|---|---|
| `oddfellow_letta_backend.py:281,296` | system-prompt prose sent to the agent ("Begg AI Industries for its owner…", "Begg AI Industries doctrine") | **Phase 2 candidate** — safe prose; update when the owner confirms the public-facing name. Not changed yet because it shapes agent behavior and the owner has not reviewed the wording. |
| `README.md:199`, `RESOURCES.md:1`, `IP-INVENTORY.md:1,49`, `GRANTS-*.md` | documentation | **Phase 1 — this document establishes the canonical name; files migrate as each is next edited.** No blind bulk replace: each file's context decides whether "legacy alias" needs noting. |
| `LIVE-REHEARSAL-*.md`, `CORRELATION-*.md` | historical records | **Never rewritten.** They are audit history; the name was correct when written. |

## Migration phases (owner-directed order)

1. ✅ **Documentation / canonical terminology** — this document.
2. ⏳ Internal labels, manifests, schemas, safe UI copy — pending owner review of the
   system-prompt wording change.
3. ⏳ Corporate-facing references.
4. ⏳ External accounts where safe.
5. ⏳ Infrastructure/service identifiers — **LAST**, and the two `begg-ai-*` Render
   services are excluded until their source is recovered into version control.
6. ⏳ Regression/security verification after each phase — 579 tests pass at the time
   of this writing (`b635f3d`); re-run after every phase.

## Truth in labeling

Nothing in this file changes any deployed behavior. The live service, the front end,
and all identifiers are untouched. This is a documentation commit only.
