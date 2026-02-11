#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
LITEX_DIR="$REPO_ROOT/third_party/litex"
LITEX_SETUP_URL="https://raw.githubusercontent.com/enjoy-digital/litex/master/litex_setup.py"

sudo apt-get update
sudo apt-get install -y curl wget git python3-venv python3-pip make gcc g++ cmake pkg-config

# Create a local Python virtual environment for reproducibility.
python3 -m venv "$REPO_ROOT/.venv"

# Activate the virtual environment for all subsequent installs.
source "$REPO_ROOT/.venv/bin/activate"

# Pin core packaging tools to known-good versions.
python -m pip install --upgrade pip==24.2 setuptools==70.0.0 wheel==0.44.0

# Install common LiteX Python dependencies with pinned versions.
python -m pip install pyyaml==6.0.2 pyserial==3.5 requests==2.32.3

# Install LiteX into a local third_party directory.
mkdir -p "$LITEX_DIR"

if command -v curl >/dev/null 2>&1; then
  curl -L "$LITEX_SETUP_URL" -o "$LITEX_DIR/litex_setup.py"
elif command -v wget >/dev/null 2>&1; then
  wget -O "$LITEX_DIR/litex_setup.py" "$LITEX_SETUP_URL"
else
  echo "Error: neither curl nor wget is available." >&2
  exit 1
fi
chmod +x "$LITEX_DIR/litex_setup.py"

# Initialize and install LiteX with the standard set of cores.
(
  cd "$LITEX_DIR"
  ./litex_setup.py --init --install --config=standard
)
