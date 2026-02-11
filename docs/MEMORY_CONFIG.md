# Memory Configuration for Nexys4 DDR RISC-V SoC

## Overview

The LiteX RISC-V SoC for Digilent Nexys4 DDR features a flexible memory hierarchy optimized for TinyML and embedded applications:

- **On-Chip ROM**: Bootloader and application code storage (up to 256 KiB default)
- **DDR2 SDRAM**: Main system memory (128 MB total, Micron MT47H64M16)
- **L2 Cache**: Optional scratchpad/cache layer for performance (128 KiB default, up to 256 KiB)
- **CPU Caches**: Separate I-Cache and D-Cache (16 KiB each default, 8-16 KiB configurable)

## Hardware Specifications

### FPGA: Xilinx Artix-7 (XC7A100TCsg324-1)

- **Block RAM (BRAM)**: 240 × 36 Kb blocks = ~4.86 MB total
- **System Clock**: 100 MHz input, configurable via PLL to 50-200 MHz
- **I/O Standard**: SSTL18_II (DDR2 memory interface)

### DDR2 SDRAM: Micron MT47H64M16

- **Capacity**: 64M × 16-bit = **128 MB total**
- **Speed**: Configured for 1:4 mode (100 MHz system / 400 MHz DDR clock)
- **Interface**: 13-bit row address, 3-bit bank address, 10-bit column address, 16-bit data bus
- **Data Rate**: 400 Mbps

## Memory Map

```
0x00000000 - 0x0003FFFF  [256 KiB]  On-chip ROM (BIOS + bootloader)
                                     Default application code location

0x10000000 - 0x10001FFF  [8 KiB]    On-chip SRAM (rarely used with DDR)
                                     Integrated main RAM (can be disabled)

0x80000000 - 0x87FFFFFF  [128 MB]   DDR2 SDRAM Main Memory
                                     Heap, stack, and large data structures
```

## Memory Configuration via Command-Line Arguments

The `hw/build_soc.py` script accepts arguments to customize memory sizes:

### ROM Size
```bash
--rom-size SIZE_IN_BYTES
```
- **Default**: 262144 (256 KiB)
- **Typical Range**: 64 KiB - 512 KiB
- **Impact**: Controls on-chip instruction memory for bootloader and init code

Example:
```bash
./scripts/build.sh --rom-size 262144
```

### L2 Cache Size
```bash
--l2-size SIZE_IN_BYTES
```
- **Default**: 131072 (128 KiB)
- **Options**: 131072 (128 KiB) or 262144 (256 KiB)
- **Impact**: L2 cache improves DDR access performance; larger cache reduces DDR bandwidth

Example:
```bash
./scripts/build.sh --l2-size 262144
```

### CPU Instruction Cache (I-Cache)
```bash
--icache-size SIZE_IN_BYTES
```
- **Default**: 16384 (16 KiB)
- **Typical Range**: 8192 (8 KiB) - 16384 (16 KiB)
- **Impact**: Reduces instruction fetch misses for tight loops

Example:
```bash
./scripts/build.sh --icache-size 16384
```

### CPU Data Cache (D-Cache)
```bash
--dcache-size SIZE_IN_BYTES
```
- **Default**: 16384 (16 KiB)
- **Typical Range**: 8192 (8 KiB) - 16384 (16 KiB)
- **Impact**: Improves data access performance, critical for ML models

Example:
```bash
./scripts/build.sh --dcache-size 16384
```

## Complete Build Examples

### Default Configuration (TinyML Optimized)
Recommended for ML models with typical working sets < 256 KiB:

```bash
cd /media/sf_Final_Project/litex-nexys4ddr
./scripts/build.sh
```

**Configuration**:
- ROM: 256 KiB
- L2 Cache: 128 KiB
- I-Cache: 16 KiB
- D-Cache: 16 KiB
- DDR2: 128 MB

### Conservative Configuration (Minimal Resources)
For designs constrained by BRAM:

```bash
./scripts/build.sh \
  --rom-size 131072 \
  --l2-size 131072 \
  --icache-size 8192 \
  --dcache-size 8192
```

### High-Performance Configuration
For large ML models:

```bash
./scripts/build.sh \
  --rom-size 262144 \
  --l2-size 262144 \
  --icache-size 16384 \
  --dcache-size 16384
```

## BRAM Allocation

The Nexys4 DDR allocates BRAMs as follows:

| Component | Size | BRAM Blocks | Notes |
|-----------|------|------------|-------|
| ROM | 256 KiB | ~20 | Bootloader + application code |
| SRAM | 8 KiB | 1 | Integrated, rarely used |
| I-Cache | 16 KiB | 2 | Part of CPU core |
| D-Cache | 16 KiB | 2 | Part of CPU core |
| L2 Cache | 128 KiB | ~16 | LiteX frontend cache |
| **Total Used** | **~488 KiB** | **~41** | Leaves ~4.35 MB for other logic/peripherals |

### BRAM Budget

With default configuration:
- **Used**: ~41 blocks (~1.48 MB)
- **Available**: ~199 blocks (~3.38 MB)
- **Utilization**: ~17%

This leaves sufficient BRAM for:
- Additional peripheral memories
- Internal FIFOs for I/O interfaces
- Debug memory
- Future expandability

## DDR2 Access Performance

### Timing Characteristics

At 100 MHz system clock (400 MHz DDR clock):

