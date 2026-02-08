# Program Nexys4 DDR (Vivado)

## Prerequisites
- LiteX gateware generated: `bash scripts/build_hw.sh` (on Linux/WSL)
- Generated files at: `hw/build/gateware/`

## GUI method (Windows/Linux)
1. Open Vivado.
2. Select **Hardware Manager**.
3. Click **Open Target → Auto Connect**.
4. Select the device in the Hardware view.
5. Right-click the device → **Program Device**.
6. For **Bitstream file**, select:
   - `hw/build/gateware/nexys4ddr_vexriscv.bit`
7. Click **Program**.

## TCL method (Windows)
If using WSL on Windows, navigate to the gateware directory and run Vivado:

```bash
# From Windows Command Prompt or PowerShell:
cd C:\path\to\litex-nexys4ddr\hw\build\gateware
"C:\Xilinx\Vivado\2023.2\bin\vivado" -mode tcl -source digilent_nexys4ddr.tcl
```

(Adjust the Vivado version path as needed; e.g., 2023.1, 2022.2, etc.)

## TCL method (Linux)
Run this from the repo root:

```tcl
open_hw
connect_hw_server
open_hw_target
current_hw_device [lindex [get_hw_devices] 0]
refresh_hw_device -update_hw_probes false [current_hw_device]
set_property PROGRAM.FILE {hw/build/gateware/nexys4ddr_vexriscv.bit} [current_hw_device]
program_hw_devices [current_hw_device]
close_hw_target
quit
```

To invoke Vivado in TCL mode on Linux, use:

```bash
"$XILINX_VIVADO/bin/vivado" -mode tcl
```

(Requires Vivado installed and `$XILINX_VIVADO` environment variable set.)
