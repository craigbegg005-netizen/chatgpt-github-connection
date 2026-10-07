"""Tests for the Cognitive Capability Profile.

The tests that matter most are the ones that make a number MOVE. A profile whose
dimensions cannot be shown to change is a set of constants, and a constant that
reads 1.0 is the most dangerous kind of false control this project has produced.

So the shape here is: for each dimension, build a counterfactual where the thing
being measured is genuinely worse, and assert the number is worse. If someone
later "fixes" a dimension by hard-coding its value, these tests fail.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cognition.profile import (  # noqa: E402
    Confidence,
    Context,
    Measurement,
    build_profile,
    contradiction_detection,
    goal_continuity,
    identity_continuity,
    memory_accuracy,
    memory_continuity,
    metacognitive_performance,
    render,
    self_model_accuracy,
    summarise,
    uncertainty_calibration,
    autonomous_task_completion,
    adaptation_after_failure,
)


# --------------------------------------------------------------------------
# The structural rule: a measurement must be able to name its own falsifier
# --------------------------------------------------------------------------


def test_a_measurement_without_a_falsifier_is_refused():
    """The rule the whole module rests on.

    A number that cannot name what would move it is a claim wearing a number's
    clothes. Refusing to construct one is stronger than warning about it, because
    a warning can be ignored by the next caller.
    """
    with pytest.raises(ValueError, match="declares no falsifier"):
        Measurement(
            dimension="pretend", value=1.0, unit="made up",
            confidence=Confidence.REPRODUCED, can_fail="   ",
        )


def test_an_unmeasurable_dimension_must_explain_itself():
    """`None` with no reason is indistinguishable from an oversight."""
    with pytest.raises(ValueError, match="gives no reason"):
        Measurement(
            dimension="pretend", value=None, unit="made up",
            confidence=Confidence.ARTIFACT, can_fail="anything", reason="",
        )


def test_self_reported_measurements_never_count_toward_a_score():
    """A dimension that can only cite its own narrative is recorded, not scored."""
    m = Measurement(
        dimension="narrative", value=1.0, unit="vibes",
        confidence=Confidence.SELF_REPORTED, can_fail="anything",
    )
    assert m.measurable is True
    assert m.counts_toward_score is False


# --------------------------------------------------------------------------
# memory_continuity
# --------------------------------------------------------------------------


def test_memory_continuity_falls_when_the_entry_point_answers_nothing(tmp_path):
    (tmp_path / "CURRENT_STATE.md").write_text("just some prose\n", encoding="utf-8")
    m = memory_continuity(Context(repo_root=tmp_path, memory_dir=None))
    assert m.value == 0.0, "an entry point with no reconstruction headings scores zero"


def test_memory_continuity_rises_when_the_entry_point_answers_all_five(tmp_path):
    (tmp_path / "CURRENT_STATE.md").write_text(
        "# What is happening\n# Why\n# Evidence\n# Open and uncertain\n# Next steps\n",
        encoding="utf-8",
    )
    m = memory_continuity(Context(repo_root=tmp_path, memory_dir=None))
    assert m.value == pytest.approx(1.0)


def test_memory_continuity_is_unmeasurable_with_no_entry_point(tmp_path):
    m = memory_continuity(Context(repo_root=tmp_path, memory_dir=None))
    assert m.value is None
    assert "no entry-point document" in m.reason


# --------------------------------------------------------------------------
# memory_accuracy
# --------------------------------------------------------------------------


def _git_repo(path):
    """A real, empty git repo -- so the head check has something to disagree with.

    Without this the check correctly reports 'git unavailable' rather than
    'failed', which is a different observation and not what this test is about.
    """
    import subprocess
    subprocess.run(["git", "init", "-q"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.email", "t@example.com"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=path, check=True)
    (path / "seed.txt").write_text("seed\n", encoding="utf-8")
    subprocess.run(["git", "add", "seed.txt"], cwd=path, check=True)
    subprocess.run(["git", "commit", "-qm", "seed"], cwd=path, check=True)
    return path


def test_memory_accuracy_falls_when_a_recorded_claim_is_false(tmp_path):
    """The check that would have caught the six-day-old wrong deployed commit."""
    _git_repo(tmp_path)
    ctx = Context(
        repo_root=tmp_path, memory_dir=None,
        recorded_claims={"canonical_head": "0" * 40},
    )
    m = memory_accuracy(ctx)
    assert m.value == 0.0, "a recorded head that matches nothing must score zero"
    assert any("FAIL" in e for e in m.evidence)


def test_memory_accuracy_is_unmeasurable_rather_than_zero_when_nothing_ran():
    """'Could not run' and 'failed' are different observations.

    The first version of this function conflated them and reported 0.333 for a
    system whose claims were in fact fine. A checker that cannot run must not
    manufacture a failure.
    """
    m = memory_accuracy(Context(repo_root=None, memory_dir=None, recorded_claims={}))
    assert m.value is None
    assert "could run" in m.reason


# --------------------------------------------------------------------------
# self_model_accuracy
# --------------------------------------------------------------------------


def test_self_model_accuracy_falls_when_a_capability_is_declared_but_absent(tmp_path):
    (tmp_path / "oddfellow" / "cognition").mkdir(parents=True)
    (tmp_path / "oddfellow" / "cognition" / "SELF_MODEL.json").write_text(
        json.dumps({"modules_present": ["definitely_not_here"]}), encoding="utf-8")
    m = self_model_accuracy(Context(repo_root=tmp_path, memory_dir=None))
    assert m.value == 0.0


def test_self_model_accuracy_checks_declared_limitations_too(tmp_path):
    """A self-model that lists only strengths is a brochure.

    Declaring a limitation is a claim like any other: if the thing declared
    absent is in fact present, the self-model is wrong and must say so.
    """
    (tmp_path / "oddfellow" / "cognition").mkdir(parents=True)
    (tmp_path / "oddfellow" / "cognition" / "SELF_MODEL.json").write_text(
        json.dumps({"tools_absent": ["PATH"]}), encoding="utf-8")
    m = self_model_accuracy(Context(repo_root=tmp_path, memory_dir=None))
    assert m.value == 0.0, "$PATH is present, so declaring it absent is a false limitation"


def test_secrets_are_observed_but_never_scored(tmp_path):
    """Scoring a secret check would manufacture failures.

    Whether a secret is visible depends on how the caller was invoked -- the
    harness injects it only when the command text names it literally -- so a
    scored check would report a present credential as missing.
    """
    (tmp_path / "oddfellow" / "cognition").mkdir(parents=True)
    (tmp_path / "oddfellow" / "cognition" / "SELF_MODEL.json").write_text(
        json.dumps({"secrets_available": ["A_SECRET_THAT_IS_NOT_SET"],
                    "modules_present": ["cognition"]}), encoding="utf-8")
    m = self_model_accuracy(Context(repo_root=tmp_path, memory_dir=None))
    assert m.value == 1.0, "the module check passes; the secret check must not drag it down"
    assert any("NOT OBSERVABLE" in e for e in m.evidence)


# --------------------------------------------------------------------------
# uncertainty_calibration
# --------------------------------------------------------------------------


def test_calibration_records_a_verified_claim_that_proved_wrong(tmp_path):
    (tmp_path / "oddfellow" / "cognition").mkdir(parents=True)
    (tmp_path / "oddfellow" / "cognition" / "claims.jsonl").write_text(
        json.dumps({"claim": "a", "outcome": "held", "resolved_at": "t"}) + "\n" +
        json.dumps({"claim": "b", "outcome": "failed", "resolved_at": "t"}) + "\n",
        encoding="utf-8",
    )
    m = uncertainty_calibration(Context(repo_root=tmp_path, memory_dir=None))
    assert m.value == pytest.approx(0.5)
    assert any("failed" in e for e in m.evidence)


def test_calibration_is_unmeasurable_with_no_resolved_claims(tmp_path):
    (tmp_path / "oddfellow" / "cognition").mkdir(parents=True)
    (tmp_path / "oddfellow" / "cognition" / "claims.jsonl").write_text(
        json.dumps({"claim": "a", "outcome": "unresolved"}) + "\n", encoding="utf-8")
    m = uncertainty_calibration(Context(repo_root=tmp_path, memory_dir=None))
    assert m.value is None, "unresolved claims are not evidence of calibration"


# --------------------------------------------------------------------------
# contradiction_detection
# --------------------------------------------------------------------------


def test_contradiction_detection_finds_two_files_that_disagree(tmp_path):
    (tmp_path / "one.md").write_text("638 tests pass\n", encoding="utf-8")
    (tmp_path / "two.md").write_text("999 tests pass\n", encoding="utf-8")
    m = contradiction_detection(Context(repo_root=tmp_path, memory_dir=tmp_path))
    assert m.value == 1.0
    assert m.falsifier_demonstrated is True


def test_contradiction_detection_does_not_flag_history_as_disagreement(tmp_path):
    """A time series is not a contradiction.

    The first version of this detector scanned every file including the cycle
    log and reported seven distinct test counts as a contradiction. They were
    each true when written. A detector that cries wolf is a false control in its
    own right, so archives and logs are excluded and only the last value in each
    current-state file counts.
    """
    (tmp_path / "current.md").write_text("638 tests pass\n", encoding="utf-8")
    (tmp_path / "cycles-archive-9.md").write_text("107 tests pass\n", encoding="utf-8")
    (tmp_path / "lessons.md").write_text("509 tests pass\n", encoding="utf-8")
    m = contradiction_detection(Context(repo_root=tmp_path, memory_dir=tmp_path))
    assert m.value == 0.0, "history must not be reported as a present disagreement"


def test_contradiction_detection_is_unmeasurable_if_the_detector_cannot_detect():
    """A detector that finds nothing is indistinguishable from one that cannot find.

    With no memory directory the dimension reports NOT MEASURABLE rather than 0.0,
    because 0.0 would read as 'no contradictions' when the truth is 'not looked'.
    """
    m = contradiction_detection(Context(repo_root=None, memory_dir=None))
    assert m.value is None


# --------------------------------------------------------------------------
# adaptation_after_failure
# --------------------------------------------------------------------------


def test_adaptation_falls_when_a_lesson_has_no_control_behind_it(tmp_path):
    (tmp_path / "lessons.md").write_text(
        "## a lesson\n\nI was careless and I felt bad about it.\n", encoding="utf-8")
    m = adaptation_after_failure(Context(repo_root=tmp_path, memory_dir=tmp_path))
    assert m.value == 0.0, "a lesson with no test, guard, or commit is a lesson to be relearned"


def test_adaptation_rises_when_a_lesson_names_a_regression_test(tmp_path):
    (tmp_path / "lessons.md").write_text(
        "## a lesson\n\nThe fix is a regression test in tests/test_thing.py, commit abc1234.\n",
        encoding="utf-8")
    m = adaptation_after_failure(Context(repo_root=tmp_path, memory_dir=tmp_path))
    assert m.value == 1.0


# --------------------------------------------------------------------------
# autonomous_task_completion
# --------------------------------------------------------------------------


def test_autonomy_scores_zero_on_a_log_of_pure_no_ops(tmp_path):
    """The bug this test exists to prevent.

    The first version looked for productive verbs and scored 19/19 on a log whose
    entries mostly read 'Clean sweep. No drift.' A measurement that reports 1.0
    on a corpus of no-ops is the false-control shape, so the test is inverted:
    idleness is detected explicitly.
    """
    d = tmp_path / "projects" / "oddfellow"
    d.mkdir(parents=True)
    (d / "cycles.md").write_text(
        "".join(f"### entry {i}\n\n**Clean sweep.** No drift, nothing changed.\n\n"
                for i in range(6)),
        encoding="utf-8")
    m = autonomous_task_completion(Context(repo_root=tmp_path, memory_dir=tmp_path))
    assert m.value == 0.0


def test_autonomy_scores_one_when_every_cycle_changed_something(tmp_path):
    d = tmp_path / "projects" / "oddfellow"
    d.mkdir(parents=True)
    (d / "cycles.md").write_text(
        "".join(f"### entry {i}\n\nFound a defect and pushed a fix.\n\n" for i in range(6)),
        encoding="utf-8")
    m = autonomous_task_completion(Context(repo_root=tmp_path, memory_dir=tmp_path))
    assert m.value == 1.0


# --------------------------------------------------------------------------
# identity_continuity
# --------------------------------------------------------------------------


def test_identity_falls_when_the_persona_carries_two_identities(tmp_path):
    (tmp_path / "persona.md").write_text(
        "name: Oddfellow\n"
        "agent-aaaaaaaa-1111-2222-3333-444444444444\n"
        "agent-bbbbbbbb-1111-2222-3333-444444444444\n",
        encoding="utf-8")
    m = identity_continuity(Context(repo_root=tmp_path, memory_dir=tmp_path))
    assert m.value < 1.0


def test_identity_requires_the_non_sentience_rule(tmp_path):
    """The directive's hard boundary is part of the identity, so it is checked."""
    (tmp_path / "persona.md").write_text("name: Oddfellow\n", encoding="utf-8")
    m = identity_continuity(Context(repo_root=tmp_path, memory_dir=tmp_path))
    assert m.value < 1.0
    assert any("non-sentience" in e for e in m.evidence)


