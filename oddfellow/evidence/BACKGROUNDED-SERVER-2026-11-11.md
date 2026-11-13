# A backgrounded server does not survive in this sandbox — and my check reported that as a branch defect

**Date:** 2026-11-11 04:0x UTC · **Status:** environment property, confirmed by direct comparison

## What happened

Following the previous cycle's finding that Gate A needs three variables, I tried to turn the technique
that found it — *start the backend from the working tree, ask it `/livez`, read `checks_failed`* — into a
reusable script, `oddfellow/boot_check.sh`.

**It reported `DID NOT BOOT within 30s. That is a real finding: this branch does not start. Do not deploy
it.`** That was false. The branch boots fine.

## The evidence, by direct comparison

| Form | Result |
|---|---|
| `uvicorn … ` **in the foreground** | ✅ `Application startup complete` / `Uvicorn running on http://127.0.0.1:8903` |
| `uvicorn … &` (plain background) | ❌ no output, `/livez` never answers |
| `( uvicorn … & )` (subshell background) | ❌ no output, `/livez` never answers |
| `( … exec uvicorn … & )` | ❌ no output, `/livez` never answers |

The foreground form works every time; every backgrounded form produces an **empty log** and a port that
never answers. Note the empty log specifically: a process that failed to import would print a traceback.
Nothing printing at all means the process is not running, not that it is broken.

**This is an environment property, not a branch defect.** The same backgrounded form *did* work on
2026-11-10, so it is not stable across sandbox cycles either — which is the reason not to build tooling
that depends on it.

## Addendum — the backgrounded form also HANGS, and the mechanism is not fully explained

Recorded after the fact, when the delayed result of one of those attempts arrived: the
`nohup ... &` form did not merely fail to answer, it **hung until the harness killed it at its
300-second timeout**. The loop finished (15 polls, no answer), the final `curl` returned empty,
and the command then sat there until it was timed out.

**A plausible mechanism, offered as a hypothesis and not as a finding:** a backgrounded process
inherits the command's output pipe, so the harness waits for that pipe to close even after the
script itself is done. That would explain the hang.

**It does not explain the empty log or the unanswered `/livez`**, and I am not going to pretend
it does. A process that is running serves; a process that fails to import prints a traceback.
Neither happened. So the mechanism is **unexplained**, and the practical conclusion is unchanged
and does not depend on it: **do not build tooling that needs a backgrounded server here.**

## Why this is recorded rather than just fixed

**The script's failure mode was a confident false negative about the product.** It did not say "I could
not tell"; it said *"this branch does not start. Do not deploy it."* I was one step from recording that
as a finding — and it would have been believed, because it is exactly the kind of specific, actionable
statement this project acts on.

That is the same shape as the vacuous-check family this codebase has been burned by, inverted: instead of
a check that always passes, a check that always fails and blames the thing under test.

## The rule

**When a tool reports a defect in the thing it is testing, verify the tool before believing it.** Here
that meant running the same command in the foreground and watching it succeed. The cost was one command;
the cost of believing it would have been a false "do not deploy" on the eve of a deploy.

## What is actually true

- **The current branch boots** — verified in the foreground, repeatedly.
- It reports `checks_failed: ["LETTA_MODEL"]` with the other two variables set, which is the previous
  cycle's finding and stands.
- **The reliable way to check a boot in this sandbox is the foreground form**, with `timeout` to bound it.
  A start-and-probe script cannot be relied on here, so none is committed.

---

## Related, 2026-11-13: a fetch that does not decompress looks like an empty page

Checking the Fourthwall storefront from a customer's side, the first fetch returned **200 with 25 KB of
body** — and grepping it for a title or product links found **nothing**. The obvious reading was "the shop
is live but empty".

It was not. The body was **gzip-compressed** and `curl` had not been asked to decompress it, so every
pattern match ran against binary. Re-fetching with `--compressed` gave the real page: title
`Wesellstuff`, product links, and product pages with prices.

**The rule is the same one as the backgrounded server, and it is worth stating twice: an empty result
from a tool is a fact about the tool until proven otherwise.** Here the tell was the body size — 25 KB of
"nothing" is not nothing — and the fix was one flag. A 200 with content that greps empty should send you
to look at the bytes, not to write down a finding.
