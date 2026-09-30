#!/usr/bin/env bash
#
# Keep the live rehearsal alive.
#
# A quick-tunnel URL is unrecoverable if the tunnel dies, and a dead rehearsal
# blocks the one acceptance gate only the owner can run. This loop restarts the
# backend or the tunnel if either stops answering, and keeps a file containing
# the URL that *currently* answers — validated against a live /livez, never
# trusted from a log line.
#
# Started by `rehearsal.sh keepalive`, which passes LETTA_API_KEY and
# ODDFELLOW_OWNER_TOKEN in this process's environment. They stay in memory:
# nothing secret is written to disk.
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PORT="${ODDFELLOW_REHEARSAL_PORT:-8130}"
VENV="${ODDFELLOW_VENV:-/tmp/venv}"
CLOUDFLARED="${CLOUDFLARED:-/tmp/cloudflared}"
BACKEND_LOG=/tmp/oddfellow-rehearsal-backend.log
TUNNEL_LOG=/tmp/oddfellow-rehearsal-tunnel.log
URLFILE=/tmp/oddfellow-rehearsal-url.txt
WATCHDOG_LOG=/tmp/oddfellow-watchdog.log
PIDFILE=/tmp/oddfellow-watchdog.pid
INTERVAL="${ODDFELLOW_WATCHDOG_INTERVAL:-30}"

log() { printf '%s %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*" >>"$WATCHDOG_LOG"; }

# See the note in rehearsal.sh: `pgrep -f` (and any bare command-line substring
# match) matches any process whose command line merely mentions the pattern,
# including a shell running this script's own name. That produced a real false
# "still alive" reading, so discovery anchors on /proc/<pid>/exe, which a shell
# cannot fake by talking about cloudflared.
pids_where() {
  local exe="$1"; shift
  local p line s ok
  for p in /proc/[0-9]*; do
    p="${p#/proc/}"
    [ "$p" = "$$" ] && continue
    [ "$p" = "$PPID" ] && continue
    case "$(basename "$(readlink "/proc/$p/exe" 2>/dev/null || true)")" in
      $exe) ;;
      *) continue ;;
    esac
    line="$(tr '\0' ' ' <"/proc/$p/cmdline" 2>/dev/null)" || continue
    [ -n "$line" ] || continue
    ok=1
    for s in "$@"; do
      case "$line" in *"$s"*) ;; *) ok=0; break ;; esac
    done
    [ "$ok" = 1 ] && printf '%s\n' "$p"
  done
  return 0
}

backend_pids() { pids_where 'python*' oddfellow_letta_backend:app "--port $PORT"; }
tunnel_pids()  { pids_where cloudflared "--url http://127.0.0.1:$PORT"; }

backend_up() { curl -fsS --max-time 5 "http://127.0.0.1:$PORT/livez" >/dev/null 2>&1; }
tunnel_up()  { [ -n "$(tunnel_pids)" ]; }

start_backend() {
  ( cd "$HERE" && ODDFELLOW_FRONTEND_DIR=frontend LETTA_MODEL=letta/auto \
      LETTA_API_KEY="$LETTA_API_KEY" ODDFELLOW_OWNER_TOKEN="$ODDFELLOW_OWNER_TOKEN" \
      ODDFELLOW_AGENT_ID="${ODDFELLOW_AGENT_ID:-agent-a9a8eb2c-2fed-4554-9998-aa4783c7efc4}" \
      exec setsid --fork "$VENV/bin/python" -m uvicorn oddfellow_letta_backend:app \
      --host 127.0.0.1 --port "$PORT" ) >>"$BACKEND_LOG" 2>&1 </dev/null &
  disown
  for _ in $(seq 1 30); do backend_up && return 0; sleep 1; done
  return 1
}

start_tunnel() {
  [ -x "$CLOUDFLARED" ] || { log "cloudflared missing at $CLOUDFLARED"; return 1; }
  ( cd "$(dirname "$CLOUDFLARED")" && exec setsid --fork "$CLOUDFLARED" tunnel \
      --url "http://127.0.0.1:$PORT" --no-autoupdate ) >>"$TUNNEL_LOG" 2>&1 </dev/null &
  disown
  return 0
}

# Return the first candidate URL that actually answers /livez. An old log holds a
# URL that is now dead, so a live response is the only thing worth trusting.
# Newest-first, because the live tunnel is almost always the most recent one and
# each dead candidate costs a full curl timeout.
live_url() {
  local f u
  for f in "$TUNNEL_LOG" /tmp/tunnel3.log /tmp/tunnel2.log /tmp/tunnel.log; do
    [ -f "$f" ] || continue
    for u in $(grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' "$f" 2>/dev/null \
        | awk '!seen[$0]++' | tail -6 \
        | awk '{a[NR]=$0} END{for(i=NR;i>0;i--) print a[i]}'); do
      if curl -fsS --max-time 5 "$u/livez" >/dev/null 2>&1; then echo "$u"; return 0; fi
    done
  done
  return 1
}

printf '%s\n' "$$" >"$PIDFILE"
trap 'rm -f "$PIDFILE"' EXIT
log "watchdog started (pid $$, port $PORT, interval ${INTERVAL}s)"
last_url=""

while true; do
  if ! backend_up; then
    log "backend DOWN — restarting"
    start_backend && log "backend restarted" || log "backend restart FAILED"
  fi

  if ! tunnel_up; then
    log "tunnel DOWN — restarting"
    start_tunnel
    sleep 5
  fi

  if url="$(live_url)"; then
    if [ "$url" != "$last_url" ]; then
      printf '%s\n' "$url" >"$URLFILE"
      log "live url: $url"
      last_url="$url"
    fi
  else
    log "no candidate url answers yet"
  fi

  sleep "$INTERVAL"
done
