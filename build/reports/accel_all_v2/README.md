# Vivado Reports — accel_all_v2 (DOT8 + EXP-LUT + GEMV v2)

Vivado 2025.2 reports for the fully-accelerated SoC (GEMV v2 packed 4-lane MAC),
generated **Mon May 18 2026** on the xc7a100t-csg324-1 at a 100 MHz (10.0 ns) clock
constraint. These correspond to the GEMV v2 design that produces the reported
4.82× speedup.

## Key results (post-route unless noted)

| Metric | Value | Source |
|---|---|---|
| Total on-chip power | **0.792 W** | `digilent_nexys4ddr_power.rpt` |
| Slice LUTs | **6363 (10.04%)** | `digilent_nexys4ddr_utilization_place.rpt` |
| LUT as Logic | 5451 (8.60%) | `digilent_nexys4ddr_utilization_place.rpt` |
| Slice Registers (FF) | **5478 (4.32%)** | `digilent_nexys4ddr_utilization_place.rpt` |
| DSPs | **4 (1.67%)** — DSP48E1 | `digilent_nexys4ddr_utilization_place.rpt` |
| Routing | Fully routed, 0 routing errors | `digilent_nexys4ddr_route_status.rpt` |

## Timing — NOT met at 100 MHz

`digilent_nexys4ddr_timing.rpt` (post-route):

```
WNS = -6.309 ns   TNS = -447.818 ns   Failing endpoints: 390 / 20741
Timing constraints are not met.
```

`digilent_nexys4ddr_timing_synth.rpt` (synthesis): WNS = -6.086 ns, 96 failing endpoints.

The accelerated design does **not** close timing at 100 MHz. The worst path is the
GEMV v2 4-lane MAC (multiply + adder-tree + accumulate combinational chain). The
bitstream routes cleanly and produces bit-identical `ENC_CKSUM` output at room
temperature, but it is operating outside timing closure at 100 MHz. To close timing,
pipeline the GEMV dot4 stage (one extra latency cycle) or lower `sys_clk_freq`
(~75 MHz). Reported cycle counts are clock-independent; latency in ms scales with
whatever clock the design is actually closed at.

Hold timing is met (WHS = +0.026 ns).
