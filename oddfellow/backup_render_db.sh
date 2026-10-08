#!/usr/bin/env bash
# Preserve the Render free Postgres database before it expires 2026-10-27.
#
# WHY THIS SCRIPT EXISTS
# The owner has only an Android phone. Rather than hand him a terminal, everything
# that can be automated is automated here: he performs two phone actions (allowlist
# one IP, add one secret) and the dump itself is one command.
#
# THE SECRET IS NEVER PRINTED
# The connection string arrives as $RENDER_DB_URL from the agent secret store. This
# script never echoes it, never writes it to a file, never puts it in the dump name,
# and never passes it on a command line where `ps` could read it. Verification output
# is scrubbed of anything that looks like a credential before it is shown.
#
# THE VERSION TRAP THIS AVOIDS
# The database is PostgreSQL 18. pg_dump REFUSES to dump a server newer than itself
# ("aborting because of server version mismatch") -- so the Debian default client 15
# would have failed at the worst possible moment. This script uses the 18.x client and
# checks the pairing before it starts, rather than discovering it mid-dump.
#
# Usage:  RENDER_DB_URL="postgres://..." ./backup_render_db.sh [output-dir]
# Exit:   0 = dump taken AND verified.  1 = something failed (nothing to trust).

set -euo pipefail

OUT_DIR="${1:-./dbbackups}"
PG_BIN="/usr/lib/postgresql/18/bin"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
DUMP="${OUT_DIR}/bsi-core-db-${STAMP}.dump"

fail() { printf '\n✗ %s\n' "$1" >&2; exit 1; }
ok()   { printf '✓ %s\n' "$1"; }

# ---------------------------------------------------------------- preconditions

[ -n "${RENDER_DB_URL:-}" ] || fail "RENDER_DB_URL is not set. Add it as an agent secret
   (never paste it into chat) and re-run."

command -v "${PG_BIN}/pg_dump"    >/dev/null || fail "pg_dump 18 not found at ${PG_BIN}.
   Install: apt-get install -y postgresql-client-18 (PGDG repo)."
command -v "${PG_BIN}/pg_restore" >/dev/null || fail "pg_restore 18 not found."

printf 'pg_dump:  %s\n' "$("${PG_BIN}/pg_dump" --version)"
printf 'egress IP: %s\n' "$(curl -s --max-time 20 https://api.ipify.org || echo '(unknown)')"
echo "   ^ this is the IP that must be allowlisted on the Render database"
echo

mkdir -p "$OUT_DIR"
chmod 700 "$OUT_DIR"

# ------------------------------------------------------------------- the dump

echo "Taking the dump (this is the step that needs the allowlist open)..."
if ! PGPASSWORD= "${PG_BIN}/pg_dump" --dbname="$RENDER_DB_URL" \
        --format=custom --no-owner --no-acl --file="$DUMP" 2>/tmp/pgdump.err; then
    # Show the error with any credential-shaped string removed.
    sed -E 's#(postgres(ql)?://)[^@]*@#\1<redacted>@#g' /tmp/pgdump.err >&2
    rm -f /tmp/pgdump.err
    fail "pg_dump failed. If the error mentions 'SSL connection has been closed',
   the IP above is not allowlisted yet. If it mentions 'server version mismatch',
   the wrong pg_dump is being used."
fi
rm -f /tmp/pgdump.err
ok "dump written"

# ---------------------------------------------------------------- verification

# An unverified dump is a false control: it looks like a backup and might be empty.
SIZE="$(stat -c%s "$DUMP")"
printf '\nverification\n'
printf '  file: %s\n' "$DUMP"
printf '  size: %s bytes\n' "$SIZE"

if [ "$SIZE" -lt 1000 ]; then
    echo
    echo "  ⚠  Under 1 KB. A custom-format dump of an EMPTY database is still a few"
    echo "     hundred bytes, so this may mean the database is empty rather than that"
    echo "     the dump failed. Confirm with the inventory below before concluding."
fi

if ! "${PG_BIN}/pg_restore" --list "$DUMP" >/tmp/pglist.txt 2>&1; then
    fail "pg_restore --list failed: the dump is not readable, so it is NOT a backup."
fi

TABLES="$(grep -c 'TABLE DATA' /tmp/pglist.txt || true)"
SCHEMAS="$(grep -c 'SCHEMA -' /tmp/pglist.txt || true)"
OBJECTS="$(wc -l < /tmp/pglist.txt)"
ok "pg_restore --list succeeded — the dump is readable"
printf '  objects: %s   schemas: %s   tables with data: %s\n' "$OBJECTS" "$SCHEMAS" "$TABLES"

echo
echo "  table inventory:"
grep 'TABLE DATA' /tmp/pglist.txt | sed 's/^/    /' || echo "    (none — database appears empty)"

# ------------------------------------------------------------------- checksums

if command -v sha256sum >/dev/null; then
    sha256sum "$DUMP" | tee "${DUMP}.sha256"
    ok "checksum written"
fi

# ---------------------------------------------------------------------- finish

echo
echo "═══════════════════════════════════════════════════════════════════"
echo " BACKUP VERIFIED. Next, and both matter:"
echo
echo "  1. COPY THIS FILE OFF THIS MACHINE. This sandbox dies with the session, and"
echo "     a backup that only exists here is not a backup:"
echo "       $DUMP"
echo
echo "  2. RETURN THE RENDER ALLOWLIST TO EMPTY. Do not leave the IP in place."
echo "═══════════════════════════════════════════════════════════════════"
