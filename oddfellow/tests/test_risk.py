"""Tests for the server-side risk classifier, including a real drift check.

The classifier exists in two places: ``risk.py`` (the authority, used by the
server to decide whether to demand an approval) and a copy inside
``frontend/index.html`` (a UX hint, so the plan chip and the pre-created
approval do not need a round trip).

Two copies of a rule is a drift risk, so the second half of this file does not
trust them to stay in sync: it extracts the regular expressions out of the HTML
and runs the same corpus through both. If someone edits one and not the other,
this fails.
"""

import os
import re
import sys

import pytest
import unittest

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, APP_DIR)

from risk import classify, is_elevated  # noqa: E402
from command_center import CommandCenter  # noqa: E402

FRONTEND = os.path.join(APP_DIR, "frontend", "index.html")


# --------------------------------------------------------------------------- #
# The classifier itself
# --------------------------------------------------------------------------- #

ELEVATED_CASES = [
    "delete the old branch",
    "publish this to the store",
    "send an email to the client",
    "send money to the supplier",
    "spend $50 on ads",
    "buy the domain",
    "purchase the pro plan",
    "pay the invoice",
    "transfer the balance",
    "deploy to production now",
    "production deploy",
    "change my password",
    "rotate the credential",
    "update the api key",
    "make a payment",
    "erase the audit log",
    "remove the rollback version",
    "post to instagram",
]

NORMAL_CASES = [
    # Questions are not commands -- the bug this rule was written for.
    "what is the zero-spend rule?",
    "how does the spend guard work?",
    "explain the payment flow",
    "why did the deploy to production fail?",
    "tell me about the api key rotation policy",
    "describe the publish pipeline",
    "show me the payment records",
    "is the credential stored safely?",
    "should I buy the domain?",
    # Plain work.
    "write a summary of the connector",
    "run the test suite",
    "what is the current branch?",
    "summarise the security review",
    "",
    "   ",
]


@pytest.mark.parametrize("text", ELEVATED_CASES)
def test_elevated_commands_are_elevated(text):
    assert is_elevated(text), f"{text!r} should be elevated"
    assert classify(text) == "elevated"


@pytest.mark.parametrize("text", NORMAL_CASES)
def test_questions_and_plain_work_are_not_elevated(text):
    assert not is_elevated(text), f"{text!r} should not be elevated"
    assert classify(text) == "normal"


def test_non_string_input_is_not_elevated():
    """There is nothing to authorise in a non-string, so it cannot be elevated."""
    assert is_elevated(None) is False
    assert is_elevated(123) is False
    assert is_elevated(["delete everything"]) is False


def test_classification_is_case_insensitive():
    assert is_elevated("DELETE THE BRANCH")
    assert is_elevated("Delete The Branch")


def test_a_question_mark_anywhere_at_the_end_excuses_it():
    assert not is_elevated("you should delete the branch?")
    # ...but only at the end. A trailing clause does not excuse a command.
    assert is_elevated("delete the branch, ok")


# --------------------------------------------------------------------------- #
# The drift check
# --------------------------------------------------------------------------- #

def _js_regex_literals(line: str) -> list[str]:
    """Pull `/.../` literals out of one line of JavaScript."""
    return re.findall(r"/((?:[^/\\]|\\.)+)/", line)


def _client_classifier():
    """Rebuild the front end's classifier from the HTML, as Python.

    This is deliberately a re-implementation from the *source text* rather than
    a shared import: the point is to test what is actually shipped to the
    browser, not what a refactor would prefer it to be.
    """
    html = open(FRONTEND, encoding="utf-8").read()
    asking_line = re.search(r"^\s*const asking=.*$", html, re.M)
    risky_line = re.search(r"^\s*const risky=.*$", html, re.M)
    assert asking_line, "could not find the client's `asking` rule in index.html"
    assert risky_line, "could not find the client's `risky` rule in index.html"

    asking = [re.compile(p) for p in _js_regex_literals(asking_line.group(0))]
    risky = [re.compile(p) for p in _js_regex_literals(risky_line.group(0))]
    assert asking, "no regex literals found in the client's `asking` rule"
    assert risky, "no regex literals found in the client's `risky` rule"

    def client_is_elevated(text: str) -> bool:
        lowered = text.lower()
        if any(r.search(lowered) for r in asking):
            return False
        return any(r.search(lowered) for r in risky)

    return client_is_elevated


@pytest.mark.parametrize("text", ELEVATED_CASES + NORMAL_CASES)
def test_client_and_server_classifiers_agree(text):
    """The browser copy is a hint, but a hint that disagrees is a bug.

    The server is the authority and the front end recovers from a disagreement,
    so drift is not a security hole -- it is a wasted round trip and a confusing
    UI. This catches it at the source instead.
    """
    assert _client_classifier()(text) == is_elevated(text), (
        f"client and server disagree about {text!r}: "
        f"client={_client_classifier()(text)} server={is_elevated(text)}"
    )