# --------------------------------------------------------------------------
# goal_continuity
#
# This dimension exists because of a specific failure: nineteen consecutive work
# cycles re-confirmed a known blocker and produced nothing, because there was
# nowhere a goal could be left OPEN. The tests below are all variations on one
# question -- can the number tell the difference between a goal that survives a
# restart and one that does not?
# --------------------------------------------------------------------------


def _write_register(repo, goals):
    d = repo / "oddfellow" / "cognition"
    d.mkdir(parents=True, exist_ok=True)
    p = d / "GOALS.json"
    p.write_text(json.dumps({"goals": goals}), encoding="utf-8")
    return p


def _goal(gid, status="open", next_action="do it"):
    return {"id": gid, "statement": f"statement for {gid}",
            "status": status, "next_action": next_action}


def _commit_repo(repo, *paths):
    """A throwaway repo with one commit, so survival can actually be tested."""
    def run(*args):
        subprocess.run(["git", *args], cwd=repo, capture_output=True,
                       text=True, timeout=30)
    run("init", "-q")
    run("add", *paths)
    run("-c", "user.email=t@localhost", "-c", "user.name=t",
        "commit", "-q", "-m", "t")


def test_goal_continuity_falls_when_a_goal_is_never_committed(tmp_path):
    """The failure the dimension was built for: real work that dies with the sandbox.

    One goal is committed and one is left in the working tree. A sandbox reset
    keeps the first and loses the second, so the number must show it.
    """
    _write_register(tmp_path, [_goal("shipped")])
    _commit_repo(tmp_path, "oddfellow/cognition/GOALS.json")
    _write_register(tmp_path, [_goal("shipped"), _goal("unshipped")])

    m = goal_continuity(Context(repo_root=tmp_path, memory_dir=None))
    assert m.value == 0.5
    assert any("unshipped" in e for e in m.evidence)


