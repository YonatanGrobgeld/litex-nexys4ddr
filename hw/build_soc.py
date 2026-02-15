#!/usr/bin/env python3
import argparse
import os
import sys

from migen import ClockDomain, Module, Signal

from litex.soc.integration.builder import Builder, builder_args, builder_argdict
from litex.soc.integration.soc_core import SoCCore, soc_core_args, soc_core_argdict
from litex.soc.cores.clock import S7PLL, S7MMCM, S7IDELAYCTRL

from litex_boards.platforms import digilent_nexys4ddr

from litedram.phy import s7ddrphy
from litedram.modules import MT47H64M16


class _CRG(Module):
    def __init__(self, platform, sys_clk_freq):
        self.rst = Signal()
        self.clock_domains.cd_sys = cd_sys = ClockDomain()
        self.clock_domains.cd_sys2x = cd_sys2x = ClockDomain()
        self.clock_domains.cd_sys2x_dqs = cd_sys2x_dqs = ClockDomain(reset_less=True)
        self.clock_domains.cd_iodelay = cd_iodelay = ClockDomain()

        clk100 = platform.request("clk100")
        rst = ~platform.request("cpu_reset")

        self.submodules.pll = pll = S7MMCM(speedgrade=-1)
        self.comb += pll.reset.eq(rst | self.rst)

        pll.register_clkin(clk100, 100e6)
        pll.create_clkout(cd_sys, sys_clk_freq)
        pll.create_clkout(cd_sys2x, 2 * sys_clk_freq)
        pll.create_clkout(cd_sys2x_dqs, 2 * sys_clk_freq, phase=90)
        pll.create_clkout(cd_iodelay, 200e6)
        
        platform.add_false_path_constraints(self.cd_sys.clk, pll.clkin) # Ignore sys_clk to pll.clkin path created by SoC's rst.

        self.submodules.idelayctrl = S7IDELAYCTRL(self.cd_iodelay)


class BaseSoC(SoCCore):
    def __init__(self, platform, sys_clk_freq=int(75e6), 
                 rom_size=None, l2_size=None, 
                 icache_size=None, dcache_size=None, 
                 **kwargs):
        # Set sensible defaults
        defaults = {
            "cpu_type": "vexriscv",
            "cpu_variant": "standard",
            "with_uart": True,
            "with_timer": True,
            "with_cpu_icache": True,
            "with_cpu_dcache": True,
            "cpu_icache_size": icache_size or 16 * 1024,
            "cpu_dcache_size": dcache_size or 16 * 1024,
            "uart_name": "serial",
            "uart_baudrate": 115200,
        }
        # ROM size: 128 KiB default
        if rom_size is None:
            rom_size = 128 * 1024
        
        defaults.update(kwargs)
        
        # Create clock/reset generator
        self.crg = _CRG(platform, sys_clk_freq)

        # Initialize SoCCore with integrated ROM only
        # DDR2 will be added as the main RAM
        super().__init__(
            platform=platform,
            clk_freq=sys_clk_freq,
            integrated_rom_size=rom_size,
            **defaults,
        )

        # DDR2 SDRAM with optional L2 cache
        # L2 cache size: 128 KiB default, configurable to 256 KiB
        if l2_size is None:
            l2_size = 128 * 1024
        
        # Create DDR2 PHY for Artix-7 with appropriate 2:1 ratio (Reference Target Specs)
        self.ddrphy = s7ddrphy.A7DDRPHY(
            pads=platform.request("ddram"),
            memtype="DDR2",
            nphases=2,
            sys_clk_freq=sys_clk_freq
        )
        
        # Add DDR2 SDRAM as main system RAM
        self.add_sdram(
            "sdram",
            phy=self.ddrphy,
            module=MT47H64M16(sys_clk_freq, "1:2"),
            size=0x08000000,  # 128 MB
            l2_cache_size=l2_size
        )


def _default_sys_clk_freq(platform):
    if hasattr(platform, "default_clk_period"):
        return int(1e9 / platform.default_clk_period)
    return int(100e6)


