"""Local execution, refusal gates and process-boundary persistence."""
import json
import os
import subprocess
import sys

import pytest

from connector import Job, Risk, Status, Store, TaskKind, Transport
from connector.research_worker import run_research_job
from connector.store import ClaimRefused


def make_job(store, job_id="research", **kwargs):
    data = dict(job_id=job_id, title="local screen", kind=TaskKind.RESEARCH,
                payload={"screen": "sum-v1", "input": {"a": 2, "b": 3}})
    data.update(kwargs)
    return store.create_job(Job(**data), actor="owner")[0]


def add(data):
    return {"sum": data["a"] + data["b"]}


def test_executes_once_and_persists_after_restart(tmp_path):
    db = str(tmp_path / "research.sqlite")
    with Store(db) as store:
        make_job(store)
        r = run_research_job(store, "research", {"sum-v1": add})
        assert r["executed"] is True
        assert r["receipt"]["result"] == {"sum": 5}
        assert store.get_job("research").status is Status.COMPLETE
        assert store.get_job("research").verified is False
    code = '''
import json, sys
from connector import Store
from connector.research_worker import run_research_job
def must_not_run(data):
    raise AssertionError("completed work was repeated")
with Store(sys.argv[1]) as store:
    print(json.dumps(run_research_job(store, "research", {"sum-v1": must_not_run})))
'''
    result = subprocess.run([sys.executable, "-c", code, db],
                            env={**os.environ, "PYTHONPATH": os.pathsep.join(
                                [str(__import__('pathlib').Path(__file__).resolve().parents[2]),
                                 os.environ.get("PYTHONPATH", "")])},
                            capture_output=True, text=True, check=True, timeout=10)
    assert json.loads(result.stdout)["executed"] is False


@pytest.mark.parametrize("risk", [Risk.MEDIUM, Risk.HIGH, Risk.CRITICAL])
def test_refuses_risk_before_callback(risk):
    with Store() as store:
        make_job(store, risk=risk)
        with pytest.raises(ClaimRefused):
            run_research_job(store, "research", {"sum-v1": add})
        assert store.get_job("research").attempts == 0


def test_refuses_external_actions():
    with Store() as store:
        make_job(store, kind=TaskKind.EXTERNAL_ACTION)
        with pytest.raises(ClaimRefused):
            run_research_job(store, "research", {"sum-v1": add})


def test_pause_refuses_before_claim():
    with Store() as store:
        make_job(store)
        store.set_paused(True, actor="owner")
        with pytest.raises(ClaimRefused):
            run_research_job(store, "research", {"sum-v1": add})
        assert store.get_job("research").attempts == 0


def test_unverified_dependency_refused_then_independent_verification_allows():
    with Store() as store:
        make_job(store, "dep")
        run_research_job(store, "dep", {"sum-v1": add})
        make_job(store, depends_on=("dep",))
        with pytest.raises(ClaimRefused):
            run_research_job(store, "research", {"sum-v1": add})
        store.verify_result("dep", verified_by="reviewer", evidence="tests/report.json")
        assert run_research_job(store, "research", {"sum-v1": add})["executed"]
        assert store.get_job("research").verified is False


@pytest.mark.parametrize("payload", [
    {"screen": "os.system", "input": {}},
    {"screen": "sum-v1", "input": {}, "command": "shell"},
    {"screen": "sum-v1", "input": {"x": float("nan")}},
])
def test_bad_payload_refused_before_claim(payload):
    with Store() as store:
        make_job(store, payload=payload)
        with pytest.raises(ValueError):
            run_research_job(store, "research", {"sum-v1": add})
        assert store.get_job("research").attempts == 0


def test_exception_fails_once_without_leaking_message():
    def broken(data):
        raise ValueError("sensitive-sentinel")
    with Store() as store:
        make_job(store)
        with pytest.raises(RuntimeError, match="computation failed"):
            run_research_job(store, "research", {"sum-v1": broken})
        assert store.get_job("research").status is Status.FAILED_TERMINAL
        assert "sensitive-sentinel" not in json.dumps(store.audit_trail())
        with pytest.raises(ClaimRefused):
            run_research_job(store, "research", {"sum-v1": broken})
        assert store.get_job("research").attempts == 1


def test_active_claim_not_stolen():
    with Store() as store:
        make_job(store)
        store.claim_job("research", "other", Transport.QUEUE, actor="other")
        with pytest.raises(ClaimRefused):
            run_research_job(store, "research", {"sum-v1": add})
        assert store.get_job("research").provider == "other"


def test_result_nan_fails_and_input_copy_isolated():
    def broken(data):
        data["a"] = 99
        return {"value": float("nan")}
    with Store() as store:
        make_job(store)
        with pytest.raises(RuntimeError):
            run_research_job(store, "research", {"sum-v1": broken})
        assert store.get_job("research").payload["input"]["a"] == 2


def test_non_research_completion_not_reused():
    with Store() as store:
        make_job(store)
        store.claim_job("research", "other", Transport.QUEUE, actor="other")
        store.submit_result("research", {"answer": 5}, actor="other", provider="other")
        with pytest.raises(ClaimRefused):
            run_research_job(store, "research", {"sum-v1": add})


def test_corrupted_saved_receipt_not_reused():
    with Store() as store:
        make_job(store)
        receipt = run_research_job(store, "research", {"sum-v1": add})["receipt"]
        receipt["result"]["sum"] = 999
        # Simulate corruption through the trusted Store API, retaining old hash.
        job = store.get_job("research")
        store.set_status(job, Status.READY, actor="owner")
        store.claim_job("research", "other", Transport.QUEUE, actor="other")
        store.submit_result("research", receipt, actor="other", provider="other")
        with pytest.raises(ClaimRefused):
            run_research_job(store, "research", {"sum-v1": add})
