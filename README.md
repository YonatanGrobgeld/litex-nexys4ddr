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
	- `bash scripts/verify_litex.sh`
- Build/bitstream:
	- **Ubuntu (VM):** `bash scripts/build_hw.sh`
	- Generates gateware in `hw/build/gateware/` and copies to shared folder (if available)
	- **Windows (Vivado):** see `docs/VIVADO_WINDOWS_BUILD.md` for full workflow
	- Final bitstream: `hw/build/gateware/nexys4ddr_vexriscv.bit` (after Vivado synthesis)
- Load/flash (Vivado):
	- Ensure Vivado is on PATH or set `$XILINX_VIVADO` to the Vivado install root.
	- TCL (from repo root):
		- `"$XILINX_VIVADO/bin/vivado" -mode tcl -source - <<'TCL'`
		- `open_hw`
		- `connect_hw_server`
		- `open_hw_target`
		- `current_hw_device [lindex [get_hw_devices] 0]`
		- `refresh_hw_device -update_hw_probes false [current_hw_device]`
		- `set_property PROGRAM.FILE {hw/build/gateware/nexys4ddr_vexriscv.bit} [current_hw_device]`
		- `program_hw_devices [current_hw_device]`
		- `close_hw_target`
		- `quit`
	- GUI:
		- Open Vivado, then Hardware Manager → Open Target → Auto Connect.
		- Right-click device → Program Device → select `hw/build/gateware/nexys4ddr_vexriscv.bit`.
- Run software: (TBD)
- Collect results: (TBD)

## Repository layout
- docs/: Plans, notes, and documentation
- scripts/: Automation scripts (build, load, run)
- hw/: Hardware sources and generated artifacts
- sw/: Software sources and build outputs
- results/: Experimental results and logs
