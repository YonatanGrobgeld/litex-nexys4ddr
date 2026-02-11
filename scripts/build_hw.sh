#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)

# Auto-detect VirtualBox shared folder mount
# Look for /media/sf_* (VirtualBox default mount pattern)
detect_shared_folder() {
  local sf_mounts
  sf_mounts=$(mount -t vboxsf 2>/dev/null | awk '{print $3}' | head -1)
  
  if [[ -z "$sf_mounts" ]]; then
    # Try manual path if no auto-mount found
    if [[ -d "/media/sf_Operating_Systems_Ubuntu" ]]; then
      echo "/media/sf_Operating_Systems_Ubuntu"
      return 0
    fi
    return 1
  fi
  
  echo "$sf_mounts"
  return 0
}

# Determine output directory
if [[ -n "${SHARED_OUT:-}" ]]; then
  # Explicit override
  SHARED_FOLDER="$SHARED_OUT"
else
  # Auto-detect
  if SHARED_FOLDER=$(detect_shared_folder); then
    : # Success
  else
    echo "Error: VirtualBox shared folder not found." >&2
    echo "" >&2
    echo "To fix, either:" >&2
    echo "  1. Add your user to vboxsf group: sudo usermod -aG vboxsf \$USER" >&2
    echo "  2. Or enable auto-mount in VirtualBox device settings" >&2
    echo "  3. Or set manually: export SHARED_OUT=/path/to/shared/folder" >&2
    exit 1
  fi
fi

# Build output directory inside shared folder (short path for Windows)
# Use a single clean directory structure: litex_nexys4ddr/
BUILD_FOLDER="$SHARED_FOLDER/litex_nexys4ddr"

# Clean up old build artifacts if they exist
if [[ -d "$BUILD_FOLDER" ]]; then
  echo "Cleaning previous build at $BUILD_FOLDER..."
  rm -rf "$BUILD_FOLDER"
fi

mkdir -p "$BUILD_FOLDER"

if [[ -f "$REPO_ROOT/.venv/bin/activate" ]]; then
  source "$REPO_ROOT/.venv/bin/activate"
else
  echo "Error: .venv not found. Run scripts/setup_litex.sh first." >&2
  exit 1
fi

echo "=== LiteX Build Configuration ==="
echo "Repo root: $REPO_ROOT"
echo "Shared folder: $SHARED_FOLDER"
echo "Build output: $BUILD_FOLDER"
echo ""

# Run LiteX build with output directed to shared folder
# Remove --no-compile-software to enable BIOS compilation
python "$REPO_ROOT/hw/build_soc.py" \
  --output-dir "$BUILD_FOLDER" \
  --no-compile-gateware

GATEWARE_DIR="$BUILD_FOLDER/gateware"
TCL_FILE="$GATEWARE_DIR/digilent_nexys4ddr.tcl"

if [[ ! -f "$TCL_FILE" ]]; then
  echo "Error: TCL file not found at $TCL_FILE" >&2
  exit 1
fi

echo ""
echo "=== LiteX Gateware Generated Successfully ==="
echo "Build directory: $BUILD_FOLDER"
echo ""

# Post-process TCL to make paths Windows-portable
# All paths will be relative to the gateware subfolder
echo "Post-processing TCL for Windows portability..."

# Replace absolute paths with relative paths
# The third_party folder will be at ../third_party from the gateware folder
sed -i 's|/home/[^/]*/[^/]*/litex-nexys4ddr/third_party/|../third_party/|g' "$TCL_FILE"
sed -i 's|/home/[^/]*/[^/]*/litex-nexys4ddr/hw/build/gateware/|./|g' "$TCL_FILE"

# Also fix shared folder absolute paths
sed -i "s|$BUILD_FOLDER/gateware/|./|g" "$TCL_FILE"

# Remove any remaining absolute paths
sed -i 's|/home/[^/]*/[^/]*/litex-nexys4ddr/||g' "$TCL_FILE"

# Copy third_party to build folder so Vivado can find referenced files
echo "Copying third_party dependencies to build folder..."
if [[ -d "$REPO_ROOT/third_party" ]]; then
  mkdir -p "$BUILD_FOLDER/third_party"
  # Only copy what we need: VexRiscv
  if [[ -d "$REPO_ROOT/third_party/litex/pythondata-cpu-vexriscv" ]]; then
    mkdir -p "$BUILD_FOLDER/third_party/litex"
    cp -r "$REPO_ROOT/third_party/litex/pythondata-cpu-vexriscv" \
          "$BUILD_FOLDER/third_party/litex/" 2>/dev/null || true
  fi
fi

echo ""
echo "=== Ready for Windows Vivado Build ==="
echo "Shared folder path: $SHARED_FOLDER"
echo "Project directory: litex_nexys4ddr"
echo "Windows UNC path: \\\\vboxsrv\\$(basename "$SHARED_FOLDER")\\litex_nexys4ddr"
echo ""
echo "On Windows, run these commands (PowerShell or CMD):"
echo "  cd \"\\\\vboxsrv\\$(basename "$SHARED_FOLDER")\\fpga\\nexys4ddr_build\""
echo "  vivado -mode batch -source digilent_nexys4ddr.tcl"
echo ""
echo "Expected output bitstream:"
echo "  $BUILD_FOLDER/nexys4ddr_vexriscv.bit"
echo "  (Windows path: \\\\vboxsrv\\$(basename "$SHARED_FOLDER")\\fpga\\nexys4ddr_build\\nexys4ddr_vexriscv.bit)"
