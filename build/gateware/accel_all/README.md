# Vivado Reports — accel_all (GEMV v3 pipelined + EXP-LUT)

Vivado 2025.2 reports for the accelerated SoC, generated **Fri Jul 17 2026** on the
xc7a100t-csg324-1 at a 100 MHz (10.0 ns) clock constraint. This is the
timing-clean configuration: the GEMV core is pipelined (v3) and the single-cycle
DOT8 custom instruction was removed (its execute→bypass path could not close
timing); acceleration is provided by GEMV + EXP-LUT.

## Timing — MET at 100 MHz

`digilent_nexys4ddr_timing.rpt` (post-route):

```
WNS = +0.019 ns   TNS = 0.000 ns   0 failing endpoints / 20969
All user specified timing constraints are met.
```

Synthesis WNS = +0.125 ns; hold (WHS) = +0.026 ns; fully routed, 0 routing errors.
The worst path is the GEMV pipelined MAC (`gemv_core/w_word_c_reg → dot4_r_reg`) —
now split across register stages so it closes with positive slack.

## Key results (post-route)

| Metric | Value | Source |
|---|---|---|
| Total on-chip power | **0.785 W** | `digilent_nexys4ddr_power.rpt` |
| Slice LUTs | **6026 (9.50%)** | `digilent_nexys4ddr_utilization_place.rpt` |
| LUT as Logic | 5114 (8.07%) | `digilent_nexys4ddr_utilization_place.rpt` |
| Slice Registers (FF) | **5582 (4.40%)** | `digilent_nexys4ddr_utilization_place.rpt` |
| DSPs | **4 (1.67%)** — VexRiscv RV32IM multiplier | `digilent_nexys4ddr_utilization_place.rpt` |
| Block RAM | 51 tiles (47 RAMB36, 34.81%) | `digilent_nexys4ddr_utilization_place.rpt` |
| Routing | Fully routed, 0 errors | `digilent_nexys4ddr_route_status.rpt` |

Note: the 4 DSPs are the VexRiscv CPU multiplier; GEMV and EXP-LUT use LUT logic /
distributed RAM, not DSPs.
