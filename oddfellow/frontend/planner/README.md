# Planner integration point

**Status: placeholder. Nothing is published.**

The 7-Day Reset Planner PWA will be served from this directory at `/planner/` on the
existing Oddfellow service — same origin, no extra account, no extra charge, no CORS.

## Where the bundle goes

Drop the integration bundle here so that `index.html` is at this directory's root:

```
oddfellow/frontend/planner/index.html      <- the app entry point
oddfellow/frontend/planner/<assets...>
```

## Why this directory and not a separate host

Verified 2026-10-02: the backend already serves static subdirectories on **both** the
rehearsal and the live Render service (`/icons/icon-192.png` → 200, `/command.html` →
200). A directory here is served. `/planner/` returned 404 only because nothing was in
it — that was the absence of content, not the absence of a route.

Checked and unavailable: GitHub Pages (no admin; `has_pages: false`), Floot (5/5 full),
Cloudflare Pages / Netlify / Vercel (no account).

## Rules

- **Do not publish without the owner's explicit authorization.** Adding files here is
  preparation; a deploy is publication.
- The current `index.html` is an honest holding page. Replace it with the real bundle —
  do not build on top of it.
- Keep the Planner's own service worker scoped to `/planner/` so it cannot interfere
  with the Oddfellow app's worker at `/sw.js`.
