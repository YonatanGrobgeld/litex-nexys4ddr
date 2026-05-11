#!/usr/bin/env python3
"""
LiteX peripheral wrapper for Exp LUT (Exponential Lookup Table) accelerator.

This module provides:
- CSR registers for index (write) and value (read)
- Memory-mapped interface to the hardware Exp LUT core
- Auto-generated CSR header functions: exp_lut_index_write(), exp_lut_value_read()
"""

from litex.soc.interconnect.csr import AutoCSR, CSRStorage, CSRStatus
from migen import *


class ExpLUTPeriph(Module, AutoCSR):
    """Exp LUT peripheral with CSR interface."""
    
    def __init__(self, platform=None, sys_clk_freq=None):
        """
        Initialize Exp LUT peripheral.
        
        Args:
            platform: LiteX platform object (may be None if not using board constraints)
            sys_clk_freq: System clock frequency (unused, present for consistency)
        """
        # CSR registers
        self.index = CSRStorage(16, name="index")
        self.value = CSRStatus(16, name="value")
        
        # Internal computation: read from index, compute, output to value
        # In real hardware, this would interface with exp_lut.v RTL
        # For now, a simple combinational path
        self.comb += [
            self.value.status.eq(self.index.storage),  # Placeholder: output = input
        ]
