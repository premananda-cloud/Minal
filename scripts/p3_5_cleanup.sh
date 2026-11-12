#!/usr/bin/env bash
# P3.5 repo cleanup. Run from the project root. Commit first so you can undo.
set -euo pipefail

echo "== Stray folders and redundant files =="
rm -rfv zip src/minal/vectorstore requirements.txt

echo "== _legacy (placeholder only?) =="
find src/minal/_legacy -type f ! -path '*__pycache__*' -print
echo "If only __init__.py is listed above, remove it:  rm -rf src/minal/_legacy"

echo "== References to remove by hand =="
grep -rIn --exclude-dir=.git --exclude-dir=__pycache__ --exclude=uv.lock \
  -i -E "opencv|ollama|requirements\.txt|_legacy|minal\.vectorstore" . || echo "none"

echo "== pytest config =="
grep -n "asyncio" pyproject.toml || echo "Add: asyncio_default_fixture_loop_scope = \"function\" under [tool.pytest.ini_options]"

echo "== Gate =="
echo "Run:  uv sync && uv run pytest   (expect 145 passed)"
