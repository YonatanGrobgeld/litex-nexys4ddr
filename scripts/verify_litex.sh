#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)

if [[ ! -f "$REPO_ROOT/.venv/bin/activate" ]]; then
  echo "Error: .venv not found. Run scripts/setup_litex.sh first." >&2
  exit 1
fi

source "$REPO_ROOT/.venv/bin/activate"

python -V
python -m pip show migen litex
python -c "import migen, litex; print('OK', migen.__file__, litex.__file__)"