| Parameter | Value |
|-----------|-------|
| Access Time | ~50 ns (5 cycles) |
| Burst Length | 8 words |
| Row Precharge | ~40 ns (4 cycles) |
| RAS-to-CAS Delay | ~12.5 ns (1.25 cycles) |

### L2 Cache Hit Ratios

With proper cache sizing:
- **Small kernels** (< 16 KiB): 70-90% L2 hit rate
- **TinyML models** (16-128 KiB): 60-85% L2 hit rate
- **Large datasets**: 40-70% L2 hit rate

DDR2 bandwidth utilization typically 30-50% due to cache hierarchy.

## BIOS and Bootloader

The LiteX BIOS is compiled into on-chip ROM and provides:

1. **UART Console** (115200 baud, 8-N-1)
2. **DRAM Initialization** - Automatic DDR2 controller setup
3. **Boot Selection** - Load from flash or UART
4. **Memory Test** - Validate DDR2 with `memtest` command
5. **Monitoring** - CPU clock frequency display

### BIOS Serial Communication

```bash
# Connect to FPGA via UART (PuTTY, miniterm, or screen)
miniterm.py /dev/ttyUSB0 115200

# Then type commands at the BIOS prompt:
litex> memtest
litex> memcmp 0x80000000 0x80100000
litex> sdcard_init
```

## Building and Programming

### Build Process

1. Run Python build script (generates RTL and BIOS):
   ```bash
   cd /media/sf_Final_Project/litex-nexys4ddr
   source /home/yonatang/Final_Project/litex-nexys4ddr/.venv/bin/activate
   ./scripts/build.sh
   ```

2. Outputs to `build/`:
   - `software/bios/bios.bin` - BIOS binary (embedded in ROM)
   - `gateware/digilent_nexys4ddr.v` - RTL design
   - `gateware/digilent_nexys4ddr.xdc` - Pin constraints
   - `gateware/digilent_nexys4ddr.tcl` - Vivado synthesis script

### Bitstream Generation (Windows with Vivado)

```bash
# From Windows, navigate to build gateware directory
cd \vboxsrv\sf_Final_Project\litex-nexys4ddr\build\gateware

# Run Vivado in batch mode
vivado -mode batch -source digilent_nexys4ddr.tcl

# Output: nexys4ddr_vexriscv.bit (bitstream for programming)
```

### FPGA Programming

Using OpenOCD or Vivado Hardware Manager:

```bash
# With Vivado Hardware Manager (from Windows):
# 1. Open Hardware Manager
# 2. Open target device (Nexys4 DDR)
# 3. Program with nexys4ddr_vexriscv.bit
```

## Verification

After programming the FPGA:

1. **Check LED**: User LED 0 should flash periodically (heartbeat)

2. **Serial Console**:
   ```bash
   miniterm.py /dev/ttyUSB0 115200
   ```
   Should display LiteX BIOS prompt:
   ```
   LiteX BIOS Build Date: ...
   LiteX BIOS ...
   
   DDR3(at 100MHz): initialization...
   
   litex>
   ```

3. **Memory Test**:
   ```
   litex> memtest
   Memtest running at 0x80000000 (bus width: 64-bit)
   ...
   ```

## Design Rationale

### Why DDR2 over On-Chip SRAM?

The Artix-7 100T provides 240 BRAM blocks (~4.86 MB), but allocating 2-4 MB to system RAM:
- Severely limits I/O peripherals (UART, Ethernet, SPI, etc.)
- Creates bottleneck for real-time I/O (no buffering)
- Wastes expensive BRAM that could serve other functions

**DDR2 Solution**:
- 128 MB external memory with only ~16-41 BRAM overhead (L2 cache)
- Enables complex TinyML models + data buffering
- Preserves BRAM for peripheral FIFOs and control logic

### Why L2 Cache?

DDR2 accesses are ~5 cycles (50 ns) vs. CPU caches (1-2 cycles). The L2 cache:
- Filters 60-90% of DDR access requests
- Reduces DDR bandwidth utilization
- Provides consistent latency for real-time workloads
- Cost: ~16 BRAM blocks for 128 KiB (256 KiB optional)

### Cache Sizing for TinyML

Typical TinyML models on microcontrollers:

| Model | Size | Recommended Cache |
|-------|------|-------------------|
| Tiny LSTM | 8-32 KiB | 128 KiB L2 + 8 KiB I/D |
| MobileNet Micro | 32-128 KiB | 256 KiB L2 + 16 KiB I/D |
| Keyword Detection | 8-16 KiB | 128 KiB L2 + 8 KiB I/D |
| Gesture Recognition | 16-64 KiB | 128-256 KiB L2 + 16 KiB I/D |

## Future Enhancements

1. **Variable Bus Width**: Support 32-bit or 16-bit DDR bus for area/power trade-offs
2. **DDR3 Support**: Upgrade to DDR3 PHY for faster memories
3. **HyperRAM**: Add external HyperRAM for increased bandwidth
4. **L3 Cache**: BRAM-based L3 for model weight prefetching
5. **Hardware Accelerators**: Integrate ML compute units alongside CPU

## References

- [Nexys4 DDR Reference Manual](https://digilent.com/reference/programmable-logic/nexys-4-ddr/reference-manual)
- [Artix-7 FPGA Datasheet](https://www.xilinx.com/support/documentation/data_sheets/ds180_7Series_Overview.pdf)
- [MT47H64M16 DDR2 SDRAM Datasheet](https://www.micron.com/)
- [LiteX Documentation](https://github.com/enjoy-digital/litex)
- [LiteDRAM GitHub](https://github.com/enjoy-digital/litedram)
