#!/usr/bin/env bash
set -euo pipefail

# Install RISC-V GCC toolchain for LiteX BIOS compilation
# This script installs a prebuilt toolchain from SiFive/Freedom Tools

echo "=== Installing RISC-V GCC Toolchain for LiteX ==="
echo ""

TOOLCHAIN_DIR="$HOME/.local/riscv"
TOOLCHAIN_VERSION="2020.12.8"
TOOLCHAIN_URL="https://static.dev.sifive.com/dev-tools/freedom-tools/v${TOOLCHAIN_VERSION}/riscv64-unknown-elf-toolchain-${TOOLCHAIN_VERSION}-x86_64-linux-ubuntu14.tar.gz"

mkdir -p "$TOOLCHAIN_DIR"

echo "Downloading RISC-V toolchain..."
cd /tmp
wget -O riscv-toolchain.tar.gz "$TOOLCHAIN_URL"

echo "Extracting toolchain..."
tar -xzf riscv-toolchain.tar.gz -C "$TOOLCHAIN_DIR" --strip-components=1

echo "Cleaning up..."
rm riscv-toolchain.tar.gz

echo ""
echo "=== Installation Complete ==="
echo "Toolchain installed to: $TOOLCHAIN_DIR"
echo ""
echo "Add to your PATH by running:"
echo "  export PATH=\"$TOOLCHAIN_DIR/bin:\$PATH\""
echo ""
echo "Or add this line to ~/.bashrc for permanent setup:"
echo "  echo 'export PATH=\"$TOOLCHAIN_DIR/bin:\$PATH\"' >> ~/.bashrc"
echo "  source ~/.bashrc"
