#!/usr/bin/env python3
"""
Turn a PostgreSQL connection URI into a libpq password file plus non-secret
environment settings, so the credential never reaches a command line.

WHY THIS EXISTS
---------------
The DB-preservation scripts used to pass the connection string as an argument:

    pg_dump --dbname="postgres://user:password@host/db" ...

A process argument list is readable by every user on the box (`ps -eo args`,
/proc/<pid>/cmdline). Verified 2026-10-11: a URL passed as an argument appears
in full, password included -- while the script's own header claimed it "never
passes it on a command line where `ps` could read it". A security claim the code
does not enforce is worse than no claim, because it stops the next reader from
checking.

WHY NOT JUST AN ENVIRONMENT VARIABLE
------------------------------------
libpq does not expand a URI supplied through PGDATABASE -- tested 2026-10-11,
it is treated as a plain database name and the connection goes to the default
socket. So the URI cannot simply be moved into one variable and left whole.
This helper splits it instead: the password goes into a mode-600 password file
that only libpq reads, and everything else (host, port, user, database, sslmode)
becomes an ordinary environment setting.

Usage:  printf '%s' "$URL" | db_url_to_pgpass.py /path/to/pgpass
Writes: the password file, created at mode 0600.
Prints: PG*=<value> lines on stdout, for the caller to export.
Exit:   0 ok, 2 bad input (nothing written to stdout in that case).
"""

from __future__ import annotations

import os
import sys
import urllib.parse

# Query parameters libpq understands, mapped to the environment variable each
# one corresponds to. Carried across so that moving the credential does not
# silently drop sslmode -- Render requires TLS, so losing it would break the
# dump for a reason that looks nothing like the change that caused it.
_QUERY_TO_ENV = {
    "sslmode": "PGSSLMODE",
    "sslrootcert": "PGSSLROOTCERT",
    "sslcert": "PGSSLCERT",
    "sslkey": "PGSSLKEY",
    "connect_timeout": "PGCONNECT_TIMEOUT",
    "application_name": "PGAPPNAME",
    "options": "PGOPTIONS",
    "target_session_attrs": "PGTARGETSESSIONATTRS",
    "channel_binding": "PGCHANNELBINDING",
    "gssencmode": "PGGSSENCMODE",
}


def _pgpass_field(value: str) -> str:
    """Escape one field for a pgpass line (backslash, then colon)."""
    return value.replace("\\", "\\\\").replace(":", "\\:")


def _has_control(value: str) -> bool:
    return any(ord(ch) < 32 or ord(ch) == 127 for ch in value)


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: db_url_to_pgpass.py <pgpass-path>", file=sys.stderr)
        return 2

    path = argv[1]
    raw = sys.stdin.read().strip()
    if not raw:
        print("db_url_to_pgpass: no connection string on stdin", file=sys.stderr)
        return 2

    try:
        parts = urllib.parse.urlsplit(raw)
        port = parts.port  # raises ValueError on a non-numeric port
    except ValueError as exc:
        print(f"db_url_to_pgpass: unparseable connection string ({exc})", file=sys.stderr)
        return 2

    if parts.scheme not in ("postgres", "postgresql"):
        print(
            f"db_url_to_pgpass: unexpected scheme {parts.scheme!r}; "
            "expected postgres:// or postgresql://",
            file=sys.stderr,
        )
        return 2

    host = parts.hostname or ""
    user = urllib.parse.unquote(parts.username or "")
    password = urllib.parse.unquote(parts.password or "")
    database = urllib.parse.unquote(parts.path.lstrip("/")) or "postgres"
    port_s = str(port or 5432)

    if not host:
        print("db_url_to_pgpass: connection string has no host", file=sys.stderr)
        return 2
    if _has_control(host) or _has_control(user) or _has_control(password) or _has_control(database):
        print(
            "db_url_to_pgpass: connection string contains control characters",
            file=sys.stderr,
        )
        return 2

    line = ":".join(_pgpass_field(x) for x in (host, port_s, database, user, password)) + "\n"

    # Create at 0600 in the same call that writes it, so there is never a window
    # in which the password file exists with looser permissions.
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        os.write(fd, line.encode("utf-8"))
    finally:
        os.close(fd)
    os.chmod(path, 0o600)  # an existing file keeps its old mode through O_CREAT

    # Non-secret settings for the caller to export. Never the password.
    print(f"PGHOST={host}")
    print(f"PGPORT={port_s}")
    print(f"PGUSER={user}")
    print(f"PGDATABASE={database}")

    for key, values in urllib.parse.parse_qs(parts.query, keep_blank_values=True).items():
        env = _QUERY_TO_ENV.get(key)
        if env and values and not _has_control(values[0]):
            print(f"{env}={values[0]}")

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
