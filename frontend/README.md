# Oddfellow front end — Letta backend integration

**Status: 🛠 IMPLEMENTED + 🧪 TESTED against a local backend. NOT DEPLOYED.**

The deployed site at `oddfellow-synthetic-v020.onrender.com` does not call the
backend. This directory holds a patched copy that does.

**Provenance:** reconstructed from the *deployed* page (the static site at the
live URL is its own source). It is not copied from any origin repository —
if the real front-end source exists elsewhere, this should be reconciled with
it rather than replacing it silently.

## What changed

Only the client-side routing. Everything else — voice input, speech output,
Puter account connection, memory chips, export, PWA manifest, service worker —
is byte-for-byte the original.

Added:

1. A **Backend** chip showing connection state (`Backend: off` when unconfigured).
2. Two settings fields, saved to `localStorage` only — **no secret is embedded
   in this file**: `Letta backend URL` and `Owner token`.
3. A **Test connection** button that calls `GET /api/letta/status` and reports the
   agent name, model, and conversation id.
4. `send()` routes to `POST /api/letta/message` when a backend is configured,
   and falls back to the original free-only Puter router when it is not.
5. On load, if a backend is configured, it calls `GET /api/letta/history` and
   restores server-side history.

The owner token is entered by the owner and stored in that browser's
`localStorage`. It is never in the page source, never in a repo, and never in a
network request to any origin other than the configured backend.

## v2 — fewer taps (2026-09-30)

The backend URL is now **pre-filled** with `https://oddfellow-letta-poc.onrender.com`,
so a first-time visitor only has to paste **one** thing: the owner token. The URL
stays editable and a stored value always wins over the default.

Pressing **Test connection** with no token now says exactly what is missing and
focuses the token field, instead of a generic failure.

Verified for a first-time visitor (`localStorage` cleared, reloaded): the URL
field shows the default, the token field is empty, and the chip reads
`Backend: off`.

## Verified 2026-09-30 (local, real Letta agent)

Served on `127.0.0.1:8080`, backend on `127.0.0.1:8092`, driven in Chrome:

- Config chip flipped to `Backend: Oddfellow` (green) after Test connection
- Router chip showed `Router: letta/auto`
- Test connection reported: `Agent: Oddfellow · model letta/auto · conversation conv-c0d02720-...`
- Sending a message returned, live:
  *"I'm Oddfellow, and the zero-spend rule — free tiers only, no paid service or
  provider without your explicit authorization — remains a standing instruction."*
  tagged `letta · conv-c0d02720-... · 34 tok`
- CORS preflight from the page origin returns the expected allow headers
- No `sk-`-shaped string anywhere in the file

## Not verified

- Against the real deployed backend (it is not deployed yet)
- On a phone
- The Puter fallback path was re-exercised 2026-09-30: with no backend
  configured, the router chip read **"Router: 22 free routes"** — discovery ran
  and found 22 free models. The fallback is alive.
- The full message flow after the v2 change: reply returned and tagged
  `letta · conv-c0d02720-... · 219 tok`. The agent also volunteered, unprompted,
  that it had noticed the same question four times in a row — evidence that
  conversation continuity is real, not cosmetic.

## Deploying

Static site — nothing to build. Deploy `index.html`, `manifest.json`, `sw.js`.
Set `ALLOWED_ORIGIN` on the backend to this site's origin, or the browser will
block the calls.
