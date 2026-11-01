"""
The sandbox IPv4 fix must actually take effect, and must be shown to be necessary.

Why this file exists
--------------------
The IPv6 failure in this sandbox was written off as flakiness three separate
times (2026-10-09), because it clears on retry: the resolver returns the AAAA
record first on some lookups and the A record on others, so a passing retry
never disproved the fault. When it was finally diagnosed, the first fix
(`gai.conf` ordering) turned out to be insufficient -- Python still attempted
IPv6 and raised instead of falling back, which showed up as *the failing gate
moving* between runs rather than the failure disappearing.

The fix then lived only in sandbox state and was re-derived by hand after every
sandbox reset. It is now a repo script with a single source of truth for the
module. This file holds both properties in place:

  1. The `.pth` mechanism actually loads, in a real interpreter, and resolution
     becomes IPv4-only. Not asserted by grepping the script -- that is a proxy.
  2. The guard is *necessary*: the same interpreter, before the fix, returns
     AF_INET6. Without this control a green result could just mean the
     environment never had an AAAA record to begin with.

`test_verify_mode_fails_without_the_patch` is the falsifier for the script's own
`verify` mode: if `verify` passed on an unpatched interpreter it would be a check
whose condition cannot vary, which is worse than no check because it manufactures
confidence.
"""

from __future__ import annotations

import os
import subprocess
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
ODDFELLOW = os.path.join(REPO, "oddfellow")
SCRIPT = os.path.join(ODDFELLOW, "sandbox_ipv4_fix.sh")
MODULE_SRC = os.path.join(ODDFELLOW, "sandbox", "force_ipv4.py")

# Numeric literals, not hostnames. A literal is parsed rather than resolved, so
# these probes need no DNS and cannot fail for a network reason. The previous
# probe resolved trycloudflare.com, which made the tests below depend on live
# DNS -- the same defect that made the script's `verify` mode intermittent.
#
# Returns (control, ipv6_literal):
#   control      -- families for 127.0.0.1; must always contain AF_INET (2)
#   ipv6_literal -- families for ::1; [10] unpatched, [] patched (the patch
#                   removes the only answer and raises gaierror)
#
# int(r[0]) matters: AddressFamily is an IntEnum, and its repr is not
# eval-able, so printing the raw set produced a SyntaxError in the test rather
# than a result.
FAMILIES_PROBE = (
    "import socket\n"
    "ctrl = sorted({int(r[0]) for r in socket.getaddrinfo('127.0.0.1', 443)})\n"
    "try:\n"
    "    v6 = sorted({int(r[0]) for r in socket.getaddrinfo('::1', 443)})\n"
    "except socket.gaierror:\n"
    "    v6 = []\n"
    "print(repr((ctrl, v6)))\n"
)


def _families(python: str) -> tuple[list[int], list[int]]:
    out = subprocess.run(
        [python, "-c", FAMILIES_PROBE],
        capture_output=True,
        text=True,
        timeout=60,
        check=True,
    )
    return eval(out.stdout.strip())  # noqa: S307 - our own literal output


@pytest.fixture()
def fresh_venv(tmp_path):
    """A real venv, so the .pth is processed by `site` exactly as in production.

    A directory merely placed on PYTHONPATH would not do: `site` only processes
    `.pth` files in site directories, so a PYTHONPATH-based test would pass or
    fail for reasons unrelated to the mechanism under test.
    """
    venv = tmp_path / "venv"
    subprocess.run(
        [sys.executable, "-m", "venv", "--without-pip", str(venv)],
        check=True,
        capture_output=True,
        timeout=180,
    )
    return str(venv / "bin" / "python")


def test_fix_makes_resolution_ipv4_only(fresh_venv, tmp_path):
    """After `apply --for-python`, that interpreter resolves IPv4 only."""
    gai = tmp_path / "gai.conf"
    gai.write_text("# empty\n")

    subprocess.run(
        ["bash", SCRIPT, "apply", "--for-python", fresh_venv],
        check=True,
        capture_output=True,
        text=True,
        timeout=120,
        env={**os.environ, "GAI_CONF": str(gai)},
    )

    control, v6 = _families(fresh_venv)
    assert control == [2], f"control probe is broken: {control}"
    assert 10 not in v6, f"AF_INET6 still resolved for the IPv6 literal: {v6}"
    assert v6 == [], f"expected no answer for '::1' once patched, got {v6}"


