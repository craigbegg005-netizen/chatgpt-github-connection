#!/usr/bin/env bash
#
# Deploy the Oddfellow backend to Cloudflare Workers, set its secrets, and prove
# it works — in one command.
#
#   ./deploy.sh verify              local only, no Cloudflare account needed
#   ./deploy.sh deploy              deploy, set secrets, then verify the live URL
#
# Secrets are read from the environment, never from arguments, so they do not end
# up in shell history or a process listing:
#
#   LETTA_API_KEY=... ODDFELLOW_OWNER_TOKEN=... ./deploy.sh deploy
#
# Exit codes: 0 = every gate passed, 1 = something failed, 2 = misuse.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HARNESS="$HERE/../acceptance_check.py"
MODE="${1:-}"

# PID of the local dev server. Deliberately NOT a function-local: the cleanup
# trap below is installed for EXIT as well as RETURN, and on the EXIT path the
# function that assigned it has already returned, so a `local pid` is out of
# scope. Under `set -u` that made a completely successful run finish with
# "./deploy.sh: line 50: pid: unbound variable" — an error printed after
# "RESULT: all checks passed", which reads like the run failed when it had not.
pid=""

say()  { printf '\n\033[1m%s\033[0m\n' "$*"; }
die()  { printf '\nERROR: %s\n' "$*" >&2; exit 1; }

