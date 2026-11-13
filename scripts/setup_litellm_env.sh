#!/usr/bin/env bash
# Create or update the conda env for the LiteLLM gateway. Safe to re-run; never prompts.
set -euo pipefail
cd "$(dirname "$0")/.."
# shellcheck disable=SC1091
source configs/litellm.env
command -v conda >/dev/null || { echo "conda not found on PATH"; exit 1; }
conda env update -n "$LITELLM_CONDA_ENV" -f configs/litellm-env.yml
conda run -n "$LITELLM_CONDA_ENV" litellm --version
echo "Record the litellm version in STATUS.md."
