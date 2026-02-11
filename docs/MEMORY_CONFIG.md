# Memory Configuration for Nexys4 DDR RISC-V SoC

## Overview

The LiteX RISC-V SoC for Digilent Nexys4 DDR features a flexible memory hierarchy optimized for TinyML and embedded applications:

- **On-Chip ROM**: Bootloader and application code storage (128 KiB default, configurable)
- **DDR2 SDRAM**: Main system memory for large weights/activations (128 MB total, Micron MT47H64M16)
- **L2 Cache/Scratchpad**: Performance optimization layer (128 KiB default, can expand to 256 KiB)
- **CPU Caches**: Separate I-Cache and D-Cache for instruction and data (16 KiB each default, 8-16 KiB configurable)

## Hardware Specifications

### FPGA: Xilinx Artix-7 (XC7A100TCsg324-1)

- **Block RAM (BRAM)**: 240 × 36 Kb blocks = ~4.86 MB total
- **System Clock**: 100 MHz input, configurable via PLL to 50-200 MHz
- **I/O Standard**: SSTL18_II (DDR2 memory interface)
- **LUT Count**: 63,400 (sufficient for VexRiscv + peripherals)

### DDR2 SDRAM: Micron MT47H64M16

- **Capacity**: 64M × 16-bit = **128 MB total**
- **Speed**: Configured for 1:4 mode (100 MHz system / 400 MHz DDR clock)
- **Interface**: 13-bit row address, 3-bit bank address, 10-bit column address, 16-bit data bus
- **Data Rate**: 400 Mbps
- **Latency**: ~100-200 ns (acceptable for embedded ML inference)

## Why DDR2 as Main RAM?

### Key Design Rationale

1. **BRAM Budget Optimization**: The Artix-7 100T has only ~4.86 MB of BRAM (240 × 36 Kb blocks). Dedicating most of this to caches and scratchpad is more efficient than trying to fit large models in BRAM.

2. **TinyML Model Weights**: A typical TinyML model (e.g., MobileNetV2 micro, CIFAR-10 model) can range from 100 KiB to several MB. DDR2 provides ample capacity (128 MB) without resource contention.

3. **Performance Trade-offs**:
   - DDR2 latency (~100-200ns) is acceptable for models with sequential memory access patterns
   - L2 cache (128 KiB) bridges the speed gap for frequently-accessed data
   - CPU caches (16 KiB I$ + 16 KiB D$) handle instruction locality and hot data

4. **Resource Efficiency**: Using DDR2 as main RAM leaves BRAM for:
   - L2 unified cache (128/256 KiB)
   - VexRiscv I-Cache and D-Cache (16 KiB each)
   - UART and other peripheral buffers

## Memory Map

```
Address Range            Size        Description
─────────────────────────────────────────────────────────
0x00000000 - 0x0001FFFF  128 KiB    On-Chip ROM (BIOS + bootloader)
                                      Default application code location
                                      [Configurable: --rom-size]

0x80000000 - 0x87FFFFFF  128 MB     DDR2 SDRAM (Main System RAM)
                                      Heap, stack, and ML model weights
                                      Fastest access when L2 cache hit
                                      
CSR Registers            (varies)    Control/Status for DDR PHY, Timer, UART
```

## BRAM Allocation Strategy

The Artix-7 100T BRAM budget (~4.86 MB) is allocated as follows:

| Component              | Size (default) | Size (max)  | Purpose                           |
|------------------------|----------------|-------------|-----------------------------------|
| **L2 Cache**           | 128 KiB        | 256 KiB     | Unified cache for DDR hit/miss pattern smoothing |
| **I-Cache (VexRiscv)** | 16 KiB         | 16 KiB      | Instruction fetch optimization   |
| **D-Cache (VexRiscv)** | 16 KiB         | 16 KiB      | Data access optimization         |
| **Total Used**         | **160 KiB**    | **288 KiB** | ~3-6% of total BRAM              |

