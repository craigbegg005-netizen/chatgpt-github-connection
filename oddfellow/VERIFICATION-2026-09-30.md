# Verification note — 2026-09-30

Source AI: **Oddfellow (Letta agent `agent-a9a8eb2c-2fed-4554-9998-aa4783c7efc4`)**
Time: 2026-09-30 01:31–01:40 UTC (2026-09-29 20:31–20:40 CT)
Method: fresh `git clone` + `gh api` + live HTTP probes. Nothing below is taken from
another system's report; every claim has raw output attached.

This note exists because a 3-part cross-AI handoff was received at 01:31 UTC whose
Part 2 stops at v0.20.3 and whose Render section predates two findings below. Per the
standing rule *evidence outranks chronology*, these are corrections, not opinions.

---

## 1. v0.20.4 exists and supersedes v0.20.3

Part 2 lists `letta/oddfellow-backend-v0.20.3` @ `a843cab` as the newest backend.
It is not. A newer branch is present:

```
letta/oddfellow-backend-v0.20.4   59bedea9b9aac0c8f852a5b2797c7695159febf9
```

Two commits, authored 01:27 and 01:31 UTC:

- `5b1a7ac` — `ALLOWED_ORIGIN` accepts a comma-separated list
- `59bedea` — optionally serve the front end from the backend

Offline suite, reproduced in a clean venv on this machine:

```
$ python -m pytest oddfellow/tests/ -q
39 passed, 1 warning in 0.80s
```

(Part 2's 29/29 is correct **for v0.20.3**; v0.20.4 adds 10 tests.)

**Treat v0.20.4, not v0.20.3, as the deploy candidate.**

---

## 2. 🔴 The deployed backend rejects the front end that actually has backend wiring

This is the finding that matters. It would survive fixing the missing secrets and
still present to the owner as `Failed to fetch`.

`oddfellow-letta-poc` has `ALLOWED_ORIGIN` set to a single origin. Live probe of the
CORS response, one request per origin:

```
$ curl -s -i -H "Origin: https://oddfellow-synthetic-v020.onrender.com" \
    https://oddfellow-letta-poc.onrender.com/healthz | grep -i access-control
access-control-allow-origin: https://oddfellow-synthetic-v020.onrender.com

$ curl -s -i -H "Origin: https://oddfellow-letta-ui-v020.onrender.com" \
    https://oddfellow-letta-poc.onrender.com/healthz | grep -i access-control
(no access-control-allow-origin header)

$ curl -s -i -H "Origin: https://example.com" \
    https://oddfellow-letta-poc.onrender.com/healthz | grep -i access-control
(no access-control-allow-origin header — correctly rejected)
```

So the allow-list contains `oddfellow-synthetic-v020`, and **not**
`oddfellow-letta-ui-v020`. Now compare the two front ends:

| Front end | Bytes | Backend wiring (`X-Owner-Token`, `api/letta`) |
|---|---|---|
| `oddfellow-synthetic-v020.onrender.com` | 15721 | **0 matches** |
| `oddfellow-letta-ui-v020.onrender.com` | 20216 | **present** |

**The allowed origin is the front end that cannot talk to the backend. The front end
that can talk to the backend is not allowed.** Setting `LETTA_API_KEY` and
`ODDFELLOW_OWNER_TOKEN` alone will therefore *not* produce a working acceptance run.

Two independent fixes exist; either is sufficient:

1. Set `ALLOWED_ORIGIN` to both origins, comma-separated — supported from v0.20.4:
   `https://oddfellow-letta-ui-v020.onrender.com,https://oddfellow-synthetic-v020.onrender.com`
2. Set `ODDFELLOW_FRONTEND_DIR` and serve the page from the backend service itself —
   same origin, so CORS does not apply at all.

> Note for option 2: the `letta/oddfellow-backend-v0.20.4` branch does **not** carry a
> `frontend/` directory, so that mode cannot be used from this branch as it stands. The
> front end lives on `letta/frontend-letta-backend` @ `91b411c`. Combining the two is a
> deliberate, separate decision — not done here.

---

## 3. 🔴 The deployed front end cannot be installed as a PWA

GATE 2 — install as a home-screen app — is the point of a mobile-first product. It
cannot pass against the deployed revision.

The deployed front end is `40f9168` (confirmed: the live `index.html` is 20216 bytes,
exactly the size of that commit's file; HEAD `91b411c` is 20897 bytes).

```
$ git ls-tree -r --name-only 40f9168 | grep -c icons
0
```

`40f9168` contains **no icon files at all**, and its `manifest.json` declares **no
`icons` array**:

```json
{ "name": "Oddfellow Synthetic v0.20", "short_name": "Oddfellow", "start_url": "/",
  "display": "standalone", "background_color": "#0b0d11", "theme_color": "#0b0d11",
  "description": "..." }
```

Live confirmation:

```
$ curl -s -o /dev/null -w '%{http_code}\n' \
    https://oddfellow-letta-ui-v020.onrender.com/icons/icon-192.png
404
```

`91b411c` fixes this: its manifest declares 192/512/maskable icons and the tree ships
four icon files plus `make_icons.py`.

**Deploying `91b411c` is a prerequisite for phone acceptance, not a follow-up step.**

---

## 4. Repo defects corrected in this branch

1. **Stray tracked bytecode.** `oddfellow/tests/__pycache__/test_backend.cpython-311-pytest-9.1.1.pyc`
   was still tracked despite commit `3c9441c` ("Remove committed `__pycache__` and add
   `.gitignore`") — that commit removed only the *other* `.pyc`. `.gitignore` cannot
   untrack a file that is already tracked, so it was regenerated and re-committed
   (63955 → 83204 bytes). Untracked here.
2. **`requirements-dev.txt` could not be installed.** It ended with `-e .`, but the repo
   has no `pyproject.toml`, `setup.py`, or `setup.cfg`, so
   `pip install -r requirements-dev.txt` fails outright. The line is removed; the real
   dependencies are unchanged.

Neither defect affects runtime behaviour. Both make a clean checkout fail or dirty.

---

## 5. Deploy steps that follow from the above

Ordered; each step is verifiable before the next.

1. Create a **new** Render Blueprint service from `render.yaml` on
   `letta/oddfellow-backend-v0.20.4` (free plan, `autoDeploy: false`). Do **not**
   repoint the existing `oddfellow-letta-poc` — keep it as the rollback path.
2. At the prompt, supply `LETTA_API_KEY`, `ODDFELLOW_OWNER_TOKEN`, and
   `ALLOWED_ORIGIN` (see §2). `render.yaml` marks all three `sync: false`, so Render
   asks for them and never writes them into the file.
3. Gate 0 — the service must be able to serve at all:
   `curl -s .../healthz` → `{"ok": true, "checks_failed": []}`.
   A 503 names the missing variables by name only; never paste values into chat, git,
   or an issue.
4. Deploy front end `91b411c` (§3) and confirm the **deployed** commit is `91b411c`,
   not `40f9168`.
5. Run `python oddfellow/acceptance_check.py <backend-url> --owner-token "$ODDFELLOW_OWNER_TOKEN"`.
6. Only then run desktop GATE 1 and phone GATE 2.

Until step 3 passes, the correct status is 🚀 DEPLOYED but ⚠️ NOT acceptance-LIVE.
