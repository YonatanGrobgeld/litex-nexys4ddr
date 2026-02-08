#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
BITSTREAM="$REPO_ROOT/hw/build/gateware/nexys4ddr_vexriscv.bit"

# Shared folder path for Windows Vivado build (VirtualBox shared folder or mounted network path)
# Default: /media/sf_shared (VirtualBox default for "shared" folder)
# Override with: export SHARED_OUT=/path/to/windows/shared
SHARED_OUT="${SHARED_OUT:-/media/sf_shared}"

if [[ -f "$REPO_ROOT/.venv/bin/activate" ]]; then
  source "$REPO_ROOT/.venv/bin/activate"
else
  echo "Error: .venv not found. Run scripts/setup_litex.sh first." >&2
  exit 1
fi

python "$REPO_ROOT/hw/build_soc.py" --no-compile-software --no-compile-gateware

GATEWARE_DIR="$REPO_ROOT/hw/build/gateware"
TCL_FILE="$GATEWARE_DIR/digilent_nexys4ddr.tcl"

if [[ ! -f "$TCL_FILE" ]]; then
  echo "Error: TCL file not found at $TCL_FILE" >&2
  exit 1
fi

echo ""
echo "=== LiteX Gateware Generated Successfully ==="
echo "Gateware location: $GATEWARE_DIR"
echo ""

# Copy gateware to shared folder if provided and exists
if [[ -d "$SHARED_OUT" ]]; then
  SHARED_BUILD_DIR="$SHARED_OUT/nexys4ddr_build"
  mkdir -p "$SHARED_BUILD_DIR"
  
  echo "Copying gateware to shared folder: $SHARED_BUILD_DIR"
  cp -r "$GATEWARE_DIR"/* "$SHARED_BUILD_DIR/"
  
  echo ""
  echo "=== Ready for Windows Vivado Build ==="
  echo "Shared folder: $SHARED_BUILD_DIR"
  echo "TCL script: digilent_nexys4ddr.tcl"
  echo ""
  echo "On Windows, run this command (in PowerShell or CMD):"
  echo "  cd \"$SHARED_BUILD_DIR\""
  echo "  vivado -mode batch -source digilent_nexys4ddr.tcl"
  echo ""
  echo "Expected output bitstream:"
  echo "  $SHARED_BUILD_DIR/nexys4ddr_vexriscv.bit"
  echo ""
else
  echo "Warning: Shared folder not accessible at $SHARED_OUT"
  echo "To enable Windows build, either:"
  echo "  1. Mount/create shared folder at: $SHARED_OUT"
  echo "  2. Or set: export SHARED_OUT=/path/to/your/shared/folder"
  echo ""
  echo "Manual copy instructions:"
  echo "  Copy entire directory: $GATEWARE_DIR"
  echo "  To Windows Vivado machine, then run:"
  echo "  vivado -mode batch -source digilent_nexys4ddr.tcl"
fi
