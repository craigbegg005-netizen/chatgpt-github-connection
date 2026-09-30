#!/usr/bin/env bash
#
# Bring up the Oddfellow live rehearsal: the v0.20.5 backend, served from this
# sandbox and published through a Cloudflare quick tunnel so it can be reached
# from a phone.
#
#   ./rehearsal.sh up        start the backend and the tunnel, print the URL
#   ./rehearsal.sh status    is it up, and what does the harness say
#   ./rehearsal.sh keepalive start a detached watchdog that restarts either
#                            process if it dies and keeps the live URL in
#                            /tmp/oddfellow-rehearsal-url.txt
#   ./rehearsal.sh down      stop everything, including the watchdog
#
# THIS IS A REHEARSAL, NOT A DEPLOYMENT. It dies with the sandbox, it uses the
# sandbox's platform-managed Letta key (which the owner cannot rotate), and
# traffic passes through Cloudflare's tunnel edge, which terminates TLS. It
# exists to prove the stack works and to let a human run the gates only a human
# can run. The permanent paths are cloudflare/deploy.sh and the Render blueprint.
#
# The Letta key is read from the environment and never written to disk.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PORT="${ODDFELLOW_REHEARSAL_PORT:-8130}"
# State lives under /root, not /tmp: the sandbox has been observed to cycle and
# clear /tmp, which wiped the venv, the cloudflared binary and the tunnel log —
# forcing a full reinstall and losing the URL history. /root survives.
STATE_DIR="${ODDFELLOW_STATE_DIR:-/root/.oddfellow}"
VENV="${ODDFELLOW_VENV:-$STATE_DIR/venv}"
CLOUDFLARED="${CLOUDFLARED:-$STATE_DIR/bin/cloudflared}"
BACKEND_LOG="$STATE_DIR/logs/backend.log"
TUNNEL_LOG="$STATE_DIR/logs/tunnel.log"
WATCHDOG_PIDFILE="$STATE_DIR/watchdog.pid"
MODE="${1:-}"

say() { printf '\n\033[1m%s\033[0m\n' "$*"; }
die() { printf '\nERROR: %s\n' "$*" >&2; exit 1; }

ensure_dirs() {
  mkdir -p "$STATE_DIR/bin" "$STATE_DIR/logs" "$(dirname "$VENV")"
}

# Fetch cloudflared if it is missing.
#
# Why this is automatic: state moved to $STATE_DIR precisely so the rehearsal
# survives a sandbox cycle, but the binary is not part of the repo, so a cycle
# still left `up` dying with "fetch it from the Cloudflare releases page" --
# a manual step that defeats the point of the move. It is a public download
# with no account and no cost, so there is no reason to make a human do it.
#
# Verified by deleting the binary and running `up`: it is fetched, and the
# rehearsal comes up. The download is atomic (temp file + mv) so an interrupted
# fetch cannot leave a truncated binary that looks executable.
ensure_cloudflared() {
  [ -x "$CLOUDFLARED" ] && return 0
  local url="https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64"
  say "cloudflared missing -- fetching it to $CLOUDFLARED"
  local tmp="$CLOUDFLARED.download.$$"
  if ! curl -fsSL --max-time 180 -o "$tmp" "$url"; then
    rm -f "$tmp"
    die "could not download cloudflared from $url (no network?)"
  fi
  chmod +x "$tmp"
  mv -f "$tmp" "$CLOUDFLARED"
  "$CLOUDFLARED" --version >/dev/null 2>&1 \
    || die "the downloaded cloudflared at $CLOUDFLARED does not run"
}

# A background bash task is reaped when it times out, so anything long-running
# must be detached from the shell that started it. This is how.
#
# Two details matter, both learned by getting them wrong. The redirect goes on
# the *subshell*, not on the command inside it: `setsid` execs in place when it
# is not already a process-group leader, so if only the inner command is
# redirected, the detached process inherits the caller's stdout pipe and the
# caller hangs until its timeout even though the work started fine. And
# `setsid --fork` guarantees a fork, so the launching shell always returns.

# Find PIDs whose executable matches the given glob AND whose /proc/<pid>/cmdline
# contains every substring given, skipping this shell and its parent.
#
# `pgrep -f` is deliberately NOT used anywhere in this script, and neither is a
# bare command-line substring match. Both match any process whose command line
# merely *mentions* the pattern — including a shell that runs `./rehearsal.sh up`
# or a diagnostic that greps for "cloudflared tunnel". That is not theoretical:
# it made the watchdog conclude the tunnel was still alive after the tunnel had
# been killed, so the rehearsal stayed down while the watchdog reported nothing
# wrong. Anchoring on /proc/<pid>/exe is what makes the answer trustworthy: a
# shell cannot become cloudflared by talking about it.
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

