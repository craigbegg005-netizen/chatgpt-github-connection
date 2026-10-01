# Production gap review — 2026-10-01 23:55 UTC

**Question this answers (handoff §17.3):** canonical is ahead of production. What is
actually in the gap, and what would change if it were deployed?

**Short answer:** the gap is **additive and tooling**. It contains **no behaviour
removals** — every one of its 28 deletions is a replacement. Two things would change
for a user of the live service: one new owner-only endpoint, and changed voice/approval
behaviour in the page.

---

## The gap, measured

| | |
|---|---|
| Live production commit | `70c02b3cc9452b10ac49502ccd389d5137c7ab59` |
| Canonical head at time of review | `d00ad7ab` |
| Commits ahead | **18** (the handoff recorded 14; the difference is my own pushes since) |
| Lines | **4740 insertions, 28 deletions** |
| Auto-deploy | **off** — nothing deploys unless someone clicks |

## The 28 deletions, examined

This is the part a deploy decision actually turns on, so it was checked line by line
rather than summarised.

| File | Deletions | What they are |
|---|---|---|
| `oddfellow/frontend/index.html` | 24 | **All replacements.** The old `confirm()` gate, the old `speak()`, the old `setListening`, the old `onresult`, the old `stopvoice` handler, and the `#voice` chip's class attribute. Each has a corresponding addition. |
| `CURRENT_STATE.md` | 2 | The date line and the branch-table row. |
| `RESOURCES.md` | 2 | The connector branch row and status paragraph. |

**No feature was removed.** Nothing in the gap takes away a capability the live
service currently has.

## What would actually change on the live service

### 1. A new owner-only endpoint — additive

`GET /api/command/jobs` exposes the connector's queue and dead-letter view.

- **Owner-gated** through the existing guard: `401` without a token, `401` with a
  wrong one, `400` on an unknown status filter.
- **Degrades rather than fails.** With no `ODDFELLOW_QUEUE_DB` set it returns
  `configured: false` and a note — **so deploying without setting that variable is
  safe**, it simply reports no queue.
- To make it useful in production, set `ODDFELLOW_QUEUE_DB` to a writable path.
  This is the one deployment-time configuration note in the whole gap.

### 2. Changed front-end behaviour — user-visible, verified

`frontend/index.html`, +189/−24. Elevated-risk commands now create a **real**
approval in the backend and stop, instead of a browser `confirm()`. Voice gains
listening / thinking / speaking states.

Both were **verified in a real browser against the merged tree**, not only on the
feature branch: the states flow correctly, and the approval gate holds (`sent: 0`,
bar shown).

### 3. New package, imported lazily — inert unless used

`oddfellow/connector/` (~2900 lines including 113 tests). Nothing imports it except
the new endpoint, and that import is **inside the handler**, so a connector problem
cannot take down the service that serves the page.

### 4. Tooling and documentation — not served

`post_gate_a_check.py`, `rehearsal.sh`, `rehearsal_watchdog.sh`, and four handoff
documents. None of these is reachable by a request to the service.

## What this review does NOT claim

- **It does not recommend deploying.** Deployment is a separate decision with its own
  gate (§18), and the live service is currently `ready:false` because Gate A is
  uncleared — deploying would not change that.
- **It does not verify the gap in production.** Everything above is measured from the
  repository. The live service is still running the old commit.
- **It does not claim the phone works.** Voice states are verified in a desktop
  browser only.

## If a deploy is decided

Order, so nothing is improvised:

1. Clear Gate A first — a deploy does not fix an unconfigured service.
2. Set `ODDFELLOW_QUEUE_DB` if the queue view is wanted.
3. Deploy `d00ad7ab` (or later).
4. Run `post_gate_a_check.py` against the deployed URL and record the raw results.
5. Phone acceptance remains the owner's, and remains unverified until done.

**Evidence outranks chronology. Nothing above outranks its evidence.**
