# What this folder is (in simple words)

A SNAPSHOT of a complete, finished build - everything here is machine-generated.
Kept in the repo so the exact shipped result is reproducible without rebuilding.

- `gateware/digilent_nexys4ddr.bit` - **the bitstream**: the file actually programmed
  onto the FPGA. This one contains the full accelerated SoC (DOT8 CPU + EXP-LUT + GEMV).
- `gateware/*.rpt` - Vivado reports: timing, utilization, power. These are the source of
  the resource/power numbers quoted in the project report (LUT %, DSP count, WNS, watts).
- `gateware/digilent_nexys4ddr.v` / `.xdc` / `.tcl` - the generated top-level Verilog,
  pin constraints, and the Vivado project script.
- `software/bios/` - the compiled LiteX BIOS (the tiny boot program in on-chip ROM that
  initializes DDR2, runs memtest, and can receive firmware over serial).
- `software/include/generated/` - the auto-generated C headers (`csr.h` = the address
  'phonebook' of every peripheral register) that the TinyML firmware compiles against.
- `csr.csv` / `csr.json` - the same register map in machine-readable form.
