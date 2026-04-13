#!/usr/bin/env bash
set -euo pipefail

# Find and validate TCL files in shared folder
# Ensures paths are Windows-portable (no /home/... or other Linux absolute paths)

detect_shared_folder() {
  local sf_mounts
  sf_mounts=$(mount -t vboxsf 2>/dev/null | awk '{print $3}' | head -1)
  
  if [[ -z "$sf_mounts" ]]; then
    if [[ -d "/media/sf_Operating_Systems_Ubuntu" ]]; then
      echo "/media/sf_Operating_Systems_Ubuntu"
      return 0
    fi
    return 1
  fi
  
  echo "$sf_mounts"
  return 0
}

if SHARED_FOLDER=$(detect_shared_folder); then
  : # Success
else
  echo "Error: VirtualBox shared folder not found." >&2
  exit 1
fi

BUILD_FOLDER="$SHARED_FOLDER/litex_nexys4ddr"

if [[ ! -d "$BUILD_FOLDER" ]]; then
  echo "Error: Build folder not found at $BUILD_FOLDER" >&2
  echo "Run 'bash scripts/build_hw.sh' first to generate gateware." >&2
  exit 1
fi

# Find TCL file
TCL_FILE=$(find "$BUILD_FOLDER" -name "*.tcl" -type f | head -1)

if [[ -z "$TCL_FILE" ]]; then
  echo "Error: No TCL file found in $BUILD_FOLDER" >&2
  exit 1
fi

echo "Checking TCL file: $TCL_FILE"
echo ""

FAILED=0

# Check for Linux-specific absolute paths
BAD_PATTERNS=(
  "/home/"
  "/root/"
  "/tmp/"
  "/usr/"
  "/media/sf_"
)

for pattern in "${BAD_PATTERNS[@]}"; do
  if grep -q "$pattern" "$TCL_FILE"; then
    echo "❌ FAIL: Found Linux-specific path: $pattern"
    grep -n "$pattern" "$TCL_FILE" | head -5
    echo ""
    FAILED=1
  fi
done

# Check for relative paths (good) or short paths
if ! grep -q "/" "$TCL_FILE" || grep -q "^\s*set\s.*\./\|[a-zA-Z0-9_]\.v" "$TCL_FILE"; then
  echo "✅ PASS: TCL contains relative or short paths (Windows-portable)"
else
  # If no slash paths, might be OK - be lenient
  if [[ $FAILED -eq 0 ]]; then
    echo "✅ PASS: TCL does not contain Linux-specific absolute paths"
  fi
fi

if [[ $FAILED -eq 1 ]]; then
  echo ""
  echo "Path validation FAILED. TCL is not Windows-portable."
  echo "Rebuild with: bash scripts/build_hw.sh"
  exit 1
fi

echo ""
echo "=== TCL Path Validation Complete ==="
echo "Status: ✅ Windows-Portable"
echo "TCL file: $TCL_FILE"
echo ""
echo "Ready to use on Windows Vivado:"
echo "  cd \"\\\\vboxsrv\\$(basename "$SHARED_FOLDER")\\fpga\\nexys4ddr_build\""
echo "  vivado -mode batch -source digilent_nexys4ddr.tcl"