watchdog_pid() {
  [ -f "$WATCHDOG_PIDFILE" ] || return 1
  local p; p="$(cat "$WATCHDOG_PIDFILE" 2>/dev/null || true)"
  [ -n "$p" ] || return 1
  [ -r "/proc/$p/cmdline" ] || return 1
  tr '\0' ' ' <"/proc/$p/cmdline" 2>/dev/null | grep -qF "rehearsal_watchdog.sh" || return 1
  printf '%s\n' "$p"
}

up() {
  [ -n "${LETTA_API_KEY:-}" ]         || die "LETTA_API_KEY is not set in the environment"
  [ -n "${ODDFELLOW_OWNER_TOKEN:-}" ] || die "ODDFELLOW_OWNER_TOKEN is not set in the environment"
  ensure_dirs

  if [ ! -x "$VENV/bin/python" ]; then
    say "Creating the venv at $VENV"
    python3 -m venv "$VENV"
    "$VENV/bin/pip" install -q -r "$HERE/requirements.txt" pytest
  fi

  if ! curl -fsS --max-time 3 "http://127.0.0.1:$PORT/livez" >/dev/null 2>&1; then
    say "Starting the backend on 127.0.0.1:$PORT"
    ( cd "$HERE" && ODDFELLOW_FRONTEND_DIR=frontend LETTA_MODEL=letta/auto \
        LETTA_API_KEY="$LETTA_API_KEY" ODDFELLOW_OWNER_TOKEN="$ODDFELLOW_OWNER_TOKEN" \
        ODDFELLOW_AGENT_ID="${ODDFELLOW_AGENT_ID:-agent-a9a8eb2c-2fed-4554-9998-aa4783c7efc4}" \
        exec setsid --fork "$VENV/bin/python" -m uvicorn oddfellow_letta_backend:app \
        --host 127.0.0.1 --port "$PORT" ) >"$BACKEND_LOG" 2>&1 </dev/null &
    disown
    for _ in $(seq 1 30); do
      curl -fsS --max-time 3 "http://127.0.0.1:$PORT/livez" >/dev/null 2>&1 && break
      sleep 1
    done
  else
    say "Backend already up on 127.0.0.1:$PORT"
  fi
  curl -fsS --max-time 5 "http://127.0.0.1:$PORT/livez" >/dev/null 2>&1 \
    || { tail -20 "$BACKEND_LOG" 2>/dev/null; die "the backend never answered"; }

  # Record where the log ends before starting anything, so the URL we report is
  # one this run actually produced. The log is appended to across restarts, and
  # its newest line is not necessarily the live tunnel — a URL from an earlier
  # tunnel can be the last thing written. Reporting that stale URL is worse than
  # reporting nothing, because it looks like success.
  local before=0
  [ -f "$TUNNEL_LOG" ] && before="$(wc -c <"$TUNNEL_LOG")"

  if [ -z "$(tunnel_pids)" ]; then
    ensure_cloudflared
    say "Opening a Cloudflare quick tunnel"
    ( cd "$(dirname "$CLOUDFLARED")" && exec setsid --fork "$CLOUDFLARED" tunnel \
        --url "http://127.0.0.1:$PORT" --no-autoupdate ) >>"$TUNNEL_LOG" 2>&1 </dev/null &
    disown
  else
    say "Tunnel already running"
  fi

  local url=""
  for _ in $(seq 1 30); do
    url="$(tail -c "+$((before + 1))" "$TUNNEL_LOG" 2>/dev/null \
      | grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' | tail -1 || true)"
    [ -n "$url" ] && break
    sleep 2
  done
  # Nothing new was appended, so the tunnel was already up: ask which candidate
  # actually answers instead of guessing from the log.
  [ -n "$url" ] || url="$(find_url || true)"
  [ -n "$url" ] || { tail -20 "$TUNNEL_LOG" 2>/dev/null; die "no tunnel URL appeared"; }

  say "Waiting for the public URL to answer"
  local answered=""
  for _ in $(seq 1 15); do
    curl -fsS --max-time 6 "$url/livez" >/dev/null 2>&1 && { answered=1; break; }
    sleep 2
  done
  [ -n "$answered" ] || url="$(find_url || true)"
  [ -n "$url" ] || { tail -20 "$TUNNEL_LOG" 2>/dev/null; die "no tunnel URL answers /livez"; }

  say "REHEARSAL URL"
  echo "$url"
  echo
  echo "Owner token: the value of ODDFELLOW_OWNER_TOKEN. Paste it into the page's"
  echo "'Owner token' field. It is never printed here."
}

