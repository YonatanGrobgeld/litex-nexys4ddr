# Building Bitstream on Windows with Vivado

## Overview
The LiteX SoC gateware is generated on Ubuntu (in the VirtualBox VM), then synthesized with Vivado on Windows. This document covers the Windows workflow.

## Why We Use Shared Folders (Path Portability Fix)

### Problem: Linux Absolute Paths
Earlier attempts to run Vivado TCL scripts on Windows failed because:
- LiteX generated files with absolute Linux paths like `/home/yonatang/.../VexRiscv.v`
- When copied to Windows, Vivado interpreted these as `C:\home\...` — paths that don't exist
- Windows also complained about extremely long paths (especially under OneDrive)

### Solution: Build Inside VirtualBox Shared Folder
By generating ALL gateware files directly inside the shared folder (`/media/sf_Operating_Systems_Ubuntu/fpga/nexys4ddr_build`), we ensure:
- ✅ Paths are valid on both Ubuntu and Windows
- ✅ No path translation needed
- ✅ Short relative paths in generated TCL
- ✅ Works with OneDrive or any Windows path

---

## Prerequisites
- Vivado installed on Windows (any recent version; 2020.2 or later recommended)
- VirtualBox shared folder configured and mounted in Ubuntu (usually at `/media/sf_*`)
- LiteX gateware generated in the shared folder (done automatically by `bash scripts/build_hw.sh`)

## Step 1: Generate Gateware on Ubuntu (VM)

Run this in the Ubuntu VM:
```bash
cd /home/yonatang/Final_Project/litex-nexys4ddr
bash scripts/build_hw.sh
```

This will:
1. Detect the VirtualBox shared folder mount point
2. Create `/media/sf_Operating_Systems_Ubuntu/fpga/nexys4ddr_build`
3. Generate LiteX gateware (Verilog, constraints, TCL script) directly inside it
4. Post-process the TCL to make paths Windows-portable

**Output:**
```
=== Ready for Windows Vivado Build ===
Shared folder path: /media/sf_Operating_Systems_Ubuntu
Windows UNC path: \\vboxsrv\Operating_Systems_Ubuntu\fpga\nexys4ddr_build

On Windows, run these commands (PowerShell or CMD):
  cd "\\vboxsrv\Operating_Systems_Ubuntu\fpga\nexys4ddr_build"
  vivado -mode batch -source digilent_nexys4ddr.tcl
```

### Validate TCL Paths (Optional)
To verify the TCL file has Windows-portable paths:
```bash
bash scripts/check_tcl_paths.sh
```

Expected output:
```
✅ PASS: TCL does not contain Linux-specific absolute paths
Status: Windows-Portable
```

---

## Step 2: Synthesize on Windows

### Option A: PowerShell (Recommended)
Open PowerShell on Windows and run:
```powershell
# Navigate to the gateware build folder
cd "\\vboxsrv\Operating_Systems_Ubuntu\fpga\nexys4ddr_build"

# Verify TCL file exists
dir *.tcl

# Run Vivado synthesis
vivado -mode batch -source digilent_nexys4ddr.tcl
```

### Option B: Command Prompt (CMD)
```cmd
cd \\vboxsrv\Operating_Systems_Ubuntu\fpga\nexys4ddr_build
vivado -mode batch -source digilent_nexys4ddr.tcl
```

### Option C: Windows PowerShell Script
Create a file `run_vivado.ps1` on Windows:
```powershell
$buildFolder = "\\vboxsrv\Operating_Systems_Ubuntu\fpga\nexys4ddr_build"
cd $buildFolder
Write-Host "Running Vivado synthesis in: $buildFolder" -ForegroundColor Green
vivado -mode batch -source digilent_nexys4ddr.tcl
if ($LASTEXITCODE -eq 0) {
    Write-Host "Success! Bitstream generated." -ForegroundColor Green
    Get-Item *.bit
} else {
    Write-Host "Vivado failed with exit code: $LASTEXITCODE" -ForegroundColor Red
}
```

Run it:
```powershell
.\run_vivado.ps1
```

---

## Step 3: Locate the Generated Bitstream

After Vivado completes, the bitstream should be at:
```
\\vboxsrv\Operating_Systems_Ubuntu\fpga\nexys4ddr_build\nexys4ddr_vexriscv.bit
```

To verify on Windows:
```powershell
dir "\\vboxsrv\Operating_Systems_Ubuntu\fpga\nexys4ddr_build\*.bit"
```

Expected output:
```
    Directory: \\vboxsrv\Operating_Systems_Ubuntu\fpga\nexys4ddr_build

Mode                 LastWriteTime         Length Name
----                 -------------         ------ ----
-a----         2/8/2026  3:00 PM      1234567 nexys4ddr_vexriscv.bit
```

---

## Step 4: Program the Board

Once you have the `.bit` file:

1. **In Vivado Hardware Manager (GUI):**
   - Open Vivado
   - Go to **Hardware Manager**
   - **Open Target → Auto Connect**
   - Right-click the device → **Program Device**
   - Select `nexys4ddr_vexriscv.bit`
   - Click **Program**

2. **Via TCL in Vivado:**
   ```tcl
   open_hw
   connect_hw_server
   open_hw_target
   current_hw_device [lindex [get_hw_devices] 0]
   set_property PROGRAM.FILE {\\vboxsrv\Operating_Systems_Ubuntu\fpga\nexys4ddr_build\nexys4ddr_vexriscv.bit} [current_hw_device]
   program_hw_devices [current_hw_device]
   close_hw_target
   ```

---

## Troubleshooting

### VirtualBox Shared Folder Not Found
On Ubuntu, verify the shared folder is mounted:
```bash
mount | grep vboxsf
df -h | grep sf_
```

If not mounted, add your user to the `vboxsf` group:
```bash
sudo usermod -aG vboxsf $USER
# Log out and log back in
```

### Vivado Not Found on Windows
Ensure Vivado is in your `PATH`. Test with:
```powershell
vivado -version
```

If not found, add Vivado to PATH:
1. Open **Environment Variables** (Windows Start → "env")
2. Edit `PATH` and add `C:\Xilinx\Vivado\<version>\bin`
3. Restart PowerShell

### TCL Script Fails on Windows
Check if paths in the TCL are still absolute:
```bash
# On Ubuntu, run:
bash scripts/check_tcl_paths.sh
```

If it fails, rebuild:
```bash
bash scripts/build_hw.sh
bash scripts/check_tcl_paths.sh
```

### Long Path Errors on Windows
Windows has a 260-character path limit (unless long paths enabled). Using the short VirtualBox UNC path avoids this:
- ✅ Good: `\\vboxsrv\Operating_Systems_Ubuntu\fpga\nexys4ddr_build`
- ❌ Bad: `C:\Users\YourName\OneDrive\Documents\Projects\...`

If you see "path too long" errors, ensure Vivado output is in the shared folder.

---

## UART Connection

Once the bitstream is programmed to the board:

1. Connect the Nexys4 DDR USB UART port to your computer
2. Open a terminal program (e.g., PuTTY, minicom, screen)
3. Settings:
   - **Baud rate:** 115200
   - **Data bits:** 8
   - **Parity:** None
   - **Stop bits:** 1
   - **Flow control:** None
4. You should see boot banner or prompt

---

## Notes
- The TCL script generated by LiteX handles all synthesis, place & route, and bitstream generation automatically
- The process is non-interactive; Vivado will exit when complete
- Check `vivado.log` in the build folder for detailed output if there are errors
- All paths in the TCL are now relative or use short shared-folder paths, ensuring Windows portability