def main() -> int:
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
    output_dir = os.path.join(repo_root, "hw", "build")

    platform = digilent_nexys4ddr.Platform()
    if getattr(platform, "name", None) not in (None, "digilent_nexys4ddr"):
        raise ValueError(
            f"Expected platform 'digilent_nexys4ddr', got '{platform.name}'."
        )

    parser = argparse.ArgumentParser(description="LiteX SoC for Nexys4 DDR with DDR2 and Configurable Memory")
    builder_args(parser)
    soc_core_args(parser)

    parser.add_argument(
        "--sys-clk-freq",
        default=75e6, # Default to 75 MHz for safe DDR2 operation
        type=float,
        help="System clock frequency in Hz (default: 75 MHz).",
    )

    parser.add_argument(
        "--rom-size",
        default=128 * 1024,
        type=int,
        help="On-chip ROM size in bytes (default: 128 KiB).",
    )

    parser.add_argument(
        "--icache-size",
        default=16 * 1024,
        type=int,
        help="Instruction cache (I-Cache) size in bytes (default: 16 KiB, min: 8 KiB).",
    )

    parser.add_argument(
        "--dcache-size",
        default=16 * 1024,
        type=int,
        help="Data cache (D-Cache) size in bytes (default: 16 KiB, min: 8 KiB).",
    )

    parser.set_defaults(
        output_dir=output_dir,
        build_name="nexys4ddr_vexriscv",
        build_backend="litex",
        l2_size=128 * 1024,  # 128 KiB default L2 cache
    )

    args = parser.parse_args()
    
    # Get SoC core arguments
    soc_core_kwargs = soc_core_argdict(args)
    soc_core_kwargs.pop("integrated_rom_size", None)
    soc_core_kwargs.pop("l2_size", None)  # Remove l2_size from soc_core_kwargs, we handle it separately
    
    rom_size = args.rom_size
    # L2 size from soc_core_args (default 128 KiB already set in parser.set_defaults)
    l2_size = getattr(args, "l2_size", 128 * 1024)
    icache_size = args.icache_size
    dcache_size = args.dcache_size
    
    # Validate memory sizes
    if rom_size < 64 * 1024:
        raise ValueError(f"ROM size must be at least 64 KiB, got {rom_size // 1024} KiB")
    if l2_size not in [128 * 1024, 256 * 1024]:
        raise ValueError(f"L2 size must be 128 KiB or 256 KiB, got {l2_size // 1024} KiB")
    if icache_size not in [8 * 1024, 16 * 1024]:
        raise ValueError(f"I-Cache size must be 8 KiB or 16 KiB, got {icache_size // 1024} KiB")
    if dcache_size not in [8 * 1024, 16 * 1024]:
        raise ValueError(f"D-Cache size must be 8 KiB or 16 KiB, got {dcache_size // 1024} KiB")
    
    soc = BaseSoC(
        platform=platform,
        sys_clk_freq=int(args.sys_clk_freq),
        rom_size=rom_size,
        l2_size=l2_size,
        icache_size=icache_size,
        dcache_size=dcache_size,
        **soc_core_kwargs,
    )

    builder = Builder(soc, **builder_argdict(args))
    # Always skip Vivado synthesis on Linux
    print(f"[DEBUG] compile_software: {builder.compile_software}")
    print(f"[DEBUG] compile_gateware: {builder.compile_gateware}")
    try:
        builder.build()
        print("[INFO] Vivado synthesis and bitstream generation completed.")
    except Exception as e:
        print(f"[ERROR] Build failed with: {e}")
        import traceback
        traceback.print_exc()
        if sys.platform.startswith("linux") and (
            "Vivado" in str(e) or "Unable to find or source Vivado" in str(e) or "OSError" in str(type(e))):
            print("\n[INFO] Vivado synthesis is skipped on Linux due to missing Vivado toolchain.")
            print("[ACTION] Copy the following files to your Windows machine:")
            print(f"  - RTL: {os.path.join(args.output_dir, 'gateware', f'{args.build_name}.v')}")
            print(f"  - Constraints: {os.path.join(args.output_dir, 'gateware', 'digilent_nexys4ddr.xdc')}")
            print("  - Any other generated files needed for Vivado.")
            print("[INFO] Run Vivado synthesis on Windows to generate the bitstream.")
        else:
            raise

    bitstream = os.path.join(
        args.output_dir,
        "gateware",
        f"{args.build_name}.bit",
    )
    print(f"Bitstream: {bitstream}")
    print("UART: 115200 8-N-1")
    print("\n" + "="*60)
    print("MEMORY CONFIGURATION FOR TINYML")
    print("="*60)
    print("\nMemory Map:")
    print(f"  0x00000000 - 0x{rom_size-1:08X}  [{rom_size // 1024:3d} KiB]  On-Chip ROM (BIOS)")
    print(f"  0x80000000 - 0x87FFFFFF  [128   MiB]  DDR2 SDRAM (Main RAM)")
    print("\nBRAM Allocation:")
    print(f"  L2 Cache/Scratchpad:     {l2_size // 1024:3d} KiB")
    print(f"  I-Cache (VexRiscv):      {icache_size // 1024:3d} KiB")
    print(f"  D-Cache (VexRiscv):      {dcache_size // 1024:3d} KiB")
    total_cache = l2_size + icache_size + dcache_size
    print(f"  Total Cache/BRAM Used:   {total_cache // 1024:3d} KiB")
    print(f"\nSystem Configuration:")
    print(f"  CPU: VexRiscv (standard variant)")
    print(f"  System Clock: {int(args.sys_clk_freq / 1e6)} MHz")
    print("="*60)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
