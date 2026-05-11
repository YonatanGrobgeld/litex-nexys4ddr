# TinyML Accelerator Integration: Exact Paths & Build Commands

This document provides the **exact file paths, changes required, and build commands** to integrate the Dot8Plugin, Exp LUT, and GEMV accelerators into the LiteX SoC for the Nexys4 DDR board.

---

## 1. Main SoC Build Script

### **File: `/home/yonatang/litex-project/hw/build_soc.py`**

**Purpose:**  
Entry point for LiteX SoC generation. Defines `BaseSoC` class that instantiates the CPU, DDR, ROM, and all system peripherals.

**Current Status:**  
- CPU: VexRiscv (standard variant, no custom plugins)
- DDR: 128 MiB MT47H64M16 @ 50 MHz (1:4 mode)
- Clock: 75 MHz system clock (not 100 MHz)
- No accelerators instantiated

**Key Sections:**
- **Lines 36–68**: `_CRG` class defines clock/reset generator (PLL)
- **Lines 71–115**: `BaseSoC.__init__()` instantiates SoCCore and DDR
- **Lines 158–232**: `main()` function parses args and builds gateware

**What needs to change:**
- After line 111 (after `self.add_sdram(...)`), add accelerator module instantiations:
  ```python
  # Add Exp LUT peripheral
  from sw.exp_lut.litex.exp_lut_periph import ExpLUTPeriph
  self.exp_lut = ExpLUTPeriph(platform, sys_clk_freq)
  self.add_csr("exp_lut", self.exp_lut)
  
  # Add GEMV peripheral
  from sw.gemv.litex.gemv_periph import GEMVPeriph
  self.gemv = GEMVPeriph(platform, sys_clk_freq)
  self.add_csr("gemv", self.gemv)
  ```

---

## 2. VexRiscv CPU Configuration & Custom Instruction (Dot8Plugin)

### **File: `third_party/litex/pythondata-cpu-vexriscv/pythondata_cpu_vexriscv/verilog/VexRiscv.v`**
(This file is the **generated netlist** from the external VexRiscv Scala repo)

**Purpose:**  
CPU Verilog netlist. If a custom CPU instruction (Dot8Plugin) is needed, it must be added in the **external VexRiscv Scala generator**, then the netlist must be regenerated and placed here.

**Current Status:**  
Baseline VexRiscv with standard instructions (RV32I + M + Zicsr extensions).

**Integration Path:**
1. External VexRiscv repo has `src/main/scala/vexriscv/plugin/Dot8Plugin.scala`
2. Modify `src/main/scala/vexriscv/GenCoreDefault.scala` to add `Dot8Plugin` to the plugin list:
   ```scala
   plugins += new Dot8Plugin()
   ```
3. Run the VexRiscv generator to produce a new `VexRiscv.v`
4. Copy the generated `VexRiscv.v` to:
   ```
   third_party/litex/pythondata-cpu-vexriscv/pythondata_cpu_vexriscv/verilog/VexRiscv.v
   ```
5. Run SoC rebuild (see Section 8 below)

**Note:**  
If you do **not** need a custom CPU instruction, use the **baseline VexRiscv.v** and skip Dot8Plugin integration.

---

## 3. Exp LUT Peripheral Integration

### **3a. Verilog Instantiation (LiteX Wrapper)**

**File: `sw/exp_lut/litex/exp_lut_periph.py`** (you must create this)

**Purpose:**  
LiteX Python wrapper that instantiates the Exp LUT Verilog and creates CSR registers.

**Expected Structure:**
```python
from litex.gen import *
from litex.soc.interconnect.csr import *
import os

class ExpLUTPeriph(Module):
    def __init__(self, platform, sys_clk_freq):
        # Read Verilog RTL
        exp_lut_v_file = os.path.join(
            os.path.dirname(__file__), 
            "..", "rtl", "exp_lut.v"
        )
        self.specials += Instance(
            "exp_lut",
            i_clk=ClockSignal(),
            i_rst=ResetSignal(),
            i_x_fixed=Signal(16),  # Example fixed-point input
            o_y_fixed=Signal(16),  # Example fixed-point output
        )
        # Add Instance search paths for Verilog
        self.verilog_sources.append(exp_lut_v_file)
```

**File: `sw/exp_lut/rtl/exp_lut.v`** (reference only; read-only)

**Purpose:**  
RTL implementation of Exp LUT. Should be read-only; called by the LiteX wrapper above.

### **3b. Where it's integrated:**

In `hw/build_soc.py`, line ~112, add:
```python
from sw.exp_lut.litex.exp_lut_periph import ExpLUTPeriph
self.exp_lut = ExpLUTPeriph(platform, sys_clk_freq)
self.add_csr("exp_lut", self.exp_lut)
```

