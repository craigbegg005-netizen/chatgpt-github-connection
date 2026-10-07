# Render free Postgres preservation — `begg-ai-core-db`

**Written 2026-10-07, revised 21:45 UTC. Status: READY TO EXECUTE — blocked only on
owner access. Nothing backed up yet.**

This is P0 from the master handoff. Everything that can be done without the database
password has been done: the tooling is written, and every command below was run
end-to-end against a real PostgreSQL 18 server before being written down.

---

## 1. The deadline, from Render's own documentation

Verified 2026-10-07 against `render.com/docs/free` and the 2024-05-20 changelog:

| Fact | Detail |
|---|---|
| Free Postgres lifetime | **30 days** from creation (was 90 before 2024-05-20) |
| On expiry | Database becomes **inaccessible** unless upgraded to paid |
| Grace period | **14 days** to upgrade before Render deletes it |
| After grace | Render deletes the database and all of its data |
| Backups on free plan | **None of any kind.** No PITR, no logical exports |
| Storage cap | 1 GB |

**Two dates, and they are different:**

- **2026-10-27T23:21:01Z — the free-access deadline.** After this the database cannot be
  read *without paying*. This is the operative deadline for a zero-spend plan.
- **~2026-11-10 — the deletion deadline** (expiry + 14 days). After this the data is gone
  and no copy exists anywhere on Render's side.

The 14-day grace does not help a zero-spend plan, because regaining access *during* the
grace requires the paid upgrade. **Treat 2026-10-27 as the deadline.**

---

## 2. Correction to the handoff's premise about the allowlist

The handoff says the backup failed because "external IP allowlist is empty". Render's own
documentation says something that changes how that should be read:

> "By default, your Render Postgres instance is accessible from any IP address (if the
> connection uses valid credentials). … The default block is `0.0.0.0/0`, which allows
> access from any IP address."

So an **empty** allowlist is ambiguous, and the two readings are opposites:

- **Never configured** → the effective rule is `0.0.0.0/0`, i.e. *already open to the
  internet*. Adding a `/32` then **tightens** security.
- **`0.0.0.0/0` deliberately removed** → public access is blocked. Adding a `/32` then
  **restores** access for exactly one address.

**Both readings have the same correct action, so this does not need resolving before
acting: replace whatever is there with exactly one `/32`.** What must *not* happen is
adding a `/32` while `0.0.0.0/0` is still present — that leaves the database open to the
world while looking locked down. **The `0.0.0.0/0` entry must be removed, not joined.**

⚠️ Render's CLI replaces the whole list (`--ip-allow-list`), while the Dashboard adds a
row. On the Dashboard, **remove `0.0.0.0/0` first, then add the `/32`.**

---

## 3. The trap that makes a failed backup look successful

`pg_dump` refuses to dump a server whose major version is newer than its own — and it
refuses **after creating the output file**. Verified empirically on 2026-10-07 against a
real PostgreSQL 18.6 server:

```
$ /usr/lib/postgresql/15/bin/pg_dump -d dump_probe -f probe15.dump -Fc
pg_dump: error: aborting because of server version mismatch
pg_dump: detail: server version: 18.6; pg_dump version: 15.19
$ ls -l probe15.dump
-rw------- 1 postgres postgres 0 ... probe15.dump      <-- exists, and is empty
```

**A checklist item reading "backup file exists" passes on a completely empty dump.** This
is the false-control shape this project has hit eleven times: a check that cannot
distinguish success from failure. The checklist below therefore requires **size > 0 AND
`pg_restore --list` parsing the file**, because neither alone is sufficient.

The same run proved the fix: `pg_dump` 18.6 against the same server produced a 1,601-byte
archive, `pg_restore --list` listed 7 TOC entries, and a full restore into a fresh
database returned the original rows.

---

## 4. What is already done (no owner access needed)

