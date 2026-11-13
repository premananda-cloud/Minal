#!/usr/bin/env bash
# P4a test gate: vLLM answers chat requests; records peak VRAM during inference.
# Start serve_vllm.sh first and wait for "Application startup complete".
# For the real number, also load the BGE embedder on the GPU before running this.
set -euo pipefail
cd "$(dirname "$0")/.."
# shellcheck disable=SC1091
source configs/vllm.env
URL="http://$HOST:$PORT"
TOTAL=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits | head -1)

echo "== waiting for server (up to 5 min) =="
for i in $(seq 1 60); do
  curl -fsS "$URL/v1/models" >/dev/null 2>&1 && break
  [ "$i" = 60 ] && { echo "Server not reachable at $URL. Is scripts/serve_vllm.sh running? Check its terminal for errors."; exit 1; }
  sleep 5
done
echo "== models =="
curl -fsS "$URL/v1/models" | head -c 400; echo

LOG=$(mktemp)
( while true; do nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | head -1 >> "$LOG"; sleep 0.5; done ) &
SAMPLER=$!
trap 'kill $SAMPLER 2>/dev/null || true; rm -f "$LOG"' EXIT

echo "== chat (3 back-to-back requests) =="
for q in "Who are you? Answer in one sentence." \
         "List three things a college ambassador can help a visitor with." \
         "Explain what a semester credit is, in two sentences."; do
  curl -fsS "$URL/v1/chat/completions" -H 'Content-Type: application/json' \
    -d "{\"model\":\"$SERVED_NAME\",\"max_tokens\":120,\"messages\":[{\"role\":\"user\",\"content\":\"$q\"}]}" \
  | python3 -c 'import sys,json; r=json.load(sys.stdin); print(r["choices"][0]["message"]["content"].strip()); print("  usage:", r["usage"])'
done

kill $SAMPLER 2>/dev/null || true
peak=$(sort -n "$LOG" | tail -1)
echo "== VRAM =="
echo "peak: ${peak} MiB of ${TOTAL} MiB; headroom: $((TOTAL - peak)) MiB"
echo "Paste the above into STATUS.md (P4a evidence)."
