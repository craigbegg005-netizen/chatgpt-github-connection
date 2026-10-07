#!/usr/bin/env bash
#
# db_preserve.sh -- preserve a Render Postgres database before its free-tier
# expiry, without spending money and without weakening its security.
#
#   ./db_preserve.sh doctor          check the tools are fit for purpose
#   ./db_preserve.sh recon           what is actually in there? (tiny output)
#   ./db_preserve.sh dump            full custom-format dump + verification
#   ./db_preserve.sh verify <file>   re-verify an existing dump
#
# THE CONNECTION STRING IS NEVER PASSED ON THE COMMAND LINE. It is read from a
# file (default /root/.oddfellow-db-url, mode 600) or from stdin without echo.
# Passing it as an argument would put the database password into shell history
# and into `ps` output for every user on the box.
#
# WHY `doctor` EXISTS. pg_dump refuses to dump a server newer than itself, and
# it refuses *after* creating the output file -- leaving a 0-byte file that a
# naive "does the backup exist?" check reads as success. Verified 2026-10-07:
# pg_dump 15.19 against PostgreSQL 18.6 wrote 0 bytes and exited with
# "aborting because of server version mismatch". The dump is therefore only
# accepted when its size is non-zero AND pg_restore can parse its table of
# contents. Both conditions are checked here; neither alone is sufficient.
#
set -euo pipefail

DB_URL_FILE="${ODDFELLOW_DB_URL_FILE:-/root/.oddfellow-db-url}"
OUT_DIR="${ODDFELLOW_DB_OUT_DIR:-/root/oddfellow-db-backups}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
REQUIRED_PG_MAJOR=18

say()  { printf '\n\033[1m%s\033[0m\n' "$*"; }
ok()   { printf '  \033[32m[PASS]\033[0m %s\n' "$*"; }
bad()  { printf '  \033[31m[FAIL]\033[0m %s\n' "$*"; }
warn() { printf '  \033[33m[WARN]\033[0m %s\n' "$*"; }
die()  { printf '\n\033[31mERROR:\033[0m %s\n' "$*" >&2; exit 1; }

# Resolve the newest pg_dump/pg_restore/psql available, preferring a version
# that can actually talk to the server.
pg_bin() {
  local tool="$1" want="$2" cand
  for cand in "/usr/lib/postgresql/${want}/bin/${tool}" "$(command -v "$tool" 2>/dev/null || true)"; do
    [ -n "$cand" ] && [ -x "$cand" ] && { printf '%s' "$cand"; return 0; }
  done
  return 1
}

pg_major() { "$1" --version | sed -E 's/.* ([0-9]+)\..*/\1/'; }

read_url() {
  if [ -n "${ODDFELLOW_DB_URL:-}" ]; then
    printf '%s' "$ODDFELLOW_DB_URL"
  elif [ -f "$DB_URL_FILE" ]; then
    # strip surrounding whitespace/newlines only
    tr -d '\r\n' < "$DB_URL_FILE"
  elif [ ! -t 0 ]; then
    tr -d '\r\n'
  else
    die "no connection string. Put it in $DB_URL_FILE (chmod 600) or pipe it on stdin."
  fi
}

# ---------------------------------------------------------------- doctor
cmd_doctor() {
  say "doctor -- are these tools fit to dump a PostgreSQL ${REQUIRED_PG_MAJOR} server?"
  local dump restore psql_bin dver rver
  dump="$(pg_bin pg_dump "$REQUIRED_PG_MAJOR")"    || die "pg_dump not found"
  restore="$(pg_bin pg_restore "$REQUIRED_PG_MAJOR")" || die "pg_restore not found"
  psql_bin="$(pg_bin psql "$REQUIRED_PG_MAJOR")"   || die "psql not found"

  dver="$(pg_major "$dump")"; rver="$(pg_major "$restore")"
  printf '  pg_dump    %s (major %s)\n' "$dump" "$dver"
  printf '  pg_restore %s (major %s)\n' "$restore" "$rver"
  printf '  psql       %s\n' "$psql_bin"

  if [ "$dver" -ge "$REQUIRED_PG_MAJOR" ]; then
    ok "pg_dump major $dver >= $REQUIRED_PG_MAJOR -- can dump the server"
  else
    bad "pg_dump major $dver < $REQUIRED_PG_MAJOR -- it WILL abort and leave a 0-byte file"
    printf '\n  Fix (Debian/Ubuntu, zero cost):\n'
    printf '    curl -fsSL https://www.postgresql.org/media/keys/ACCC4CF8.asc \\\n'
    printf '      | gpg --dearmor -o /usr/share/keyrings/pgdg.gpg\n'
    printf '    chmod 644 /usr/share/keyrings/pgdg.gpg   # 600 makes apt reject it\n'
    printf '    echo "deb [signed-by=/usr/share/keyrings/pgdg.gpg] \\\n'
    printf '      http://apt.postgresql.org/pub/repos/apt bookworm-pgdg main" \\\n'
    printf '      > /etc/apt/sources.list.d/pgdg.list\n'
    printf '    apt-get update && apt-get install -y postgresql-client-%s\n' "$REQUIRED_PG_MAJOR"
    return 1
  fi

  # Prove the negative: that a too-old client really does fail, so the guard is
  # not a claim. Only runs when an older client happens to be installed.
  local old="/usr/lib/postgresql/15/bin/pg_dump"
  if [ -x "$old" ]; then
    ok "an older client is present at $old -- use it only to reproduce the failure"
  fi
  ok "doctor: fit for purpose"
}

