# Render free Postgres preservation — `begg-ai-core-db`

**Written 2026-10-07 21:10 UTC. Status: BLOCKED on owner access. Nothing backed up yet.**

This is the P0 item from the master handoff. I could not complete it, and this file
records exactly what I verified, what I could not, and the shortest safe path to done.

---

## 1. The deadline, from Render's own documentation

Verified 2026-10-07 against `render.com/docs/free` and the 2024-05-20 changelog:

| Fact | Detail |
|---|---|
| Free Postgres lifetime | **30 days** from creation (was 90 before 2024-05-20) |
| On expiry | Database becomes **inaccessible** unless upgraded to paid |
| Grace period | **14 days** to upgrade before Render deletes it |
| After grace | **Render deletes the database and all of its data** |
| Backups on free plan | **None of any kind.** No PITR, no logical exports |
| Storage cap | 1 GB |

**Two dates, and they are different:**

- **2026-10-27 — the free-access deadline.** After this the database cannot be read
  *without paying*. This is the operative deadline for a zero-spend plan.
- **~2026-11-10 — the deletion deadline** (expiry + 14 days). After this the data is
  gone, and no copy exists anywhere on Render's side.

The handoff's "before October 27" is correct for the free path. The 14-day grace does
not help a zero-spend plan, because regaining access *during* the grace requires the
paid upgrade — so treat **2026-10-27 as the deadline**, with ~11-10 as the point of
no return.

---

## 2. What I could and could not establish

**Could not:** take the dump. I have no Render API access, no database credentials, and
no `DATABASE_URL`. Checked directly: the only MCP server available to me (`BeggAi`) is a
**Stripe** connector, not Render, and no secret in my environment matches
`begg|core|api_token|render`.

**Could not:** read the application data. Both live services gate their data endpoints —
`GET /api/tasks` returns **401 `{"detail":"Invalid or missing Begg API token"}`** — and I
do not hold that token. The gating is correct; this is a permissions limit, not a defect.

**Established, from the services themselves (verified 2026-10-07 21:07 UTC):**

| Service | `/health` | `/ready` |
|---|---|---|
| `begg-ai-industries-v013` (v0.13.0) | `ok:true` | `ready:true`, `api_token_configured:true` |
| `begg-ai-core-v010` (v0.12.1) | `ok:true` | `ready:true`, `api_token_configured:true` |

Both expose: `/api/tasks`, `/api/tasks/{id}`, `/api/approvals`, `/api/schedules`,
`/api/audit`, `/api/departments`, `/api/budget/events`.

**So the database plausibly holds durable task, approval, schedule, audit and budget
state** — exactly the "persistent project state" Oddfellow exists to provide. That is a
reason to preserve it, not to skip it.

⚠️ **Two observations that point the other way, and are NOT proof:**

1. **`/ready` reports no database field.** It checks `api_token_configured`,
   `external_provider_*`, and `budget` — but nothing about Postgres. A service whose
   readiness does not check its database is often a service not using one.
2. **No code in this repository connects to Postgres.** No `psycopg`, `asyncpg`, or
   `sqlalchemy` anywhere. Whatever uses the database is not in the canonical repo.

These two together suggest the database **may be provisioned but unused**. I want to be
explicit that this is **an inference from absence, not a verified finding** — and the
lesson from the 20-hour blind spot applies directly here: *"I tested A and B and neither
had it" rules out A and B, not "it went somewhere else."* The only way to settle it is
to look at the database.

**Practical consequence:** if it turns out empty, this costs one `psql` command to
confirm and the urgency disappears. If it turns out to hold real task history, the
deadline above is real. **Confirming which takes minutes; guessing wrong is
unrecoverable.**

---

## 3. The security-preserving path

The handoff correctly forbids weakening the database's security to make backup easier.
The IP-allowlist obstacle has a clean solution that does **not** involve opening the
database to the internet:

**Add one IP — the owner's own — not `0.0.0.0/0`.**

1. Render dashboard → `begg-ai-core-db` → **Info** → copy the **External Connection**
   string (contains the password — do not paste it into chat or a repo).
2. Render dashboard → `begg-ai-core-db` → **Networking / Access Control** → add the
   **single IP of the machine taking the dump**. Look it up with
   `curl -s https://api.ipify.org`. **Do not add `0.0.0.0/0`.**
3. Take the dump **on that machine** (`pg_dump` and `psql` are already installed in this
   sandbox — `/usr/bin/pg_dump`, `/usr/bin/psql` — but the sandbox has no stable IP, so
   the dump must run where the allowlisted IP lives):

   ```bash
   # read the connection string from an env var, never from the command line,
   # so it does not land in shell history
   read -rs RENDER_DB_URL            # paste, press Enter; nothing echoes
   pg_dump -Fc "$RENDER_DB_URL" > begg-ai-core-db-$(date -u +%Y%m%dT%H%M%SZ).dump
   unset RENDER_DB_URL
   ```

4. **Verify before trusting it** — an unverified dump is a false control:

   ```bash
   pg_restore --list <the.dump> | head            # must list objects, not error
   ls -l <the.dump>                                # a few hundred bytes means "empty", not "done"
   ```

5. **Remove the allowlist entry** once the dump is verified.
6. **Store the dump somewhere that is not Render** — the whole point is surviving the
   Render deletion. And keep it out of git.

**If the dump is empty:** say so, and record it. That is a complete and useful answer.

---

## 4. Restore procedure

Into a fresh free instance later, or a local Postgres for inspection:

```bash
pg_restore --no-owner --no-acl -d "$TARGET_URL" <the.dump>
```

Note the dump is `-Fc` (custom format), so it needs `pg_restore`, not `psql`. Restoring
drops existing objects — restore only into an empty database.

---

## 5. What the owner needs to decide

1. **Take the dump before 2026-10-27**, using §3. Requires adding one IP and running one
   command — no spend, no security weakening.
2. **Or** confirm the database is unused and let it expire deliberately. Legitimate, but
   it should be a decision made by looking, not by assuming.

Either way this needs the owner: I have no path to the database or the dashboard, and I
will not weaken an access control to create one.
