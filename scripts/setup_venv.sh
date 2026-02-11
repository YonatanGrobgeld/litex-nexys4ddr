#!/usr/bin/env bash
set -euo pipefail

# Setup script to create and configure Python venv in home directory
# The venv MUST be in the home directory because VirtualBox shared folders
# don't support the symlinks that Python venv requires.

echo "=== LiteX RISC-V venv Setup ==="
echo ""
echo "NOTE: VirtualBox shared folders don't support Python symlinks."
echo "Creating venv in home directory..."
echo ""

# Create venv in home directory
HOME_PROJECT="/home/yonatang/Final_Project/litex-nexys4ddr"
VENV_PATH="$HOME_PROJECT/.venv"

if [[ -d "$VENV_PATH" ]]; then
  echo "✓ venv already exists at $VENV_PATH"
else
  echo "Creating venv at $VENV_PATH..."
  python3 -m venv "$VENV_PATH"
  echo "✓ venv created"
fi

echo ""
echo "Activating venv..."
source "$VENV_PATH/bin/activate"

echo "✓ venv activated"
echo ""

# Upgrade pip, setuptools, wheel
echo "Updating pip, setuptools, wheel..."
pip install --upgrade pip setuptools wheel -q
echo "✓ Updated"
echo ""

# Install core dependencies
echo "Installing core dependencies..."
pip install \
  meson \
  ninja \
  migen \
  pyserial \
  PyYAML \
  -q
echo "✓ Core dependencies installed"
echo ""

# Set up Python paths for LiteX modules in third_party
echo "Configuring Python paths for LiteX modules..."

LITEX_DIR="$HOME_PROJECT/third_party"

# Create .pth file for easier importing
mkdir -p "$VENV_PATH/lib/python3.10/site-packages"

cat > "$VENV_PATH/lib/python3.10/site-packages/litex_local.pth" << 'EOF'
import sys; sys.path.extend([
    '/home/yonatang/Final_Project/litex-nexys4ddr/third_party/litex/litex',
    '/home/yonatang/Final_Project/litex-nexys4ddr/third_party/litedram/litedram',
    '/home/yonatang/Final_Project/litex-nexys4ddr/third_party/liteeth/liteeth',
    '/home/yonatang/Final_Project/litex-nexys4ddr/third_party/litei2c/litei2c',
    '/home/yonatang/Final_Project/litex-nexys4ddr/third_party/litex-boards/litex_boards',
    '/home/yonatang/Final_Project/litex-nexys4ddr/third_party/migen',
    '/home/yonatang/Final_Project/litex-nexys4ddr/third_party/pythondata-cpu-vexriscv/pythondata_cpu_vexriscv',
    '/home/yonatang/Final_Project/litex-nexys4ddr/third_party/litesdcard/litesdcard',
    '/home/yonatang/Final_Project/litex-nexys4ddr/third_party/litesata/litesata',
    '/home/yonatang/Final_Project/litex-nexys4ddr/third_party/litespi/litespi',
])
EOF

echo "✓ Python paths configured"
echo ""

# Test the setup
echo "Testing LiteX import..."
if python -c "from litex.soc.integration.builder import Builder; print('✓ LiteX available')" 2>&1; then
  echo "✓ Setup successful!"
else
  echo "⚠ Warning: LiteX import test failed"
  echo "  This might be okay if you just updated paths."
  echo "  Try: source $VENV_PATH/bin/activate"
fi

echo ""
echo "=== Setup Complete ==="
echo ""
echo "To use this setup in the future:"
echo "  source $VENV_PATH/bin/activate"
echo ""
echo "Then run build scripts from either location:"
echo "  cd /media/sf_Final_Project/litex-nexys4ddr && bash scripts/build.sh"
echo "  OR"
echo "  cd /home/yonatang/Final_Project/litex-nexys4ddr && bash scripts/build.sh"
echo ""
