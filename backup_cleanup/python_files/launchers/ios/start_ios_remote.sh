#!/usr/bin/env bash
# Starts the iOS remote. Extra arguments go to ios_remote_server.py (e.g. --host 192.168.1.20).
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PY="$HERE/venv/bin/python"
[[ -x "$PY" ]] || PY=python3
exec "$PY" "$HERE/ios_remote_server.py" "$@"
