# Live surface capture — 2026-10-13

Point-in-time capture of the **publicly readable** surface of the four live BSI
services, taken with no credentials. `probes.jsonl` is one JSON object per line.

Why this exists: the company's highest structural risk is that the only surviving
record of something is a running service, and a running service can stop. This is
the part of that surface which needs no credential to read, so it can be captured
unilaterally and repeatedly.

What it does **not** contain: anything behind authentication. Every `/api/*`
endpoint on these services returns `401 {"detail":"Invalid or missing Begg API
token"}` — verified, not assumed. The durable task/audit state is therefore **not**
in this capture and cannot be without a token.

Notable in the capture: `begg-ai-industries-v013` and `begg-ai-core-v010` both
report `api_token_configured: true`, and `oddfellow-personal-staging-v017b`
reports `database: true` — so that service holds a working database connection.
Whether it is `begg-ai-core-db` is **not established**.
