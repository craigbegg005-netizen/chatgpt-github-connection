"""Tests for the operator CLI.

Deliberately narrow. The connector's behaviour is already covered by the other
suites; duplicating it here to inflate a count would be worse than useless,
because a padded suite hides which tests actually matter. What is tested here is
only what the CLI adds:

  * **exit codes carry meaning.** A refusal is not a success, so `apply` must exit
    non-zero when nothing was accepted -- otherwise a script cannot tell "done"
    from "the gate said no".
  * **the CLI never prints a token value it did not just mint.** `tokens` lists
    metadata only.
  * **it does not bypass enforcement.** It is a convenience layer, not an
    authority: the same approval and ownership rules apply.
"""

from __future__ import annotations

import io
import os
import sys
import contextlib

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from connector import Job, Risk, Store, TaskKind, new_job_id  # noqa: E402
from connector import cli  # noqa: E402


def run(argv):
    """Run the CLI, returning (exit_code, stdout, stderr)."""
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = cli.main(argv)
    return code, out.getvalue(), err.getvalue()


@pytest.fixture()
def db(tmp_path):
    path = str(tmp_path / "cli.db")
    s = Store(path)
    for title, risk in (("low job", Risk.LOW), ("critical job", Risk.CRITICAL)):
        payload = {"spec": title}
        s.create_job(
            Job(job_id=new_job_id(TaskKind.CODE, title, payload), kind=TaskKind.CODE,
                title=title, payload=payload, risk=risk),
            actor="x",
        )
    s.close()
    return path


def test_jobs_lists_the_queue(db):
    code, out, _ = run(["--db", db, "jobs"])
    assert code == 0
    assert "low job" in out and "critical job" in out


def test_jobs_can_filter_by_status(db):
    code, out, _ = run(["--db", db, "jobs", "--status", "COMPLETE"])
    assert code == 0
    assert "low job" not in out


def test_handoff_prints_a_document(db):
    code, out, _ = run(["--db", db, "handoff", "--provider", "claude"])
    assert code == 0
    assert out.startswith("# Oddfellow handoff for claude")
    assert "job-" in out


def test_connect_prints_the_token_once_with_a_warning(db):
    code, out, err = run(["--db", db, "connect", "--provider", "claude", "--scopes", "read"])
    assert code == 0
    assert "odf_" in out
    assert "shown ONCE" in err


def test_tokens_lists_metadata_and_never_a_value(db):
    _, out, _ = run(["--db", db, "connect", "--provider", "claude", "--scopes", "read"])
    minted = [line for line in out.splitlines() if "odf_" in line]
    assert minted, "the connect output should contain the token"

    code, listing, _ = run(["--db", db, "tokens"])
    assert code == 0
    assert "ctk-" in listing
    assert "odf_" not in listing, "the token listing must never print a token value"


def test_apply_accepts_a_low_risk_result(db):
    s = Store(db)
    low = next(j for j in s.jobs() if j.risk is Risk.LOW)
    s.close()

    reply = f'```json\n{{"job_id": "{low.job_id}", "result": {{"ok": 1}}, "evidence": "checked"}}\n```'
    reply_path = db + ".reply.md"
    with open(reply_path, "w") as fh:
        fh.write(reply)

    code, out, _ = run(["--db", db, "apply", "--provider", "claude", "--file", reply_path])
    assert code == 0, "a fully accepted batch is a success"
    assert '"state": "COMPLETE"' in out
    assert '"verified": false' in out


def test_apply_exits_nonzero_when_something_was_refused(db):
    """A refusal is a normal outcome but it is not a success."""
    s = Store(db)
    crit = next(j for j in s.jobs() if j.risk is Risk.CRITICAL)
    s.close()
    reply = f'```json\n{{"job_id": "{crit.job_id}", "result": "done"}}\n```'
    path = db + ".crit.md"
    with open(path, "w") as fh:
        fh.write(reply)

    code, out, _ = run(["--db", db, "apply", "--provider", "claude", "--file", path])
    assert code == 1, "a refused batch must not exit zero"
    assert "approv" in out.lower()


def test_cli_does_not_bypass_the_approval_gate(db):
    """The CLI is a convenience layer, not an authority."""
    s = Store(db)
    crit = next(j for j in s.jobs() if j.risk is Risk.CRITICAL)
    s.close()
    reply = f'```json\n{{"job_id": "{crit.job_id}", "result": "done"}}\n```'
    path = db + ".crit2.md"
    with open(path, "w") as fh:
        fh.write(reply)
    run(["--db", db, "apply", "--provider", "claude", "--file", path])

    s = Store(db)
    after = next(j for j in s.jobs() if j.job_id == crit.job_id)
    s.close()
    assert after.status.value == "READY", "the critical job must be untouched"


def test_disconnect_revokes_and_reports(db):
    run(["--db", db, "connect", "--provider", "claude", "--scopes", "read"])
    code, out, _ = run(["--db", db, "disconnect", "--provider", "claude", "--reason", "test"])
    assert code == 0
    assert '"clean": true' in out


def test_requeue_requires_a_reason(db):
    # argparse enforces it before the command runs.
    with pytest.raises(SystemExit):
        cli.main(["--db", db, "requeue", "--job-id", "job-x"])


def test_unknown_status_is_an_error_not_a_silent_empty_list(db):
    code, _, err = run(["--db", db, "jobs", "--status", "NOT_A_STATUS"])
    assert code == 2
    assert "error" in err.lower()
