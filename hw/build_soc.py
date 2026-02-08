#!/usr/bin/env python3
import argparse
import os
import sys

from migen import ClockDomain, Module

from litex.soc.integration.builder import Builder, builder_args, builder_argdict
from litex.soc.integration.soc_core import SoCCore, soc_core_args, soc_core_argdict
from litex.soc.cores.clock import S7PLL

from litex_boards.platforms import digilent_nexys4ddr


class _CRG(Module):
    def __init__(self, platform, sys_clk_freq):
        self.clock_domains.cd_sys = cd_sys = ClockDomain()

        clk100 = platform.request("clk100")
        rst = ~platform.request("cpu_reset")

        self.submodules.pll = pll = S7PLL(speedgrade=-1)
        pll.register_clkin(clk100, 100e6)
        pll.create_clkout(cd_sys, sys_clk_freq)
        pll.reset.eq(rst)


class BaseSoC(SoCCore):
    def __init__(self, platform, sys_clk_freq, **kwargs):
        # Set sensible defaults for VexRiscv with caches
        defaults = {
            "cpu_type": "vexriscv",
            "cpu_variant": "standard",
            "with_uart": True,
            "with_timer": True,
            "with_cpu_icache": True,
            "with_cpu_dcache": True,
            "cpu_icache_size": 8 * 1024,
            "cpu_dcache_size": 8 * 1024,
            "uart_name": "serial",
            "uart_baudrate": 115200,
        }
        defaults.update(kwargs)
        
        self.crg = _CRG(platform, sys_clk_freq)

        super().__init__(
            platform=platform,
            clk_freq=sys_clk_freq,
            **defaults,
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

    parser = argparse.ArgumentParser(description="LiteX SoC for Nexys4 DDR")
    builder_args(parser)
    soc_core_args(parser)

    parser.add_argument(
        "--sys-clk-freq",
        default=_default_sys_clk_freq(platform),
        type=float,
        help="System clock frequency in Hz.",
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

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
