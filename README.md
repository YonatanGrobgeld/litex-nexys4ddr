# LiteX + VexRiscv on Nexys4 DDR

## Overview
Project goal: bring up a LiteX SoC with a VexRiscv CPU on a Digilent Nexys4 DDR board, then run a CPU-only kernel baseline, then add an accelerator.

## Requirements
- Board: Digilent Nexys4 DDR
- Vivado: (TBD)
- LiteX: (TBD)

## How to run scripts
- Setup LiteX (Ubuntu 22.04):
	- `bash scripts/setup_litex.sh`
- Verify LiteX install:
	- `. .venv/bin/activate`
	- `python scripts/verify_litex.py`
- Build/bitstream: (TBD)
- Load/flash: (TBD)
- Run software: (TBD)
- Collect results: (TBD)

## Repository layout
- docs/: Plans, notes, and documentation
- scripts/: Automation scripts (build, load, run)
- hw/: Hardware sources and generated artifacts
- sw/: Software sources and build outputs
- results/: Experimental results and logs
