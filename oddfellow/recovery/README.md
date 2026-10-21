# Safe Render configuration inventory (offline, limited scope)

**Status:** offline tooling only. Nothing here exports databases, accesses Render,
reads environment values, performs deployments, configures jobs, or backs up
runtime state. The user has paused database backup work.

This intentionally narrow tool snapshots **only** the reviewed
`oddfellow-letta-backend-v0206` and `oddfellow-letta-ui-v020-pwa` deployment
metadata. Other services, especially the independent Peace framework, are
rejected. Legacy BSI services whose code exists in environment-provided source
archives **are not** covered by this inventory.

Run on a trusted machine with a temporary **local JSON input file containing
only permitted service metadata**, never committed to the public repository:

```bash
python3 oddfellow/recovery/render_config_snapshot.py create \
  --input /secure/local/render-service-metadata.json \
  --snapshot /secure/local/oddfellow-config.json \
  --manifest /secure/local/oddfellow-config.sha256.json \
  --captured-at 2026-10-21T16:00:00Z

python3 oddfellow/recovery/render_config_snapshot.py verify \
  --snapshot /secure/local/oddfellow-config.json \
  --manifest /secure/local/oddfellow-config.sha256.json

python3 -m unittest discover -s oddfellow/recovery/tests -v
```

Replace the timestamp with the actual UTC capture time. `create` refuses to
overwrite existing outputs; store results away from the public repo. Test files
use fabricated metadata only; no connection to Render/PostgreSQL is needed.

## Security design

- Input schema is restrictive: unfamiliar service names or metadata keys fail
  closed. Only **literal-reviewed** repo names, branches, public URLs and safe
  commands are emitted; arbitrary build/start commands are never echoed.
- `envVars` is accepted as *untrusted discarded input* so it is never included
  in output; raw input and exception contents are never printed. Do **not** put
  credentials into the input in the first place.
- Output uses stable JSON and a SHA-256 content digest verified on readback.
  **A checksum is not authentication:** anyone who can edit both files can
  recompute it. A separately stored trusted copy or signed manifest is required
  for adversarial tamper evidence.
- No encryption keys or confidential runtime data are handled by this program.
  Encryption, private backup destination, retention, scheduling and isolated
  restore tests remain unimplemented and require a separate review.
- Do not commit the unfiltered Render API response, even if it appears safe.
  The existing GitHub repository is public.