def test_the_guard_is_necessary(fresh_venv):
    """Negative control: the same interpreter, unfixed, DOES return AF_INET6.

    If this ever stops holding, `test_fix_makes_resolution_ipv4_only` proves
    nothing -- it would be green in an environment where the fault cannot occur.

    This no longer skips. It used to skip whenever DNS returned no AAAA record
    for the probe hostname, which meant the control could quietly stop
    controlling and still look green. A numeric literal always has an IPv6
    answer to find, so the control is unconditional now.
    """
    control, v6 = _families(fresh_venv)
    assert control == [2], f"control probe is broken: {control}"
    assert 10 in v6, (
        "the unfixed interpreter did not return AF_INET6 for '::1', so "
        "test_fix_makes_resolution_ipv4_only proves nothing"
    )


def test_installed_module_is_the_repo_module(fresh_venv, tmp_path):
    """The installed copy is a copy of the single source of truth, not a twin.

    Two hand-maintained copies of a rule drift -- that is the mechanism of
    divergence, not a coincidence.
    """
    gai = tmp_path / "gai.conf"
    gai.write_text("# empty\n")
    subprocess.run(
        ["bash", SCRIPT, "apply", "--for-python", fresh_venv],
        check=True,
        capture_output=True,
        timeout=120,
        env={**os.environ, "GAI_CONF": str(gai)},
    )
    site_dir = subprocess.run(
        [fresh_venv, "-c", "import site;print(site.getsitepackages()[0])"],
        capture_output=True,
        text=True,
        check=True,
        timeout=60,
    ).stdout.strip()
    installed = open(os.path.join(site_dir, "force_ipv4.py"), "rb").read()
    source = open(MODULE_SRC, "rb").read()
    assert installed == source


def test_verify_mode_fails_without_the_patch(tmp_path):
    """The falsifier for `verify`: on an unpatched interpreter it must FAIL.

    `python3 -S` disables `site`, so no `.pth` is processed. If `verify` still
    reported OK here, it would be a check that cannot fail.
    """
    wrapper = tmp_path / "unpatched-python"
    wrapper.write_text(f'#!/bin/sh\nexec {sys.executable} -S "$@"\n')
    wrapper.chmod(0o755)

    result = subprocess.run(
        ["bash", SCRIPT, "verify", str(wrapper)],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode != 0, (
        "verify passed on an interpreter with site disabled -- it is not "
        f"checking anything. stdout={result.stdout!r}"
    )


def test_verify_mode_passes_with_the_system_patch(fresh_venv, tmp_path):
    """Verify a deliberately patched disposable interpreter, not host state."""
    subprocess.run(
        ["bash", SCRIPT, "apply", "--for-python", fresh_venv],
        check=True, capture_output=True, text=True, timeout=120,
        env={**os.environ, "GAI_CONF": str(tmp_path / "gai.conf")},
    )
    result = subprocess.run(
        ["bash", SCRIPT, "verify", fresh_venv],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_apply_is_idempotent_for_gai_conf(tmp_path, fresh_venv):
    """Running `apply` twice must not append the precedence rule twice."""
    gai = tmp_path / "gai.conf"
    gai.write_text("# empty\n")
    env = {**os.environ, "GAI_CONF": str(gai)}
    for _ in range(2):
        subprocess.run(
            ["bash", SCRIPT, "apply", "--for-python", fresh_venv],
            check=True,
            capture_output=True,
            timeout=120,
            env=env,
        )
    text = gai.read_text()
    active = [
        line
        for line in text.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    assert active == ["precedence ::ffff:0:0/96  100"], active


def test_module_never_falls_back_to_ipv6(monkeypatch):
    """The module raises rather than returning an IPv6-only answer.

    The first version of this fix was `return v4 or res`, which silently
    reintroduced the attempt the patch exists to prevent.
    """
    sys.path.insert(0, os.path.join(ODDFELLOW, "sandbox"))
    try:
        import force_ipv4  # noqa: PLC0415
    finally:
        sys.path.pop(0)

    ipv6_only = [(10, 1, 6, "", ("2606:4700::1", 443, 0, 0))]
    monkeypatch.setattr(
        force_ipv4, "_original_getaddrinfo", lambda *a, **k: ipv6_only
    )
    with pytest.raises(OSError):
        force_ipv4._ipv4_only_getaddrinfo("example.invalid", 443)
