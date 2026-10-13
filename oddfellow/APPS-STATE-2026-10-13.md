# Apps — what the record actually contains (2026-10-13)

**Status: ⚠️ NOT VERIFIABLE FROM THIS REPOSITORY. No app was probed, because no app is recorded.**

## Why this file exists

The 2026-10-12 master directive lists, under **APPS**:

> *"Previously reported: Merge Forge, Home Ledger and Ready Card. Re-check live URLs, function,
> privacy and mobile usability before calling them live or verified."*

That item cannot be actioned from here, and the reason is worth recording rather than leaving as a
silent omission — a future session reading the directive would otherwise spend time hunting for
three apps that the repository has no record of.

## What was searched, and what was found

Searched the whole repository (every file type, excluding `.venv` and `.git`):

| Name | Occurrences | Where |
|---|---|---|
| **Merge Forge** | **none** | — |
| **Home Ledger** | 1 | `IP-INVENTORY.md`, in a list of *"App Factory concepts"* |
| **Ready Card** | 1 | same line, same list |

No live URL, no repository, no deployment, no build artifact, and no screenshot exists for any of the
three. A search for URLs matching `mergeforge` / `homeledger` / `readycard` (and the hyphenated forms)
returns nothing.

## What this does and does not mean

- **It does not mean the apps do not exist.** They may live outside this repository, on an account or
  host this agent has no access to. Nothing here is evidence of absence beyond *this* record.
- **It does mean they are not "previously reported" in any surviving artifact.** The directive
  describes them as previously reported; the repository, which is the canonical record, does not
  contain that report. That is the same shape as the commerce canon's receipt gap: a directive
  resting on material that did not arrive.
- **The two that are recorded are recorded as *concepts*, not products.** `IP-INVENTORY.md` lists them
  among *"App Factory concepts (… Ready Card, Home Ledger, Opportunity Exchange)"* and marks their
  distinctiveness **"Weak to unknown"**, noting several are descriptive and hard to protect as marks.
  A concept list is not a shipping record.

## What would resolve it

One of:

1. The URLs, from Craig or from ChatGPT — then each can be probed for liveness, function and mobile
   usability as the directive asks.
2. A statement that these are unbuilt concepts, in which case the directive's APPS item should be
   removed rather than carried forward as an open gate.

Until one of those arrives, **the honest status is `NOT CHECKED — no artifact to check`**, not
`BLOCKED`, and certainly not `LIVE`.
