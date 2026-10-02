# Oddfellow front end — Letta backend integration

**Status: 🚀 DEPLOYED (as part of the single-service build) + 🧪 TESTED.**

> **Corrected 2026-10-02 02:5x UTC.** This line previously read
> "🛠 IMPLEMENTED + 🧪 TESTED against a local backend. NOT DEPLOYED." **That is no longer
> true.** This front end is now served by the live service
> **`oddfellow-letta-backend-v0206`** (`https://oddfellow-letta-backend-v0206.onrender.com/`),
> page + API + PWA on one origin. The page defaults to its own origin (`SAME_ORIGIN_BACKEND`)
> and only falls back to `FALLBACK_BACKEND_URL = https://oddfellow-letta-backend-v0206.onrender.com`
> (line 114 of `index.html`). ⚠️ It is still **NOT READY** end-to-end: the two secrets are
> unset, so `/healthz` is 503. The separate static site at `oddfellow-synthetic-v020` is a
> *different, older* deployment and still does not call a backend.

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

## v3 — installable (2026-09-30)

The manifest declared **no icons at all**, so "Add to home screen" would have used
a generic placeholder. Fixed:

- `icons/make_icons.py` renders the orb mark to PNG reproducibly, so the
  home-screen icon matches the in-app mark instead of being an unrelated asset
  someone has to hunt for.
- `icons/icon-192.png`, `icons/icon-512.png` (standard),
  `icons/icon-maskable-512.png` (extra padding for Android's adaptive mask),
  `icons/apple-touch-icon.png` (180px, for iOS).
- `manifest.json` now declares them, plus `scope` and `orientation`.
- `index.html` head gained `apple-touch-icon` and the iOS web-app meta tags.
- `sw.js` now precaches the shell and icons, skips cross-origin requests (so it
  can never cache API calls), and falls back to the cached shell offline.

Verified in Chrome 2026-09-30: all five assets return 200; the manifest parses
with `["192x192 any","512x512 any","512x512 maskable"]`; the service worker is
active; the apple-touch-icon link resolves; and the app still connects to the
backend afterwards (`Backend: Oddfellow`).

Getting a detail wrong here is easy and invisible: the first attempt centred the
gradient circle on the light source instead of on the orb, which shifted the whole
mark up and to the left. Fixed by centring the orb on the canvas and offsetting
the light *inside* it, with the stop scale set to the CSS `farthest-corner`
distance (~0.955 x diameter) rather than the radius.

## v2 — fewer taps (2026-09-30)

The backend URL is now **pre-filled** with `https://oddfellow-letta-poc.onrender.com`,
so a first-time visitor only has to paste **one** thing: the owner token. The URL
stays editable and a stored value always wins over the default.

> ⚠️ **Superseded 2026-10-02:** the pre-filled/fallback URL is no longer
> `oddfellow-letta-poc`. The page now prefers its own origin and falls back to
> **`https://oddfellow-letta-backend-v0206.onrender.com`** (`index.html:114`). This
> paragraph is kept as history.

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

- ~~Against the real deployed backend (it is not deployed yet)~~ — **no longer accurate.**
  The front end is deployed on `oddfellow-letta-backend-v0206`; what remains unverified is the
  **authenticated** path, because the two secrets are unset. Corrected 2026-10-02.
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
