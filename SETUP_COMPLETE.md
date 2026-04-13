# LiteX RISC-V Project Setup Summary

## ✅ Setup Complete

All Python environments and build tooling are now configured to work with the shared folder location: `/media/sf_Final_Project/litex-nexys4ddr/`

### Virtual Environment Location

**venv**: `/home/yonatang/Final_Project/litex-nexys4ddr/.venv`

- Located in home directory (VirtualBox shared folders don't support Python symlinks)
- All build scripts automatically detect and use this venv
- Contains all required dependencies: meson, ninja, migen, pyserial, PyYAML

### Source Code Location

**Project root**: `/media/sf_Final_Project/litex-nexys4ddr/` (shared folder)

- All actual source code and scripts are in the shared folder
- Allows editing from Windows via UNC path: `\\vboxsrv\sf_Final_Project\litex-nexys4ddr\`
- LiteX modules are in: `/media/sf_Final_Project/litex-nexys4ddr/third_party/litex/`

### Build Artifacts

Recent successful build (2026-02-11 13:50):
- **BIOS**: `build/software/bios/bios.bin` (24 KB)
- **BIOS ELF**: `build/software/bios/bios.elf` (267 KB)
- **Gateware**: `build/gateware/digilent_nexys4ddr.{v,xdc,tcl}`
- **TCL Script**: Correctly points to `/media/sf_Final_Project/` paths

## 🏗️ Building from Shared Folder

Run from either location - the script auto-detects and uses the correct venv:

```bash
cd /media/sf_Final_Project/litex-nexys4ddr
bash scripts/build.sh
```

Or from home directory:
```bash
cd /home/yonatang/Final_Project/litex-nexys4ddr
bash scripts/build.sh
```

Both work because the build script automatically:
1. Locates venv in `/home/yonatang/Final_Project/litex-nexys4ddr/.venv`
2. Sets PYTHONPATH to `/media/` modules (shared folder)
3. Outputs to the specified build directory

## 🖥️ Generating Bitstream on Windows

```powershell
cd "\\vboxsrv\sf_Final_Project\litex-nexys4ddr\build\gateware"
vivado -mode batch -source digilent_nexys4ddr.tcl
```

This creates: `digilent_nexys4ddr.bit` (ready to program FPGA)

## 📋 Key Scripts

- `scripts/build.sh` - Build BIOS + generate gateware Verilog for Vivado
- `scripts/build_sw_hello.sh` - Build hello_measure user program
- `scripts/run_hello.sh` - Load and run hello_measure via serial boot
- `scripts/setup_venv.sh` - (Re)configure Python environment

## ✨ Key Fix Applied

The TCL script now correctly points to `/media/sf_Final_Project/` paths, so Vivado will properly include:
- VexRiscv CPU module
- All generated HDL files

This ensures the bitstream includes the actual CPU implementation (was previously missing, causing "no BIOS output" issue).

## 📝 Next Steps

1. Generate bitstream: Run Vivado TCL script on Windows
2. Program FPGA with bitstream
3. Verify BIOS output in PuTTY (should see LiteX prompt and BIOS commands)
4. Test with hello_measure program: `bash scripts/build_sw_hello.sh && bash scripts/run_hello.sh /dev/ttyS0`
