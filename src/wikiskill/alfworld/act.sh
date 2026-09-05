#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
PYTHON="${ALFWORLD_PYTHON:-$(command -v python3)}"
if [[ ! -x "$PYTHON" ]]; then
  echo "ALFWorld python missing: $PYTHON" >&2
  exit 2
fi
if [[ $# -eq 0 ]]; then
  exec "$PYTHON" "$ROOT/step.py" --root "$ROOT" --reset
fi
exec "$PYTHON" "$ROOT/step.py" --root "$ROOT" --action "$*"
