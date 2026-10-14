# Connected channels — live capability matrix

**Tested: 2026-10-14 02:23 UTC.** Every row is a **live call I made**, not a registration.

## Only 2 of 7 channels actually work

| Channel | Registration | **Working?** | Evidence |
|---|---|---|---|
| **GitHub** | ✅ | ✅ **read + write** | 6+ pushes this session, remote read-back each time |
| **Fourthwall** | ✅ 126 tools | ✅ **works** | live API calls return shop/offer/collection/payout data |
| **BeggAi (Stripe)** | ✅ 10 tools | ❌ **`Invalid refresh token`** | `isError: true` on a read |
| **Google Drive** | ✅ 92 tools | ❌ **500 config unavailable** | 3 different tools, identical failure |
| **Gmail** | ✅ 61 tools | ❌ **500 config unavailable** | **identical failure to Drive** |
| Sentry | ✅ | ❌ **0 tools** | nothing exposed |
| Cloudflare | ✅ | ❌ **0 tools** | nothing exposed |

**Five of seven channels are registered and unusable.**

## The diagnostic that matters: this is NOT a general outage

`Fourthwall` is also a managed `streamable_http` server and **it works fine** on live calls.
So the 500s are **not** "managed MCP servers are down."

**They are specific to the two Google integrations** — Drive and Gmail fail with the *exact same*
message, which points at a shared provisioning or credential path rather than two coincidences.

**Practical read:** both Google integrations were connected recently and neither finished
provisioning. **That is also why "connect Google Drive" did not unblock the artwork transfer** —
the connection was made, but nothing behind it came up.

## Consequence for the multi-channel directive

Phase 3's failover chain (**GitHub → Drive → Gmail**) now reads:

| Tier | Channel | State |
|---|---|---|
| Preferred | GitHub | ✅ works |
| Secondary | Drive | ❌ 500 |
| Notification | Gmail | ❌ 500 |

**The chain still has exactly one working link — and now I can say why: it is the Google
integrations, specifically, that are dead.** Two independent connections failing identically is a
much stronger signal than one, and it names the suspect.

## Recommended fix, in order

1. **Disconnect and reconnect BOTH Google integrations together.** One shared path is failing, so fixing one and not the other is likely to leave the same fault. This is free.
2. **If both still 500 after a fresh connect**, it is provider-side and worth reporting to Letta with the exact message — it is already recorded in the repo.
3. **Stripe's `Invalid refresh token`** is a separate, older fault. Not needed for coordination; relevant only to the payments lane.

## What is still unknown because of this

- **The artwork's presence in the Drive folder.** No call reaches Google, so I have no evidence either way. **I did not conclude the folder is empty** — "cannot read it" and "it is empty" are different claims.
- **Anything in Gmail**, including whether the investor or grant lanes have replies.
- Whether the 51 MB archive was ever uploaded.

## Not claimed

No Drive access. No Gmail access. No Stripe access. **Two channels are described as working
because I called them; five are described as broken because I called them and they failed.**
