#!/usr/bin/env bash
# Start the LiteLLM gateway on localhost:4000 in front of vLLM.
set -euo pipefail
cd "$(dirname "$0")/.."
# shellcheck disable=SC1091
source configs/litellm.env
command -v conda >/dev/null || { echo "conda not found on PATH"; exit 1; }

# Secret lives in configs/litellm.local.env (gitignored). Created on first run.
KEYFILE=configs/litellm.local.env
if [ ! -f "$KEYFILE" ]; then
  echo "LITELLM_MASTER_KEY=sk-minal-$(python3 -c 'import secrets; print(secrets.token_hex(24))')" > "$KEYFILE"
  chmod 600 "$KEYFILE"
  echo "Created $KEYFILE with a new master key."
fi
# shellcheck disable=SC1090
source "$KEYFILE"; export LITELLM_MASTER_KEY

# Some distros ship without legacy zone names (e.g. Asia/Calcutta); LiteLLM's scheduler
# then crashes at startup with a tzlocal error. Drop a TZ the system cannot resolve.
if [ -n "${TZ:-}" ] && [ ! -e "/usr/share/zoneinfo/$TZ" ]; then
  echo "TZ=$TZ not found in /usr/share/zoneinfo; ignoring it for the gateway."
  unset TZ
fi

conda run -n "$LITELLM_CONDA_ENV" litellm --version >/dev/null 2>&1 \
  || { echo "LiteLLM is not installed in conda env '$LITELLM_CONDA_ENV'. Run: bash scripts/setup_litellm_env.sh"; exit 1; }
exec conda run --no-capture-output -n "$LITELLM_CONDA_ENV" \
  litellm --config configs/litellm.yaml --host "$LITELLM_HOST" --port "$LITELLM_PORT"
