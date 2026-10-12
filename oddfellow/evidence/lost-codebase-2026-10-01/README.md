# Captures of the lost codebase — 2026-10-01 (root page recovered 2026-10-12)

**What this is.** The only surviving record of a codebase whose source exists nowhere in
version control. Two live Render services run it; nothing in this repository is its code.

| Service | Version | Evidence here |
|---|---|---|
| `begg-ai-industries-v013` | v0.13.0 | `industries-v013.openapi.json`, `.root.html`, `.health.json`, `.ready.json` |
| `begg-ai-core-v010` | v0.12.1 | `core-v010.openapi.json`, `.root.html`, `.health.json`, `.ready.json` |

The repo's own `command_center.py` records the situation:

```
{"name": "Begg AI Core v0.15.0", "state": "BLOCKED", "blocker": "SOURCE NOT PRESERVED",
 "note": "No trace of it or its SHA in any branch or history."}
```

**Why they are committed here.** Until 2026-10-12 these captures lived only in
`/root/workspace/capture/out/` — a sandbox directory that is not version-controlled and does
not survive a sandbox reset. The API surface of a codebase whose source is lost was one
sandbox reset away from being lost too. This directory is the fix.

**Provenance.** The `_openapi.json`, `_health` and `_ready` files are byte-for-byte copies of
the 2026-10-01 04:0x UTC capture sweep (`capture/out/<service>/`), renamed to
`<service>.<kind>.<ext>`. `industries-v013.root.html` is the one surface that sweep missed: its
`/` request timed out against a Render cold start, and a failed request leaves no capture file.
It was re-fetched on 2026-10-12 and returned **HTTP 200, 17,260 bytes** — the exact size
recorded in `RESOURCES.md`, which is what confirms it is the same page.

**These are evidence, not source.** An OpenAPI document describes the API's shape; it does not
contain the implementation. The root pages are the served HTML. Read them as a description of
what the lost codebase did, not as something that can be redeployed.

**Secret scan before committing (the repo is public).** All files were scanned for
key/token/password/connection-string/private-key shapes: **no credentials found.** One hit was
investigated rather than waved through — the string `Bearer authorization.` in
`industries-v013.root.html` matches a broad `bearer <token>` pattern, and it is the English word
*authorization* in the sentence "Use the same Begg API token as Bearer authorization." Recorded
here so the next person running that scan does not have to re-derive it.

**What these files do not establish.** Whether the services still behave as documented, and
whether this codebase is the one that wrote to `begg-ai-core-db`. See
`projects/bsi-codebase-reconciliation.md` in agent memory: if it is, the database is the last
surviving artifact of this codebase, and it is scheduled for deletion around 2026-11-10.
