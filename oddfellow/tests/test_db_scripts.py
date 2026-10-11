"""
The DB-preservation scripts must not put the database credential on a command
line.

Why this file exists
--------------------
Both `db_preserve.sh` and `backup_render_db.sh` carried a header saying the
connection string "is never passed on a command line" -- and both passed it as
an argument (`--dbname="$url"`, `"$psql_bin" "$url"`). A process argument list is
readable by every user on the box, so the database password was visible in
`ps -eo args`. Verified 2026-10-11 with a harmless stand-in: a URL passed as an
argument appears in full, password included.

A security claim the code does not enforce is worse than no claim, because it
stops the next reader from checking. So the claim is now enforced and this file
holds it in place.

How it is tested
----------------
Not by grepping the script for a suspicious-looking line -- that is a proxy, and
a proxy catches the defect you had in mind and nothing else. Instead the shipped
script is *run*, with `ODDFELLOW_PG_BIN_DIR` pointed at stub binaries that record
their own argv and environment. The assertion is on what the real script actually
handed to a real process.

`test_the_recorder_would_see_a_leak` is the negative control: it invokes the same
recorder the way the old code did and asserts the credential *does* show up. Without
it, a green result could just mean the recorder never records anything.
"""

from __future__ import annotations

import os
import subprocess

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
ODDFELLOW = os.path.join(REPO, "oddfellow")
ENGINE = os.path.join(ODDFELLOW, "db_preserve.sh")
WRAPPER = os.path.join(ODDFELLOW, "backup_render_db.sh")
HELPER = os.path.join(ODDFELLOW, "db_url_to_pgpass.py")

FAKE_PASSWORD = "FAKEPASSWORD_NOTAREALSECRET"
FAKE_HOST = "db.example.invalid"
FAKE_URL = (
    f"postgres://oddfellow:{FAKE_PASSWORD}@{FAKE_HOST}:5432/bsi_core?sslmode=require"
)

_TOC = (
    "1; 1259 16385 TABLE public conversations oddfellow\n"
    "2; 1259 16386 TABLE public messages oddfellow\n"
    "3; 0 0 ENCODING - ENCODING\n"
)


def _stub(tool: str, extra: str = "") -> str:
    """A recording stand-in for a pg client. Never touches a network."""
    return f"""#!/usr/bin/env bash
for a in "$@"; do
  if [ "$a" = "--version" ]; then
    printf '%s (PostgreSQL) 18.0\\n' "{tool}"
    exit 0
  fi
done
printf 'argv: %s\\n' "$*" >> "$STUB_LOG"
printf 'PGHOST=%s\\n' "${{PGHOST:-}}" >> "$STUB_LOG"
printf 'PGPORT=%s\\n' "${{PGPORT:-}}" >> "$STUB_LOG"
printf 'PGUSER=%s\\n' "${{PGUSER:-}}" >> "$STUB_LOG"
printf 'PGDATABASE=%s\\n' "${{PGDATABASE:-}}" >> "$STUB_LOG"
printf 'PGSSLMODE=%s\\n' "${{PGSSLMODE:-}}" >> "$STUB_LOG"
printf 'PGPASSFILE=%s\\n' "${{PGPASSFILE:-}}" >> "$STUB_LOG"
if [ -n "${{PGPASSFILE:-}}" ] && [ -f "$PGPASSFILE" ]; then
  printf 'pgpass-mode=%s\\n' "$(stat -c '%a' "$PGPASSFILE")" >> "$STUB_LOG"
  printf 'pgpass-content=%s\\n' "$(cat "$PGPASSFILE")" >> "$STUB_LOG"
fi
{extra}
exit 0
"""


def _bindir(tmp_path):
    """Stub pg clients plus a stub curl, so nothing in the test hits the network."""
    bindir = tmp_path / "bin"
    bindir.mkdir(exist_ok=True)
    scripts = {
        "pg_dump": _stub(
            "pg_dump",
            'for a in "$@"; do case "$a" in --file=*) '
            'printf \'PGDMP-stub-payload\' > "${a#--file=}" ;; esac; done',
        ),
        "pg_restore": _stub("pg_restore", f"printf '%s' \"{_TOC}\""),
        "psql": _stub("psql"),
        "curl": "#!/usr/bin/env bash\nprintf '203.0.113.7'\n",
    }
    for name, body in scripts.items():
        p = bindir / name
        p.write_text(body)
        p.chmod(0o755)
    return bindir


def _run(tmp_path, script, argv, env_extra=None):
    bindir = _bindir(tmp_path)
    log = tmp_path / "stub.log"
    env = os.environ.copy()
    env.pop("PGPASSWORD", None)
    env.pop("PGPASSFILE", None)
    env.update(
        {
            "PATH": f"{bindir}:{env['PATH']}",
            "ODDFELLOW_PG_BIN_DIR": str(bindir),
            "ODDFELLOW_DB_OUT_DIR": str(tmp_path / "out"),
            "STUB_LOG": str(log),
        }
    )
    env.update(env_extra or {})
    proc = subprocess.run(
        ["bash", script, *argv], env=env, capture_output=True, text=True, timeout=120
    )
    return proc, (log.read_text() if log.exists() else "")


