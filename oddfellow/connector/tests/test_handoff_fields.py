"""Tests for the Phase 4 universal-handoff fields: ``asset_refs`` and ``next_action``.

These are the last two items the failover directive's universal field set asked for
and the code did not have. The directive's own words are "asset + GitHub refs" and
"next action" -- the point being that a job handed to another provider should carry
*where the material is* and *what to do next*, so the receiver does not have to ask
or infer either.

The failure mode they guard against is quiet: a field that exists on the in-memory
object but never reaches the database looks correct in every unit test that does not
reload, and is simply absent for the next provider. So the round-trip test is the
load-bearing one, not the rendering test.
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from connector import (  # noqa: E402
    Job,
    Priority,
    Risk,
    Store,
    TaskKind,
    new_job_id,
)
from connector.handoff import render_handoff  # noqa: E402


def job(title, **kwargs):
    payload = {"spec": title}
    return Job(
        job_id=new_job_id(TaskKind.RESEARCH, title, payload),
        kind=TaskKind.RESEARCH,
        title=title,
        payload=payload,
        risk=Risk.LOW,
        **kwargs,
    )


# ------------------------------------------------------------------- defaults


def test_defaults_are_empty_so_existing_jobs_are_unaffected():
    """Every job that predates these fields must keep working unchanged."""
    j = job("a")
    assert j.asset_refs == ()
    assert j.next_action is None


# ------------------------------------------------------------- round trip


def test_fields_round_trip_through_storage(tmp_path):
    """The load-bearing test: a field that never reaches the DB is silently lost."""
    db = str(tmp_path / "c.db")
    refs = ("docs/plan.md", "https://github.com/o/r/pull/7", "abc1234")
    with Store(db) as store:
        created, _ = store.create_job(
            job("publish the plan", asset_refs=refs, next_action="open the PR"),
            actor="oddfellow",
        )
    with Store(db) as store:
        reloaded = store.get_job(created.job_id)

    assert tuple(reloaded.asset_refs) == refs, (
        "asset_refs did not survive the round trip -- check the INSERT and UPDATE "
        "column lists in store.py, not just the dataclass"
    )
    assert reloaded.next_action == "open the PR"


def test_a_changed_value_persists_through_the_update_path(tmp_path):
    """The UPDATE path has its own column list, and the failure it causes is subtle.

    An UPDATE that omits a column does NOT drop the value -- it leaves the stored
    value alone. So a field present in the INSERT list but missing from the UPDATE
    set list round-trips perfectly on create and then silently fails to record any
    later change. Testing "does it survive an update" therefore proves nothing; the
    test has to CHANGE the value and check the change landed.

    White-box on purpose: `_update` is the only path that writes these fields after
    creation, and there is no public mutator for them yet. If one is added, this
    should move to it.
    """
    db = str(tmp_path / "c.db")
    with Store(db) as store:
        created, _ = store.create_job(job("a", next_action="first"), actor="oddfellow")
        created.next_action = "second"
        created.asset_refs = ("docs/plan.md",)
        store._update(created, actor="oddfellow", event="test.mutate")
    with Store(db) as store:
        reloaded = store.get_job(created.job_id)

    assert reloaded.next_action == "second", (
        "a changed next_action did not persist -- it is in the INSERT column list but "
        "missing from the UPDATE set list in store.py"
    )
    assert tuple(reloaded.asset_refs) == ("docs/plan.md",)


# ---------------------------------------------------------------- handoff


def test_handoff_renders_assets_and_next_action(tmp_path):
    db = str(tmp_path / "c.db")
    with Store(db) as store:
        store.create_job(
            job("publish the plan",
                asset_refs=("docs/plan.md", "abc1234"),
                next_action="open the PR"),
            actor="oddfellow",
        )
        text = render_handoff(store, "chatgpt")

    assert "**Assets:**" in text
    assert "`docs/plan.md`" in text
    assert "`abc1234`" in text
    assert "**Next action:** open the PR" in text


def test_handoff_renders_priority(tmp_path):
    """priority was in the schema but never rendered, so a recipient could not
    tell an urgent job from a routine one."""
    db = str(tmp_path / "c.db")
    with Store(db) as store:
        store.create_job(job("urgent", priority=Priority.URGENT), actor="oddfellow")
        text = render_handoff(store, "chatgpt")
    assert "**priority:** urgent" in text


def test_handoff_omits_empty_blocks(tmp_path):
    """A job with neither field must not gain empty noise -- an 'Assets:' heading
    with nothing under it reads as missing data rather than as 'none'."""
    db = str(tmp_path / "c.db")
    with Store(db) as store:
        store.create_job(job("plain"), actor="oddfellow")
        text = render_handoff(store, "chatgpt")
    assert "**Assets:**" not in text
    assert "**Next action:**" not in text
