# Render → GitHub recovery preparation — 2026-10-21

**Owner project:** Begg Synthetic Industries / Oddfellow Synthetic Intelligence  
**Status:** Non-secret service configuration snapshot CREATED on a non-deploying review branch; **no runtime data backup, private repository, scheduled job, restoration test, or live-system change has been completed**.

## Verified at source today
- The existing source repository `craigbegg005-netizen/chatgpt-github-connection` is **PUBLIC**. Its default branch is `main`; Oddfellow's canonical code branch is `letta/combined-single-service-v0.20.4`.
- Render's `oddfellow-letta-backend-v0206` is connected to that canonical GitHub branch. The Render deployment record most recently returned `live` for a deployment created **2026-10-01**; this **does not** establish current application readiness or that newer Git commits were deployed.
- Render's PWA service `oddfellow-letta-ui-v020-pwa` is connected to `letta/frontend-letta-backend`. Its returned deployment record is `live` from **2026-09-30**.
- **Auto-deploy is OFF** for both services. Preserve this setting.
- The canonical branch already contains `oddfellow/db_preserve.sh` and `oddfellow/backup_render_db.sh`. **Do not duplicate or run them** in this workstream.
- Several *other* legacy BSI/Oddfellow Render services construct source files from environment-provided archives or code during builds. GitHub source history alone will **not** reproduce those services. Recovering any such source must be done through a secure, separately authorized owner-only workflow, with no raw environment values committed.
- The adjacent JSON file preserves a small, verified, **non-secret** configuration snapshot for the primary backend and PWA, **not** a backup of any database, storage volume, runtime record, or environment-variable value.

## Explicit exclusions and security constraints
- **Database work is paused by owner instruction.** Do not connect, export, restore, inspect, or configure the Render PostgreSQL database under this task.
- The independent Global Peace framework is **out of scope** and must not share BSI backup files, security credentials, repository, or policies.
- Never publish Render API credentials, `.env` data, authorization tokens, private files, backups of user records, embedded source reconstructed from environment variables, or plaintext database dumps to this public repository.
- Never treat a **private** GitHub repository as sufficient protection by itself: encrypt confidential data before upload; test independent decryption and restoration.
- Do not create paid resources, deploy a service, change auto-deploy, or alter live service settings without specific approval.

## Backup classes and target design
1. **Source:** existing Git commits and pinned branch/commit references; audit missing source used by legacy services without extracting secrets into source control.
2. **Non-secret deployment configuration:** branch, root directory, runtime, sanitized build/start commands, service type, and auto-deploy state. Snapshot already provided for the primary two services.
3. **Secrets:** inventory **names and required access procedures only**. Values remain in authorized secret stores; re-entry or rotation occurs securely during recovery.
4. **Runtime state:** **not backed up**. Any later backup must use a private, access-controlled destination, authenticated encryption, checksum/integrity manifest, size limits and retention policy, plus a tested isolated recovery. Do not upload live records to the existing public repository.
5. **PostgreSQL:** excluded until owner explicitly resumes it; reuse the existing scripts and tests instead of reimplementing them.

## Next engineering task — Codex
Work from this **review branch**, compare it with the latest canonical head, and do not edit the deploy branch directly. Implement only the **non-destructive, zero-spend, offline/dry-run** portion first:
- A stdlib-only service-metadata normalizer/validator using sample fixtures (including hostile values), with an explicit BSI/Oddfellow scope allowlist.
- Strict omission/redaction of **all environment values**, connection strings, authorization headers, and source payloads embedded into build commands. Reject unknown or unsafe fields rather than passing arbitrary data through.
- A manifest with timestamp, source identifier, scope, SHA-256 digest, deterministic encoding, and schema version; prove that the output can be read back and compared.
- Unit tests for accidental secrets, sensitive source build commands, empty/truncated data, no live writes, repeatability, and GitHub size limitations. Any actual encryption or upload mechanism must be tested offline against dummy data before real data is considered.
- Keep backup files and key material out of the public repository. Any GitHub Actions workflow must be **manual-only and no-op by default** until credentials and destination are explicitly approved.
- Reuse existing `db_preserve.sh` logic if later authorized rather than creating a competing database export implementation.

**Codex acceptance evidence:** commits, offline test results, exact file list, discovered risk, confirmation of *no live data accessed* and *no deploys triggered*. No claims of deployed, scheduled, or verified backups.

## Subsequent Operations task — Work
After Codex reports tests and code review: assess an appropriately private backup destination, GitHub account permission boundaries, data size/retention, secure credentials, Render source reconstruction risks, and a controlled restore drill. Request owner approval before introducing secrets, scheduled exports, deployments, or runtime-data handling.

**Operating doctrine:** Preserve → Integrate → Improve → Execute → Verify → Continue. Evidence outranks status summaries. Keep one writer per branch/service.