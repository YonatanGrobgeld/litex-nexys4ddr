#!/usr/bin/env python3
"""
LiteX peripheral wrapper for GEMV (General Matrix-Vector multiply) accelerator.

This module provides:
- CSR registers for control (start, reset) and status (done, error)
- Data ports for matrix/vector write and result read
- Auto-generated CSR header functions:
  - gemv_ctrl_write(), gemv_ctrl_read()
  - gemv_status_read()
  - gemv_addr_write(), gemv_addr_read()
  - gemv_data_write(), gemv_data_read()
"""

from litex.soc.interconnect.csr import AutoCSR, CSRStorage, CSRStatus
from migen import *


class GEMVPeriph(Module, AutoCSR):
    """GEMV (matrix-vector multiply) peripheral with CSR interface."""
    
    def __init__(self, platform=None, sys_clk_freq=None):
        """
        Initialize GEMV peripheral.
        
        Args:
            platform: LiteX platform object (may be None if not using board constraints)
            sys_clk_freq: System clock frequency (unused, present for consistency)
        """
        # Control register: bit[0]=start, bit[1]=reset
        self.ctrl = CSRStorage(2, name="ctrl")
        
        # Status register: bit[0]=done, bit[1]=error, bit[15:2]=unused
        self.status = CSRStatus(16, name="status")
        
        # Address register: select matrix/vector row/column for data access
        self.addr = CSRStorage(16, name="addr")
        
        # Data input register: write matrix/vector values
        self.data_in = CSRStorage(32, name="data_in")
        
        # Data output register: read computation results
        self.data_out = CSRStatus(32, name="data_out")
        
        # Internal state
        self.done = Signal(reset=0)
        self.error = Signal(reset=0)
        self.busy = Signal(reset=0)
        
        # Simple state machine for demonstration
        # In real hardware, this would interface with the actual GEMV core
        self.comb += [
            self.status.status.eq(Cat(self.done, self.error)),
            self.data_out.status.eq(0x12345678),  # Placeholder output
        ]
        
        # On write to ctrl[0] (start), set busy and done signals
        # (In real hardware, this would trigger the GEMV computation)
        self.sync += [
            If(self.ctrl.re & self.ctrl.storage[0],  # start bit written
                self.busy.eq(1),
                self.done.eq(0),
            ).Elif(self.busy,
                self.busy.eq(0),
                self.done.eq(1),
            ),
            If(self.ctrl.re & self.ctrl.storage[1],  # reset bit written
                self.done.eq(0),
                self.error.eq(0),
                self.busy.eq(0),
            ),
        ]
