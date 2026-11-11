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