- **`oddfellow/db_preserve.sh`** — `doctor` / `recon` / `dump` / `verify`. Written and
  tested end-to-end. It refuses to run with a `pg_dump` older than 18, and it will not
  accept a dump that is empty or unparseable.
- **PostgreSQL 18 client installed and verified** in this sandbox
  (`/usr/lib/postgresql/18/bin/pg_dump`, 18.6).
- **Dependency map — negative result, and the negative result is the finding.** There is
  **no** `DATABASE_URL`, `psycopg`, `asyncpg`, or `SQLAlchemy` anywhere in the canonical
  repository, and no `.sql`, schema, migration, or seed file. Nothing in this repo
  connects to Postgres.
- **Pre-flight connectivity proven.** From this sandbox: DNS for
  `dpg-dasq9ne0tbcc738ifeug-a.ohio-postgres.render.com` resolves, and TCP 5432 to it
  connects. The sandbox can reach the database once the allowlist permits it.

⚠️ The negative result does **not** mean the database is unused — see §6.

---

## 5. Two execution paths

### Path A — the sandbox takes the dump (recommended)

Owner taps: **four.** No PC, no terminal on the phone, no credential in chat.

1. **On the phone, in the Render Dashboard:** `begg-ai-core-db` → **Networking** →
   remove `0.0.0.0/0` if present → add one rule: the sandbox's IP as `/32`.
   Get that IP by asking me to run `curl -s https://api.ipify.org` — it is not a secret,
   but it changes when the sandbox restarts, so read it fresh rather than reusing a value
   from an earlier message.
2. **On the phone, in the Render Dashboard:** `begg-ai-core-db` → **Info** → copy the
   **External Connection** string. Do not paste it into chat.
3. **In this chat:** [Open computer](#letta-computer) → in the sandbox terminal, write the
   connection string to a file without echoing it:
   ```bash
   umask 077; cat > /root/.oddfellow-db-url
   # paste, press Enter, then Ctrl-D
   ```
   The credential now exists only on the machine that will use it. It is never in chat,
   never in shell history, never in `ps` output.
4. **In this chat:** tell me it is in place. I run recon, then the dump, then verification,
   and report. Then you remove the `/32` rule.

**Why this is safe:** the credential reaches exactly one machine, which is the machine
that needs it, by a path that does not include any chat transcript or repository.

**Weakness, stated honestly:** this sandbox is not permanent storage. The dump must be
copied somewhere durable — I will deliver a copy to `/root/downloads` for you to save on
the phone, and the dump must **not** be committed to git (the repo is public).

### Path B — Termux on the phone (fully on-device, no sandbox)

Viable: **Termux ships PostgreSQL 18.2** (`postgresql_18.2-1_aarch64.deb`, packaged
2026-09-03), so it can dump a PG18 server. More taps, and the phone's mobile IP changes
between networks, so the allowlist entry is short-lived.

1. Install Termux from **F-Droid** (not the Play Store — that build is abandoned).
2. `pkg update && pkg install postgresql`
3. `pg_dump --version` → **must report 18.x.** If it reports 17 or lower, stop: it will
   produce a 0-byte file and appear to succeed.
4. Allowlist the phone's current IP as `/32` (find it at `ifconfig.me` in the phone
   browser). On mobile data this IP changes; on Wi-Fi it is the router's.
5. ```bash
   read -rs DBURL          # paste the External Connection string; nothing echoes
   pg_dump -Fc --no-owner --no-privileges -f ~/begg-ai-core-db.dump "$DBURL"
   unset DBURL
   ls -l ~/begg-ai-core-db.dump     # must be > 0
   pg_restore --list ~/begg-ai-core-db.dump | head
   ```
6. Move the file off the phone (`termux-setup-storage`, then copy to shared storage), or
   leave it and tell me the path.
7. Remove the allowlist rule.

### Path C — a free Render service dumps it over the private network (fewest owner taps)

