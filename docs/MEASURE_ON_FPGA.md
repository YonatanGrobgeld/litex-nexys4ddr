# Measure Inference Cycles on the FPGA

This is the step **after** programming the bitstream (`docs/PROGRAM_FPGA.md`).
It uploads a TinyFormer firmware over UART, runs the inference demo, and records
the **hardware cycle count** the firmware reports — the authoritative performance
number (baseline vs. accelerated ⇒ speedup).

The two host scripts live in `scripts/`:

| Script | Measures |
|---|---|
| `scripts/run_baseline_and_measure.py`  | Baseline firmware (pure software) |
| `scripts/run_accel_all_and_measure.py` | Accelerated firmware (GEMV + EXP-LUT) |

They are self-contained: each one **auto-uploads `firmware.bin` via the LiteX SFL
protocol** (the same wire protocol `litex_term` uses), so you do **not** need a
separate `litex_term` step.

---

## What you need first

1. **Board programmed** with the SoC bitstream — see `docs/PROGRAM_FPGA.md`.
   (The bitstream defines the CPU + accelerators; the firmware you upload must
   match it — e.g. don't run accel firmware on a no-accelerator bitstream.)
2. **A `firmware.bin`** for the mode you want to measure. This is built in the
   **sibling repo** `TinyML_algo` (the firmware/algorithm side), not here:
   - baseline → build the `baseline` firmware
   - accelerated → build the `accel_all` firmware
   See `TinyML_algo/README.md` for the firmware build commands. Copy the
   resulting `firmware.bin` next to the script (or pass `--firmware <path>`).
3. **Python + pyserial** on the host: `pip install pyserial`.
4. **The serial port** the board enumerates as (Windows: `COM3`, …; Linux:
   `/dev/ttyUSB1`). Close any other program holding the port (PuTTY, Vivado).

> Cross-repo note: the **bitstream** comes from this repo (`litex-nexys4ddr`),
> the **firmware.bin** comes from `TinyML_algo`. The measurement joins the two.

---

## Run it

Baseline:

```bash
python scripts/run_baseline_and_measure.py --port COM3 --runs 10 --firmware firmware.bin
```

Accelerated:

```bash
python scripts/run_accel_all_and_measure.py --port COM3 --runs 10 --firmware firmware.bin
```

Useful flags (both scripts): `--port` (serial port; auto-detects if omitted),
`--runs` (measurement iterations, default 10), `--firmware` (path to the .bin),
`--verbose` (print every UART line), `--power_val estimate|<watts>` (label the
power column), `--out <file.csv>` (results file).

---

## What the script does (the flow)

1. **Reset the board** with a DTR pulse. The LiteX BIOS boots, runs its memtest,
   and waits for a `serialboot` request. *(If nothing happens in ~5 s, press the
   board's RESET/PROG button.)*
2. **SFL upload:** the script answers the BIOS boot request and streams
   `firmware.bin` to `0x40000000` (calibrated, CRC-checked frames), then sends a
   JUMP so the CPU starts the firmware.
3. **Wait for `Ready`** — the firmware's prompt that it has started.
4. **For each run:** send `s`, then read UART lines until the `Done` token.
   The firmware prints a `CYCLES=<n>` line — the on-chip hardware timer count.
5. **Report:** time = `CYCLES / 100 MHz`. It prints per-run and summary stats and
   writes a CSV (`results_baseline.csv` / `results_accel_all.csv`).

The **firmware `CYCLES` value is authoritative** — the script also prints a
Python wall-clock time, but that under-measures (host can drop serial bytes), so
always use the firmware timer.

---

## Reading the result

```
FIRMWARE TIMER (authoritative — hardware-measured cycles @ 100 MHz)
  Avg :  157.550 ms   (0.157550 s)
```

The number you cite is the **average CYCLES** (and `CYCLES / 100 MHz` in ms).

**Speedup** = `baseline_cycles / accelerated_cycles`. Run both scripts (each with
its matching `firmware.bin`) and divide. The `ENC_CKSUM` line printed each run
must be identical between baseline and accelerated — that proves the speedup is
real (same output), not skipped work.

---

## If it doesn't work

- **No boot request / no `Ready`:** wrong bitstream loaded, wrong COM port, or the
  board needs a manual RESET. Re-program per `docs/PROGRAM_FPGA.md`.
- **Only `s` echoed back / no `CYCLES`:** the firmware isn't the one you think, or
  it doesn't match the bitstream (e.g. accel firmware on a plain-CPU bitstream).
- **Calibration errors during upload:** flaky USB/serial — retry; lower host load.
- Every run is logged to `serial_debug*.log` for post-mortem.
