# LiteX + VexRiscv on Nexys4 DDR

## Overview
LiteX SoC with VexRiscv CPU on Digilent Nexys4 DDR (Artix-7 xc7a100t), running a TinyFormer TinyML accelerator with three hardware extensions: DOT8 custom instruction, Exp LUT peripheral, and GEMV peripheral.

**SoC configuration:** VexRiscv @ 100 MHz, DDR2 @ 400 MT/s (1:2 PHY ratio), 128 MiB main RAM.

## Requirements
- Board: Digilent Nexys4 DDR (xc7a100t CSG324-1)
- Vivado 2020.x or later (Windows, for synthesis/bitstream)
- Python 3.10+ with LiteX (Ubuntu VM, for RTL generation and firmware build)
- RISC-V toolchain: `riscv64-unknown-elf-gcc` (for firmware)

## Build flow

### Step 1 — Generate RTL and BIOS (Linux/Ubuntu VM)
```bash
python3 hw/build_soc.py
```
Outputs in `hw/build/gateware/`: `digilent_nexys4ddr.v`, `.xdc`, `_rom.init`, `_sram.init`, `resynth_windows.tcl`.

### Step 2 — Copy to Windows shared folder
```bash
TARGET=/media/sf_Final_Project/accelerators/accel_all
cp hw/build/gateware/digilent_nexys4ddr.v      $TARGET/
cp hw/build/gateware/digilent_nexys4ddr_rom.init $TARGET/
cp hw/build/gateware/digilent_nexys4ddr_sram.init $TARGET/
cp hw/build/gateware/digilent_nexys4ddr.xdc    $TARGET/
cp hw/build/gateware/resynth_windows.tcl       $TARGET/
cp hw/rtl/exp_lut.v hw/rtl/gemv_core.v hw/rtl/VexRiscv_Dot8.v $TARGET/
```

### Step 3 — Synthesize bitstream (Windows Vivado)
In the Vivado Tcl Console:
```tcl
cd C:/Final_Project/accelerator
source resynth_windows.tcl
```
Produces `digilent_nexys4ddr.bit`.

### Step 4 — Program FPGA (Vivado Hardware Manager)
Open Vivado → Hardware Manager → Auto Connect → Program Device → select `digilent_nexys4ddr.bit`.

### Step 5 — Build and load firmware (Linux build, Windows run)
```bash
# Build on Linux
cd /path/to/TinyML_Algo/litex_port
make TARGET=accel_all      # or: baseline, accel_dot8, accel_lut, accel_gemv, accel_dot8_lut
cp firmware.bin /media/sf_Final_Project/accelerators/accel_all/
```
```powershell
# Load on Windows PowerShell
python -m litex.tools.litex_term --kernel C:\Final_Project\accelerator\firmware.bin COM3
```
The BIOS loads `firmware.bin` into DDR2 RAM and boots it. Firmware waits for `s` over UART, runs one TinyFormer inference, prints `CYCLES=<N>` / `TIME_US=<N>` / `Done`.

## Repository layout
- `hw/build_soc.py` — Main SoC build script (CRG, DDR2 PHY, accelerator peripherals)
- `hw/rtl/` — Accelerator Verilog sources (VexRiscv_Dot8.v, exp_lut.v, gemv_core.v)
- `hw/build/` — Generated RTL, BIOS binary, and constraints (not hand-edited)
- `sw/exp_lut/litex/` — ExpLUT LiteX CSR peripheral wrapper
- `sw/gemv/litex/` — GEMV LiteX CSR peripheral wrapper
- `docs/` — Architecture notes and documentation
- `scripts/` — Utility scripts
