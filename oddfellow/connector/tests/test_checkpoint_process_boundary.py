"""
The failover resume flow must survive a PROCESS boundary, not just a Store reload.

Why this file exists
--------------------
Phase 3 (`becfa05`) added ``priority`` and the checkpoint trail with the claim
"resume scenario tested". Two tests carry that claim, and both are real -- neither
uses a mock:

  * ``test_checkpoints_survive_store_reload`` writes to a file-backed store and
    reopens it, so **durability** is genuinely tested.
  * ``test_failover_resume_scenario_keeps_the_trail`` exercises claim -> checkpoint
    -> release -> re-claim, so the **handoff logic** is genuinely tested.

They are tested *separately*, though. The resume test uses ``Store()``, which is
in-memory. The directive's actual flow is the combination: provider A and provider
B are different processes, possibly on different machines, and the trail has to
cross between them. Neither existing test would fail if the trail were durable but
lost on re-claim, or if re-claim preserved the trail but the write never reached
disk. Two properties, each verified alone, is not the property that matters.

This file tests the combination, with the second provider in a real subprocess.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import textwrap

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
ODDFELLOW = os.path.join(REPO, "oddfellow")

sys.path.insert(0, ODDFELLOW)

from connector import (  # noqa: E402
    Job,
    Priority,
    Risk,
    Store,
    TaskKind,
    Transport,
    new_job_id,
)

# Runs as a separate interpreter: the second provider, in its own process.
SECOND_PROVIDER = textwrap.dedent(
    """
    import json, sys
    sys.path.insert(0, sys.argv[1])
    from connector import Store, Transport
    with Store(sys.argv[2]) as store:
        store.claim_job(
            sys.argv[3], provider="claude", transport=Transport.QUEUE, actor="claude"
        )
        job = store.get_job(sys.argv[3])
        print(json.dumps({
            "provider": job.provider,
            "steps": [e["step"] for e in job.checkpoints],
            "notes": [e["note"] for e in job.checkpoints],
            "actors": [e["actor"] for e in job.checkpoints],
        }))
    """
)


def test_resume_crosses_a_process_boundary(tmp_path):
    db = str(tmp_path / "failover.db")
    payload = {"spec": "handoff across providers"}

    # Provider A: claim, make progress, release -- then this process ends.
    with Store(db) as store:
        job = Job(
            job_id=new_job_id(TaskKind.RESEARCH, "handoff", payload),
            kind=TaskKind.RESEARCH,
            title="handoff",
            payload=payload,
            risk=Risk.LOW,
            priority=Priority.URGENT,
            max_attempts=2,
        )
        job, _ = store.create_job(job, actor="oddfellow")
        store.claim_job(job.job_id, provider="grok", transport=Transport.HANDOFF, actor="grok")
        store.record_checkpoint(
            job.job_id, "demand researched", actor="grok", note="3 competitors", evidence="out/d.md"
        )
        store.release_claim(job.job_id, actor="grok", reason="cannot reach storefront")
        job_id = job.job_id

    # Provider B: a different interpreter, opening the same database.
    proc = subprocess.run(
        [sys.executable, "-c", SECOND_PROVIDER, ODDFELLOW, db, job_id],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode == 0, f"second provider failed:\n{proc.stdout}\n{proc.stderr}"
    resumed = json.loads(proc.stdout.strip().splitlines()[-1])

    assert resumed["provider"] == "claude", "B did not take the job over"
    assert resumed["steps"] == ["demand researched"], (
        "the trail did not cross the process boundary -- B would redo A's completed step"
    )
    assert resumed["notes"] == ["3 competitors"], "the note was lost in the handoff"
    assert resumed["actors"] == ["grok"], "the trail lost who did the work"

    # And the priority survived too, which is the other half of Phase 3.
    with Store(db) as store:
        assert store.get_job(job_id).priority is Priority.URGENT


def test_the_control_a_job_with_no_checkpoints_hands_over_an_empty_trail(tmp_path):
    """Negative control for the test above.

    If the second provider reported a trail regardless of what was written, the
    assertion in ``test_resume_crosses_a_process_boundary`` would pass for the
    wrong reason -- it would be a check whose condition cannot vary. Here nothing
    is recorded, so the trail must come back empty.
    """
    db = str(tmp_path / "empty.db")
    payload = {"spec": "no progress yet"}

    with Store(db) as store:
        job = Job(
            job_id=new_job_id(TaskKind.RESEARCH, "empty", payload),
            kind=TaskKind.RESEARCH,
            title="empty",
            payload=payload,
            risk=Risk.LOW,
            priority=Priority.NORMAL,
            max_attempts=2,
        )
        job, _ = store.create_job(job, actor="oddfellow")
        store.claim_job(job.job_id, provider="grok", transport=Transport.HANDOFF, actor="grok")
        store.release_claim(job.job_id, actor="grok", reason="no progress")
        job_id = job.job_id

    proc = subprocess.run(
        [sys.executable, "-c", SECOND_PROVIDER, ODDFELLOW, db, job_id],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    resumed = json.loads(proc.stdout.strip().splitlines()[-1])
    assert resumed["steps"] == [], (
        "a job with no recorded progress handed over a non-empty trail, so the "
        "test above is not measuring what was written"
    )
