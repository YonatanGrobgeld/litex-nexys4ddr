# Quick Start - LiteX Nexys4 DDR TinyML Build

## ✅ Status: Build Complete - Ready for Windows Vivado

**Date**: 11 February 2026  
**All Files**: `/home/yonatang/litex-project/build/gateware/`

---

## Files Ready for Vivado

| File | Size | Purpose |
|------|------|---------|
| `digilent_nexys4ddr.v` | 648 KB | Complete SoC RTL (includes VexRiscv) |
| `digilent_nexys4ddr.xdc` | 11 KB | Pin constraints |
| `digilent_nexys4ddr.tcl` | 2.1 KB | Vivado synthesis script |

**Note**: VexRiscv is fully embedded in the main Verilog file. No separate vexriscv.v needed.

---

## Vivado Bitstream Generation (Windows)

### Option 1: Batch Mode (Automated)
```bash
cd C:\path\to\gateware
vivado -mode batch -source digilent_nexys4ddr.tcl
```

### Option 2: GUI Mode
1. Open Vivado
2. In Tcl Console: `source C:\path\to\gateware\digilent_nexys4ddr.tcl`
3. Wait for synthesis, P&R, bitstream generation

**Output**: `nexys4ddr_vexriscv.bit`

---

## Memory Map

```
0x00000000 - 0x0001FFFF   128 KiB   ROM (BIOS)
0x80000000 - 0x87FFFFFF   128 MB    DDR2 SDRAM (Main RAM)
```

---

## Configuration (Default)

- ROM: 128 KiB
- DDR2: 128 MB
- L2 Cache: 128 KiB
- I-Cache: 16 KiB
- D-Cache: 16 KiB
- System Clock: 100 MHz
- **Total BRAM: 160 KiB (3.3%)**

---

## After Programming FPGA

```bash
miniterm.py /dev/ttyUSB0 115200
```

Expected:
```
LiteX BIOS...
DDR2 initialization...
litex> memtest
```

---

## Rebuild with Different Config

```bash
# Default (recommended)
./scripts/build.sh

# Larger cache
./scripts/build.sh --l2-size 262144

# Minimal BRAM
./scripts/build.sh --l2-size 131072 --icache-size 8192 --dcache-size 8192
```

---

## Documentation

- **BUILD_SUMMARY.md** - Complete build details
- **CHANGES_SUMMARY.txt** - All modifications made
- **docs/MEMORY_CONFIG.md** - Memory subsystem documentation

---

**Next Step**: Copy `build/gateware/` to Windows and run Vivado!