def _argv_lines(log_text: str) -> list[str]:
    return [line for line in log_text.splitlines() if line.startswith("argv:")]


@pytest.mark.skipif(not os.path.isfile(ENGINE), reason="engine not in this checkout")
def test_engine_dump_keeps_the_credential_out_of_argv(tmp_path):
    proc, log = _run(tmp_path, ENGINE, ["dump"], {"ODDFELLOW_DB_URL": FAKE_URL})

    assert proc.returncode == 0, f"dump failed:\n{proc.stdout}\n{proc.stderr}"
    assert _argv_lines(log), "the stubs recorded no argv, so this test proves nothing"

    for line in _argv_lines(log):
        assert FAKE_PASSWORD not in line, f"credential in argv: {line!r}"
        assert "postgres://" not in line, f"connection string in argv: {line!r}"


@pytest.mark.skipif(not os.path.isfile(ENGINE), reason="engine not in this checkout")
def test_engine_still_connects_from_the_url(tmp_path):
    """Moving the credential must not mean losing it.

    The password has to arrive somewhere libpq reads, and the non-secret parts
    have to survive the split -- including sslmode, which Render requires.
    """
    proc, log = _run(tmp_path, ENGINE, ["dump"], {"ODDFELLOW_DB_URL": FAKE_URL})
    assert proc.returncode == 0, f"dump failed:\n{proc.stdout}\n{proc.stderr}"

    assert f"PGHOST={FAKE_HOST}" in log
    assert "PGPORT=5432" in log
    assert "PGUSER=oddfellow" in log
    assert "PGDATABASE=bsi_core" in log
    assert "PGSSLMODE=require" in log, "sslmode was dropped in the split"

    assert "pgpass-mode=600" in log, "the password file must be mode 600"
    assert f"pgpass-content={FAKE_HOST}:5432:*:oddfellow:{FAKE_PASSWORD}" in log, (
        "the password did not reach the password file, so nothing was connected"
    )


@pytest.mark.skipif(not os.path.isfile(WRAPPER), reason="wrapper not in this checkout")
def test_wrapper_delegates_without_leaking(tmp_path):
    """The owner-facing entry point named in the handoffs must behave the same."""
    proc, log = _run(tmp_path, WRAPPER, [], {"RENDER_DB_URL": FAKE_URL})

    assert proc.returncode == 0, f"wrapper failed:\n{proc.stdout}\n{proc.stderr}"
    assert _argv_lines(log), "the wrapper never reached the engine"
    for line in _argv_lines(log):
        assert FAKE_PASSWORD not in line, f"credential in argv: {line!r}"
    assert FAKE_PASSWORD not in proc.stdout
    assert FAKE_PASSWORD not in proc.stderr


def test_the_recorder_would_see_a_leak(tmp_path):
    """Negative control: the old invocation shape is detected by this recorder.

    Without this, a passing argv assertion could simply mean the recorder records
    nothing. Here the URL is passed as an argument deliberately, and the password
    must show up.
    """
    bindir = _bindir(tmp_path)
    log = tmp_path / "stub.log"
    env = os.environ.copy()
    env["STUB_LOG"] = str(log)
    env["PGHOST"] = FAKE_HOST

    proc = subprocess.run(
        [str(bindir / "pg_dump"), "--format=custom", "--dbname=" + FAKE_URL],
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert proc.returncode == 0
    recorded = log.read_text()
    assert FAKE_PASSWORD in recorded, (
        "the recorder did not see a credential that was genuinely on the command "
        "line, so the argv assertions above are vacuous"
    )


@pytest.mark.skipif(not os.path.isfile(HELPER), reason="helper not in this checkout")
def test_helper_escapes_pgpass_fields(tmp_path):
    """pgpass is colon-separated, so a colon or backslash in a field must escape."""
    out = tmp_path / "pgp"
    url = "postgresql://bob:p%40ss%3Aword%2Fx@h.example.com/oddfellow?sslmode=require"
    proc = subprocess.run(
        ["python3", HELPER, str(out)],
        input=url,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert proc.returncode == 0, proc.stderr
    assert out.read_text() == "h.example.com:5432:*:bob:p@ss\\:word/x\n"
    assert oct(out.stat().st_mode & 0o777) == oct(0o600)
    assert "PGSSLMODE=require" in proc.stdout
    assert "p@ss" not in proc.stdout, "the password must not be printed for the caller"


@pytest.mark.skipif(not os.path.isfile(HELPER), reason="helper not in this checkout")
def test_helper_refuses_a_non_postgres_url(tmp_path):
    out = tmp_path / "pgp"
    proc = subprocess.run(
        ["python3", HELPER, str(out)],
        input="mysql://u:p@h/d",
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert proc.returncode == 2
    assert not out.exists() or out.read_text() == ""
