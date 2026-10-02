"""Tier 3 and Tier 4 of the fallback ladder: structured handoff, and the queue.

The ladder is MCP -> API -> structured handoff -> durable queue. The first two
need credentials nobody has yet, so *nothing* in this connector was usable with a
real provider. This module is the rungs that need nothing: it turns the job queue
into a document a human can paste into any AI, and turns that AI's answer back
into results -- through the same `submit_result` enforcement as every other path.

That matters beyond convenience. It means the connector is usable **today** with
Claude or any other provider, at zero cost, with no account, no key, and no
network exposure -- which is also the safest possible way to find out whether the
job schema and the approval rules are right before anything is connected.

Three properties are load-bearing:

  * **A handoff carries no secrets.** It contains job ids, kinds, titles, payloads
    and risk -- never a token, never the owner credential. A document meant to be
    pasted into a third-party chat has to be safe to paste.
  * **A returned result is untrusted input.** It is parsed defensively, and it then
    goes through `submit_result`, which enforces that the job is RUNNING and that
    the submitting provider holds the claim. A handoff cannot talk its way past
    the gate; it can only submit like anything else.
  * **Nothing is auto-verified.** A returned result lands as COMPLETE. It becomes
    VERIFIED only through the separate, evidenced `verify_result` path.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from .schema import Job, Risk, Status, canonical_json
from .store import ClaimRefused, Store, SubmitRefused

#: Fenced blocks the parser will look for. A provider is asked to answer inside
#: one; if it answers in prose instead, we say so rather than guessing.
_BLOCK = re.compile(r"```(?:json)?\s*(.*?)```", re.S)


def render_handoff(store: Store, provider: str, limit: int = 20) -> str:
    """Render the claimable queue as a document a human can paste into any AI.

    Only READY jobs whose dependencies are complete are included: handing over work
    that cannot start yet would produce results that cannot be accepted, which is
    worse than not handing it over.
    """
    jobs = list(store.ready_jobs())[:limit]
    if not jobs:
        return (
            f"# Oddfellow handoff for {provider}\n\n"
            "No jobs are ready. Nothing to do.\n"
        )

    lines = [
        f"# Oddfellow handoff for {provider}",
        "",
        "You are being asked to do specific, numbered jobs. For each one you complete,",
        "return a single fenced JSON block in exactly this shape:",
        "",
        "```json",
        '{"job_id": "<the id below>", "result": <any JSON>, "evidence": "<what you actually checked>"}',
        "```",
        "",
        "Rules:",
        "- Use the `job_id` exactly as given. A result with an unknown id is refused.",
        "- `evidence` is required. A result without evidence is accepted as COMPLETE",
        "  but can never be marked VERIFIED, so it will not be treated as fact.",
        "- Do not invent results. If a job cannot be done, say so in the block instead.",
        "",
        "---",
        "",
    ]
    for j in jobs:
        lines += [
            f"## {j.job_id}",
            "",
            f"- **kind:** {j.kind.value}",
            f"- **title:** {j.title}",
            f"- **risk:** {j.risk.value}",
            "",
            "**Input:**",
            "",
            "```json",
            canonical_json(j.payload),
            "```",
            "",
        ]
    return "\n".join(lines)


@dataclass
class HandoffResult:
    job_id: str
    result: object
    evidence: str = ""


def parse_handoff(text: str) -> tuple[list[HandoffResult], list[str]]:
    """Parse a provider's answer. Returns ``(results, problems)``.

    Every failure is reported rather than skipped. A parser that silently drops the
    blocks it cannot read turns "the provider answered badly" into "the provider
    answered", which is the kind of quiet substitution this project keeps having to
    undo.
    """
    results: list[HandoffResult] = []
    problems: list[str] = []

    for n, raw in enumerate(_BLOCK.findall(text or ""), start=1):
        body = raw.strip()
        if not body:
            continue
        try:
            payload = json.loads(body)
        except json.JSONDecodeError as exc:
            problems.append(f"block {n}: not valid JSON ({exc.msg})")
            continue
        if not isinstance(payload, dict):
            problems.append(f"block {n}: expected a JSON object, got {type(payload).__name__}")
            continue
        job_id = payload.get("job_id")
        if not isinstance(job_id, str) or not job_id.strip():
            problems.append(f"block {n}: missing job_id")
            continue
        if "result" not in payload:
            problems.append(f"block {n}: missing result")
            continue
        evidence = payload.get("evidence", "")
        if not isinstance(evidence, str):
            evidence = canonical_json(evidence)
        results.append(HandoffResult(job_id.strip(), payload["result"], evidence))

    if not results and not problems and (text or "").strip():
        problems.append("no fenced JSON block found in the reply")
    return results, problems


def apply_handoff(
    store: Store,
    text: str,
    provider: str,
    actor: str,
    *,
    approval_ids: dict[str, str] | None = None,
) -> dict:
    """Claim and submit each parsed result, through the normal enforcement.

    Returns a report naming what was accepted, what was refused and why. Nothing
    here bypasses `claim_job` or `submit_result` -- a handoff is an untrusted
    channel like any other, and it must not be a way around the gate.

    ``approval_ids`` maps a job id to the approval that covers it. It replaces a
    single `approved: bool` that was applied to the whole batch: one flag for
    every job in the reply, so approving any gated job in a batch approved all of
    them. An approval is per job, and this signature is what makes that true
    rather than merely intended.
    """
    approval_ids = approval_ids or {}
    results, problems = parse_handoff(text)
    accepted, refused = [], []

    for r in results:
        job = store.get_job(r.job_id)
        if job is None:
            refused.append({"job_id": r.job_id, "reason": "unknown job"})
            continue
        try:
            if job.status is Status.READY:
                store.claim_job(
                    r.job_id, provider, None, actor=actor,
                    approval_id=approval_ids.get(r.job_id),
                )
            store.submit_result(r.job_id, r.result, actor=actor, provider=provider)
            accepted.append({
                "job_id": r.job_id,
                "state": "COMPLETE",
                "evidence_supplied": bool(r.evidence.strip()),
                "verified": False,
            })
        except (ClaimRefused, SubmitRefused) as exc:
            refused.append({"job_id": r.job_id, "reason": str(exc)})

    return {
        "provider": provider,
        "accepted": accepted,
        "refused": refused,
        "problems": problems,
        "note": (
            "Accepted results are COMPLETE, not VERIFIED. Verification is a separate "
            "act requiring evidence, performed by someone other than the submitter."
        ),
    }