def test_goal_continuity_is_one_when_every_open_goal_is_committed(tmp_path):
    _write_register(tmp_path, [_goal("a"), _goal("b")])
    _commit_repo(tmp_path, "oddfellow/cognition/GOALS.json")

    m = goal_continuity(Context(repo_root=tmp_path, memory_dir=None))
    assert m.value == 1.0


def test_goal_continuity_falls_when_a_committed_goal_has_no_next_action(tmp_path):
    """A goal with a statement but no next action is a wish, not a resumable goal."""
    _write_register(tmp_path, [_goal("a", next_action="")])
    _commit_repo(tmp_path, "oddfellow/cognition/GOALS.json")

    m = goal_continuity(Context(repo_root=tmp_path, memory_dir=None))
    assert m.value == 0.0
    assert any("no next action" in e for e in m.evidence)


def test_goal_continuity_falls_on_a_duplicate_id(tmp_path):
    """Two goals sharing an id collapse into one on restart, so one is silently lost."""
    _write_register(tmp_path, [_goal("same"), _goal("same")])
    _commit_repo(tmp_path, "oddfellow/cognition/GOALS.json")

    m = goal_continuity(Context(repo_root=tmp_path, memory_dir=None))
    assert m.value == 0.0
    assert any("duplicate id" in e for e in m.evidence)


