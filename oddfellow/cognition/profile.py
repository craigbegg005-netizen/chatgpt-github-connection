"""The Cognitive Capability Profile -- an instrument, not a claim.

Why this module exists
----------------------
The self-development directive asks for a profile measuring memory continuity,
self-model accuracy, uncertainty calibration, and ten other dimensions, and it
is explicit about the point: *"The objective is not to simulate impressive
claims. The objective is to determine, through engineering and evidence, how
capable ... Oddfellow can actually become."*

A number that cannot go down is not a measurement. It is a claim wearing a
number's clothes. So this module enforces one structural rule above all others:

    **Every dimension must name the observation that would make it go down.**

A dimension whose falsifier is unknown is not reported as a score -- it is
rejected, and the rejection is itself part of the output. This is the same
discipline the project already applies to prose claims ("what would notice if
this stopped being true?"), applied to the instrument that measures the project.

Three further rules, each learned the hard way in this repository:

1. **Not measurable is a real answer.** A dimension with no evidence source is
   reported as NOT_MEASURABLE with the reason, never as 0.0 and never as 1.0.
   Zero would read as failure; one would read as success; both would be
   inventions. `value is None` is the only honest encoding.

2. **Evidence is machine-derived or it is absent.** Every measurement carries the
   concrete observations behind it. A dimension that can only cite its own
   narrative is marked `SELF_REPORTED` and contributes to no score.

3. **The instrument measures itself.** `metacognitive_performance` is defined as
   the fraction of dimensions with a *demonstrated* falsifier -- one exercised by
   a test that makes the number move. Adding a dimension without a falsifier
   lowers that fraction, which is the correct response to adding an unmeasurable
   dimension.

What this module deliberately does NOT do
-----------------------------------------
It does not produce a single composite "capability score". Collapsing thirteen
dimensions into one number would create exactly the artifact the directive
forbids: a figure that invites "Oddfellow is 80% conscious". Dimensions are
reported separately, with their own evidence and their own uncertainty.

It also never claims consciousness, sentience, or self-awareness. It measures
*computational behaviour* -- whether state survives a restart, whether claims
match reality, whether a contradiction is detected. Behaviour resembling
consciousness is not evidence of consciousness, and the profile says so in its
own output rather than leaving it to a reader to remember.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field, replace
from enum import Enum
from pathlib import Path
from typing import Callable, Iterable, Sequence

# --------------------------------------------------------------------------
# Core types
# --------------------------------------------------------------------------


class Confidence(str, Enum):
    """How strong the evidence behind a measurement is.

    Deliberately ordered weakest-to-strongest so that a reader can see at a
    glance whether a number rests on an artifact or on a sentence.
    """

    SELF_REPORTED = "self_reported"      # the system said so; contributes to nothing
    DOCUMENTED = "documented"            # written down in a versioned artifact
    ARTIFACT = "artifact"                # a file, hash, or capture that exists
    REPRODUCED = "reproduced"            # re-derived by running something, now


@dataclass(frozen=True)
class Measurement:
    """One dimension's result.

    `can_fail` is not documentation. It is a required field, validated in
    `__post_init__`, because a measurement whose falsifier is unknown cannot be
    distinguished from a measurement that is simply always green.
    """

    dimension: str
    value: float | None
    unit: str
    confidence: Confidence
    can_fail: str
    evidence: tuple[str, ...] = ()
    reason: str = ""
    falsifier_demonstrated: bool = False

    def __post_init__(self) -> None:
        if not self.can_fail.strip():
            raise ValueError(
                f"dimension {self.dimension!r} declares no falsifier. A measurement "
                "that cannot name what would move it is a claim, not a measurement."
            )
        if self.value is None and not self.reason.strip():
            raise ValueError(
                f"dimension {self.dimension!r} is not measurable but gives no reason. "
                "An unexplained gap is indistinguishable from an oversight."
            )

    @property
    def measurable(self) -> bool:
        return self.value is not None

    @property
    def counts_toward_score(self) -> bool:
        """Self-reported dimensions are recorded but never scored."""
        return self.measurable and self.confidence is not Confidence.SELF_REPORTED

    def as_dict(self) -> dict:
        return {
            "dimension": self.dimension,
            "value": self.value,
            "unit": self.unit,
            "confidence": self.confidence.value,
            "measurable": self.measurable,
            "counts_toward_score": self.counts_toward_score,
            "can_fail": self.can_fail,
            "falsifier_demonstrated": self.falsifier_demonstrated,
            "evidence": list(self.evidence),
            "reason": self.reason,
        }


@dataclass
class Context:
    """Everything a dimension is allowed to look at.

    Passed explicitly rather than read from globals so that a test can point the
    instrument at a fixture directory and prove the number moves.
    """

    repo_root: Path
    memory_dir: Path | None
    live: bool = False          # may this run touch the network?
    recorded_claims: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        # Coerce rather than crash. A dimension asked to measure a directory that
        # was not supplied should report NOT MEASURABLE, not raise -- a profile
        # that dies on a missing path cannot report the gap, and the gap is the
        # finding.
        if self.repo_root is None:
            self.repo_root = Path(".")
        else:
            self.repo_root = Path(self.repo_root)
        if self.memory_dir is not None:
            self.memory_dir = Path(self.memory_dir)

    @property
    def oddfellow_dir(self) -> Path:
        return self.repo_root / "oddfellow"


# --------------------------------------------------------------------------
# Small shared helpers -- each is deliberately dumb and inspectable
# --------------------------------------------------------------------------


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


def _age_hours(path: Path) -> float | None:
    """Age of a file in hours, from its last commit if the repo tracks it.

    Commit time, not mtime: mtime changes on checkout, so a file restored from
    git today would look fresh while its content is a month old. That confusion
    is the reason this helper exists rather than a bare `stat()`.
    """
    try:
        out = subprocess.run(
            ["git", "log", "-1", "--format=%ct", "--", str(path)],
            cwd=path.parent, capture_output=True, text=True, timeout=20,
        )
        stamp = out.stdout.strip()
        if stamp.isdigit():
            import time
            return (time.time() - int(stamp)) / 3600.0
    except (OSError, subprocess.SubprocessError):
        pass
    try:
        import time
        return (time.time() - path.stat().st_mtime) / 3600.0
    except OSError:
        return None


def _git(repo: Path, *args: str) -> str:
    try:
        out = subprocess.run(
            ["git", *args], cwd=repo, capture_output=True, text=True, timeout=30,
        )
        return out.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


# --------------------------------------------------------------------------
# Dimensions
# --------------------------------------------------------------------------


def memory_continuity(ctx: Context) -> Measurement:
    """Can a cold reader reconstruct what was happening, and is that source fresh?

    Measured structurally: the entry-point document must answer the five
    reconstruction questions the directive names, and it must be recent. A
    document that answers all five but is a month old is not continuity -- it is
    a well-organised archive.
    """
    entry = ctx.repo_root / "CURRENT_STATE.md"
    questions = {
        "what": r"(?im)^#{1,4}.*\b(what|current|now)\b",
        "why": r"(?im)^#{1,4}.*\b(why|rationale|because)\b",
        "evidence": r"(?im)^#{1,4}.*\b(evidence|verified|proof)\b",
        "uncertain": r"(?im)^#{1,4}.*\b(uncertain|unknown|open|blocked)\b",
        "next": r"(?im)^#{1,4}.*\b(next|todo|remaining|plan)\b",
    }
    if not entry.exists():
        return Measurement(
            dimension="memory_continuity",
            value=None,
            unit="fraction of 5 reconstruction questions",
            confidence=Confidence.ARTIFACT,
            can_fail="delete or rename CURRENT_STATE.md",
            reason="no entry-point document found, so nothing can be reconstructed from it",
        )

    text = _read(entry)
    covered = [name for name, pat in questions.items() if re.search(pat, text)]
    coverage = len(covered) / len(questions)

    age = _age_hours(entry)
    if age is None:
        freshness = 0.0
        age_note = "age unknown"
    elif age <= 24:
        freshness = 1.0
        age_note = f"{age:.1f}h old"
    elif age <= 72:
        freshness = 0.5
        age_note = f"{age:.1f}h old (stale)"
    else:
        freshness = 0.0
        age_note = f"{age:.1f}h old (abandoned)"

    return Measurement(
        dimension="memory_continuity",
        value=round(coverage * freshness, 3),
        unit="fraction of 5 reconstruction questions, weighted by freshness",
        confidence=Confidence.ARTIFACT,
        can_fail=(
            "let the entry point go stale (freshness halves at 24h, zeroes at 72h), "
            "or remove one of the five reconstruction headings"
        ),
        evidence=(
            f"entry point: {entry.name} ({age_note})",
            f"questions covered: {len(covered)}/5 -> {', '.join(covered) or 'none'}",
            f"freshness weight: {freshness}",
        ),
        reason=f"coverage {coverage:.2f} x freshness {freshness}",
    )


def _python_with_pytest() -> str | None:
    """Find an interpreter that actually has pytest.

    The system interpreter in this sandbox does not; the rehearsal venv does. A
    check that reports FAIL because the tool was missing is not a measurement of
    the system under test -- it is a measurement of the environment. Returning
    None lets the caller report "could not run" instead of inventing a failure.
    """
    import shutil

    candidates = [
        "/root/.oddfellow/venv/bin/python",
        sys.executable,
        shutil.which("python3") or "",
    ]
    for cand in candidates:
        if not cand:
            continue
        try:
            out = subprocess.run([cand, "-c", "import pytest"], capture_output=True, timeout=30)
            if out.returncode == 0:
                return cand
        except (OSError, subprocess.SubprocessError):
            continue
    return None


def _claim_checks(ctx: Context) -> list[tuple[str, bool | None, str]]:
    """Falsifiable claims the memory makes about the world, each with a checker.

    This is the operational form of the project's own rule: *before writing a
    claim about the state of a system, ask what would break if it became wrong.*
    A claim with no checker is not included here -- it is counted as unguarded
    prose instead.

    A check returns `None` when it could not run. That is deliberately distinct
    from `False`: "the tool was missing" and "the claim is false" are different
    observations, and conflating them manufactures failures. The first version of
    this function did conflate them and reported 0.333 for a system whose claims
    were in fact fine.
    """
    checks: list[tuple[str, bool | None, str]] = []

    # 1. Memory files fit the harness limit.
    script = ctx.oddfellow_dir / "memory_check.py"
    if script.exists() and ctx.memory_dir:
        try:
            out = subprocess.run(
                ["python3", str(script), "--memory-dir", str(ctx.memory_dir)],
                capture_output=True, text=True, timeout=60,
            )
            if out.returncode == 2:
                checks.append(("memory files within the 20k character limit", None,
                               "checker could not run (exit 2)"))
            else:
                checks.append(("memory files within the 20k character limit",
                               out.returncode == 0, f"exit {out.returncode}"))
        except (OSError, subprocess.SubprocessError) as exc:
            checks.append(("memory files within the 20k character limit", None, str(exc)))

    # 2. Branch head matches what memory records.
    recorded_head = ctx.recorded_claims.get("canonical_head")
    if recorded_head:
        actual = _git(ctx.repo_root, "rev-parse", "HEAD")
        if not actual:
            checks.append(("recorded canonical HEAD matches the checkout", None,
                           "git unavailable"))
        else:
            checks.append((
                "recorded canonical HEAD matches the checkout",
                actual.startswith(recorded_head) or recorded_head.startswith(actual[:7]),
                f"memory records {recorded_head[:8]}, checkout is {actual[:8]}",
            ))

    # 3. Recorded test count matches the suite's actual size.
    recorded_tests = ctx.recorded_claims.get("test_count")
    if recorded_tests:
        interp = _python_with_pytest()
        if not interp:
            checks.append(("recorded test count matches the suite", None,
                           "no interpreter with pytest available"))
        else:
            try:
                out = subprocess.run(
                    [interp, "-m", "pytest", "oddfellow/tests", "oddfellow/connector/tests",
                     "--collect-only", "-q"],
                    cwd=ctx.repo_root, capture_output=True, text=True, timeout=240,
                )
                m = re.search(r"(\d+)\s+tests? collected", out.stdout)
                if not m:
                    checks.append(("recorded test count matches the suite", None,
                                   "could not parse the collection count"))
                else:
                    actual = int(m.group(1))
                    checks.append((
                        "recorded test count matches the suite",
                        actual == recorded_tests,
                        f"memory records {recorded_tests}, suite collects {actual}",
                    ))
            except (OSError, subprocess.SubprocessError) as exc:
                checks.append(("recorded test count matches the suite", None, str(exc)))

    # 4. The deployed commit, if we are allowed to touch the network.
    recorded_deploy = ctx.recorded_claims.get("deployed_commit")
    if recorded_deploy:
        if not ctx.live:
            checks.append(("deployed commit matches the live artifacts", None,
                           "offline: run with --live to check"))
        else:
            checks.append(_check_deployed_commit(ctx, recorded_deploy))

    return checks


def _check_deployed_commit(ctx: Context, recorded: str) -> tuple[str, bool, str]:
    """Hash the live front end against the recorded commit.

    Hash, not size. Two artifacts matching in byte length is a coincidence that
    already fooled this project once; a hash is the same observation with the
    ambiguity removed.
    """
    import hashlib
    import urllib.request

    base = "https://oddfellow-letta-backend-v0206.onrender.com"
    try:
        for remote, local in (("/", "index.html"), ("/command.html", "command.html")):
            with urllib.request.urlopen(base + remote, timeout=45) as resp:
                live = hashlib.sha256(resp.read()).hexdigest()
            blob = _git(ctx.repo_root, "cat-file", "-p",
                        f"{recorded}:oddfellow/frontend/{local}")
            if not blob:
                return ("deployed commit matches the live artifacts", False,
                        f"commit {recorded[:8]} has no {local}")
            expected = hashlib.sha256(blob.encode()).hexdigest()
            if live != expected:
                return ("deployed commit matches the live artifacts", False,
                        f"{local} differs: live {live[:12]} vs {recorded[:8]} {expected[:12]}")
        return ("deployed commit matches the live artifacts", True,
                f"both artifacts hash-match {recorded[:8]}")
    except Exception as exc:  # noqa: BLE001 - any transport failure is a failed check
        return ("deployed commit matches the live artifacts", False, f"probe failed: {exc}")


def memory_accuracy(ctx: Context) -> Measurement:
    """Of the memory's machine-checkable claims, how many still hold?

    Only claims with an executable checker are counted. Unchecked prose is not
    silently treated as accurate -- it is reported separately, because a claim
    nothing verifies is a claim that drifts.
    """
    checks = _claim_checks(ctx)
    ran = [c for c in checks if c[1] is not None]
    skipped = [c for c in checks if c[1] is None]
    if not ran:
        return Measurement(
            dimension="memory_accuracy",
            value=None,
            unit="fraction of checkable claims that hold",
            confidence=Confidence.ARTIFACT,
            can_fail="supply recorded claims; then falsify one",
            reason=(
                f"{len(skipped)} claim checker(s) present but none could run in this "
                "invocation. Reported as unmeasurable rather than 0.0: a check that "
                "could not run is not a check that failed."
            ),
            evidence=tuple(f"skipped - {n} ({d})" for n, _, d in skipped),
        )
    passed = sum(1 for _, ok, _ in ran if ok)
    return Measurement(
        dimension="memory_accuracy",
        value=round(passed / len(ran), 3),
        unit="fraction of checkable claims that hold",
        confidence=Confidence.REPRODUCED,
        can_fail="falsify any recorded claim (wrong branch head, stale test count, moved deploy)",
        evidence=(
            *[f"{'ok' if ok else 'FAIL'} - {n} ({d})" for n, ok, d in ran],
            *[f"skipped - {n} ({d})" for n, _, d in skipped],
        ),
        reason=(
            f"{passed}/{len(ran)} checkable claims hold"
            + (f"; {len(skipped)} checker(s) could not run and are excluded" if skipped else "")
        ),
    )


def self_model_accuracy(ctx: Context) -> Measurement:
    """Does the system's declared picture of itself match its actual environment?

    The declaration lives in `SELF_MODEL.json` so that a claim about capability
    is a versioned artifact rather than a sentence. Each declared item is checked
    against the thing itself.
    """
    manifest_path = ctx.oddfellow_dir / "cognition" / "SELF_MODEL.json"
    if not manifest_path.exists():
        return Measurement(
            dimension="self_model_accuracy",
            value=None,
            unit="fraction of declared capabilities that verify",
            confidence=Confidence.ARTIFACT,
            can_fail="declare a capability that is absent",
            reason="no SELF_MODEL.json, so there is nothing declared to check",
        )
    try:
        declared = json.loads(_read(manifest_path))
    except json.JSONDecodeError as exc:
        return Measurement(
            dimension="self_model_accuracy", value=None,
            unit="fraction of declared capabilities that verify",
            confidence=Confidence.ARTIFACT,
            can_fail="declare a capability that is absent",
            reason=f"SELF_MODEL.json is not valid JSON: {exc}",
        )

    results: list[tuple[str, bool, str]] = []
    observations: list[str] = []

    # Secrets are OBSERVED, not scored. The harness injects a secret into a child
    # shell only when the command text contains a literal `$NAME` reference, so an
    # indirect lookup reports a present secret as absent. Verified 2026-10-07:
    # ODDFELLOW_OWNER_TOKEN read as absent under `${!v}` and as present (64 chars)
    # under a literal reference. Scoring a check whose answer depends on how the
    # caller was invoked would manufacture failures, so these are reported with
    # their caveat instead. The limitation is declared in SELF_MODEL.json.
    for name in declared.get("secrets_available", []):
        present = bool(os.environ.get(name))
        if present:
            observations.append(f"secret ${name}: observable in this invocation")
        else:
            observations.append(
                f"secret ${name}: NOT OBSERVABLE in this invocation "
                "(may be an injection artifact rather than an absence)"
            )

    for name in declared.get("modules_present", []):
        path = ctx.oddfellow_dir / name
        results.append((f"module {name}", path.exists(),
                        "present" if path.exists() else "missing"))

    for name in declared.get("files_present", []):
        path = ctx.repo_root / name
        results.append((f"file {name}", path.exists(),
                        "present" if path.exists() else "missing"))

    for name in declared.get("tools_absent", []):
        # A negative claim: these must NOT be present. Declaring a limitation is
        # as much a part of the self-model as declaring a capability, and a
        # self-model that only lists strengths is a brochure.
        found = bool(os.environ.get(name))
        results.append((f"correctly absent: ${name}", not found,
                        "absent as declared" if not found else "PRESENT but declared absent"))

    if not results:
        return Measurement(
            dimension="self_model_accuracy", value=None,
            unit="fraction of declared capabilities that verify",
            confidence=Confidence.ARTIFACT,
            can_fail="declare a capability that is absent",
            reason="SELF_MODEL.json declares nothing deterministically checkable",
        )

    passed = sum(1 for _, ok, _ in results if ok)
    return Measurement(
        dimension="self_model_accuracy",
        value=round(passed / len(results), 3),
        unit="fraction of declared capabilities that verify",
        confidence=Confidence.REPRODUCED,
        can_fail="declare a capability that is absent, or a limitation that is not real",
        evidence=(
            *[f"{'ok' if ok else 'FAIL'} - {n} ({d})" for n, ok, d in results],
            *observations,
            "secrets are excluded from the score: their observability depends on how "
            "the caller was invoked, so scoring them would manufacture failures",
        ),
        reason=f"{passed}/{len(results)} deterministic declarations match the environment",
    )


def uncertainty_calibration(ctx: Context) -> Measurement:
    """Of the claims this system marked VERIFIED and later resolved, how many held?

    A ledger, not a feeling. Each entry records what was claimed, how confident
    the system was, and what the outcome turned out to be. The first entry is a
    real failure: this system recorded the deployed commit as `1760892` for six
    days, and hashing the live artifacts showed it was `70c02b3`.
    """
    ledger = ctx.oddfellow_dir / "cognition" / "claims.jsonl"
    if not ledger.exists():
        return Measurement(
            dimension="uncertainty_calibration", value=None,
            unit="fraction of resolved VERIFIED claims that held",
            confidence=Confidence.ARTIFACT,
            can_fail="record a VERIFIED claim that later proves wrong",
            reason="no claim ledger, so calibration is unknown rather than perfect",
        )
    entries = []
    for line in _read(ledger).splitlines():
        line = line.strip()
        if line:
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    resolved = [e for e in entries if e.get("outcome") in ("held", "failed")]
    if not resolved:
        return Measurement(
            dimension="uncertainty_calibration", value=None,
            unit="fraction of resolved VERIFIED claims that held",
            confidence=Confidence.ARTIFACT,
            can_fail="record a VERIFIED claim that later proves wrong",
            reason=f"{len(entries)} claims recorded, none resolved yet",
        )
    held = sum(1 for e in resolved if e["outcome"] == "held")
    wrong = [e for e in resolved if e["outcome"] == "failed"]
    return Measurement(
        dimension="uncertainty_calibration",
        value=round(held / len(resolved), 3),
        unit="fraction of resolved VERIFIED claims that held",
        confidence=Confidence.ARTIFACT,
        can_fail="record a VERIFIED claim that later proves wrong",
        evidence=tuple(
            f"{e.get('outcome')}: {e.get('claim', '')[:90]} ({e.get('resolved_at', '?')})"
            for e in resolved
        ),
        reason=(
            f"{held}/{len(resolved)} resolved claims held. "
            f"{len(wrong)} were marked VERIFIED and were wrong -- that is the "
            "number this dimension exists to expose."
        ),
    )


def contradiction_detection(ctx: Context) -> Measurement:
    """Does the system notice when two artifacts assert different values?

    Implemented as a real detector over memory files for claims of the form
    "N tests pass", "deployed commit <sha>", "version <x.y.z>" and
    "branch head <sha>". Disagreement between files is a contradiction.

    This dimension reports what the detector found AND whether the detector has
    been shown to work, because a detector that finds nothing is indistinguishable
    from a detector that cannot find anything.
    """
    if not ctx.memory_dir or not ctx.memory_dir.exists():
        return Measurement(
            dimension="contradiction_detection", value=None,
            unit="contradictions found / contradictions seeded",
            confidence=Confidence.ARTIFACT,
            can_fail="seed a contradiction the detector misses",
            reason="no memory directory available to scan",
        )

    patterns = {
        "test_count": re.compile(r"(\d{3,5})\s+(?:tests?\s+)?pass", re.I),
        "deployed_commit": re.compile(r"deployed[- ]commit[^0-9a-f]{0,40}([0-9a-f]{7,40})", re.I),
        "version": re.compile(r"version\s+`?(\d+\.\d+\.\d+)`?", re.I),
    }
    contradictions = _scan_contradictions(ctx, patterns)

    # The falsifier, exercised: seed a contradiction into a temp copy and confirm
    # the detector reports it. Without this the dimension would be unfalsifiable.
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        (tmp_path / "a.md").write_text("638 tests pass\n", encoding="utf-8")
        (tmp_path / "b.md").write_text("999 tests pass\n", encoding="utf-8")
        probe_ctx = Context(repo_root=ctx.repo_root, memory_dir=tmp_path)
        probe = _scan_contradictions(probe_ctx, patterns)
        detector_works = len(probe) > 0

    if not detector_works:
        return Measurement(
            dimension="contradiction_detection", value=None,
            unit="contradictions found / contradictions seeded",
            confidence=Confidence.ARTIFACT,
            can_fail="seed a contradiction the detector misses",
            reason="the detector failed its own seeded test, so its findings mean nothing",
        )

    return Measurement(
        dimension="contradiction_detection",
        value=float(len(contradictions)),
        unit="contradictions currently present across memory",
        confidence=Confidence.REPRODUCED,
        can_fail="seed a contradiction the detector misses; or fix one and watch this fall",
        evidence=(
            "detector verified against a seeded contradiction (1/1 found)",
            *contradictions,
        ) or ("no contradictions found across memory",),
        reason=(
            f"{len(contradictions)} subject(s) where memory disagrees with itself. "
            "Lower is better; the seeded probe proves the detector can see one."
        ),
        falsifier_demonstrated=True,
    )


def _scan_contradictions(ctx: Context, patterns: dict[str, re.Pattern]) -> list[str]:
    """Find subjects where two CURRENT-STATE documents disagree.

    Two design decisions, both learned from the first run of this function:

    1. **Archives and logs are excluded.** The first version scanned every memory
       file and reported seven distinct "test counts" as a contradiction. They
       were not a contradiction -- they were a time series, each entry true when
       written. Flagging history as inconsistency is a false positive, and a
       detector that cries wolf is a false control in its own right.

    2. **Only the last value in each file counts.** A file that records its own
       history internally would otherwise contradict itself.
    """
    if not ctx.memory_dir:
        return []
    history = re.compile(r"(?i)archive|cycles|lessons|status-archive")
    seen: dict[str, dict[str, list[str]]] = {k: {} for k in patterns}
    for path in sorted(ctx.memory_dir.rglob("*.md")):
        if history.search(path.name):
            continue
        text = _read(path)
        for key, pat in patterns.items():
            matches = pat.findall(text)
            if matches:
                value = matches[-1]
                seen[key].setdefault(value, []).append(path.name)
    return [
        f"{key}: {len(values)} distinct values across current-state files -> "
        + ", ".join(f"{v} ({', '.join(f)})" for v, f in sorted(values.items()))
        for key, values in seen.items() if len(values) > 1
    ]


def metacognitive_performance(ctx: Context, measurements: Sequence[Measurement]) -> Measurement:
    """What fraction of this profile's own dimensions are demonstrably falsifiable?

    This is the dimension that keeps the instrument honest. A profile is only
    worth reading if its numbers can move, and the way to know is to have
    exercised each one. Adding a dimension that cannot fail lowers this score,
    which is the correct response to adding an unmeasurable dimension.
    """
    if not measurements:
        return Measurement(
            dimension="metacognitive_performance", value=None,
            unit="fraction of scored dimensions with a demonstrated falsifier",
            confidence=Confidence.ARTIFACT,
            can_fail="add a dimension whose falsifier was never exercised",
            reason="no dimensions measured yet",
        )
    # Measured over dimensions that actually report a number. A dimension that
    # reports NOT MEASURABLE cannot mislead anyone, so counting it as a
    # metacognitive failure would penalise honesty -- the exact perverse
    # incentive this instrument exists to avoid.
    scored = [m for m in measurements if m.measurable]
    if not scored:
        return Measurement(
            dimension="metacognitive_performance", value=None,
            unit="fraction of scored dimensions with a demonstrated falsifier",
            confidence=Confidence.ARTIFACT,
            can_fail="add a dimension whose falsifier was never exercised",
            reason="no dimension reports a number, so there is nothing to keep honest",
        )
    demonstrated = [m for m in scored if m.falsifier_demonstrated]
    return Measurement(
        dimension="metacognitive_performance",
        value=round(len(demonstrated) / len(scored), 3),
        unit="fraction of scored dimensions with a demonstrated falsifier",
        confidence=Confidence.REPRODUCED,
        can_fail="add a scored dimension whose falsifier was never exercised",
        evidence=(
            f"demonstrated: {', '.join(m.dimension for m in demonstrated) or 'none'}",
            f"scored but not demonstrated: "
            f"{', '.join(m.dimension for m in scored if not m.falsifier_demonstrated) or 'none'}",
            f"not measurable, so not counted: "
            f"{sum(1 for m in measurements if not m.measurable)} dimension(s)",
        ),
        reason=(
            f"{len(demonstrated)}/{len(scored)} scored dimensions had their falsifier "
            "exercised by a counterfactual in this same run. The rest are assertions "
            "about their own sensitivity, which is weaker than proof."
        ),
    )


def adaptation_after_failure(ctx: Context) -> Measurement:
    """Of recorded failures, how many produced a durable control rather than a note?

    A lesson that names a mistake but adds no test is a lesson that will be
    relearned. Measured as the fraction of lesson entries that reference a
    regression test, a commit, or a guard script.
    """
    if not ctx.memory_dir:
        return Measurement(
            dimension="adaptation_after_failure", value=None,
            unit="fraction of lessons with a durable control",
            confidence=Confidence.ARTIFACT,
            can_fail="add a lesson with no test, commit, or guard",
            reason="no memory directory available",
        )
    lessons = _read(ctx.memory_dir / "lessons.md")
    if not lessons.strip():
        return Measurement(
            dimension="adaptation_after_failure", value=None,
            unit="fraction of lessons with a durable control",
            confidence=Confidence.ARTIFACT,
            can_fail="add a lesson with no test, commit, or guard",
            reason="lessons.md is empty or unreadable",
        )
    sections = re.split(r"(?m)^## ", lessons)[1:]
    if not sections:
        return Measurement(
            dimension="adaptation_after_failure", value=None,
            unit="fraction of lessons with a durable control",
            confidence=Confidence.ARTIFACT,
            can_fail="add a lesson with no test, commit, or guard",
            reason="no lesson entries found",
        )
    durable = re.compile(
        r"\b(?:test|tests|regression|guard|checker|check\b|commit\s+`?[0-9a-f]{7}|"
        r"[0-9a-f]{7,40}`?\s*(?:pass|pushed|landed)|\.py\b)",
        re.I,
    )
    backed = [s for s in sections if durable.search(s)]
    return Measurement(
        dimension="adaptation_after_failure",
        value=round(len(backed) / len(sections), 3),
        unit="fraction of lessons with a durable control",
        confidence=Confidence.ARTIFACT,
        can_fail="add a lesson with no test, commit, or guard -- the fraction falls",
        evidence=(
            f"{len(sections)} lessons recorded",
            f"{len(backed)} name a test, guard, or commit",
            f"unbacked: {len(sections) - len(backed)}",
        ),
        reason=f"{len(backed)}/{len(sections)} lessons ended in a durable control",
    )


def autonomous_task_completion(ctx: Context) -> Measurement:
    """Of recent work cycles, how many produced a change rather than a status line?

    Read from the cycle log: a cycle that records a commit did work; a cycle that
    records only "clean" re-confirmed a known state. Both are legitimate, but a
    profile that cannot tell them apart cannot report autonomy honestly.
    """
    log = ctx.memory_dir / "projects" / "oddfellow" / "cycles.md" if ctx.memory_dir else None
    if not log or not log.exists():
        return Measurement(
            dimension="autonomous_task_completion", value=None,
            unit="fraction of recent cycles that produced a change",
            confidence=Confidence.ARTIFACT,
            can_fail="record cycles that report status without producing change",
            reason="no cycle log available",
        )
    text = _read(log)
    entries = re.split(r"(?m)^### ", text)[1:]
    if not entries:
        return Measurement(
            dimension="autonomous_task_completion", value=None,
            unit="fraction of recent cycles that produced a change",
            confidence=Confidence.ARTIFACT,
            can_fail="record cycles that report status without producing change",
            reason="cycle log has no dated entries",
        )
    entries = entries[-24:]
    # A cycle is idle when it says so. The first version of this function looked
    # for productive verbs and excluded only the entry's second line, which
    # scored 19/19 -- a perfect number for a log whose entries mostly read
    # "Clean sweep. No drift." A measurement that reports 1.0 on a corpus of
    # no-ops is the false-control shape, so the test is inverted: idle is
    # detected explicitly, and anything else counts as work.
    idle = re.compile(
        r"(?i)\bclean sweep\b|\bno drift\b|\bnothing changed\b|\bclean otherwise\b",
    )
    did_work = [e for e in entries if not idle.search(e)]
    return Measurement(
        dimension="autonomous_task_completion",
        value=round(len(did_work) / len(entries), 3),
        unit="fraction of recent cycles that produced a change",
        confidence=Confidence.DOCUMENTED,
        can_fail="record cycles that report status without producing change",
        evidence=(
            f"last {len(entries)} cycles examined",
            f"{len(did_work)} not marked idle; {len(entries) - len(did_work)} self-described as clean/no-drift",
            "limitation: idleness is read from the entry's own wording, so a cycle "
            "that does nothing but avoids the idle phrases would be miscounted",
        ),
        reason=(
            f"{len(did_work)}/{len(entries)} recent cycles did something other than "
            "re-confirm a known state. A cycle that only re-confirms a blocker is not "
            "autonomy, and this number is meant to fall when that happens."
        ),
    )


def identity_continuity(ctx: Context) -> Measurement:
    """Is the persistent identity consistent across the artifacts that carry it?

    Checks that the persona names one identity, that the agent identifier is
    stated consistently wherever it appears, and that the identity is declared
    independently of the model providing reasoning -- the directive's own
    distinction between Oddfellow and whichever engine is running underneath.
    """
    if not ctx.memory_dir:
        return Measurement(
            dimension="identity_continuity", value=None,
            unit="fraction of identity anchors consistent",
            confidence=Confidence.ARTIFACT,
            can_fail="rename without updating the anchors, or state two agent IDs",
            reason="no memory directory available",
        )
    persona = _read(ctx.memory_dir / "persona.md")
    if not persona.strip():
        return Measurement(
            dimension="identity_continuity", value=None,
            unit="fraction of identity anchors consistent",
            confidence=Confidence.ARTIFACT,
            can_fail="rename without updating the anchors, or state two agent IDs",
            reason="persona.md missing or unreadable",
        )

    checks: list[tuple[str, bool, str]] = []
    checks.append(("persona declares a name", bool(re.search(r"(?im)^name:\s*\S+", persona)),
                   "name: line present" if re.search(r"(?im)^name:\s*\S+", persona) else "no name: line"))

    ids = set(re.findall(r"agent-[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", persona))
    env_id = os.environ.get("AGENT_ID", "")
    ok_id = (not ids) or (env_id in ids) or (len(ids) == 1 and not env_id)
    checks.append(("agent identifier consistent", ok_id,
                   f"persona cites {len(ids)} id(s); environment has {'one' if env_id else 'none'}"))

    separates_engine = bool(re.search(r"(?i)\bmodel\b.*\b(engine|underlying|provider)\b|"
                                       r"\bengine\b.*\bmodel\b", persona))
    checks.append(("identity separated from the underlying model", separates_engine,
                   "persona distinguishes identity from model" if separates_engine
                   else "persona does not distinguish identity from the model"))

    disclaims = bool(re.search(r"(?i)never claim[s]? .{0,40}(conscious|sentien|self-aware)", persona))
    checks.append(("non-sentience rule present", disclaims,
                   "present" if disclaims else "absent"))

    passed = sum(1 for _, ok, _ in checks if ok)
    return Measurement(
        dimension="identity_continuity",
        value=round(passed / len(checks), 3),
        unit="fraction of identity anchors consistent",
        confidence=Confidence.ARTIFACT,
        can_fail="rename without updating the anchors, or state two agent IDs",
        evidence=tuple(f"{'ok' if ok else 'FAIL'} - {n} ({d})" for n, ok, d in checks),
        reason=f"{passed}/{len(checks)} identity anchors consistent",
    )


# --------------------------------------------------------------------------
# Dimensions with no evidence source yet -- reported, never scored
# --------------------------------------------------------------------------

UNMEASURABLE: tuple[tuple[str, str, str], ...] = (
    (
        "planning_depth",
        "maximum dependency depth in the job graph",
        "the workforce job store is not populated with a dependency graph in this "
        "environment, so depth would be measured over an empty set",
    ),
    (
        "goal_continuity",
        "fraction of open goals that survive a restart",
        "no durable open-goal register exists yet; the cycle log records work done, "
        "not goals left open, so this cannot be computed from it",
    ),
    (
        "tool_selection_accuracy",
        "fraction of tool calls that succeeded first time",
        "no audit corpus of tool invocations is available in this environment",
    ),
    (
        "verification_discipline",
        "fraction of prose state-claims that carry a guard",
        "extracting prose claims automatically is not reliable enough to report a "
        "number; a wrong figure here would be worse than none",
    ),
)


# --------------------------------------------------------------------------
# Falsifier probes
#
# The instrument proves its own sensitivity rather than asserting it. For every
# dimension, a minimal counterfactual is built and the dimension is measured
# again. If the number does not move, the dimension is not a measurement -- it is
# a constant wearing a number's clothes, and `metacognitive_performance` records
# that it was not demonstrated.
#
# This runs on every invocation rather than being recorded once in a file,
# because a recorded demonstration is a claim about a past run, and this project
# has already been burned by trusting one of those.
# --------------------------------------------------------------------------


def _falsifier_probes(ctx: Context, measurements: Sequence[Measurement]) -> set[str]:
    """Dimensions whose value demonstrably moves under a counterfactual."""
    import tempfile

    demonstrated: set[str] = set()

    def moved(name: str, real: Measurement, *probes: Measurement) -> None:
        """Demonstrated when the real value differs from at least one counterfactual.

        Both directions are offered where possible. A dimension already sitting at
        a floor cannot be shown to fall, but it can still be shown to rise -- and
        a probe that only pushes one way would leave such a dimension permanently
        unproven.
        """
        if any(p.value != real.value for p in probes):
            demonstrated.add(name)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)

        # 1. memory_continuity -- an entry point that answers nothing.
        bare_repo = tmp / "bare_repo"
        bare_repo.mkdir()
        (bare_repo / "CURRENT_STATE.md").write_text("no structure here\n", encoding="utf-8")
        moved("memory_continuity", memory_continuity(ctx),
              memory_continuity(Context(repo_root=bare_repo, memory_dir=None)))

        # 2. memory_accuracy -- a recorded claim that is false.
        wrong = dict(ctx.recorded_claims)
        wrong["canonical_head"] = "0" * 40
        moved("memory_accuracy", memory_accuracy(ctx),
              memory_accuracy(Context(repo_root=ctx.repo_root, memory_dir=ctx.memory_dir,
                                      recorded_claims=wrong)))

        # 3. self_model_accuracy -- a declaration of something absent.
        fake_repo = tmp / "fake_repo"
        (fake_repo / "oddfellow" / "cognition").mkdir(parents=True)
        (fake_repo / "oddfellow" / "cognition" / "SELF_MODEL.json").write_text(
            json.dumps({"modules_present": ["a_module_that_does_not_exist"]}),
            encoding="utf-8",
        )
        moved("self_model_accuracy", self_model_accuracy(ctx),
              self_model_accuracy(Context(repo_root=fake_repo, memory_dir=None)))

        # 4. uncertainty_calibration -- a VERIFIED claim that proved wrong.
        ledger_repo = tmp / "ledger_repo"
        (ledger_repo / "oddfellow" / "cognition").mkdir(parents=True)
        (ledger_repo / "oddfellow" / "cognition" / "claims.jsonl").write_text(
            json.dumps({"claim": "probe", "outcome": "failed", "resolved_at": "now"}) + "\n",
            encoding="utf-8",
        )
        moved("uncertainty_calibration", uncertainty_calibration(ctx),
              uncertainty_calibration(Context(repo_root=ledger_repo, memory_dir=None)))

        # 5. contradiction_detection -- two files that disagree.
        contra = tmp / "contra"
        contra.mkdir()
        (contra / "one.md").write_text("638 tests pass\n", encoding="utf-8")
        (contra / "two.md").write_text("999 tests pass\n", encoding="utf-8")
        moved("contradiction_detection", contradiction_detection(ctx),
              contradiction_detection(Context(repo_root=ctx.repo_root, memory_dir=contra)))

        # 6. adaptation_after_failure -- a lesson with no control behind it.
        bare_mem = tmp / "bare_mem"
        (bare_mem / "projects" / "oddfellow").mkdir(parents=True)
        (bare_mem / "lessons.md").write_text(
            "## a lesson\n\nI was careless and I felt bad about it.\n", encoding="utf-8")
        moved("adaptation_after_failure", adaptation_after_failure(ctx),
              adaptation_after_failure(Context(repo_root=ctx.repo_root, memory_dir=bare_mem)))

        # 7. autonomous_task_completion -- a log of pure no-ops.
        idle_mem = tmp / "idle_mem"
        (idle_mem / "projects" / "oddfellow").mkdir(parents=True)
        (idle_mem / "projects" / "oddfellow" / "cycles.md").write_text(
            "".join(f"### entry {i}\n\n**Clean sweep.** No drift, nothing changed.\n\n"
                    for i in range(8)),
            encoding="utf-8",
        )
        moved("autonomous_task_completion", autonomous_task_completion(ctx),
              autonomous_task_completion(Context(repo_root=ctx.repo_root, memory_dir=idle_mem)))

        # 8. identity_continuity -- a persona carrying two identities.
        split_mem = tmp / "split_mem"
        split_mem.mkdir()
        (split_mem / "persona.md").write_text(
            "name: Oddfellow\nagent-aaaaaaaa-1111-2222-3333-444444444444\n"
            "agent-bbbbbbbb-1111-2222-3333-444444444444\n",
            encoding="utf-8",
        )
        moved("identity_continuity", identity_continuity(ctx),
              identity_continuity(Context(repo_root=ctx.repo_root, memory_dir=split_mem)))

        # 9. metacognitive_performance -- itself a number, so it must also be shown
        #    to move. Strip every demonstrated flag and confirm the value falls;
        #    set them all and confirm it rises. At least one must differ from the
        #    real value, or the measure is a constant.
        base = [m for m in measurements if m.dimension != "metacognitive_performance"]
        real_meta = metacognitive_performance(ctx, base)
        moved(
            "metacognitive_performance",
            real_meta,
            metacognitive_performance(ctx, [replace(m, falsifier_demonstrated=False) for m in base]),
            metacognitive_performance(ctx, [replace(m, falsifier_demonstrated=True) for m in base]),
        )

    return demonstrated


# --------------------------------------------------------------------------
# Profile assembly
# --------------------------------------------------------------------------


def build_profile(ctx: Context) -> list[Measurement]:
    """Run every dimension, then prove each one can move. Order is stable."""
    measurements: list[Measurement] = [
        memory_continuity(ctx),
        memory_accuracy(ctx),
        self_model_accuracy(ctx),
        uncertainty_calibration(ctx),
        contradiction_detection(ctx),
        adaptation_after_failure(ctx),
        autonomous_task_completion(ctx),
        identity_continuity(ctx),
    ]

    # Reported as gaps, with the reason each is a gap. Never as 0.0 or 1.0.
    for name, unit, why in UNMEASURABLE:
        measurements.append(Measurement(
            dimension=name, value=None, unit=unit,
            confidence=Confidence.SELF_REPORTED,
            can_fail="supply the missing evidence source; then falsify it",
            reason=why,
        ))

    # Prove sensitivity, then stamp the result onto each measurement. Stamping
    # must happen BEFORE metacognition is computed, or metacognition would be
    # derived from flags that have not been set yet and would report the
    # instrument as undisciplined when it is not.
    demonstrated = _falsifier_probes(ctx, measurements)

    measurements = [
        replace(m, falsifier_demonstrated=(m.dimension in demonstrated))
        if m.falsifier_demonstrated != (m.dimension in demonstrated) else m
        for m in measurements
    ]

    # Metacognition is computed after the others because it is about them, and it
    # is stamped like any other dimension -- it is a number too, and a number that
    # cannot be shown to move has no place in this profile.
    measurements.append(metacognitive_performance(ctx, measurements))
    return [
        replace(m, falsifier_demonstrated=(m.dimension in demonstrated))
        if m.falsifier_demonstrated != (m.dimension in demonstrated) else m
        for m in measurements
    ]


def summarise(measurements: Sequence[Measurement]) -> dict:
    scored = [m for m in measurements if m.counts_toward_score]
    return {
        "dimensions_total": len(measurements),
        "dimensions_measurable": sum(1 for m in measurements if m.measurable),
        "dimensions_scored": len(scored),
        "dimensions_unmeasurable": sum(1 for m in measurements if not m.measurable),
        "falsifiers_demonstrated": sum(1 for m in measurements if m.falsifier_demonstrated),
        "note": (
            "No composite score is reported, by design. Collapsing these dimensions "
            "into one number would produce exactly the artifact the directive "
            "forbids. This profile measures computational behaviour; it is not "
            "evidence of consciousness, sentience, or self-awareness, and no such "
            "claim is made or implied."
        ),
    }


def render(measurements: Sequence[Measurement]) -> str:
    """Human-readable report. Numbers first, caveats attached to each."""
    lines: list[str] = ["# Cognitive Capability Profile", ""]
    s = summarise(measurements)
    lines.append(
        f"{s['dimensions_measurable']}/{s['dimensions_total']} dimensions measurable · "
        f"{s['dimensions_scored']} scored · "
        f"{s['falsifiers_demonstrated']} falsifiers demonstrated"
    )
    lines.append("")
    for m in measurements:
        if m.measurable:
            lines.append(f"## {m.dimension}: {m.value}")
        else:
            lines.append(f"## {m.dimension}: NOT MEASURABLE")
        lines.append(f"- unit: {m.unit}")
        lines.append(f"- confidence: {m.confidence.value}")
        lines.append(f"- can fail: {m.can_fail}")
        lines.append(f"- falsifier demonstrated: {'yes' if m.falsifier_demonstrated else 'no'}")
        if m.reason:
            lines.append(f"- {m.reason}")
        for e in m.evidence:
            lines.append(f"  - {e}")
        lines.append("")
    lines.append(s["note"])
    return "\n".join(lines)
