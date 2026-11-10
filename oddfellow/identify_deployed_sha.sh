#!/usr/bin/env bash
#
# Identify which commit the live service is actually serving.
#
#   ./identify_deployed_sha.sh [base-url]
#
# Why this exists
# ---------------
# "Which build is actually live?" has been the most expensive question in this
# project. The coordination status carried it as **NOT VERIFIABLE — no build
# endpoint** with a lower bound of 7c33404, because it assumed the answer needs a
# build endpoint from the host. It does not: the front end is static, so the
# served bytes are content-addressable and can be matched against the repo.
#
# On 2026-11-10 that identified the live build as b1bf3c4 (2026-10-01) by two
# independent files agreeing at the same revision.
#
# It reports the *served assets* revision. If the front end and backend were ever
# built separately they could differ, so the honest reading is "the deploy is at
# least this revision".
#
# Exit: 0 = identified, 1 = not identified (never guesses).
set -uo pipefail

BASE="${1:-https://oddfellow-letta-backend-v0206.onrender.com}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/.." && pwd)"

say() { printf '%s\n' "$*"; }
die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

cd "$REPO" || die "cannot cd to $REPO"

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

# Fetch the static files the service serves. Both are committed, so a match is
# meaningful; a generated file would not be.
files=(index.html command.html)
declare -A want
for f in "${files[@]}"; do
  code="$(curl -s -L -m 60 -o "$tmp/$f" -w '%{http_code}' "$BASE/$f" 2>/dev/null)"
  [ "$code" = "200" ] || die "$BASE/$f returned HTTP $code -- cannot identify a build from a missing file"
  want[$f]="$(sha256sum "$tmp/$f" | cut -d' ' -f1)"
  say "served  $f  ${want[$f]}"
done

# Walk the history of the first file and require EVERY file to match at the same
# revision. One file matching is weak -- a file that has not changed in months
# matches many commits. Two agreeing is the evidence.
say ""
say "searching history for a revision where all of these match..."
checked=0
for rev in $(git log --format=%H -400 -- "oddfellow/frontend/${files[0]}"); do
  checked=$((checked + 1))
  ok=1
  for f in "${files[@]}"; do
    got="$(git show "$rev:oddfellow/frontend/$f" 2>/dev/null | sha256sum | cut -d' ' -f1)"
    [ "$got" = "${want[$f]}" ] || { ok=0; break; }
  done
  if [ "$ok" = "1" ]; then
    say ""
    say "IDENTIFIED: $rev"
    git log -1 --format='  %h  %ad  %s' --date=iso "$rev"
    say ""
    say "Read this as 'the deploy is at least this revision' -- it identifies the served"
    say "assets, not the backend source."
    exit 0
  fi
done

say ""
say "NOT IDENTIFIED after checking $checked revisions of oddfellow/frontend/${files[0]}."
say "The served assets do not match any revision in this checkout. That is a real"
say "finding, not a failure to try harder: either the deploy predates this history, or"
say "the served files were modified outside the repo. Do not record a guess."
exit 1