find_url() {
  # A quick-tunnel URL cannot be recovered any other way, and an old log holds a
  # URL that is now dead — so try candidates newest-first and return the first
  # that actually answers. Never trust a log line over a live response.
  #
  # Newest-first matters for speed: the live tunnel is almost always the most
  # recent one, and each dead candidate costs a full curl timeout.
  local f u
  for f in "$TUNNEL_LOG" /tmp/oddfellow-rehearsal-tunnel.log /tmp/tunnel3.log /tmp/tunnel2.log /tmp/tunnel.log; do
    [ -f "$f" ] || continue
    for u in $(grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' "$f" 2>/dev/null \
        | awk '!seen[$0]++' | tail -6 \
        | awk '{a[NR]=$0} END{for(i=NR;i>0;i--) print a[i]}'); do
      if curl -fsS --max-time 5 "$u/livez" >/dev/null 2>&1; then echo "$u"; return 0; fi
    done
  done
  return 1
}

status() {
  local url
  # `|| true` matters: find_url returns non-zero when nothing answers, and under
  # `set -e` an unguarded command substitution would abort the script with no
  # output at all -- i.e. it would fail silently in exactly the situation the
  # status report exists for.
  url="$(find_url || true)"
  [ -n "$(backend_pids)" ] && echo "backend: UP" || echo "backend: DOWN"
  [ -n "$(tunnel_pids)" ]  && echo "tunnel:  UP" || echo "tunnel:  DOWN"
  [ -n "$(watchdog_pid || true)" ] && echo "watchdog: UP" || echo "watchdog: DOWN"
  if [ -n "$url" ]; then
    echo "url:     $url"
    curl -s --max-time 20 "$url/livez" || true; echo
    if [ -n "${ODDFELLOW_OWNER_TOKEN:-}" ] && [ -x "$VENV/bin/python" ]; then
      "$VENV/bin/python" "$HERE/acceptance_check.py" "$url" --owner-token "$ODDFELLOW_OWNER_TOKEN" 2>&1 | tail -5
    fi
  else
    echo "url:     (none answering — run '$0 up')"
  fi
  return 0
}

keepalive() {
  [ -n "${LETTA_API_KEY:-}" ]         || die "LETTA_API_KEY is not set in the environment"
  [ -n "${ODDFELLOW_OWNER_TOKEN:-}" ] || die "ODDFELLOW_OWNER_TOKEN is not set in the environment"
  if [ -n "$(watchdog_pid || true)" ]; then
    say "Watchdog already running (pid $(watchdog_pid))"
  else
    say "Starting the rehearsal watchdog"
    ( cd "$HERE" && exec setsid --fork env \
        LETTA_API_KEY="$LETTA_API_KEY" ODDFELLOW_OWNER_TOKEN="$ODDFELLOW_OWNER_TOKEN" \
        ODDFELLOW_REHEARSAL_PORT="$PORT" ODDFELLOW_VENV="$VENV" CLOUDFLARED="$CLOUDFLARED" \
        bash "$HERE/rehearsal_watchdog.sh" ) >/dev/null 2>&1 </dev/null &
    disown
    for _ in $(seq 1 10); do [ -n "$(watchdog_pid || true)" ] && break; sleep 1; done
  fi
  if [ -n "$(watchdog_pid || true)" ]; then
    echo "watchdog: UP (pid $(watchdog_pid))"
  else
    die "watchdog did not start"
  fi
}

down() {
  say "Stopping the rehearsal"
  local p
  for p in $(watchdog_pid 2>/dev/null || true); do kill "$p" 2>/dev/null || true; done
  for p in $(tunnel_pids); do kill "$p" 2>/dev/null || true; done
  for p in $(backend_pids); do kill "$p" 2>/dev/null || true; done
  sleep 2
  rm -f "$WATCHDOG_PIDFILE"
  echo "stopped"
}

case "$MODE" in
  up) up ;;
  status) status ;;
  keepalive) keepalive ;;
  down) down ;;
  *) sed -n '2,24p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 2 ;;
esac
