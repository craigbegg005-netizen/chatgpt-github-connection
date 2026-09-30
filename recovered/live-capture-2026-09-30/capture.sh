#!/usr/bin/env bash
# Read-only capture of every known live Begg/Oddfellow surface.
set -u
OUT=/root/workspace/capture/out
mkdir -p "$OUT"
UA="Mozilla/5.0 (compatible; Oddfellow-recovery/1.0)"
svc() {
  name="$1"; base="$2"; shift 2
  d="$OUT/$name"; mkdir -p "$d"
  for p in "$@"; do
    fn=$(echo "$p" | tr '/?&=' '____'); [ -z "$fn" ] && fn="root"
    code=$(curl -s -A "$UA" -L --max-time 25 -o "$d/$fn" -w "%{http_code}" "$base$p" 2>/dev/null || echo 000)
    sz=$(stat -c%s "$d/$fn" 2>/dev/null || echo 0)
    printf "%-34s %-16s %s %sB\n" "$name" "$p" "$code" "$sz"
  done
}
svc oddfellow-letta-poc        https://oddfellow-letta-poc.onrender.com        / /healthz /openapi.json /docs /api/letta/status
svc oddfellow-letta-ui-v020    https://oddfellow-letta-ui-v020.onrender.com    / /manifest.json /sw.js /icons/icon-192.png
svc oddfellow-synthetic-v020   https://oddfellow-synthetic-v020.onrender.com   / /manifest.json /sw.js
svc oddfellow-personal-v019b   https://oddfellow-personal-v019b.onrender.com   / /health /ready /openapi.json
svc oddfellow-staging-v017b    https://oddfellow-personal-staging-v017b.onrender.com / /health /ready /openapi.json /setup
svc oddfellow-personal-secure  https://oddfellow-personal-secure.onrender.com  / /openapi.json /health /ready
svc begg-ai-industries-v013    https://begg-ai-industries-v013.onrender.com    / /openapi.json /health /ready
svc begg-ai-core-v010          https://begg-ai-core-v010.onrender.com          / /openapi.json /health /ready
svc begg-ai-command-center     https://begg-ai-command-center.craigbegg005.chatgpt.site /
svc peace-framework            https://peace-human-security-framework.floot.app /
