# LiteX + VexRiscv on Nexys4 DDR

## Overview
LiteX SoC with VexRiscv CPU on Digilent Nexys4 DDR (Artix-7 xc7a100t), running a TinyFormer TinyML accelerator with three hardware extensions: DOT8 custom instruction, Exp LUT peripheral, and **GEMV v2 peripheral (32-bit packed data path + 4-lane parallel signed int8 MAC)**.

**SoC configuration:** VexRiscv @ 100 MHz, DDR2 @ 400 MT/s (1:2 PHY ratio), 128 MiB main RAM.

### Final speedup measured on this SoC (Nexys4DDR @ 100 MHz)

`ENC_CKSUM` bit-identical across all modes (same FPGA, swap firmware only):

| Mode | CYCLES | Time | Speedup |
|---|---|---|---|
| Baseline (real-math softmax, software matvec) | 75,900,400 | **759.00 ms** | 1.00× |
| **accel_all** (packed 32-bit GEMV + 4-lane MAC + DOT8 + EXP_LUT) | **15,755,300** | **157.55 ms** | **4.82×** |

Time = CYCLES / 100 MHz. The TinyML_Algo repo's [REPORT_NOTES_IMPLEMENTATION.md §9](https://github.com/YonatanGrobgeld/TinyML_Algo/blob/main/REPORT_NOTES_IMPLEMENTATION.md) has the full breakdown.

### Important `build_soc.py` fix

The standard VexRiscv CPU and our DOT8-extended VexRiscv both define a Verilog module named `VexRiscv`. To make Vivado actually pick up the DOT8 variant (instead of silently defaulting to LiteX's bundled standard one), the SoC build calls `self.cpu.use_external_variant(VexRiscv_Dot8.v)` rather than plain `platform.add_source()`. The former sets `external_variant = True` inside LiteX's VexRiscv core, which causes `do_finalize()` to skip adding the bundled `VexRiscv.v`, leaving only our DOT8 file in the source list. Without this fix the DOT8 instruction is silently dropped and `accel_all` firmware traps on its first `dot8_4_lanes()` call. See the commit log for details.

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
Outputs in `hw/build/gateware/`: `digilent_nexys4ddr.v`, `.xdc`, `_rom.init`, `_sram.init`, `digilent_nexys4ddr.tcl` (the LiteX-generated Vivado build script).

### Step 2 — Copy to Windows shared folder
```bash
TARGET=/media/sf_Final_Project/accelerators/accel_all
cp hw/build/gateware/digilent_nexys4ddr.v      $TARGET/
cp hw/build/gateware/digilent_nexys4ddr_rom.init $TARGET/
cp hw/build/gateware/digilent_nexys4ddr_sram.init $TARGET/
cp hw/build/gateware/digilent_nexys4ddr.xdc    $TARGET/
cp hw/build/gateware/digilent_nexys4ddr.tcl    $TARGET/
cp hw/rtl/exp_lut.v hw/rtl/gemv_core.v hw/rtl/VexRiscv_Dot8.v $TARGET/
```

### Step 3 — Synthesize bitstream (Windows PowerShell)
```powershell
cd C:\Final_Project\accelerators\accel_all
vivado -mode batch -source digilent_nexys4ddr.tcl
```
Produces `digilent_nexys4ddr.bit` (Vivado runs synthesis, place & route, and bitstream generation non-interactively; check `vivado.log` in the same folder if it fails).

### Step 4 — Program FPGA (Vivado Hardware Manager)
Open Vivado → Hardware Manager → Auto Connect → Program Device → select `digilent_nexys4ddr.bit`.

### Step 5 — Build firmware, then run + measure (Linux build, Windows run)
```bash
# Build on Linux
cd /path/to/TinyML_Algo/litex_port
make TARGET=accel_all      # or: baseline, accel_dot8, accel_lut, accel_gemv, accel_dot8_lut
cp firmware.bin /media/sf_Final_Project/accelerators/accel_all/
```
```powershell
# Run + measure on Windows PowerShell
python scripts/run_accel_all_and_measure.py --port COM3 --runs 10 --firmware firmware.bin
# or, for a baseline (non-accelerated) firmware build:
python scripts/run_baseline_and_measure.py --port COM3 --runs 10 --firmware firmware.bin
```
There's no separate `litex_term` upload step — the measurement script resets the
board, auto-uploads `firmware.bin` over the LiteX SFL protocol itself, waits for
the firmware's `Ready` prompt, sends `s` to trigger one inference, and records the
hardware `CYCLES` count to a results CSV. See `docs/MEASURE_ON_FPGA.md` for the
full flow.

## Repository layout
- `hw/build_soc.py` — Main SoC build script (CRG, DDR2 PHY, accelerator peripherals)
- `hw/rtl/` — Accelerator Verilog sources (VexRiscv_Dot8.v, exp_lut.v, gemv_core.v)
- `hw/build/` — Generated RTL, BIOS binary, and constraints (not hand-edited)
- `sw/exp_lut/litex/` — ExpLUT LiteX CSR peripheral wrapper
- `sw/gemv/litex/` — GEMV LiteX CSR peripheral wrapper
- `docs/` — Build instructions, FPGA programming guide, memory configuration
- `.agent/notes/` — Archived development working notes (not project documentation)
- `scripts/` — Utility scripts
