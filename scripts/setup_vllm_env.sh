#!/usr/bin/env bash
# Create the separate vLLM environment (it must not share the app's uv.lock).
set -euo pipefail
cd "$(dirname "$0")/.."
command -v nvidia-smi >/dev/null || { echo "nvidia-smi not found: NVIDIA driver required"; exit 1; }
nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv
uv venv .venv-vllm --python 3.12
uv pip install --python .venv-vllm/bin/python vllm
.venv-vllm/bin/python -c "import vllm; print('vllm', vllm.__version__)"
echo "Record the vllm version in STATUS.md. First serve downloads ~5.3 GiB of weights."
