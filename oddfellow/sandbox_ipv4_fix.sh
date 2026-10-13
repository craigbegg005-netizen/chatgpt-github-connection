#!/usr/bin/env bash
#
# Make IPv4-only name resolution durable across sandbox resets.
#
#   ./sandbox_ipv4_fix.sh apply                     system interpreter + gai.conf
#   ./sandbox_ipv4_fix.sh apply --for-python BIN    that interpreter's site-packages
#   ./sandbox_ipv4_fix.sh verify [BIN]              assert IPv4-only resolution
#
# Why this is a script and not a note
# -----------------------------------
# This fix has been re-derived by hand at least three times (2026-10-09, and
# again after each sandbox reset), because it lived only in sandbox state --
# /etc/gai.conf and a .pth file in site-packages -- and sandbox state does not
# survive. The failure it prevents is expensive and confusing: a harness that
# fails with `Errno 97` on one run and a DNS error on the next, both of which
# clear on retry, which is exactly the shape that gets written off as flakiness.
#
# Two mechanisms, both needed, and they are not redundant:
#   * /etc/gai.conf orders IPv4 first. This is what makes `curl` work, because
#     curl does its own resolution and never loads a Python .pth file.
#   * force_ipv4.py removes AF_INET6 from Python's getaddrinfo. Ordering is not
#     prevention -- Python still attempted the IPv6 address and raised instead
#     of falling back, which is why the failing gate moved rather than cleared.
#
# Idempotent: safe to run on every `up`.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODULE_SRC="$HERE/sandbox/force_ipv4.py"
PTH_NAME="zz_force_ipv4.pth"
GAI_CONF="${GAI_CONF:-/etc/gai.conf}"
PRECEDENCE_LINE="precedence ::ffff:0:0/96  100"

say() { printf '%s\n' "$*"; }
warn() { printf 'WARN: %s\n' "$*" >&2; }

# The `.pth` is what makes the module load. A venv sitecustomize.py is shadowed
# by the system one (Ubuntu's apport hook), so it never runs; a .pth is
# processed regardless of that.
install_into() {
  local dir="$1"
  if [ ! -d "$dir" ]; then
    warn "no such site-packages directory: $dir"
    return 1
  fi
  if ! cp -f "$MODULE_SRC" "$dir/force_ipv4.py" 2>/dev/null; then
    warn "could not write $dir/force_ipv4.py (read-only?)"
    return 1
  fi
  if ! printf 'import force_ipv4\n' >"$dir/$PTH_NAME" 2>/dev/null; then
    warn "could not write $dir/$PTH_NAME"
    return 1
  fi
  say "installed force_ipv4 -> $dir"
  return 0
}

site_packages_of() {
  "$1" -c 'import site; print(site.getsitepackages()[0])' 2>/dev/null
}

apply_gai_conf() {
  # Only append if an *active* (uncommented) precedence rule is not already
  # present. Grepping for the string alone would match the commented examples
  # that ship in the default file, so the check is anchored on a line that does
  # not begin with '#'.
  if grep -qE "^${PRECEDENCE_LINE//\//\\/}[[:space:]]*$" "$GAI_CONF" 2>/dev/null; then
    say "gai.conf already prefers IPv4"
    return 0
  fi
  if ! printf '\n# Added by sandbox_ipv4_fix.sh: this sandbox has no IPv6, and\n# trycloudflare.com publishes AAAA first.\n%s\n' \
      "$PRECEDENCE_LINE" >>"$GAI_CONF" 2>/dev/null; then
    warn "could not append to $GAI_CONF"
    return 1
  fi
  say "gai.conf: added IPv4 precedence"
  return 0
}

verify_with() {
  local bin="$1"
  "$bin" - <<'PY'
import socket
import sys

# Probe with NUMERIC LITERALS, never a hostname.
#
# This check used to resolve trycloudflare.com, which made it depend on live DNS.
# When resolution was slow or failed the check failed too -- and it failed inside
# the full suite while passing in isolation, so it read as a broken patch rather
# than a flaky probe. A literal is parsed, not resolved: no network, no DNS, and
# nothing left to be intermittent about.
#
# Control first. 127.0.0.1 must still resolve to AF_INET. Without this, a probe
# that returned nothing for every input would "pass" the check below.
try:
    control = {r[0] for r in socket.getaddrinfo("127.0.0.1", 443)}
except OSError as exc:
    print("FAIL: control probe itself failed: %r" % (exc,))
    sys.exit(1)
if socket.AF_INET not in control:
    print("FAIL: control probe returned no AF_INET -- the probe is broken, not the patch")
    sys.exit(1)

# ::1 has no IPv4 answer, so a loaded patch removes it entirely and raises.
# An unpatched interpreter returns AF_INET6 here.
try:
    probe = {r[0] for r in socket.getaddrinfo("::1", 443)}
except socket.gaierror:
    probe = set()
if socket.AF_INET6 in probe:
    print("FAIL: AF_INET6 still returned for '::1' -- the .pth did not load")
    sys.exit(1)
print("OK: IPv4-only resolution (AF_INET6 removed, AF_INET intact)")
PY
}

MODE="${1:-}"
shift || true

case "$MODE" in
  apply)
    rc=0
    apply_gai_conf || rc=1
    if [ "$#" -eq 0 ]; then
      dir="$(site_packages_of python3 || true)"
      [ -n "$dir" ] && { install_into "$dir" || rc=1; }
    else
      while [ "$#" -gt 0 ]; do
        case "$1" in
          --for-python)
            shift
            [ "$#" -gt 0 ] || { warn "--for-python needs a path"; rc=1; break; }
            dir="$(site_packages_of "$1" || true)"
            if [ -z "$dir" ]; then
              warn "could not discover site-packages for $1"
              rc=1
            else
              install_into "$dir" || rc=1
            fi
            ;;
          *)
            install_into "$1" || rc=1
            ;;
        esac
        shift
      done
    fi
    exit "$rc"
    ;;
  verify)
    verify_with "${1:-python3}"
    ;;
  *)
    sed -n '2,10p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
    exit 2
    ;;
esac