def test_goal_continuity_ignores_deferred_and_done_goals(tmp_path):
    """A deferred goal is not being carried by anyone; a done goal has nothing to survive for."""
    _write_register(tmp_path, [_goal("a"), _goal("d", status="deferred"),
                               _goal("e", status="done")])
    _commit_repo(tmp_path, "oddfellow/cognition/GOALS.json")

    m = goal_continuity(Context(repo_root=tmp_path, memory_dir=None))
    assert m.value == 1.0
    assert "1 goal(s) open or blocked" in m.evidence[0]


def test_goal_continuity_is_unmeasurable_without_a_register(tmp_path):
    """Not measurable, never 0.0 -- zero would read as a failure that did not happen."""
    m = goal_continuity(Context(repo_root=tmp_path, memory_dir=None))
    assert m.value is None
    assert "no goal register" in m.reason


def test_goal_continuity_is_unmeasurable_outside_a_git_repo(tmp_path):
    """'Could not run' is a different state from 'failed'.

    Survival cannot be tested without history. Reporting 0.0 here would invent a
    failure out of a missing tool, which is the mistake the first version of
    memory_accuracy made.
    """
    _write_register(tmp_path, [_goal("a")])
    m = goal_continuity(Context(repo_root=tmp_path, memory_dir=None))
    assert m.value is None
    assert "not a git work tree" in m.reason