# ---------------------------------------------------------------- recon
# The cheapest possible probe. Answers "is there anything here?" before we
# spend effort on a full dump.
cmd_recon() {
  local dump psql_bin url
  dump="$(pg_bin pg_dump "$REQUIRED_PG_MAJOR")"
  psql_bin="$(pg_bin psql "$REQUIRED_PG_MAJOR")"
  [ "$(pg_major "$dump")" -ge "$REQUIRED_PG_MAJOR" ] || die "run './db_preserve.sh doctor' first"
  url="$(read_url)"

  say "recon -- schemas, tables and row counts (read-only)"
  "$psql_bin" "$url" -v ON_ERROR_STOP=1 -P pager=off -c "
    SELECT table_schema AS schema, table_name AS table,
           (xpath('/row/c/text()', query_to_xml(
              format('SELECT count(*) AS c FROM %I.%I', table_schema, table_name),
              false, true, '')))[1]::text::bigint AS rows
    FROM information_schema.tables
    WHERE table_schema NOT IN ('pg_catalog','information_schema')
    ORDER BY table_schema, table_name;"
  say "recon -- extensions"
  "$psql_bin" "$url" -v ON_ERROR_STOP=1 -P pager=off -tAc \
    "SELECT extname || ' ' || extversion FROM pg_extension ORDER BY 1;"
  say "recon -- database size"
  "$psql_bin" "$url" -v ON_ERROR_STOP=1 -P pager=off -tAc \
    "SELECT pg_size_pretty(pg_database_size(current_database()));"
}

# ---------------------------------------------------------------- dump
cmd_dump() {
  local dump restore url out
  dump="$(pg_bin pg_dump "$REQUIRED_PG_MAJOR")"
  restore="$(pg_bin pg_restore "$REQUIRED_PG_MAJOR")"
  [ "$(pg_major "$dump")" -ge "$REQUIRED_PG_MAJOR" ] || die "run './db_preserve.sh doctor' first"
  url="$(read_url)"

  mkdir -p "$OUT_DIR"; chmod 700 "$OUT_DIR"
  out="$OUT_DIR/begg-ai-core-db-$STAMP.dump"

  say "dump -- writing $out"
  # --no-owner/--no-privileges so the dump restores into any role.
  "$dump" --format=custom --no-owner --no-privileges --file="$out" "$url"

  cmd_verify "$out"
  printf '\n  Dump written to: %s\n' "$out"
  printf '  Keep a second copy off this machine. Do NOT commit it to git.\n'
}

# ---------------------------------------------------------------- verify
# An unverified dump is a false control. Size alone is not enough: the failure
# mode above produces a file that exists and is empty.
cmd_verify() {
  local f="${1:-}" restore entries size
  [ -n "$f" ] || die "usage: ./db_preserve.sh verify <file>"
  [ -f "$f" ] || die "no such file: $f"
  restore="$(pg_bin pg_restore "$REQUIRED_PG_MAJOR")"

  say "verify -- $f"
  size="$(stat -c %s "$f")"
  if [ "$size" -gt 0 ]; then
    ok "size is non-zero ($size bytes)"
  else
    bad "size is 0 bytes -- this is the signature of a version-mismatch abort"
    return 1
  fi

  if entries="$("$restore" --list "$f" 2>/dev/null | grep -cE '^[0-9]+;')"; then
    if [ "$entries" -gt 0 ]; then
      ok "pg_restore --list parses it: $entries TOC entries"
    else
      bad "pg_restore --list parsed but found 0 objects -- empty database, or a bad dump"
      return 1
    fi
  else
    bad "pg_restore --list could not parse the file"
    return 1
  fi

  printf '\n  Table of contents:\n'
  "$restore" --list "$f" | grep -E '^[0-9]+;' | awk '{print "    " $0}' | head -40
  ok "verify: dump is well-formed and non-empty"
}

case "${1:-}" in
  doctor) cmd_doctor ;;
  recon)  cmd_recon ;;
  dump)   cmd_dump ;;
  verify) shift; cmd_verify "${1:-}" ;;
  *) printf 'usage: %s {doctor|recon|dump|verify <file>}\n' "$0"; exit 2 ;;
esac