**Remaining BRAM** (~4.57-4.70 MB) is available for:
- DDR PHY calibration buffers
- UART/debug logging buffers
- Future peripheral requirements
- Register files and distributed RAM

## Memory Configuration via Command-Line Arguments

The `hw/build_soc.py` script accepts arguments to customize memory sizes:

### ROM Size
```bash
--rom-size SIZE_IN_BYTES
```
- **Default**: `131072` (128 KiB)
- **Minimum**: `65536` (64 KiB)
- **Typical Range**: 64 KiB - 256 KiB
- **Impact**: Controls on-chip instruction memory for bootloader and BIOS code. Larger ROM allows pre-loading more utility code or test vectors.

Example:
```bash
./scripts/build.sh --rom-size 131072
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

## Constraints and Considerations

### Timing and Clock Speeds

- **System Clock**: Default 100 MHz from FPGA. Can be increased to 150-200 MHz via:
  ```bash
  ./scripts/build.sh --sys-clk-freq 150000000
  ```
  Higher clocks improve cache hit rate benefit but may require timing closure effort in Vivado.

- **DDR Clock**: Automatically set to 4× system clock (1:4 mode)
  - 100 MHz sys → 400 MHz DDR
  - 150 MHz sys → 600 MHz DDR
  - Micron MT47H64M16 supports up to 667 MHz

### BRAM Usage Limits

- **Artix-7 100T**: 240 BRAM36 blocks (~4.86 MB max)
- **Current usage**: ~160 KiB (default) to 288 KiB (max), leaving >4.5 MB available
- **Safety margin**: Keep total cache/BRAM < 500 KiB to avoid resource conflicts

### DDR Bandwidth

- **Theoretical Peak**: 128-bit data bus × 400 MHz = 6.4 GB/s (1:4 mode)
- **Practical Throughput**: ~3-4 GB/s (due to refresh, write leveling, command overhead)
- **Inference Bottleneck**: Most TinyML models achieve <500 MB/s actual memory bandwidth
  - L2 cache hit rates >80% are typical for iterative workloads

### Power Consumption

- **DDR2 Active Power**: ~100-150 mW @ 400 MHz
- **Cache Power**: ~10-20 mW per 64 KiB @ 100 MHz
- **Total System**: ~400-500 mW @ 100 MHz (CPU, DDR, peripherals)

## Validation Checklist

After building with custom memory configuration:

- [ ] Check `build/csr.json` for correct DDR base address (should be `0x80000000`)
- [ ] Verify ROM size in `build/csr.csv` matches configured size
- [ ] Review timing report in `build/gateware/digilent_nexys4ddr_timing.rpt` (WNS > 0 for closure)
- [ ] Confirm BRAM usage in `build/gateware/digilent_nexys4ddr_utilization_synth.rpt` (<15%)
- [ ] Test UART communication at 115200 baud after FPGA programming
- [ ] Run BIOS memory test: `mtest` in UART console (if implemented)

## Troubleshooting

### Issue: Timing Fails with Large L2 Cache

**Solution**: Reduce L2 cache to 128 KiB, or lower system clock to 80 MHz:
```bash
./scripts/build.sh --l2-size 131072 --sys-clk-freq 80000000
```

### Issue: DDR Initialization Fails

**Solution**: Ensure correct DDR PHY parameters in build output. Check:
- DDR clock alignment (should be 4× system clock)
- Write leveling calibration in BIOS console output

### Issue: Out of BRAM Resources

**Solution**: Reduce cache sizes:
```bash
./scripts/build.sh --icache-size 8192 --dcache-size 8192
```

## References

- **Xilinx Artix-7 FPGA**: DS181 - 7 Series FPGAs Overview
- **Micron MT47H64M16**: DDR2 SDRAM datasheet (MT47H64M16 rev J)
- **LiteX Documentation**: https://github.com/enjoy-digital/litex
- **VexRiscv CPU**: https://github.com/SpinalHDL/VexRiscv
