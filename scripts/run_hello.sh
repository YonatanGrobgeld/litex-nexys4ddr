#!/usr/bin/env bash

# Script to upload and run hello_measure program via serial boot

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BINARY="$PROJECT_ROOT/sw/hello_measure/build/hello_measure.bin"

if [[ ! -f "$BINARY" ]]; then
    echo "Error: Binary not found at $BINARY"
    echo "Run: bash scripts/build_sw_hello.sh"
    exit 1
fi

# Determine port
PORT="${1:-/dev/ttyS0}"

echo "=== LiteX hello_measure Serial Boot ==="
echo "Binary: $BINARY"
echo "Port: $PORT"
echo "Speed: 115200"
echo ""
echo "Expected output:"
echo "  hello"
echo "  cycles: <number>"
echo ""

# Auto-locate venv in home directory (VirtualBox shared folders don't support symlinks)
if [[ "$PROJECT_ROOT" == /media/* ]]; then
  HOME_PROJECT="/home/yonatang/Final_Project/litex-nexys4ddr"
  VENV_PATH="$HOME_PROJECT/.venv"
else
  VENV_PATH="$PROJECT_ROOT/.venv"
fi

# Activate virtualenv if not already active
if [[ ! "$VIRTUAL_ENV" == "$VENV_PATH" ]]; then
    if [[ -f "$VENV_PATH/bin/activate" ]]; then
      source "$VENV_PATH/bin/activate"
    else
      echo "Warning: venv not found at $VENV_PATH"
    fi
fi

# Run litex_term with serial boot
python -m litex.tools.litex_term "$PORT" --speed 115200 --kernel "$BINARY" --serial-boot
