#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY_BIN_DEFAULT="$SCRIPT_DIR/venv/bin/python"
PYTHON_BIN="${PYTHON_BIN:-$PY_BIN_DEFAULT}"

MODE="launch"
if [[ "${1:-}" == "--check-only" ]]; then
  MODE="check"
fi

echo "[GO-LIVE] Python: $PYTHON_BIN"
echo "[GO-LIVE] Running strict production gate"
PYTHON_BIN="$PYTHON_BIN" "$SCRIPT_DIR/run_pipeline.sh" --health-only --smoke --strict

if [[ "$MODE" == "check" ]]; then
  echo "[GO-LIVE] Strict checks passed (check-only mode)."
  exit 0
fi

echo "[GO-LIVE] Launching production GUI"
PYTHON_BIN="$PYTHON_BIN" "$SCRIPT_DIR/run_pipeline.sh"
