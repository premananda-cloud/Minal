#!/usr/bin/env bash
# Start vLLM on localhost. The app talks to LiteLLM, never to this port directly.
set -euo pipefail
cd "$(dirname "$0")/.."
# shellcheck disable=SC1091
source configs/vllm.env
ARGS=(--served-model-name "$SERVED_NAME"
      --quantization "$QUANTIZATION"
      --max-model-len "$MAX_MODEL_LEN"
      --gpu-memory-utilization "$GPU_MEMORY_UTILIZATION"
      --host "$HOST" --port "$PORT")
[ "${ENFORCE_EAGER:-1}" = "1" ] && ARGS+=(--enforce-eager)
exec .venv-vllm/bin/vllm serve "$MODEL" "${ARGS[@]}"
