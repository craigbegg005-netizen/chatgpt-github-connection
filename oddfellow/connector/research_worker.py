"""Bounded local research execution using the existing durable queue.

Only trusted, operator-registered pure functions may be supplied in ``screens``.
Job payloads select a name, never an import, URL, command or file path. This is
not a sandbox for arbitrary callbacks and does not start a daemon or call an AI.
Results remain unverified until the existing independent verification gate runs.
"""
from __future__ import annotations

import copy
import hashlib
import json
from typing import Callable, Mapping

from .schema import Risk, Status, TaskKind, Transport, canonical_provider
from .store import ClaimRefused, Store

MAX_JSON_BYTES = 1_000_000


def _json_bytes(value) -> bytes:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"),
                         allow_nan=False).encode("utf-8")
    if len(encoded) > MAX_JSON_BYTES:
        raise ValueError("research data exceeds local size limit")
    return encoded


def run_research_job(store: Store, job_id: str,
                     screens: Mapping[str, Callable[[dict], dict]], *,
                     provider: str = "local-research") -> dict:
    """Execute one LOW-risk RESEARCH job once; no automatic retry or verification.

Registry keys should include the screen version (e.g. ``heat-pump-v11``).
Dependencies must have independently verified results before execution. A
completed job returns its saved receipt without re-running the computation.
"""
    provider = canonical_provider(provider)
    job = store.get_job(job_id)
    if job is None:
        raise KeyError(job_id)
    if job.kind is not TaskKind.RESEARCH or job.risk is not Risk.LOW:
        raise ClaimRefused("local worker accepts LOW-risk RESEARCH jobs only")
    if store.is_paused():
        raise ClaimRefused("emergency pause is set")
    payload = job.payload
    if (not isinstance(payload, dict) or set(payload) != {"screen", "input"}
            or not isinstance(payload["screen"], str)
            or not isinstance(payload["input"], dict)):
        raise ValueError("expected only screen name and input object")
    name = payload["screen"]
    if name not in screens or not callable(screens[name]):
        raise ValueError("screen is not registered locally")
    material = _json_bytes(payload)
    input_sha = hashlib.sha256(material).hexdigest()
    if job.status is Status.COMPLETE:
        saved = job.result
        if (not isinstance(saved, dict) or saved.get("worker") != "local-research-v1"
                or saved.get("input_sha256") != input_sha
                or saved.get("screen") != name
                or not isinstance(saved.get("result"), dict)
                or saved.get("output_sha256") != hashlib.sha256(
                    _json_bytes(saved["result"])).hexdigest()):
            raise ClaimRefused("completed result is not a matching local receipt")
        return {"job_id": job_id, "executed": False, "receipt": saved}
    for dep_id in job.depends_on:
        dep = store.get_job(dep_id)
        if dep is None or dep.status is not Status.COMPLETE or not dep.verified:
            raise ClaimRefused("research dependency is incomplete or unverified")
    # Claim's conditional SQL update provides one winner for racing workers.
    claim = store.claim_job(job_id, provider, Transport.QUEUE, actor=provider,
                            paused=store.is_paused())
    try:
        # A pure function cannot edit the caller's payload by aliasing it.
        value = screens[name](copy.deepcopy(payload["input"]))
        if not isinstance(value, dict):
            raise ValueError("screen result must be an object")
        result_bytes = _json_bytes(value)
        receipt = {
            "worker": "local-research-v1", "screen": name,
            "input_sha256": input_sha,
            "output_sha256": hashlib.sha256(result_bytes).hexdigest(),
            "scope": "LOCAL_COMPUTATION_ONLY",
            "scientifically_validated": False,
            "result": value,
        }
        _json_bytes(receipt)
    except Exception:
        # Do not put exception messages (which may contain input/secrets) in audit.
        store.finish_research_claim(claim, failed=True)
        raise RuntimeError("local research computation failed") from None
    completed = store.finish_research_claim(claim, result=receipt)
    return {"job_id": job_id, "executed": True, "receipt": completed.result}
