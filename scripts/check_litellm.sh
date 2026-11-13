#!/usr/bin/env bash
# P4b test gate. Needs vLLM (serve_vllm.sh) and the gateway (serve_litellm.sh) running.
# Checks: no key -> rejected, wrong key -> rejected, right key -> answer.
set -euo pipefail
cd "$(dirname "$0")/.."
# shellcheck disable=SC1091
source configs/litellm.env
# shellcheck disable=SC1091
source configs/litellm.local.env
URL="http://$LITELLM_HOST:$LITELLM_PORT"
BODY='{"model":"minal-llm","max_tokens":60,"messages":[{"role":"user","content":"Say hello in one short sentence."}]}'
fail=0

code() { curl -s -o /dev/null -w '%{http_code}' "$URL/v1/chat/completions" -H 'Content-Type: application/json' "$@" -d "$BODY"; }

echo "== waiting for gateway (up to 2 min) =="
for i in $(seq 1 24); do
  curl -s -o /dev/null "$URL/health/liveliness" && break
  [ "$i" = 24 ] && { echo "Gateway not reachable at $URL. Is scripts/serve_litellm.sh running?"; exit 1; }
  sleep 5
done

# Without a database LiteLLM answers an unknown key with 400 ("No connected db"), a known
# bad key or missing key with 401. Any of 400/401/403 means the request was rejected.
rejected() { case "$1" in 400|401|403) return 0;; *) return 1;; esac; }
echo "== no key (expect rejection: 400/401/403) =="
c=$(code); echo "$c"; rejected "$c" || fail=1
echo "== wrong key (expect rejection: 400/401/403) =="
c=$(code -H 'Authorization: Bearer sk-wrong'); echo "$c"; rejected "$c" || fail=1
echo "== right key (expect an answer) =="
out=$(curl -s -w '\n%{http_code}' "$URL/v1/chat/completions" -H 'Content-Type: application/json' \
      -H "Authorization: Bearer $LITELLM_MASTER_KEY" -d "$BODY")
c=${out##*$'\n'}; body=${out%$'\n'*}
echo "$c"; [ "$c" = 200 ] || { fail=1; echo "$body"; }
echo "$body" | python3 -c 'import sys,json; r=json.load(sys.stdin); print(r["choices"][0]["message"]["content"].strip()); print("model:", r.get("model"))' || fail=1

[ "$fail" = 0 ] && echo "P4b GATE: PASS" || { echo "P4b GATE: FAIL"; exit 1; }
