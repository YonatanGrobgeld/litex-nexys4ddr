# Repository Guide — What Every Directory and File Is For

A plain-language map of this repo. Its sibling repo,
[TinyML_algo](https://github.com/YonatanGrobgeld/TinyML_algo), has the matching guide
for the algorithm/firmware side.

**This repo in one line:** the **SoC build tree** — it assembles the complete
System-on-Chip (VexRiscv CPU with the DOT8 instruction + DDR2 + UART + timer +
the EXP-LUT and GEMV accelerator peripherals) for the Nexys4DDR board, and holds
the resulting bitstream that gets programmed onto the FPGA.

**The two-repo split:**

| Repo | Contains |
|---|---|
| `TinyML_algo` | The algorithm (TinyFormer C firmware), accelerator *sources* (RTL, drivers, tests), training pipeline |
| `litex-nexys4ddr` (this one) | The SoC *assembly*: build script, the DOT8-extended CPU Verilog, the Vivado build snapshot, the bitstream, and the generated `csr.h` that the firmware compiles against |

**The build flow (two machines):**

1. **Linux (VM):** `python3 hw/build_soc.py` → generates the SoC Verilog, constraints,
   ROM/SRAM init images, the LiteX BIOS, and `csr.h`.
2. **Windows:** `vivado -mode batch -source digilent_nexys4ddr.tcl` (run directly in
   PowerShell, no wrapper script) synthesizes the copied files → produces
   `digilent_nexys4ddr.bit` (the bitstream).
3. **Board:** program the bitstream (see `docs/PROGRAM_FPGA.md`), then load TinyFormer
   firmware over serial and run.

---

## Root files

| File | Purpose |
|---|---|
| `README.md` | Overview, the measured speedup table (759 ms → 157.55 ms, 4.82×), the important `use_external_variant` DOT8 fix, and the step-by-step build flow. |
| `ACCELERATOR_INTEGRATION_PATHS.md` | The integration playbook: exact file paths, code changes, and build commands used to add the three accelerators to the SoC. |
| `REPO_GUIDE.md` | This file. |

---

## `hw/` — the SoC hardware definition

| File | Purpose |
|---|---|
| `build_soc.py` | **The centerpiece.** Python/LiteX script that assembles the whole SoC: clocks (PLL, 100 MHz), VexRiscv + caches, 128 KiB BIOS ROM, DDR2 (128 MiB main RAM), UART, timer, and the ExpLUT + GEMV peripherals. Contains the critical v2 fix: the DOT8 CPU is swapped in with `cpu.use_external_variant()` so Vivado doesn't silently fall back to the standard CPU. Outputs everything Vivado needs. |
| `rtl/VexRiscv_Dot8.v` | Machine-generated (SpinalHDL) Verilog of the **entire CPU with the DOT8 instruction baked in** (~6,400 lines). This is what makes the custom instruction physically exist on the chip. |
| `rtl/exp_lut.v` | Local copy of the EXP-LUT accelerator circuit (master copy in TinyML_algo). |
| `rtl/gemv_core.v` | Local copy of the GEMV matrix-engine circuit (master copy in TinyML_algo). |
| `build/` | Output of `build_soc.py`: generated top-level Verilog, constraints, ROM/SRAM init images, register map (`csr.csv/json`), generated C headers. Machine-generated (see its ABOUT file). |

## `sw/` — SoC-side software pieces

| Path | Purpose |
|---|---|
| `exp_lut/litex/exp_lut_periph.py` | LiteX wrapper putting the LUT circuit on the bus (index/value registers). Imported by `build_soc.py`. |
| `gemv/litex/gemv_periph.py` | LiteX wrapper putting the GEMV circuit on the bus (7 registers + start/clear pulses). Imported by `build_soc.py`. |
| `hello_measure/main.c` | The "is this SoC alive?" smoke test: prints hello over raw-MMIO UART and measures a busy loop with the `mcycle` counter — proved serial boot, UART, and cycle counting before any real firmware ran. |

## `scripts/` — build & bring-up automation

| File | Purpose |
|---|---|
| `setup_venv.sh`, `setup_litex.sh`, `install_riscv_toolchain.sh` | One-time environment setup: Python venv (in HOME — shared folders can't hold venvs), LiteX framework, RISC-V compiler. |
| `verify_litex.py` / `verify_litex.sh` | Sanity check that the LiteX environment works. |
| `build_hw.sh` | Runs `build_soc.py` (the Linux half of the build). |
| `build.sh` | One-stop driver for the shared-folder workflow. |
| `build_sw_hello.sh` | Compiles the hello_measure smoke test. |
| `run_hello.sh` | Upload & run the smoke test over serial boot. |
| `run_baseline_and_measure.py` / `run_accel_all_and_measure.py` | On-FPGA performance measurement: auto-upload a TinyFormer `firmware.bin` over UART (SFL) and record the hardware `CYCLES` per inference. Baseline vs. accel ⇒ speedup. See `docs/MEASURE_ON_FPGA.md`. |
| `gen_rom_fix.py` | Regenerates the ROM init image from a BIOS binary (bring-up fix). |

The Windows half of the build (Vivado synthesis) is run directly —
`vivado -mode batch -source digilent_nexys4ddr.tcl` in PowerShell — no wrapper
script needed; LiteX's generated `.tcl` is already the complete build script.

## `docs/` — how-to documents

| File | Purpose |
|---|---|
| `MEMORY_CONFIG.md` | The SoC memory map and cache/BRAM configuration choices. |
| `PROGRAM_FPGA.md` | How to program the bitstream onto the Nexys4DDR with Vivado. |
| `VIVADO_WINDOWS_BUILD.md` | The Windows/Vivado synthesis workflow in detail. |

## `build/` — the shipped build snapshot (all machine-generated)

| Path | Purpose |
|---|---|
| `gateware/digilent_nexys4ddr.bit` | **The bitstream** — the file actually programmed onto the FPGA (full accelerated SoC). |
| `gateware/*.rpt` | Vivado timing/utilization/power reports — the source of the report's resource numbers (LUT %, 8 DSPs, WNS −6.3 ns, 0.79 W). |
| `software/bios/` | The compiled LiteX BIOS (boots the board, initializes DDR2, memtest, serial boot). |
| `software/include/generated/csr.h` | The auto-generated register "phonebook" the TinyML firmware compiles against. |
| `csr.csv` / `csr.json` | The same register map, machine-readable. |

## `.agent/` — development working notes

Bring-up logs and analyses kept for history (memory-init fixes, Vivado DRC fix,
build summaries, workplan). Useful background; the authoritative docs are README,
ACCELERATOR_INTEGRATION_PATHS.md, and `docs/`.
