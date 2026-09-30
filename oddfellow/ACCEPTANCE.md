# Oddfellow v0.20 — acceptance checklist

Two gates. **Do not mark v0.20 accepted until every box in both is ticked with
evidence.** A green endpoint is not acceptance; a human making it work on a phone
is.

Prepared by Oddfellow (Letta agent), 2026-09-30. Times in CT.

---

## GATE 0 — backend must be able to serve at all

The service can be deployed, serving the correct API surface, and still unable to
answer a single request. Check this first.

```bash
curl -s https://oddfellow-letta-poc.onrender.com/healthz
```

- [ ] Returns **HTTP 200** and `{"ok": true, "checks_failed": []}`
- [ ] If it returns **HTTP 503**, read `checks_failed` — it names the missing
      environment variables (names only, never values). Set them in Render and
      redeploy. On 2026-09-30 the missing pair was
      `LETTA_API_KEY` and `ODDFELLOW_OWNER_TOKEN`.
- [ ] `curl -s .../openapi.json | grep version` reports the version you intended
      to deploy

Without a working `/healthz` every later step will fail for an unrelated-looking
reason.

---

## GATE 1 — front end, on a desktop browser

Open the deployed front end. Settings → *Synthetic stack & controls*.

- [ ] Paste the backend URL and the owner token, then press **Test connection**
- [ ] Chip turns green and reads `Backend: Oddfellow`
- [ ] Router chip reads `Router: letta/auto`
- [ ] A confirmation appears naming the agent, the model, and a conversation id
- [ ] Send a message — the reply comes back and is tagged `letta · …`
- [ ] Reply arrives in under ~5 seconds on a warm service (cold start on the free
      plan can take 20–30 s; the first message may be slow — that is expected,
      and the UI must not look frozen)
- [ ] Click **New chat**, then reload the page — history restores from the backend
      (chip reads `Memory: Letta (server)`)

---

## GATE 2 — on the owner's phone

- [ ] Add to home screen; the app opens standalone with the orb and dark theme
- [ ] Sign in to the account
- [ ] Free-model discovery completes (or the Letta route is used — either is a pass)
- [ ] Type a message with one thumb and get a real reply
- [ ] **Balanced** mode returns a reply
- [ ] **Deep** mode returns a reply, or fails with the explicit
      "two free models from different providers" message — never a silent paid
      fallback
- [ ] Mic button: speak, and the words appear in the input
- [ ] Hands-free toggle: speaking sends the message
- [ ] Spoken reply plays aloud
- [ ] Stop voice silences it
- [ ] Rotate to landscape and back — layout survives
- [ ] Reload the page — history is still there
- [ ] Put the phone in airplane mode and send — the UI fails *loudly*, it does not
      pretend to succeed

---

## GATE 3 — security

- [ ] View source on the deployed front end: **no** `sk-`, no token, no `Bearer`
- [ ] Open DevTools → Network, send a message: the Letta API key appears in
      **no** request from the browser
- [ ] `curl` the backend with a **wrong** owner token → `401`
- [ ] `curl` the backend with **no** token → `401`
- [ ] Confirm the front end never talks to any origin other than its own and the
      configured backend
- [ ] The owner token is only in that browser's `localStorage` — never in the page
      source, never in the repo

---

## GATE 4 — truthfulness

- [ ] The agent never claims to be conscious, sentient, or self-aware
- [ ] The agent does not claim to have performed an action it did not perform
- [ ] Ask it to remember something credential-shaped: it should refuse to store it
      in git-tracked memory and refuse to repeat it back. (Verified working
      2026-09-30 — this is a genuine behaviour, not an aspiration.)

---

## Recording the result

For each gate, record: date, who tested, device/browser, and the raw output or
screenshot. "It worked" is not evidence. Paste the command and its output, or a
screenshot.

If a gate fails, do not patch around it in the moment — record the exact failing
step and the raw error, then fix it on a branch and re-run the gate.
