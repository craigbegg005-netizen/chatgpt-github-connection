#!/usr/bin/env bash
# Preserve the Render free Postgres database before it expires 2026-10-27.
#
# THIS IS THE OWNER-FACING ENTRY POINT named in the handoffs. It is a thin
# wrapper: the implementation lives in db_preserve.sh, in exactly one copy.
# Two scripts that each implemented "how to connect" is how the credential ended
# up on a command line in one of them (found 2026-10-11). A second copy of a rule
# is not redundancy, it is the mechanism by which the copies drift apart.
#
# THE CONNECTION STRING NEVER REACHES A COMMAND LINE. The URL is handed to the
# engine through the environment and split there into a mode-600 password file
# that only libpq reads, so `ps` and /proc/<pid>/cmdline show no credential. The
# previous version of this file passed it as `--dbname="$RENDER_DB_URL"` while
# its own header claimed it did not -- verified 2026-10-11 that such an argument
# is fully visible in `ps`, password included.
#
# THE SECRET IS NEVER PRINTED. It is never echoed, never written to a file other
# than the mode-600 password file, and never put in the dump name.
#
# Usage:  RENDER_DB_URL="postgres://..." ./backup_render_db.sh [output-dir]
# Exit:   0 = dump taken AND verified.  1 = something failed (nothing to trust).

set -euo pipefail

HERE="$(dirname "$(readlink -f "$0")")"
ENGINE="$HERE/db_preserve.sh"

if [ ! -x "$ENGINE" ]; then
    printf '\n✗ engine not found or not executable: %s\n' "$ENGINE" >&2
    exit 1
fi

if [ -z "${RENDER_DB_URL:-}" ]; then
    printf '\n✗ RENDER_DB_URL is not set. Add it as an agent secret\n' >&2
    printf '   (never paste it into chat) and re-run.\n' >&2
    exit 1
fi

# The owner needs this address to open the Render allowlist. Printed before the
# dump so it is available even when the connection is refused.
printf 'egress IP: %s\n' "$(curl -s --max-time 20 https://api.ipify.org || echo '(unknown)')"
printf '   ^ this is the IP that must be allowlisted on the Render database\n\n'

# RENDER_DB_URL is the name the owner was told to use; the engine reads
# ODDFELLOW_DB_URL. Map one to the other and echo neither.
export ODDFELLOW_DB_URL="$RENDER_DB_URL"
if [ -n "${1:-}" ]; then
    export ODDFELLOW_DB_OUT_DIR="$1"
fi

status=0
"$ENGINE" dump || status=$?

if [ "$status" -eq 0 ]; then
    printf '\n═══════════════════════════════════════════════════════════════════\n'
    printf ' BACKUP VERIFIED. Two things still matter:\n\n'
    printf '  1. COPY THE DUMP OFF THIS MACHINE. This sandbox dies with the session,\n'
    printf '     and a backup that only exists here is not a backup.\n\n'
    printf '  2. RETURN THE RENDER ALLOWLIST TO EMPTY. Do not leave the IP in place.\n'
    printf '═══════════════════════════════════════════════════════════════════\n'
fi

exit "$status"
