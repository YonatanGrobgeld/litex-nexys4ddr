# Init Files Fix for Vivado Batch Synthesis

## Problem
Vivado synthesis was failing with critical warnings:
```
CRITICAL WARNING: [Synth 8-4445] could not open $readmem data file 'digilent_nexys4ddr_rom.init'
CRITICAL WARNING: [Synth 8-4445] could not open $readmem data file 'digilent_nexys4ddr_sram.init'
```

## Root Cause
The Verilog RTL (`digilent_nexys4ddr.v`) references the init files with bare filenames:
- Line 11063: `$readmemh("digilent_nexys4ddr_rom.init", rom);`
- Line 11078: `$readmemh("digilent_nexys4ddr_sram.init", sram);`

In batch mode on Windows, Vivado's working directory was not set to the gateware directory where these files exist, causing synthesis to fail to locate them.

## Solution
Modified `build/gateware/digilent_nexys4ddr.tcl` to:

1. **Set working directory explicitly:**
   ```tcl
   set gateware_dir [file dirname [info script]]
   cd $gateware_dir
   ```
   This ensures Vivado changes to the same directory as the script, making relative paths work.

2. **Add init files to project:**
   ```tcl
   add_files -fileset sim_1 {digilent_nexys4ddr_rom.init digilent_nexys4ddr_sram.init}
   ```
   This registers the init files with the project so Vivado knows where to find them during synthesis.

## Files Changed
- `build/gateware/digilent_nexys4ddr.tcl` (lines 7-24)

## How to Run
```bash
# On Windows (in PowerShell or Command Prompt):
cd C:\Final_Project\litex-nexys4ddr\gateware
vivado -mode batch -source digilent_nexys4ddr.tcl
```

## Init Files Location
Both init files must exist in the same directory as the TCL script:
- `build/gateware/digilent_nexys4ddr_rom.init` (BIOS/ROM data)
- `build/gateware/digilent_nexys4ddr_sram.init` (L2 cache SRAM initialization)

These files are generated during the Linux build step (`./scripts/build.sh`) and are checked into the repository. They do not need to be manually created or copied.

## Expected Result
Synthesis will now:
✓ Find and load both init files
✓ Pass without Synth 8-4445 warnings
✓ Embed ROM contents in bitstream
✓ Continue to place_design without errors