# --------------------------------------------------------------------------
# metacognition, and the profile as a whole
# --------------------------------------------------------------------------


def test_metacognition_penalises_a_scored_dimension_with_no_falsifier():
    scored = Measurement(dimension="a", value=1.0, unit="u",
                         confidence=Confidence.REPRODUCED, can_fail="x",
                         falsifier_demonstrated=True)
    asserted = Measurement(dimension="b", value=1.0, unit="u",
                           confidence=Confidence.REPRODUCED, can_fail="x",
                           falsifier_demonstrated=False)
    m = metacognitive_performance(None, [scored, asserted])
    assert m.value == pytest.approx(0.5)


def test_metacognition_does_not_penalise_an_honest_gap():
    """An unmeasurable dimension cannot mislead, so it is not a metacognitive failure.

    Counting it would create a perverse incentive: report a number you cannot
    defend, or lose points for admitting you cannot.
    """
    gap = Measurement(dimension="gap", value=None, unit="u",
                      confidence=Confidence.SELF_REPORTED, can_fail="x",
                      reason="no evidence source")
    scored = Measurement(dimension="a", value=1.0, unit="u",
                         confidence=Confidence.REPRODUCED, can_fail="x",
                         falsifier_demonstrated=True)
    m = metacognitive_performance(None, [gap, scored])
    assert m.value == 1.0


def test_every_scored_dimension_proves_its_own_sensitivity(tmp_path):
    """The whole point: run the profile and require each number to be able to move.

    This is the test that fails if someone later hard-codes a dimension.
    """
    (tmp_path / "CURRENT_STATE.md").write_text(
        "# What\n# Why\n# Evidence\n# Open\n# Next\n", encoding="utf-8")
    measurements = build_profile(Context(repo_root=tmp_path, memory_dir=None))
    scored = [m for m in measurements if m.measurable]
    not_demonstrated = [m.dimension for m in scored if not m.falsifier_demonstrated]
    assert not_demonstrated == [], (
        f"these dimensions report a number but could not be shown to move: "
        f"{not_demonstrated}"
    )


def test_the_profile_reports_no_composite_score():
    """Collapsing the dimensions into one figure would invite the forbidden claim."""
    measurements = build_profile(Context(repo_root=None, memory_dir=None))
    s = summarise(measurements)
    assert "score" not in s
    assert "composite" not in s
    assert "not evidence of consciousness" in s["note"]


def test_the_rendered_profile_states_the_non_sentience_boundary():
    measurements = build_profile(Context(repo_root=None, memory_dir=None))
    text = render(measurements)
    assert "not evidence of consciousness" in text
    assert "no such claim is made" in text


def test_unmeasurable_dimensions_are_reported_not_zeroed():
    """Zero would read as failure and one as success. Both would be inventions."""
    measurements = build_profile(Context(repo_root=None, memory_dir=None))
    gaps = [m for m in measurements if not m.measurable]
    assert gaps, "the profile should be honest about what it cannot measure"
    for m in gaps:
        assert m.reason.strip(), f"{m.dimension} is a gap with no explanation"
