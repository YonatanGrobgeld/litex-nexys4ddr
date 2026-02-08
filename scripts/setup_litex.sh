#!/usr/bin/env bash
set -euo pipefail

# Create a local Python virtual environment for reproducibility.
python3 -m venv .venv

# Activate the virtual environment for all subsequent installs.
source .venv/bin/activate

# Pin core packaging tools to known-good versions.
python -m pip install --upgrade pip==24.2 setuptools==70.0.0 wheel==0.44.0

# Install common LiteX Python dependencies with pinned versions.
python -m pip install pyyaml==6.0.2 pyserial==3.5 requests==2.32.3

# Install LiteX into a local third_party directory.
LITEX_DIR="third_party/litex"
mkdir -p "$LITEX_DIR"

# Download the official LiteX setup helper script.
curl -L https://raw.githubusercontent.com/enjoy-digital/litex/master/litex_setup.py -o "$LITEX_DIR/litex_setup.py"
chmod +x "$LITEX_DIR/litex_setup.py"

# Initialize and install LiteX with the standard set of cores.
(
  cd "$LITEX_DIR"
  ./litex_setup.py --init --install --config=standard
)
