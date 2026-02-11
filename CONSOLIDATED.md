# LiteX Nexys4 DDR - Project Consolidated

## 📁 Single Source of Truth

**All project files are now in one place:**
```
/media/sf_Final_Project/litex-nexys4ddr/
```

**Windows UNC path (from your Windows machine):**
```
\\vboxsrv\sf_Final_Project\litex-nexys4ddr\
```

---

## 📂 Directory Structure

```
litex-nexys4ddr/
├── build/                          # Build outputs (BIOS, gateware, etc.)
│   ├── gateware/                  # Vivado/synthesis files
│   │   ├── digilent_nexys4ddr.v   # Top-level Verilog
│   │   ├── digilent_nexys4ddr.xdc # Constraints
│   │   ├── digilent_nexys4ddr.tcl # Vivado build script (with relative paths)
│   │   ├── digilent_nexys4ddr_rom.init  # BIOS bitstream (53 KB)
│   │   └── csr.{csv,json}         # Register definitions
│   └── software/                  # Compiled software/BIOS
│       ├── bios/                  # LiteX BIOS
│       └── include/generated/     # Generated C headers
│
├── hw/                             # Hardware source
│   └── build_soc.py              # LiteX SoC builder
│
├── scripts/                        # Build and utility scripts
│   ├── build.sh                  # NEW: Simplified build script
│   ├── build_hw.sh               # OLD: Complex version (deprecated)
│   └── check_tcl_paths.sh        # Validate Windows portability
│
├── docs/                           # Documentation
└── README.md                       # Project info
```

---

## 🛠️ Building from Ubuntu VM

**From within the shared folder:**

```bash
cd /media/sf_Final_Project/litex-nexys4ddr
bash scripts/build.sh
```

**OR from original home location (also works):**

```bash
cd /home/yonatang/Final_Project/litex-nexys4ddr
bash scripts/build.sh
```

Both work because the script locates the `.venv` automatically.

---

## 🪟 Building from Windows

**Step 1: Open PowerShell and navigate to gateware**

```powershell
cd "\\vboxsrv\sf_Final_Project\litex-nexys4ddr\build\gateware"
```

**Step 2: Run Vivado**

```powershell
vivado -mode batch -source digilent_nexys4ddr.tcl
```

**Step 3: Output**

```
digilent_nexys4ddr.bit  # Bitstream (ready to program)
```

---

## ✅ Current Status

- **BIOS**: ✅ Compiled (23.26 KiB)
- **Gateware**: ✅ Generated (Verilog + constraints)
- **Paths**: ✅ Windows-portable (relative paths)
- **Bitstream**: ⏳ Ready for Vivado synthesis

---

## 📝 What Changed

| Before | After |
|--------|-------|
| Project in `/home/yonatang/Final_Project/litex-nexys4ddr/` | ✅ Now in shared folder |
| Build outputs in random shared folders | ✅ All in `./build/` relative to project |
| Complex shared folder detection logic | ✅ Simplified to relative paths |
| Multiple `build_hw.sh` variants | ✅ Single `build.sh` |

---

## 🚀 Next Steps

1. **Run Vivado on Windows** to generate bitstream
2. **Program the FPGA** with resulting `.bit` file
3. **Test with PuTTY** at 115200 8-N-1

---

**Consolidated:** 2026-02-11  
**Status**: Ready for deployment
