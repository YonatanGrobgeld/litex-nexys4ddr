#!/usr/bin/env bash
set -euo pipefail

# Build script for consolidated project in shared folder
# Automatically locates venv in home directory

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_DIR="$SCRIPT_DIR/build"

echo "=== LiteX Build ==="
echo "Project: $SCRIPT_DIR"
echo "Build output: $BUILD_DIR"
echo ""

# Auto-detect venv location in home directory
# VirtualBox shared folders don't support symlinks, so venv must be in home dir
VENV_PATH=""
HOME_PROJECT=""

# Check if running from shared folder
if [[ "$SCRIPT_DIR" == /media/* ]]; then
  # Map /media path to home directory equivalent
  # /media/sf_Final_Project -> /home/yonatang/Final_Project
  HOME_PROJECT="/home/yonatang/Final_Project/litex-nexys4ddr"
  VENV_PATH="$HOME_PROJECT/.venv"
else
  # Running from home directory directly
  HOME_PROJECT="$SCRIPT_DIR"
  VENV_PATH="$SCRIPT_DIR/.venv"
fi

if [[ ! -f "$VENV_PATH/bin/activate" ]]; then
  echo "Error: Virtual environment not found at $VENV_PATH"
  echo ""
  echo "NOTE: VirtualBox shared folders don't support Python symlinks."
  echo "The venv must be located in: $VENV_PATH"
  echo ""
  echo "To install venv:"
  echo "  cd $HOME_PROJECT"
  echo "  python3 -m venv .venv"
  echo "  source .venv/bin/activate"
  echo "  pip install -e $SCRIPT_DIR/third_party/litex"
  exit 1
fi

echo "Using venv: $VENV_PATH"
source "$VENV_PATH/bin/activate"

# Set PYTHONPATH for LiteX and all sub-modules
# The monorepo structure: third_party/litex/{litex,litex-boards,litedram,etc}
if [[ "$SCRIPT_DIR" == /media/* ]]; then
  LITEX_BASE="$SCRIPT_DIR/third_party/litex"
else
  LITEX_BASE="$HOME_PROJECT/third_party/litex"
fi

PYTHONPATHS=(
  "$LITEX_BASE/litex"                    # LiteX core
  "$LITEX_BASE/litex-boards"             # litex_boards
  "$LITEX_BASE/litedram"                 # litedram
  "$LITEX_BASE/liteeth"                  # liteeth
  "$LITEX_BASE/litei2c"                  # litei2c
  "$LITEX_BASE/litesdcard"               # litesdcard
  "$LITEX_BASE/litesata"                 # litesata
  "$LITEX_BASE/litespi"                  # litespi
  "$LITEX_BASE/migen"                    # migen
  "$LITEX_BASE/pythondata-cpu-vexriscv"  # VexRiscv CPU
  "$LITEX_BASE/pythondata-software-picolibc"  # picolibc
  "$LITEX_BASE/pythondata-software-compiler_rt"  # compiler_rt
)

# Build colon-separated PYTHONPATH
export PYTHONPATH=$(IFS=:; echo "${PYTHONPATHS[*]}")

echo "Using LiteX from: $LITEX_BASE"
echo ""

# Build with software (BIOS) but no gateware synthesis
python "$SCRIPT_DIR/hw/build_soc.py" \
  --output-dir "$BUILD_DIR" \
  --no-compile-gateware

echo ""
echo "=== Build Complete ==="
echo "Build directory: $BUILD_DIR"
echo "Gateware files (for Vivado):"
ls -lh "$BUILD_DIR/gateware"/*.{v,xdc,tcl} 2>/dev/null || true
echo ""
echo "BIOS with Vivado on Windows:"
echo "  cd \"\\vboxsrv\sf_Final_Project\litex-nexys4ddr\build\gateware\""
echo "  vivado -mode batch -source digilent_nexys4ddr.tcl"
