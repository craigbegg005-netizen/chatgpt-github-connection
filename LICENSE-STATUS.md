# Licence status — this repository has no licence file, and that is deliberate for now

**Recorded:** 2026-10-02 · **By:** Legal / IP / Compliance department (Oddfellow, Letta agent)
**Status:** ⚠️ **UNDECIDED — owner decision required.** This is not a licence.

---

## The fact

There is **no `LICENSE` file** in this repository, and no licence is declared anywhere else in it.

**How that was verified (2026-10-02):**

```bash
find . -iname "LICENSE*" -o -iname "COPYING*" -o -iname "NOTICE*"   # no matches (excluding .git)
git log --all --diff-filter=A --name-only | grep -iE "licen|copying"  # no matches
grep -rniE "licen[cs]e|SPDX|proprietary|all rights reserved|public domain" \
  --include=*.md --include=*.txt --include=*.yaml --include=*.json .
# only hits are the IP documents themselves; no statement of intent anywhere
```

No SPDX identifier, no `license` field in any metadata file, and no sentence in `README.md`,
`RESOURCES.md`, `CURRENT_STATE.md`, `render.yaml` or the handoffs states an intended licence.

## What that means, stated plainly

With no licence granted, **the default position under copyright is "all rights reserved."**
Copyright in the repository's contents exists automatically on fixation (see `IP-INVENTORY.md`);
its absence of a licence means no one is granted permission to copy, modify, or redistribute it.
That is a *default*, not a *decision*, and it is a poor one to leave implicit — it is invisible to
anyone who looks, and it blocks the ordinary reuse this project may eventually want.

This file does not resolve that. It records that it is unresolved, so the next person does not
have to rediscover it.

## Why no licence was invented here

Choosing a licence is an **owner decision with legal consequences**, and the repository gives no
evidence of intent to infer one from. The binding doctrine for this lane is explicit: never claim
or create a legal position that has not been verified or authorised. Writing a `LICENSE` file is
granting a licence; that is a legal commitment, and it is approval-gated. So this file exists
instead.

Two things make the choice genuinely non-obvious rather than a formality:

1. **AI authorship.** Much of this repository was written by AI agents. In several jurisdictions,
   purely machine-generated output may not attract copyright at all, and the position is unsettled
   (see `IP-INVENTORY.md`, "The AI-authorship question"). A licence purports to grant rights in
   the work; whether there are rights to grant, and who holds them, is part of the question.
2. **Third-party components.** The code depends on third-party packages under their own licences
   (all permissive, one file-level-copyleft — see `IP-INVENTORY.md`, "Third-party dependency
   licences"). A licence choice for *this* repository does not change those, but a public release
   would need to satisfy them.

## The options (for the owner to choose from — none is chosen)

| Option | Effect | Typical fit |
|---|---|---|
| **Keep it proprietary** (no licence file, or an explicit "all rights reserved" notice) | No one may reuse without permission | If Oddfellow is meant to be a closed product |
| **MIT** | Permissive: reuse, modify, sublicense, with attribution | If broad reuse and low friction are wanted |
| **Apache-2.0** | Permissive plus an express patent grant and trademark clause | If patent clarity matters (note: a patent grant in a licence is not a patent filing) |
| **AGPL-3.0 / GPL-3.0** | Copyleft: derivatives must remain open | If the intent is that improvements stay public |

**None of these is recommended here.** This table exists so the decision can be made in one place.

## What is required to close this

1. **The owner decides** the intended posture (proprietary, or a named open licence).
2. If a named open licence is chosen, add the standard, unmodified licence text as `LICENSE`
   (and, if the project is published, a short `NOTICE`/attribution section where required).
3. If proprietary is chosen, add an explicit short `LICENSE`/notice stating "all rights reserved"
   so the position is visible rather than merely implicit.

Until then, the correct reading of this repository is: **no licence granted; copyright default
applies.** Do not represent the project as open source, and do not reuse its contents on the
assumption that it is.

---

*This is not legal advice. It records a factual state of the repository and an open decision.*
