#!/usr/bin/env bash
# P4a test gate: vLLM answers a chat request; records peak VRAM during inference.
# Start serve_vllm.sh first. For the real number, also load the BGE embedder on
# the GPU (e.g. run a `minal-admin search`) before running this.
set -euo pipefail
cd "$(dirname "$0")/.."
# shellcheck disable=SC1091
source configs/vllm.env
URL="http://$HOST:$PORT"
TOTAL=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits | head -1)

echo "== models =="
curl -fsS "$URL/v1/models" | head -c 400; echo

peak=0
sample() { nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | head -1; }
( while true; do sample >> /tmp/vllm_vram.log; sleep 0.5; done ) &
SAMPLER=$!
: > /tmp/vllm_vram.log
trap 'kill $SAMPLER 2>/dev/null || true' EXIT

echo "== chat (3 back-to-back requests) =="
for q in "Who are you? Answer in one sentence." \
         "List three things a college ambassador can help a visitor with." \
         "Say hello in Manipuri-friendly simple English, one line."; do
  curl -fsS "$URL/v1/chat/completions" -H 'Content-Type: application/json' \
    -d "{\"model\":\"$SERVED_NAME\",\"max_tokens\":120,\"messages\":[{\"role\":\"user\",\"content\":\"$q\"}]}" \
  | python3 -c 'import sys,json; r=json.load(sys.stdin); print(r["choices"][0]["message"]["content"].strip()); print("  usage:", r["usage"])'
done

kill $SAMPLER 2>/dev/null || true
peak=$(sort -n /tmp/vllm_vram.log | tail -1)
echo "== VRAM =="
echo "peak: ${peak} MiB of ${TOTAL} MiB; headroom: $((TOTAL - peak)) MiB"
echo "Paste the above into STATUS.md (P4a evidence)."
