#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"

RUN_SETUP=0
INSTALL_TYPE="minimal"
RUN_SMOKE=0
HEALTH_ONLY=0
RUN_GUI=1
STRICT_HEALTH=0

usage() {
  cat <<'EOF'
AI Data Pipeline Launcher

Usage:
  ./run_pipeline.sh [options]

Options:
  --setup [minimal|full]   Install dependencies before running checks
  --smoke                  Run synthetic smoke flow during health checks
  --health-only            Run health checks and exit
  --strict                 Fail if credentials/dependencies are missing
  --no-gui                 Do not launch GUI after checks
  --python PATH            Python executable to use
  -h, --help               Show this help text

Examples:
  ./run_pipeline.sh --setup full --smoke
  ./run_pipeline.sh --setup full --smoke --strict
  ./run_pipeline.sh --health-only --smoke
  PYTHON_BIN=python3.12 ./run_pipeline.sh --setup minimal
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --setup)
      RUN_SETUP=1
      if [[ $# -gt 1 && "$2" != --* ]]; then
        INSTALL_TYPE="$2"
        shift
      fi
      ;;
    --smoke)
      RUN_SMOKE=1
      ;;
    --health-only)
      HEALTH_ONLY=1
      RUN_GUI=0
      ;;
    --strict)
      STRICT_HEALTH=1
      ;;
    --no-gui)
      RUN_GUI=0
      ;;
    --python)
      if [[ $# -lt 2 ]]; then
        echo "--python requires a value" >&2
        exit 2
      fi
      PYTHON_BIN="$2"
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage
      exit 2
      ;;
  esac
  shift
done

if [[ "$INSTALL_TYPE" != "minimal" && "$INSTALL_TYPE" != "full" ]]; then
  echo "Invalid install type: $INSTALL_TYPE (must be minimal or full)" >&2
  exit 2
fi

echo "[INFO] Using Python: $PYTHON_BIN"

if [[ -f "$PROJECT_ROOT/.env" ]]; then
  echo "[INFO] Loading environment from $PROJECT_ROOT/.env"
  while IFS= read -r raw_line || [[ -n "$raw_line" ]]; do
    line="${raw_line%$'\r'}"
    [[ -z "$line" || "$line" =~ ^[[:space:]]*# ]] && continue
    if [[ "$line" =~ ^[[:space:]]*([A-Za-z_][A-Za-z0-9_]*)=(.*)$ ]]; then
      key="${BASH_REMATCH[1]}"
      value="${BASH_REMATCH[2]}"
      value="${value#\"}"
      value="${value%\"}"
      if [[ -z "${!key+x}" ]]; then
        export "$key=$value"
      fi
    fi
  done < "$PROJECT_ROOT/.env"
fi

if [[ $RUN_SETUP -eq 1 ]]; then
  echo "[INFO] Running setup (--install-type $INSTALL_TYPE)"
  "$PYTHON_BIN" "$SCRIPT_DIR/setup.py" --install-type "$INSTALL_TYPE" --yes
fi

echo "[INFO] Running operational health checks"
HEALTH_ARGS=(--init-folders)
if [[ $RUN_SMOKE -eq 1 ]]; then
  HEALTH_ARGS+=(--smoke)
fi
if [[ $STRICT_HEALTH -eq 1 ]]; then
  HEALTH_ARGS+=(--strict)
fi
"$PYTHON_BIN" "$SCRIPT_DIR/operational_health_check.py" "${HEALTH_ARGS[@]}"

if [[ $HEALTH_ONLY -eq 1 || $RUN_GUI -eq 0 ]]; then
  echo "[INFO] Done"
  exit 0
fi

echo "[INFO] Launching unified pipeline GUI"
"$PYTHON_BIN" "$SCRIPT_DIR/unified_pipeline_gui.py"
