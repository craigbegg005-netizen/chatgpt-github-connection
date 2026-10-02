# Emergent Ventures — application draft

**Status: DRAFT. Not submitted. Nothing has been sent.**

Program verified open 2026-10-02 against Mercatus's own application form
(`mercatus.tfaforms.net/5099527`). Cost to apply: **$0**. Form limit: **1500 words**, no
PDFs.

---

## How to use this file

The form asks five things. **Two of them are the owner's to write and cannot be
drafted from this side**, because they are about his life rather than the project:

| # | Question | Who writes it |
|---|---|---|
| 1 | About you — personal story, and how it relates to the idea | 🔴 **OWNER ONLY** — see §1 |
| 2 | "What is one mainstream or 'consensus' view that you absolutely agree with?" | 🔴 **OWNER ONLY** — see §2 |
| 3 | The idea — what is new or unusual, what problem it solves | ✅ Drafted — §3 |
| 4 | Ballpark budget (revenue and expenses), not binding | ✅ Drafted — §4 |
| 5 | Duration, full/part-time, existing partnerships or supporters | ✅ Drafted — §5 |

Everything drafted below is **true and checkable against the repository**. Nothing is
invented, and where a fact is not known it says so rather than filling the gap.

**Do not submit until the owner has written §1 and §2 and approved the rest.**

---

## §1 — About you 🔴 OWNER ONLY

**I cannot write this and will not attempt it.** The form explicitly de-emphasises
credentials and asks how the idea connects to *your* life. Inventing a founder story
would be the single most damaging thing in this document — it is the part a reviewer
is most able to test in conversation, and it is the part that would be untrue.

To make it easy, these are the questions worth answering in your own words:

- What were you doing before this, and what made you start?
- What specifically frustrated you enough to build it? (Concrete beats abstract.)
- Why *you* — what do you see about this problem that someone else would miss?
- What have you actually done so far that you would defend under questioning?

**Facts that are true and available to you** if they help: you are building this as a
sole operator with no outside funding; you have shipped and tested real code; and you
have kept a written record of your own mistakes and corrections, which is unusual.

## §2 — The consensus view you agree with 🔴 OWNER ONLY

The form calls this its "trick" question — it reverses fashionable contrarianism by
asking you to *agree* with the mainstream. There is no safe generic answer, and a
filler answer is worse than a short honest one.

Worth knowing before you write: **your own project's doctrine is a candidate.** The
zero-spend-first rule and the "never claim a result you have not verified" rule are
both unfashionable *agreements* with old consensus positions — that unverified claims
are worthless, and that you should not spend money you do not have. That is a real
answer rather than a performed one, but it is yours to make or reject.

---

## §3 — The idea ✅ DRAFTED

**The short version.** A personal AI operating layer for one person or a very small
business, built so that it refuses to claim things it has not verified.

**What is actually new.** Not the assistant. The space is crowded and a reviewer would
be right to say so. Two things are genuinely unusual:

**1. Verification is enforced in code, not promised in a prompt.** The system
separates `COMPLETE` from `VERIFIED` as distinct states. A result submitted by a
worker lands as `COMPLETE`; promoting it to `VERIFIED` is a separate act that requires
evidence, and the code refuses to let the worker that produced a result verify its own
work. This exists because the failure mode of AI systems is not that they are wrong —
it is that they are confidently wrong in a way nobody notices.

**2. Irreversible actions are gated by construction, not by instruction.** Anything
classified as elevated risk enters a durable `WAITING_AUTHORIZATION` state and stops.
The approval is bound to one specific action, so a single "yes" cannot authorise a
different one. There is a separate emergency pause that blocks new work while leaving
work already in flight able to finish rather than stranding it.

**What problem it solves.** Small operators and individuals now have access to
powerful AI tools and no way to check them. The gap is not capability, it is
accountability: there is no cheap way for one person to run AI systems that can be
audited, that fail closed, and that do not quietly spend money. This is built for that
person, on free infrastructure, with a hard zero-spend default.

**Honest limitation, stated rather than hidden:** the verification discipline is
enforced where the code controls the path. It is not a proof system, and a determined
operator can bypass it. It raises the cost of being wrong; it does not make being
wrong impossible.

## §4 — Ballpark budget ✅ DRAFTED

**Current actual spend: $0.** Not a projection — the project runs entirely on free
tiers and existing hardware, by rule. Every paid service is disabled by default and
requires an explicit decision to enable.

**Proposed use of funds, if awarded** (the form asks for a ballpark, not a commitment):

| Item | Ballpark |
|---|---|
| Paid-tier infrastructure to remove free-tier cold starts and sleep limits | ~$300/yr |
| A phone dedicated to real-device testing (the one class of bug that cannot be found on a desktop) | ~$400 one-off |
| Domain and TLS | ~$30/yr |
| **Total** | **~$730** |

That is deliberately small. The program says it will consider *"very small grants if
they might change the trajectory of your life"*, and the honest ask here is small
because the constraint has never been money — it has been time and access to real
devices.

**Revenue: $0.** One digital product is listed publicly at $4.99; no verified sales.
The form states it does not mind profit, so this is stated plainly rather than dressed
up.

## §5 — Duration, commitment, supporters ✅ DRAFTED

**Duration:** ongoing, no end date. The project has been in active development since
late September 2026.

**Commitment:** part-time, alongside other work. **Not** claimed as full-time — the
form asks, and the answer is part-time.

**Existing partnerships or supporters: none.** No investors, no partners, no
institutional affiliation, no grants received, no customers. The form asks; the
honest answer is none, and inventing one would be both untrue and trivially checkable.

---

## What must be true before this is submitted

- [ ] Owner has written §1 and §2 in his own words
- [ ] Owner has read §3–§5 and approves them as accurate
- [ ] No claim in the document outruns the repository evidence
- [ ] Submitted by the owner — **this file is a draft, not a submission**

**Nothing has been submitted. No funding has been received. Verified revenue: $0.**