### **3c. Generated CSR Headers:**

After running SoC build (Section 8), check:
```
build/csr.csv        # CSV with register addresses
build/csr.json       # JSON with peripheral and register info
build/software/include/generated/csr.h  # C header with macros
```

Search for `exp_lut` entries (base address will be auto-allocated after existing peripherals).

---

## 4. GEMV Peripheral Integration

### **4a. Verilog Instantiation (LiteX Wrapper)**

**File: `sw/gemv/litex/gemv_periph.py`** (you must create this)

**Purpose:**  
LiteX Python wrapper for GEMV matrix-vector multiply accelerator.

**Expected Structure:**
```python
from litex.gen import *
from litex.soc.interconnect.csr import *
import os

class GEMVPeriph(Module):
    def __init__(self, platform, sys_clk_freq):
        # Read Verilog RTL
        gemv_v_file = os.path.join(
            os.path.dirname(__file__), 
            "..", "rtl", "gemv_core.v"
        )
        self.specials += Instance(
            "gemv_core",
            i_clk=ClockSignal(),
            i_rst=ResetSignal(),
            i_start=Signal(),  # Trigger computation
            o_done=Signal(),   # Completion signal
            # Add matrix/vector data ports as needed
        )
        self.verilog_sources.append(gemv_v_file)
```

**File: `sw/gemv/rtl/gemv_core.v`** (reference only; read-only)

**Purpose:**  
RTL implementation of GEMV accelerator. Called by LiteX wrapper above.

### **4b. Where it's integrated:**

In `hw/build_soc.py`, line ~115 (after Exp LUT), add:
```python
from sw.gemv.litex.gemv_periph import GEMVPeriph
self.gemv = GEMVPeriph(platform, sys_clk_freq)
self.add_csr("gemv", self.gemv)
```

### **4c. Generated CSR Headers:**

After running SoC build, check:
```
build/csr.csv
build/csr.json
build/software/include/generated/csr.h
```

Search for `gemv` entries to find the auto-allocated base address.

---

## 5. Generated Build Artifacts (Output Paths)

### **5a. CSR Metadata**

```
build/csr.csv                    # CSV: all CSR base addresses and register offsets
build/csr.json                   # JSON: hierarchical CSR structure
```

**Current CSR bases (before accelerators):**
```
ctrl       = 0xf0000000
ddrphy     = 0xf0000800
sdram      = 0xf0001000
timer0     = 0xf0001800
uart       = 0xf0002000
```

**After adding exp_lut and gemv:**
- `exp_lut` will be allocated a CSR base (likely `0xf0002800`)
- `gemv` will be allocated a CSR base (likely `0xf0003000`)

### **5b. Software Headers (C generated)**

```
build/software/include/generated/csr.h              # CSR register definitions and functions
build/software/include/generated/soc.h              # SoC configuration (clock freq, CPU type, etc.)
build/software/include/generated/mem.h              # Memory layout (ROM, SRAM, DDR addresses)
build/software/include/generated/sdram_phy.h        # DDR PHY configuration
```

**Key defines from `csr.h`:**
- `exp_lut_base` (macro generated if CSR added)
- `gemv_base` (macro generated if CSR added)
- Individual register macros: `EXP_LUT_<regname>`, `GEMV_<regname>`

### **5c. Linker Scripts**

```
build/software/include/generated/regions.ld         # Memory layout for linker
build/software/include/generated/output_format.ld   # Output format directives
```

### **5d. Gateware (RTL)**

```
build/gateware/digilent_nexys4ddr.v                 # Top-level Verilog
build/gateware/digilent_nexys4ddr.xdc               # Constraints
build/gateware/digilent_nexys4ddr.tcl               # Vivado batch script
build/gateware/digilent_nexys4ddr_rom.init          # BIOS initialization
build/gateware/digilent_nexys4ddr_sram.init         # SRAM initialization
```

---

## 6. MMIO Base Addresses & CSR Registers

### **Current Peripherals (from `build/csr.csv`):**

| Peripheral | CSR Base   | Offset | Size |
|------------|-----------|--------|------|
| `ctrl`     | 0xf0000000 | 0x0    | 12B  |
| `ddrphy`   | 0xf0000800 | 0x0    | 52B  |
| `sdram`    | 0xf0001000 | 0x0    | 48B  |
| `timer0`   | 0xf0001800 | 0x0    | 32B  |
| `uart`     | 0xf0002000 | 0x0    | 20B  |

### **After Adding Accelerators:**

The LiteX builder will automatically allocate the next CSR base. **You must check `build/csr.csv` after the first SoC build to see the allocated addresses.**