[ -n "$MODE" ] || { sed -n '2,16p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 2; }
[ "$MODE" = verify ] || [ "$MODE" = deploy ] || die "unknown mode '$MODE' (expected verify or deploy)"

command -v node >/dev/null || die "node is required"
command -v python3 >/dev/null || die "python3 is required"
[ -f "$HARNESS" ] || die "acceptance harness not found at $HARNESS"

# --------------------------------------------------------------------------- #
# Local verification: start wrangler dev, run the real harness against it.
# --------------------------------------------------------------------------- #
verify_local() {
  say "Starting a local Worker"
  [ -f "$HERE/.dev.vars" ] || die ".dev.vars is missing. Create it with:
  LETTA_API_KEY=<a key, invalid is fine for a smoke test>
  ODDFELLOW_OWNER_TOKEN=<any value>"

  local port=8799 log
  log="$(mktemp)"
  # setsid puts the dev server in its own process group, so the whole tree
  # (npx -> sh -> node) can be killed as one. Killing only the wrapper leaves the
  # node child running and holding the port — which is what happened the first
  # time this was tested, twice.
  ( cd "$HERE" && exec setsid npx --yes wrangler@latest dev --port "$port" --ip 127.0.0.1 >"$log" 2>&1 ) &
  pid=$!
  # Kill on ANY exit path, including SIGTERM from an outer `timeout`.
  # shellcheck disable=SC2064
  cleanup() {
    [ -n "${pid:-}" ] || return 0
    kill -- -"$pid" 2>/dev/null || kill "$pid" 2>/dev/null || true
    # The kill above can miss entirely, and this is the third time it has.
    #
    # `pid` is the PID of the SUBSHELL, but `setsid` puts the real tree
    # (npx -> node -> workerd) into a NEW session with a different process-group
    # id -- so `kill -- -$pid` targets a group that no longer contains it, and
    # `workerd` keeps holding the port. The comment above used to claim this was
    # handled; it was not, and the evidence was a live listener on 8799 after the
    # script had already exited.
    #
    # So: verify rather than assume. Whatever is still listening on the port we
    # chose gets killed, which is correct regardless of how the process tree is
    # shaped.
    local holder i
    for i in 1 2 3 4 5; do
      # ${port:-} not $port: this runs from an EXIT trap, by which point the
      # function's `local port` is gone and `set -u` would abort the cleanup --
      # turning a fix for a leaked port into a crash during cleanup.
      holder="$(ss -ltnp 2>/dev/null | awk -v p=":${port:-}" '$4 ~ p' \
                | grep -o 'pid=[0-9]*' | cut -d= -f2 | head -1)"
      [ -n "$holder" ] || break
      kill "$holder" 2>/dev/null || true
      sleep 1
    done
    wait "$pid" 2>/dev/null || true
    pid=""
  }
  trap cleanup RETURN EXIT INT TERM

  say "Waiting for it to answer /livez"
  local i
  for i in $(seq 1 60); do
    if curl -fsS --max-time 3 "http://127.0.0.1:$port/livez" >/dev/null 2>&1; then break; fi
    sleep 2
  done
  curl -fsS --max-time 5 "http://127.0.0.1:$port/livez" >/dev/null 2>&1 \
    || { tail -30 "$log"; die "the Worker never answered on 127.0.0.1:$port"; }

  say "Running the acceptance harness against the local Worker"
  echo "Note: gate 1 needs a WORKING Letta key. If .dev.vars holds a placeholder,"
  echo "gate 1 is expected to fail -- and it must fail by reporting the real 401"
  echo "from api.letta.com, never by inventing a reply."
  local token
  token="$(grep -m1 '^ODDFELLOW_OWNER_TOKEN=' "$HERE/.dev.vars" | cut -d= -f2-)"
  python3 "$HARNESS" "http://127.0.0.1:$port" --owner-token "$token"
}

# --------------------------------------------------------------------------- #
# Remote deploy.
# --------------------------------------------------------------------------- #
deploy_remote() {
  [ -n "${LETTA_API_KEY:-}" ] || die "LETTA_API_KEY is not set in the environment"
  [ -n "${ODDFELLOW_OWNER_TOKEN:-}" ] || die "ODDFELLOW_OWNER_TOKEN is not set in the environment"

  # Credentials, checked here so a missing token fails with a sentence rather
  # than a wrangler stack trace. Either an API token or an existing `wrangler
  # login` session works; wrangler picks up the token from the environment on its
  # own, so this is a precondition check and not a hand-off of the value.
  if [ -z "${CLOUDFLARE_API_TOKEN:-}" ] && [ ! -f "$HOME/.config/.wrangler/config/default.toml" ]; then
    die "No Cloudflare credential. Set CLOUDFLARE_API_TOKEN, or run 'npx wrangler login' once.
  A token needs, at minimum, the 'Workers Scripts: Edit' permission for the target account."
  fi

  # wrangler.toml deliberately carries no account_id. That works when the token
  # sees exactly one account, and fails with a clear wrangler error when it sees
  # more than one -- so name the fix here instead of letting it surprise someone
  # at the end of a deploy.
  if [ -z "${CLOUDFLARE_ACCOUNT_ID:-}" ]; then
    say "CLOUDFLARE_ACCOUNT_ID is not set; wrangler will infer it. If the token can see more than one account, set it (Cloudflare dashboard -> account -> Account ID) and re-run."
  fi

  say "Deploying to Cloudflare Workers"
  ( cd "$HERE" && npx --yes wrangler@latest deploy ) | tee /tmp/oddfellow-deploy.log

  # wrangler prints the deployed URL; take the last https://*.workers.dev it saw.
  local url
  url="$(grep -oE 'https://[a-z0-9.-]+\.workers\.dev' /tmp/oddfellow-deploy.log | tail -1 || true)"
  [ -n "$url" ] || die "could not read the deployed URL from the deploy output"

  say "Setting secrets on $url"
  # --stdin so the value never appears in argv or a process listing.
  printf '%s' "$LETTA_API_KEY"          | ( cd "$HERE" && npx --yes wrangler@latest secret put LETTA_API_KEY )
  printf '%s' "$ODDFELLOW_OWNER_TOKEN"  | ( cd "$HERE" && npx --yes wrangler@latest secret put ODDFELLOW_OWNER_TOKEN )

  say "Waiting for the new revision to answer"
  local i
  for i in $(seq 1 30); do
    if curl -fsS --max-time 5 "$url/livez" >/dev/null 2>&1; then break; fi
    sleep 2
  done

  say "Liveness and readiness"
  curl -fsS --max-time 10 "$url/livez"   || true; echo
  curl -fsS --max-time 10 "$url/healthz" || true; echo

  say "Running the acceptance harness against $url"
  python3 "$HARNESS" "$url" --owner-token "$ODDFELLOW_OWNER_TOKEN"

  say "DONE — phone URL"
  echo "$url"
}

case "$MODE" in
  verify) verify_local ;;
  deploy) deploy_remote ;;
esac
