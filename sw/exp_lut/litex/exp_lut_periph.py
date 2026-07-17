#!/usr/bin/env python3
# ==========================================================================
#  WHAT THIS FILE DOES (in simple words):
#  LiteX/Migen wrapper that puts the exp_lut.v circuit on the SoC bus: creates an
#  'index' register (CPU writes the question) and a 'value' register (CPU reads the
#  answer) and wires them to the Verilog module. Imported by hw/build_soc.py.
#  LiteX auto-generates the C accessors (exp_lut_index_write / exp_lut_value_read).
#  BIG PICTURE: Makes the LUT circuit addressable from firmware.
# ==========================================================================

import os
from litex.soc.interconnect.csr import AutoCSR, CSRStorage, CSRStatus
from migen import *

_RTL_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "..", "..", "..", "hw", "rtl", "exp_lut.v")


class ExpLUTPeriph(Module, AutoCSR):
    """Exp LUT peripheral: CPU writes index, reads exp(index) in Q10 fixed-point."""

    def __init__(self, platform=None, sys_clk_freq=None):
        if platform is not None:
            platform.add_source(_RTL_FILE)

        # CSR registers (32-bit bus → 4 bytes each)
        # Generated accessors: exp_lut_index_write() / exp_lut_value_read()
        self.index = CSRStorage(16, name="index")
        self.value = CSRStatus(16, name="value")

        _value = Signal(16)

        # exp_lut.v: index[4:0] → 5-bit signed (0=exp(0), -15=exp(-15))
        # Uses index[3:0] internally as LUT address; bit[4] is the sign.
        self.specials += Instance("exp_lut",
            i_clk=ClockSignal(),
            i_reset=ResetSignal(),
            i_index=self.index.storage[:5],
            o_value=_value,
        )

        self.comb += self.value.status.eq(_value)