**Manual allocation (if CSR auto-generation fails):**
```
exp_lut     = 0xf0002800  (example; verify in csr.csv)
gemv        = 0xf0003000  (example; verify in csr.csv)
```

### **Accessing Peripherals from Firmware:**

```c
#include <generated/csr.h>

// Example: write to exp_lut
#define EXP_LUT_BASE  0xf0002800  // Check build/csr.csv
#define EXP_LUT_X_REG (EXP_LUT_BASE + 0x00)
#define EXP_LUT_Y_REG (EXP_LUT_BASE + 0x04)

// Using LiteX-generated macros (if CSR auto-generated):
*(volatile uint32_t *)EXP_LUT_X_REG = 0x1000;  // Write input
uint32_t result = *(volatile uint32_t *)EXP_LUT_Y_REG;  // Read output
```

---

## 7. Firmware Include Paths & Compilation

### **Include Path:**

```
-I/home/yonatang/litex-project/build/software/include/generated
```

### **Compilation Example:**

```bash
riscv64-unknown-elf-gcc \
  -march=rv32i \
  -mabi=ilp32 \
  -O2 \
  -I/home/yonatang/litex-project/build/software/include/generated \
  -T/home/yonatang/litex-project/build/software/include/generated/regions.ld \
  -nostdlib -nostartfiles \
  -Wl,-e,_start \
  main_all.c \
  -o main_all.elf
```

### **Firmware Target:**

**File: `sw/accel_all/main_all.c`** (you must create this)

**Purpose:**  
Main firmware entry point that:
1. Initializes UART
2. Initializes accelerators (Exp LUT, GEMV) via CSR registers
3. Runs benchmark/algorithm using the accelerators
4. Prints results via UART

**Template:**
```c
#include <generated/csr.h>
#include <generated/soc.h>

static inline void uart_write_char(unsigned char c) {
    while (*(volatile uint32_t *)(UART_BASE + 0x04));
    *(volatile uint32_t *)(UART_BASE + 0x00) = c;
}

int main(void) {
    uart_write_char('H');
    uart_write_char('i');
    uart_write_char('\n');
    
    // Initialize accelerators here
    // Run algorithm using CSR macros
    // Print results
    
    return 0;
}
```

---

## 8. Exact Build Commands

### **8a. Rebuild SoC (with new accelerators)**

```bash
cd /home/yonatang/litex-project
source .venv/bin/activate

# Regenerate gateware and software
python3 hw/build_soc.py \
  --output-dir build \
  --no-compile-gateware \
  --sys-clk-freq 75000000
```

**Outputs:**
- `build/csr.csv`, `build/csr.json` — accelerator CSR bases
- `build/software/include/generated/csr.h` — C headers with new accelerator macros
- `build/gateware/*.v`, `build/gateware/*.xdc` — Vivado inputs

### **8b. Regenerate Just the Headers (no gateware rebuild)**

If you only modify C code:
```bash
cd /home/yonatang/litex-project
python3 hw/build_soc.py \
  --output-dir build \
  --no-compile-gateware
```

Check `build/csr.csv` to verify accelerator addresses.

### **8c. Build Firmware (accel_all)**

```bash
cd /home/yonatang/litex-project
source .venv/bin/activate

# Compile firmware
RISCV_PREFIX=riscv64-unknown-elf
${RISCV_PREFIX}-gcc \
  -march=rv32i \
  -mabi=ilp32 \
  -O2 \
  -Wall \
  -I./build/software/include/generated \
  -T./build/software/include/generated/regions.ld \
  -nostdlib -nostartfiles \
  -Wl,-e,_start \
  ./sw/accel_all/main_all.c \
  -lcompiler_rt \
  -o ./sw/accel_all/build/main_all.elf

# Generate binary for serial boot
${RISCV_PREFIX}-objcopy \
  -O binary \
  ./sw/accel_all/build/main_all.elf \
  ./sw/accel_all/build/main_all.bin
```

### **8d. Full Build Sequence (recommended)**

```bash
#!/bin/bash
cd /home/yonatang/litex-project
source .venv/bin/activate

echo "Step 1: Rebuild SoC with accelerators..."
python3 hw/build_soc.py --output-dir build --no-compile-gateware

echo "Step 2: Verify CSR bases..."
grep -E "^csr_base" build/csr.csv

echo "Step 3: Build firmware..."
bash scripts/build_sw_accel.sh  # (you must create this script)

echo "Done!"
echo "Generated files:"
echo "  Gateware: build/gateware/*.{v,xdc,tcl}"
echo "  Headers: build/software/include/generated/*.h"
echo "  Firmware: sw/accel_all/build/main_all.bin"
```

