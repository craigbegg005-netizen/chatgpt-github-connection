# grants/ — source documents, and how they become one canonical file

**Created:** 2026-10-01 by Oddfellow (Letta agent), to resolve a file collision before it happened.

## The rule

There is exactly **one canonical grants file**:

> [`../GRANTS-NON-DILUTIVE-PIPELINE-2026-10-01.md`](../GRANTS-NON-DILUTIVE-PIPELINE-2026-10-01.md) — repository root

Everything in this directory is a **source document**: a parallel session's draft, kept verbatim
so nothing is lost and so the reconciliation is auditable. Source documents are never edited to
match the canonical file and are never treated as current.

## Why this directory exists

Two sessions independently drafted a grants pipeline on the same day. Committing both to the root
under similar names would have produced two files that each *look* authoritative — the exact
failure this project has already paid for with stale status pages and a stale resumption doc. A
collision is cheap to prevent now and expensive to untangle later.

So: Claude's draft is committed **here, unmodified**, and Letta reconciles it into the canonical
file. The reconciliation is additive — Preserve → Integrate → Improve → Execute → Verify.

## Pending

- `CLAUDE-GRANTS-PIPELINE-2026-10-01.md` — **not yet committed.** Claude reports it drafted but
  uncommitted; the owner will paste it. When it lands, reconcile it into the canonical file and
  record here what was merged, what was rejected, and why.

## Reconciliation checklist

When a source document arrives:

1. Diff it against the canonical file — what does it *add*, not what does it *repeat*.
2. Verify every new program term against that program's own primary source before it is labelled
   ✅ VERIFIED. A search hit is a lead, not a finding.
3. Keep the two questions separate: is the program's **term** verified, and does Begg AI
   **qualify**? Almost never both.
4. Never fabricate eligibility, revenue, ownership, employment, certifications, or registrations.
5. Record the merge decision here, with the date and what was rejected.
