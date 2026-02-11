#!/usr/bin/env python3
import argparse
import os
import sys

from migen import ClockDomain, Module

from litex.soc.integration.builder import Builder, builder_args, builder_argdict
from litex.soc.integration.soc_core import SoCCore, soc_core_args, soc_core_argdict
from litex.soc.cores.clock import S7PLL

from litex_boards.platforms import digilent_nexys4ddr

from litedram.phy import s7ddrphy
from litedram.modules import MT47H64M16


class _CRG(Module):
    def __init__(self, platform, sys_clk_freq):
        self.clock_domains.cd_sys = cd_sys = ClockDomain()
        self.clock_domains.cd_sys4x = cd_sys4x = ClockDomain()

        clk100 = platform.request("clk100")
        rst = ~platform.request("cpu_reset")

        self.submodules.pll = pll = S7PLL(speedgrade=-1)
        pll.register_clkin(clk100, 100e6)
        pll.create_clkout(cd_sys, sys_clk_freq)
        pll.create_clkout(cd_sys4x, 4 * sys_clk_freq)
        pll.reset.eq(rst)


class BaseSoC(SoCCore):
    def __init__(self, platform, sys_clk_freq, 
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
        # ROM size: 256 KiB default
        if rom_size is None:
            rom_size = 256 * 1024
        
        defaults.update(kwargs)
        
        # Create clock/reset generator
        self.crg = _CRG(platform, sys_clk_freq)

        # Initialize SoCCore
        super().__init__(
            platform=platform,
            clk_freq=sys_clk_freq,
            integrated_rom_size=rom_size,
            **defaults,
        )

        # DDR2 SDRAM with optional L2 cache
        if not self.integrated_main_ram_size:
            # L2 cache size: 128 KiB default, configurable to 256 KiB
            if l2_size is None:
                l2_size = 128 * 1024
            
            # Create DDR2 PHY for Artix-7 with appropriate 4:1 ratio
            self.ddrphy = s7ddrphy.A7DDRPHY(
                pads=platform.request("ddram"),
                memtype="DDR2",
                nphases=4,
                sys_clk_freq=sys_clk_freq,
                iodelay_clk_freq=200e6
            )
            
            # Add DDR2 SDRAM
            self.add_sdram(
                "sdram",
                phy=self.ddrphy,
                module=MT47H64M16(sys_clk_freq, "1:4"),
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
        default=_default_sys_clk_freq(platform),
        type=float,
        help="System clock frequency in Hz (default: 100 MHz).",
    )
    
    parser.add_argument(
        "--rom-size",
        default=None,
        type=int,
        help="On-chip ROM size in bytes (default: 256 KiB).",
    )
    
    parser.add_argument(
        "--l2-size",
        default=None,
        type=int,
        help="L2 cache size in bytes, configurable to 128 KiB (default) or 256 KiB.",
    )
    
    parser.add_argument(
        "--icache-size",
        default=None,
        type=int,
        help="CPU instruction cache size in bytes (default: 16 KiB).",
    )
    
    parser.add_argument(
        "--dcache-size",
        default=None,
        type=int,
        help="CPU data cache size in bytes (default: 16 KiB).",
    )

    parser.set_defaults(
        output_dir=output_dir,
        build_name="nexys4ddr_vexriscv",
        build_backend="litex",
    )

    args = parser.parse_args()
    
    soc = BaseSoC(
        platform=platform,
        sys_clk_freq=int(args.sys_clk_freq),
        rom_size=args.rom_size,
        l2_size=args.l2_size,
        icache_size=args.icache_size,
        dcache_size=args.dcache_size,
        **soc_core_argdict(args),
    )

    builder = Builder(soc, **builder_argdict(args))
    builder.build()

    bitstream = os.path.join(
        args.output_dir,
        "gateware",
        f"{args.build_name}.bit",
    )
    print(f"Bitstream: {bitstream}")
    print("UART: 115200 8-N-1")
    print("\nMemory Configuration:")
    print(f"  ROM: {args.rom_size or 256 * 1024} bytes")
    print(f"  DDR2 SDRAM: 128 MB (0x08000000)")
    print(f"  L2 Cache: {args.l2_size or 128 * 1024} bytes")
    print(f"  I-Cache: {args.icache_size or 16 * 1024} bytes")
    print(f"  D-Cache: {args.dcache_size or 16 * 1024} bytes")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