**This is the only path that needs neither an allowlist change nor any credential
handling by the owner.** It is recorded because it is strictly better on both counts, and
it is *not* available to me: it requires a Render deployment, and the standing rule is one
deployment actor at a time.

Render's free-plan documentation states that free web services "can initiate private
network requests to data stores/paid services in the same region". The per-database IP
allowlist applies **only to external connections** — a same-region Render service using
the **internal** URL bypasses it entirely.

So: a small free web service in the **same workspace and region as the database (Ohio)**,
wired to `begg-ai-core-db` with `fromDatabase`, receives the connection string as an
injected environment variable and can dump the database without any allowlist change and
without the owner ever seeing a credential.

**What it costs:** one deployment (so it must be the deployer's turn, not mine), and the
service must expose the dump over HTTP — which **must** be token-gated and torn down
immediately after, or it is a worse exposure than the allowlist it avoided. Also note
free web services spin down after inactivity, so the dump endpoint would cold-start.

⚠️ **Ruled out, and worth recording so nobody re-checks it:** running `pg_dump` from an
existing service's dashboard Shell tab. Render's own docs are explicit — *"Free web
services don't support … Shell access via SSH or the Render Dashboard"*, and datastores
never have a shell. The obvious version of this idea does not work.

**Recommendation:** Path A. Path C is better if and only if the deployer is already
mid-deployment and can add the service without churn.

---

## 6. Verification checklist

Every line must pass. A `[ ]` that cannot fail is not a check.

- [ ] `pg_dump --version` reports **18.x** (not 15/16/17 — those abort and leave 0 bytes)
- [ ] `pg_dump` completes with exit status 0
- [ ] Dump file **size > 0** — a 0-byte file is the version-mismatch signature, not an empty database
- [ ] `pg_restore --list <file>` parses, and reports **more than 0 TOC entries**
- [ ] Schema/table inventory captured (from `recon`, before the dump)
- [ ] A **restore into a scratch database** succeeds and the row counts match `recon`
- [ ] Second copy stored off Render, and off this sandbox
- [ ] Dump **not** committed to git; no credential in any file that will be committed
- [ ] Render allowlist returned to its locked state (no `0.0.0.0/0`)

**If the database turns out to be empty:** say so and record it. That is a complete and
useful answer — it removes the urgency, and it is a real finding, not a failure.

---

## 7. What I could not establish

- **Whether the database holds anything.** No credentials, no Render API access. The
  `BeggAi` MCP server is a Stripe connector, not Render.
- **Whether it is used at all.** Four signals say unused: `/ready` on both live services
  reports no database field; no Postgres code in this repo; `command_center.py` records
  `{"name":"Database","state":"PENDING","blocker":"not connected to any app"}`; and the
  DB has been available since well before the current work. **One signal undercuts all
  four** — see below.

---

## 8. Why this is worth doing anyway: the likely consumer's source is lost

The two live services (`begg-ai-industries-v013` v0.13.0, `begg-ai-core-v010` v0.12.1)
serve a page titled **"Begg AI Industries Command Center"** at 17,260 bytes. This repo's
own `command.html` is titled **"Begg AI Command Center"** at 9,610 bytes. **Different
title, different size — the live Core is not this repository's code.** It is a separate
codebase, and the repo's own `command_center.py` records it as:

```
{"name": "Begg AI Core v0.15.0", "state": "BLOCKED", "blocker": "SOURCE NOT PRESERVED",
 "note": "No trace of it or its SHA in any branch or history."}
```

So "not connected to any app" may only mean *not connected to any app we can still read*.
If a lost codebase wrote to this database, **the database may be the only surviving
artifact of it** — and it is scheduled for deletion in three weeks.

The 20-hour-blind-spot lesson applies exactly: *"I tested A and B and neither had it"
rules out A and B, not "it went somewhere else."* Confirming takes one `psql` command.
Guessing wrong is unrecoverable.
