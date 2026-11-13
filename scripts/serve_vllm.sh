#!/usr/bin/env bash
# Start vLLM on localhost. The app talks to LiteLLM, never to this port directly.
set -euo pipefail
cd "$(dirname "$0")/.."
# shellcheck disable=SC1091
source configs/vllm.env
command -v conda >/dev/null || { echo "conda not found on PATH"; exit 1; }
conda run -n "$CONDA_ENV" python -c "import vllm" 2>/dev/null \
  || { echo "vLLM is not installed in conda env '$CONDA_ENV'. Run: bash scripts/setup_vllm_env.sh"; exit 1; }
ARGS=(--served-model-name "$SERVED_NAME"
      --quantization "$QUANTIZATION"
      --max-model-len "$MAX_MODEL_LEN"
      --gpu-memory-utilization "$GPU_MEMORY_UTILIZATION"
      --host "$HOST" --port "$PORT")
[ "${ENFORCE_EAGER:-1}" = "1" ] && ARGS+=(--enforce-eager)
exec conda run --no-capture-output -n "$CONDA_ENV" vllm serve "$MODEL" "${ARGS[@]}"
