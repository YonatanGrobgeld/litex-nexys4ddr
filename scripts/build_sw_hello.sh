#!/usr/bin/env bash
set -euo pipefail

# Build script for hello_measure program
# Builds a minimal bare-metal RISC-V program for LiteX BIOS serial boot

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SW_DIR="$PROJECT_ROOT/sw/hello_measure"
BUILD_DIR="$SW_DIR/build"

echo "=== Building hello_measure ==="
echo "Project root: $PROJECT_ROOT"
echo "Source: $SW_DIR"
echo "Build: $BUILD_DIR"
echo ""

# Auto-locate venv in home directory (VirtualBox shared folders don't support symlinks)
if [[ "$PROJECT_ROOT" == /media/* ]]; then
  HOME_PROJECT="/home/yonatang/Final_Project/litex-nexys4ddr"
  VENV_PATH="$HOME_PROJECT/.venv"
else
  VENV_PATH="$PROJECT_ROOT/.venv"
fi

if [[ -f "$VENV_PATH/bin/activate" ]]; then
  source "$VENV_PATH/bin/activate"
else
  echo "Warning: venv not found at $VENV_PATH"
fi

# Create build directory
mkdir -p "$BUILD_DIR"

# Toolchain
RISCV_PREFIX="riscv64-unknown-elf"
CC="${RISCV_PREFIX}-gcc"
OBJCOPY="${RISCV_PREFIX}-objcopy"

# LiteX CSR and memory header
CSR_H="$PROJECT_ROOT/build/software/include/generated/csr.h"
MEM_H="$PROJECT_ROOT/build/software/include/generated/mem.h"
REGIONS_LD="$PROJECT_ROOT/build/software/include/generated/regions.ld"

if [[ ! -f "$CSR_H" ]]; then
    echo "Error: CSR header not found at $CSR_H"
    echo "Run: cd $PROJECT_ROOT && bash scripts/build.sh"
    exit 1
fi

echo "Using CSR header: $CSR_H"
echo "Using linker script: $REGIONS_LD"
echo ""

# Get include paths from cross-compilation file (optional)
CROSS_FILE="$PROJECT_ROOT/build/software/libc/cross.txt"
if [[ -f "$CROSS_FILE" ]]; then
    # Extract c_args from cross.txt if available
    C_ARGS=$(grep -o "c_args = \[.*\]" "$CROSS_FILE" | head -1 | sed "s/c_args = \[//;s/\]//;s/'//g;s/,//g" || true)
fi

# Compile flags
CFLAGS=(
    "-march=rv32i"          # RV32I ISA (VexRiscv standard variant)
    "-mabi=ilp32"           # 32-bit ABI
    "-O2"                   # Optimization
    "-Wall"
)

# System include directories
INCLUDES=(
    "-I$PROJECT_ROOT/build/software/include/generated"
)

# Link flags
LDFLAGS=(
    "-T$REGIONS_LD"         # Linker script
    "-L$PROJECT_ROOT/build/software/libcompiler_rt"
    "-nostdlib"             # No standard library
    "-nostartfiles"         # No CRT0
    "-Wl,-e,_start"         # Entry point
)

# Compile and link
echo "Compiling main.c..."
$CC "${CFLAGS[@]}" "${INCLUDES[@]}" -c "$SW_DIR/main.c" -o "$BUILD_DIR/main.o"

echo "Linking..."
$CC "${CFLAGS[@]}" "${LDFLAGS[@]}" \
    "$BUILD_DIR/main.o" \
    -lcompiler_rt \
    -o "$BUILD_DIR/hello_measure.elf"

# Generate binary
echo "Creating binary..."
$OBJCOPY -O binary "$BUILD_DIR/hello_measure.elf" "$BUILD_DIR/hello_measure.bin"

echo ""
echo "=== Build Complete ==="
echo "ELF: $BUILD_DIR/hello_measure.elf"
echo "BIN: $BUILD_DIR/hello_measure.bin"
echo ""
echo "Size: $(stat -f%z "$BUILD_DIR/hello_measure.bin" 2>/dev/null || stat -c%s "$BUILD_DIR/hello_measure.bin")"
echo ""
echo "To upload and run:"
echo "  source $PROJECT_ROOT/.venv/bin/activate"
echo "  python -m litex.tools.litex_term COM3 --speed 115200 --kernel $BUILD_DIR/hello_measure.bin --serial-boot"
echo "(Replace COM3 with your actual port)"
