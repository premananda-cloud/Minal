#!/usr/bin/env bash
# Create or update the separate conda env for vLLM. Safe to re-run; never prompts.
set -euo pipefail
cd "$(dirname "$0")/.."
# shellcheck disable=SC1091
source configs/vllm.env
command -v conda >/dev/null || { echo "conda not found on PATH"; exit 1; }
command -v nvidia-smi >/dev/null || { echo "nvidia-smi not found: NVIDIA driver required"; exit 1; }
nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv
conda env update -n "$CONDA_ENV" -f configs/vllm-env.yml
conda run -n "$CONDA_ENV" python -c "import vllm; print('vllm', vllm.__version__)"
echo "Record the vllm version in STATUS.md. First serve downloads ~5.3 GiB of weights."
