# Google Drive access test — CONNECTED is not WORKING

**Date:** 2026-10-14 01:16 UTC · **Requested by:** owner, for ChatGPT's read check
**Result: 🔴 the connection is REGISTERED but non-functional at call time.**

## What happened, exactly

Google Drive appeared as a connected MCP server with **92 tools**. Every tool call fails.

```
letta mcp call mcp__Google_Drive__mcp__Google_Drive__GOOGLEDRIVE_LIST_CHILDREN_V2 \
  --args '{"folderId":"1a6Wer2z3HRYQqQ4T7cGRl1c3rKuDuogP"}'

→ 500 {"error":"Managed MCP server configuration is unavailable"}
```

**Tested for transient vs persistent:**

| Probe | Result |
|---|---|
| Same tool, attempt 1 | `500 Managed MCP server configuration is unavailable` |
| Same tool, attempt 2 | identical |
| Same tool, attempt 3 | identical |
| **A different tool** (`GOOGLEDRIVE_FIND_FOLDER`) | **identical** |

**3/3 retries identical, and a second tool fails the same way → server-level, not tool-level, and
persistent rather than transient.**

**The server IS registered:**
```
{ "name": "Google Drive", "transport": "streamable_http" }
```
It is listed. It is enabled. **It just cannot be called.**

## Why this specific distinction matters

**"Google Drive is connected to you" is true and misleading at the same time.** The connection
exists; the capability does not. Reporting the first without the second would have produced a
confident "yes I can read it" that fails the moment anyone depends on it.

This is the same shape as two earlier findings in this project:
- **Fourthwall payouts read ACTIVE** while the shop has **zero offers** — a true status with no
  content behind it.
- **Stripe's MCP connection** returns `Invalid refresh token` — present in the registry, dead in
  practice.

## Answer to the question ChatGPT asked

> **"Can Oddfellow read the artwork files through the new Drive connection?"**

**Not yet — and the failure is at the connection layer, not at the files.** No folder ID, sharing
setting, or filename issue is involved: **no Drive call reaches Google at all.** That means the
fix is on the connection side, and it also means **the artwork's presence or absence in the folder
is still UNKNOWN** — I could not see in, so I have no evidence either way.

**I did not conclude the folder is empty.** "Could not read it" and "it is empty" are different
claims, and only the first is supported.

## Likely causes, in order

1. **The managed MCP server configuration did not finish provisioning.** Most likely — the
   connection was made minutes ago and the tool list populated before the backing config was ready.
2. **The authorization completed but the credential was not stored** (the CLI also reports
   `[secrets] WARN: System secrets not available - using fallback storage`, which may or may not be
   related).
3. A provider-side issue on Letta's managed Drive server.

**First thing to try:** disconnect and reconnect Google Drive — that re-runs provisioning. If it
still fails after a fresh connect, it is provider-side and worth reporting to Letta.

## What is still true

- **The transfer blocker's root cause is unchanged:** the four archives are not on this sandbox.
- **Connecting Drive remains the right fix** — it just is not operational yet.
- **Fourthwall's media-library tools remain unexposed**, so even perfect artwork delivery does not
  unblock the launch. That is still the binding constraint.

## Not claimed

No Drive access. No folder inventory. No file verification. No checksums. **The folder was not
read.**
