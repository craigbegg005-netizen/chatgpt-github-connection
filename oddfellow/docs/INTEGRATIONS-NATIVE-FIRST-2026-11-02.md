# Oddfellow native-first integration plan — 2026-11-02

**Current stage:** two opt-in local adapters implemented and fixture-tested, not deployed, not connected to real inference or search servers, and not added to autonomous job execution. No subscriptions or new dependencies.

## Reuse existing architecture instead of duplicating it

- **Jobs, memory-of-work, audits, approvals:** retain `connector/store.py`. Do not create another queue or project-state database.
- **Provider registry/routing:** retain `connector/providers.py` and `connector/router.py`; do not advertise an unverified local model as a general-purpose code/research worker.
- **MCP:** retain the *single* `connector/gateway.py` (currently scaffolded and disabled). Do not expose a second public MCP entry point.
- **Scheduled handoff:** retain `connector/worker.py`.
- **Research execution:** draft PR #9 is separate, unmerged, and owns guarded local research jobs. Do not duplicate its worker, SQL leases, or result state machine.
- **Mobile and voice UI:** reuse the existing Oddfellow interface rather than building another frontend.

## Integration options: owner and anti-duplication decisions

| Capability | Canonical owner | Candidate alternative | Status; effort |
|---|---|---|---|
| Local text reasoning | NEW `integrations/local_inference.py` | Ollama **or** llama.cpp: one common OpenAI-compatible adapter | Code + fixture tests; no live backend. M |
| Search | NEW `integrations/local_search.py` | Self-hosted SearXNG JSON API | Code + fixture tests; no live backend. M |
| Memory/document search | Reuse existing state; only add index where missing | SQLite FTS5 | Design; M |
| Code & Git | Existing Git operations + repo; Github optional sync | Local Git CLI | Existing underlying tool; M |
| Scientific computation | Existing research engines + PR #9 after review | Restricted Python, offline simulations | Existing/draft, M |
| Browser automation | Later, dedicated sandbox adapter only | Playwright | Candidate; L |
| Speech | Existing voice/PWA | whisper.cpp, Piper | Candidate; L |
| Documents and spreadsheets | One document tool surface | python-docx, pypdf, ReportLab, openpyxl | Candidate; M |
| Email/calendar | Consent-based external transport; never pretend fully offline | IMAP/SMTP, CalDAV | Candidate; M/L |
| Images/video | Hardware/licensing review first | ComfyUI, ffmpeg | Candidate; L |
| Payments/ads/storefront platforms | Local planning only; external action requires platform | Optional adapters, owner approval | External-dependent; L |

## Implemented code, safety boundary

- `integrations/loopback_http.py`: bounded, no-proxy JSON HTTP, literal 127.0.0.1 or ::1 only; no redirects/credentials/remote hosts. No services installed or started.
- `integrations/local_inference.py`: uses GET /v1/models + POST /v1/chat/completions, explicit local-model allowlist, cloud-suffixed model refusal, no automatic tools. **An endpoint on localhost can still proxy to a paid cloud service**; the owner must confirm the model truly runs locally.
- `integrations/local_search.py`: SearXNG /search?format=json; deduplicated, bounded links marked *unverified_lead*. SearXNG still uses upstream Internet services and is not offline research.
- `integrations/__main__.py`: manual invocation, no persistent polling or production exposure.

## How to validate (only when a local service exists)

From the `oddfellow/` directory:

```bash
python -m pytest connector/tests/test_local_integrations.py -q
python -m connector.integrations models --endpoint http://127.0.0.1:8080/v1
python -m connector.integrations chat --endpoint http://127.0.0.1:8080/v1 --model VERIFIED_LOCAL_MODEL --prompt 'Test' --confirm-local
python -m connector.integrations search --endpoint http://127.0.0.1:8888 --query 'data center water recovery'
```

Ollama's default local endpoint uses port 11434, llama.cpp port depends on setup. SearXNG must have JSON results enabled. Services must run on the *same host/network namespace* for loopback to connect; a phone's localhost is not the desktop's localhost.

**Fixture evidence (2026-11-02):** 18 isolated tests passed, including endpoint/redirect/size checks, cloud model/allowlist refusal, search deduplication, and manual CLI. Full repository suite and live hardware/API checks were **not** run in the original local sandbox.

## Next steps by value/effort

1. **S:** Check full repo tests, branch diff, PR #9 overlap; keep this an independent draft review.
2. **M:** Identify existing suitable owner-controlled hardware; test one explicitly local inference model, with the Internet disconnected, and record RAM, speed, energy. No hardware purchase.
3. **M:** Validate SearXNG on available infrastructure and cite sources; disable if upstream query terms/costs cannot be satisfied.
4. **M/L:** Once PR #9 passes review, add a scoped read-only dispatcher through existing Store/Router/Gateway gates and preserve results as unverified. No direct autonomous tool call execution from model output.
5. **L:** Speech, browser, and document adapters only after checking for already-implemented equivalents and existing hardware.

### Official feasibility references

- https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md
- https://github.com/ollama/ollama/blob/main/docs/api/openai-compatibility.mdx
- https://docs.searxng.org/dev/search_api
- https://www.sqlite.org/fts5.html

**No production merge, deployment, service creation, spending, or credential movement.**
