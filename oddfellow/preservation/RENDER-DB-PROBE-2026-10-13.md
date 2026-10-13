# Render DB preservation — independent probe of the allowlist question

**Date:** 2026-10-13 13:22 UTC · **By:** Oddfellow (this sandbox, which **has** network access)
**Purpose:** independently test the claim that the database is blocked by an empty `ipAllowList`.

## Result: the claim is CORRECT — but the mechanism matters, and a TCP probe misleads

Target: `begg-ai-core-db` / `dpg-dasq9ne0tbcc738ifeug-a`, `dpg-dasq9ne0tbcc738ifeug-a.oregon-postgres.render.com:5432`.
This sandbox's egress IP at probe time: **`146.235.230.249`**.

| Step | Result |
|---|---|
| DNS | resolves → `35.227.164.209` |
| Raw TCP connect to :5432 | **SUCCEEDS** |
| Non-SSL startup packet | `FATAL  C=28000  M=SSL/TLS required` (a genuine pg_hba line) |
| `SSLRequest` | `S` — accepted |
| TLS handshake | **completes, TLSv1.3** |
| Startup packet over TLS | **connection closed, no ErrorResponse at all** |

### Why this matters more than the verdict

**A TCP probe cannot test this allowlist.** Render's platform proxy accepts the TCP connection and
completes TLS *before* the allowlist decision, then **drops the connection silently**.

So a reachability check that stops at "TCP connect: OK" — or even at "TLS established" — returns a
**false positive**. This is the same false-control shape that has cost time in this project before:
the probe measures something adjacent to the property being tested and reports it as the property.

**The tell that distinguishes the two cases:**

| Observation | Meaning |
|---|---|
| `28P01` `invalid_password` | allowlist **open**, only credentials missing |
| `FATAL` `no pg_hba.conf entry for host <ip>` | allowlist **blocking**, stated plainly |
| **silent close after TLS, no ErrorResponse** | allowlist **blocking**, via the platform proxy |

We observed the third. **The allowlist is blocking.** Credentials are not the only missing thing.

### Correction to my own earlier reasoning

A previous reconciliation noted "TCP connect reached the server (`FATAL 28000 SSL/TLS required`)"
and treated that as evidence the allowlist was *not* blocking, on the theory that the effective rule
was `0.0.0.0/0`. **That reasoning was incomplete.** Reaching the protocol layer proves the proxy is
listening; it does not prove we are authorised. Only the post-TLS behaviour distinguishes them.

## What this does NOT change

- Nothing was modified. No allowlist edit, no credential used, no query issued.
- The database remains **not backed up**; restore test **not done**; schema **unknown**.
- Expiry **2026-10-27 23:21 UTC** — **14 days** from now.
- The owner action stands exactly as Claude described: add a temporary `/32` rule for the owner's
  own public IP, dump from an allowlisted machine, checksum, store privately, test-restore, then
  remove the rule.

## The open question that is now more urgent

Claude's handoff records that the **source for nine services may exist only in Render build
commands or env vars** (`ODDFELLOW_SOURCE`, `ODDFELLOW_BOOT_*`, `ODD_BOOT*`, `BEGG_BOOT_*`,
`ODDFELLOW_BUNDLE`, `ODDFELLOW_LETTA_SRC`) — possibly the unrecovered v0.16/v0.17 and Begg Core
v0.12/v0.13 source. **That is a second, independent preservation risk that the database dump does
not cover.** Env var values were not read, and reading them is owner-gated.

## Not claimed

No table inventory, no row counts, no schema. The database was not read — only its door was tested,
and the door is shut.