### **8e. Vivado Synthesis (Windows)**

After running the above on Linux, copy to shared folder and run Vivado:

```powershell
# Windows PowerShell
cd "\\vboxsrv\Final_Project\accelerator"

# Run Vivado batch
vivado -mode batch -source .\digilent_nexys4ddr.tcl

# Program FPGA (in Vivado Hardware Manager or TCL)
vivado -mode batch -source .\program_bit.tcl
```

---

## 9. Integration Checklist

- [ ] **Dot8Plugin** (if needed):
  - [ ] Modify external VexRiscv repo to add Dot8Plugin
  - [ ] Regenerate VexRiscv.v from Scala
  - [ ] Copy to `third_party/litex/pythondata-cpu-vexriscv/pythondata_cpu_vexriscv/verilog/VexRiscv.v`

- [ ] **Exp LUT**:
  - [ ] Create `sw/exp_lut/litex/exp_lut_periph.py` (LiteX wrapper)
  - [ ] Verify `sw/exp_lut/rtl/exp_lut.v` exists (RTL)
  - [ ] Add import and instantiation to `hw/build_soc.py` (after line 111)

- [ ] **GEMV**:
  - [ ] Create `sw/gemv/litex/gemv_periph.py` (LiteX wrapper)
  - [ ] Verify `sw/gemv/rtl/gemv_core.v` exists (RTL)
  - [ ] Add import and instantiation to `hw/build_soc.py` (after line 115)

- [ ] **Firmware**:
  - [ ] Create `sw/accel_all/main_all.c` that uses accelerators
  - [ ] Run SoC build to generate `csr.h` with accelerator macros
  - [ ] Compile firmware against generated CSR headers

- [ ] **Vivado**:
  - [ ] Run Linux SoC build to generate gateware
  - [ ] Copy files to shared folder
  - [ ] Run Vivado batch on Windows
  - [ ] Program FPGA and test

---

## 10. Key Files to Edit / Create

| File | Action | Purpose |
|------|--------|---------|
| `hw/build_soc.py` | **EDIT** lines 112–115 | Add accelerator instantiation |
| `sw/exp_lut/litex/exp_lut_periph.py` | **CREATE** | LiteX wrapper for Exp LUT |
| `sw/gemv/litex/gemv_periph.py` | **CREATE** | LiteX wrapper for GEMV |
| `sw/accel_all/main_all.c` | **CREATE** | Firmware entry point |
| `sw/accel_all/build/` | **auto-generated** | Binary outputs |
| `build/csr.csv` | **auto-generated** | CSR address map |
| `build/software/include/generated/csr.h` | **auto-generated** | C CSR macros |
| `third_party/.../VexRiscv.v` | **REPLACE** (if Dot8) | Custom CPU netlist |

---

## 11. Expected Output After Integration

After running `python3 hw/build_soc.py --output-dir build --no-compile-gateware`:

```
build/
├── csr.csv              # Contains exp_lut, gemv base addresses
├── csr.json
└── software/
    └── include/
        └── generated/
            ├── csr.h    # Contains EXP_LUT_BASE, GEMV_BASE macros
            ├── soc.h    # Clock freq = 75 MHz
            ├── mem.h
            └── regions.ld
```

Check `csr.csv`:
```bash
grep -E "^csr_base.*exp_lut|gemv" build/csr.csv
```

Should show:
```
csr_base,exp_lut,0xf0002800,,
csr_base,gemv,0xf0003000,,
```

---

## 12. Troubleshooting

**Problem:** CSR headers don't include accelerator macros after SoC build
- **Cause:** LiteX wrappers (`exp_lut_periph.py`, `gemv_periph.py`) not created or import failed
- **Fix:** Verify wrapper file paths and Python imports; re-run SoC build

**Problem:** Vivado synthesis fails after SoC rebuild
- **Cause:** Missing VexRiscv.v or wrong file format
- **Fix:** If Dot8Plugin added, regenerate VexRiscv.v from external Scala repo

**Problem:** Firmware crashes when accessing accelerators
- **Cause:** Wrong CSR base address or register offset
- **Fix:** Print CSR base from `csr.csv` and check in firmware code

**Problem:** Accelerator hardware doesn't respond
- **Cause:** RTL not instantiated or optimized away by synthesis
- **Fix:** Check `build/gateware/digilent_nexys4ddr_utilization_synth.rpt` for accelerator LUT/DSP usage

---

**End of Integration Guide**

For questions, check:
- `build/csr.csv` — source of truth for peripheral addresses
- `build/software/include/generated/csr.h` — C API to peripherals
- Vivado synthesis reports — confirm accelerator logic in bitstream

