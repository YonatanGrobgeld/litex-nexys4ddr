# Vivado Reports — baseline (plain VexRiscv, no accelerators)

Vivado 2025.2 reports for the pure-software baseline SoC (no DOT8, EXP-LUT, or
GEMV), generated **Mon May 11 2026** on the xc7a100t-csg324-1 at a 100 MHz
(10.0 ns) clock constraint. This is the correctness/performance reference the
accelerated build is measured against.

## Key results (post-route unless noted)

| Metric | Value | Source |
|---|---|---|
| Total on-chip power | **0.740 W** | `digilent_nexys4ddr_power.rpt` |
| Slice LUTs | **3889 (6.13%)** | `digilent_nexys4ddr_utilization_place.rpt` |
| LUT as Logic | 3747 (5.91%) | `digilent_nexys4ddr_utilization_place.rpt` |
| Slice Registers (FF) | **3153 (2.49%)** | `digilent_nexys4ddr_utilization_place.rpt` |
| DSPs | **4 (1.67%)** — VexRiscv RV32IM multiplier | `digilent_nexys4ddr_utilization_place.rpt` |
| Block RAM | 51 tiles (47 RAMB36, 34.81%) | `digilent_nexys4ddr_utilization_place.rpt` |
| Routing | Fully routed, 0 routing errors | `digilent_nexys4ddr_route_status.rpt` |

## Timing — MET at 100 MHz

`digilent_nexys4ddr_timing.rpt` (post-route):

```
WNS = +1.237 ns   TNS = 0.000 ns   0 failing endpoints / 9829
All user specified timing constraints are met.
```

The baseline closes timing cleanly at 100 MHz. (For contrast, the accelerated
build in `../accel_all_v2/` does not: WNS = -6.309 ns.)

Note: the VexRiscv RV32IM hardware multiplier maps to **4 DSP48 blocks** even in
this baseline (see the `DPIP-1`/`DPOP-2` DSP notes in the DRC report for
`VexRiscv/..._MUL_*`). DSP usage is therefore 4 in both baseline and
accelerated builds — the accelerators (GEMV, DOT8) map their MACs to LUT logic,
not to additional DSPs.