def test_the_drift_check_can_actually_fail():
    """A check whose condition cannot vary is worse than no check.

    Prove the extraction is reading real patterns by feeding it a string the
    client's rules match and the server's do not -- if the extraction silently
    returned nothing, every comparison above would trivially pass.
    """
    client = _client_classifier()
    # "publish" is in both rule sets; assert the client rule is live.
    assert client("publish the release") is True
    assert client("what is the publish policy?") is False


# --------------------------------------------------------------------------- #
# The Worker's copy of the rule
# --------------------------------------------------------------------------- #
#
# `cloudflare/worker.js` carries a third copy, because it is a separate runtime
# that cannot import Python. It is a *fail-closed* copy: the Worker has no
# approval store (its state is per-isolate), so it refuses elevated commands
# outright rather than allowing what the backend would have gated. That makes
# agreement between the three copies load-bearing in a new way -- if the Worker's
# rule were narrower than the server's, a command the server would gate would
# sail through the Worker ungated.

WORKER = os.path.join(APP_DIR, "cloudflare", "worker.js")


def _worker_classifier():
    """Run the Worker's own `isElevatedRisk` in node, extracted from its source."""
    import json
    import shutil
    import subprocess

    if not os.path.exists(WORKER):
        pytest.skip("cloudflare/worker.js not present in this checkout")
    node = shutil.which("node")
    if not node:
        pytest.skip("node is not available to run the Worker's classifier")

    src = open(WORKER, encoding="utf-8").read()
    match = re.search(
        r"const RISK_ASKING[\s\S]*?function isElevatedRisk[\s\S]*?\n\}", src
    )
    assert match, "could not find the Worker's risk classifier in worker.js"

    script = (
        match.group(0)
        + "\nconst fn = new Function(" + json.dumps(match.group(0)) + " + '\\nreturn isElevatedRisk;');"
        + "\nconst classify = fn();"
        + "\nconst cases = JSON.parse(process.argv[1]);"
        + "\nconsole.log(JSON.stringify(cases.map(c => classify(c))));"
    )
    proc = subprocess.run(
        [node, "-e", script, json.dumps(ELEVATED_CASES + NORMAL_CASES)],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert proc.returncode == 0, f"node failed: {proc.stderr}"
    return json.loads(proc.stdout)


def test_the_worker_and_the_server_agree_on_every_case():
    results = _worker_classifier()
    cases = ELEVATED_CASES + NORMAL_CASES
    disagreements = [
        (text, got, is_elevated(text))
        for text, got in zip(cases, results)
        if got != is_elevated(text)
    ]
    assert not disagreements, (
        "worker.js and risk.py disagree (text, worker, server): "
        + repr(disagreements)
    )


def test_the_worker_classifier_extraction_is_live():
    """Prove the node extraction reads real rules, not an empty function."""
    results = _worker_classifier()
    cases = ELEVATED_CASES + NORMAL_CASES
    assert any(results), "the Worker's classifier returned False for everything"
    assert not all(results), "the Worker's classifier returned True for everything"
    assert len(results) == len(cases)


class ApprovalSingleUseTests(unittest.TestCase):
    """An APPROVED, bound approval must authorise exactly one execution.

    Found 2026-10-02 as the fourth false control: the audit line said
    "approval_consumed" but nothing was consumed, so one owner decision
    could authorise the same command any number of times.
    """

    def test_approved_approval_is_consumed_on_use(self):
        center = CommandCenter()
        rec = center.add_approval("Deploy", "d", "high", binding_text="deploy now")
        center.decide(rec["id"], "approve")
        retired = center.consume_approval(rec["id"])
        self.assertEqual(retired["state"], "CONSUMED")
        self.assertIn("consumed_at", retired)

    def test_consumed_approval_cannot_be_reused(self):
        center = CommandCenter()
        rec = center.add_approval("Deploy", "d", "high", binding_text="deploy now")
        center.decide(rec["id"], "approve")
        center.consume_approval(rec["id"])
        after = center.get_approval(rec["id"])
        self.assertEqual(after["state"], "CONSUMED")
        # The enforcement path refuses anything not APPROVED, so a second
        # use of the same approval must fail closed.
        with self.assertRaises(ValueError):
            center.consume_approval(rec["id"])

    def test_unapproved_or_unknown_cannot_be_consumed(self):
        center = CommandCenter()
        waiting = center.add_approval("Deploy", "d", "high", binding_text="deploy now")
        with self.assertRaises(ValueError):
            center.consume_approval(waiting["id"])  # still WAITING_AUTHORIZATION
        with self.assertRaises(KeyError):
            center.consume_approval("apr-doesnotexist")
