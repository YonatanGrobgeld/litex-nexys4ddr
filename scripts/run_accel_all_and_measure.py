#!/usr/bin/env python3
"""
FPGA Accel-All (DOT8 + EXP LUT + GEMV) Measurement Script

Opens the serial port, waits for the LiteX BIOS boot request, uploads
firmware.bin automatically via the SFL protocol, then runs 10 inference
passes and records wall-clock time to results_accel_all.csv.

Usage:
  python run_accel_all_and_measure.py --port COM3 --runs 10 --power_val estimate
"""
import serial
import serial.tools.list_ports
import time
import sys
import csv
import argparse
from pathlib import Path

# ---------------------------------------------------------------------------
# SFL (LiteX Serial Firmware Loader) — minimal implementation
# ---------------------------------------------------------------------------
_SFL_MAGIC_REQ = b"sL5DdSMmkekro\n"
_SFL_MAGIC_ACK = b"z6IHG7cYDID6o\n"
_SFL_CMD_LOAD  = 0x01
_SFL_CMD_JUMP  = 0x02

_CRC16_TABLE = [
    0x0000,0x1021,0x2042,0x3063,0x4084,0x50A5,0x60C6,0x70E7,
    0x8108,0x9129,0xA14A,0xB16B,0xC18C,0xD1AD,0xE1CE,0xF1EF,
    0x1231,0x0210,0x3273,0x2252,0x52B5,0x4294,0x72F7,0x62D6,
    0x9339,0x8318,0xB37B,0xA35A,0xD3BD,0xC39C,0xF3FF,0xE3DE,
    0x2462,0x3443,0x0420,0x1401,0x64E6,0x74C7,0x44A4,0x5485,
    0xA56A,0xB54B,0x8528,0x9509,0xE5EE,0xF5CF,0xC5AC,0xD58D,
    0x3653,0x2672,0x1611,0x0630,0x76D7,0x66F6,0x5695,0x46B4,
    0xB75B,0xA77A,0x9719,0x8738,0xF7DF,0xE7FE,0xD79D,0xC7BC,
    0x48C4,0x58E5,0x6886,0x78A7,0x0840,0x1861,0x2802,0x3823,
    0xC9CC,0xD9ED,0xE98E,0xF9AF,0x8948,0x9969,0xA90A,0xB92B,
    0x5AF5,0x4AD4,0x7AB7,0x6A96,0x1A71,0x0A50,0x3A33,0x2A12,
    0xDBFD,0xCBDC,0xFBBF,0xEB9E,0x9B79,0x8B58,0xBB3B,0xAB1A,
    0x6CA6,0x7C87,0x4CE4,0x5CC5,0x2C22,0x3C03,0x0C60,0x1C41,
    0xEDAE,0xFD8F,0xCDEC,0xDDCD,0xAD2A,0xBD0B,0x8D68,0x9D49,
    0x7E97,0x6EB6,0x5ED5,0x4EF4,0x3E13,0x2E32,0x1E51,0x0E70,
    0xFF9F,0xEFBE,0xDFDD,0xCFFC,0xBF1B,0xAF3A,0x9F59,0x8F78,
    0x9188,0x81A9,0xB1CA,0xA1EB,0xD10C,0xC12D,0xF14E,0xE16F,
    0x1080,0x00A1,0x30C2,0x20E3,0x5004,0x4025,0x7046,0x6067,
    0x83B9,0x9398,0xA3FB,0xB3DA,0xC33D,0xD31C,0xE37F,0xF35E,
    0x02B1,0x1290,0x22F3,0x32D2,0x4235,0x5214,0x6277,0x7256,
    0xB5EA,0xA5CB,0x95A8,0x8589,0xF56E,0xE54F,0xD52C,0xC50D,
    0x34E2,0x24C3,0x14A0,0x0481,0x7466,0x6447,0x5424,0x4405,
    0xA7DB,0xB7FA,0x8799,0x97B8,0xE75F,0xF77E,0xC71D,0xD73C,
    0x26D3,0x36F2,0x0691,0x16B0,0x6657,0x7676,0x4615,0x5634,
    0xD94C,0xC96D,0xF90E,0xE92F,0x99C8,0x89E9,0xB98A,0xA9AB,
    0x5844,0x4865,0x7806,0x6827,0x18C0,0x08E1,0x3882,0x28A3,
    0xCB7D,0xDB5C,0xEB3F,0xFB1E,0x8BF9,0x9BD8,0xABBB,0xBB9A,
    0x4A75,0x5A54,0x6A37,0x7A16,0x0AF1,0x1AD0,0x2AB3,0x3A92,
    0xFD2E,0xED0F,0xDD6C,0xCD4D,0xBDAA,0xAD8B,0x9DE8,0x8DC9,
    0x7C26,0x6C07,0x5C64,0x4C45,0x3CA2,0x2C83,0x1CE0,0x0CC1,
    0xEF1F,0xFF3E,0xCF5D,0xDF7C,0xAF9B,0xBFBA,0x8FD9,0x9FF8,
    0x6E17,0x7E36,0x4E55,0x5E74,0x2E93,0x3EB2,0x0ED1,0x1EF0,
]


def _crc16(data: bytes) -> int:
    crc = 0
    for b in data:
        crc = _CRC16_TABLE[((crc >> 8) ^ b) & 0xFF] ^ (crc << 8)
    return crc & 0xFFFF


def _sfl_frame(cmd: int, payload: bytes) -> bytes:
    """Encode one SFL frame: [len(1)] [crc(2)] [cmd(1)] [payload(N)]"""
    cmd_b = bytes([cmd])
    crc   = _crc16(cmd_b + payload)
    return bytes([len(payload)]) + crc.to_bytes(2, 'big') + cmd_b + payload


def sfl_upload(ser, firmware_path: str, boot_addr: int = 0x40000000,
               magic_timeout: float = 25.0) -> bool:
    """
    Trigger a board reset via DTR pulse, wait for the BIOS upload request,
    then upload firmware via SFL.  Returns True on success.
    """
    # Pulse DTR High→Low to trigger board reset (works on Nexys4DDR).
    # If this doesn't reset the board automatically, the user is prompted
    # to press the physical RESET button.
    print("\n--- Triggering board reset via DTR pulse ---")
    try:
        ser.dtr = True
        time.sleep(0.15)
        ser.dtr = False
    except Exception:
        pass
    ser.reset_input_buffer()

    print(f"--- Waiting for BIOS boot request (up to {magic_timeout:.0f}s) ---")
    print("    (If nothing happens in 5 s, press the RESET button on the board)")

    # Bulk-read approach: accumulate bytes and search for magic as substring.
    accumulated = bytearray()
    deadline    = time.time() + magic_timeout
    ser.timeout = 0.5

    found = False
    while time.time() < deadline:
        data = ser.read(256)
        if data:
            accumulated += data
            if _SFL_MAGIC_REQ in accumulated:
                found = True
                break

    if not found:
        print("ERROR: BIOS did not send upload request.")
        print("       Make sure the board is powered, COM port is correct,")
        print("       and try pressing the RESET button on the board manually.")
        return False

    print("[SFL] Firmware download request received.")
    ser.write(_SFL_MAGIC_ACK)
    time.sleep(0.05)          # let BIOS finish processing the magic ACK

    fw = Path(firmware_path).read_bytes()
    total = len(fw)

    CHUNK     = 60     # data bytes per frame (4-byte addr + 60 data = 64-byte payload)
    N_CAL     = 16     # calibration frames (same as litex_term)

    # Calibration: send N_CAL zero frames to let the BIOS receiver sync up.
    # Read and verify ACKs like litex_term does.
    print("[SFL] Calibrating link ...")
    cal_payload = boot_addr.to_bytes(4, 'big') + bytes(CHUNK)
    cal_frame   = _sfl_frame(_SFL_CMD_LOAD, cal_payload)
    for _ in range(N_CAL):
        ser.write(cal_frame)
        time.sleep(10e-6)   # 10 µs inter-frame (same as litex_term)
    time.sleep(0.5)         # wait for all ACKs to arrive
    cal_acks = bytearray()
    while ser.in_waiting:
        cal_acks += ser.read(ser.in_waiting)
    n_ok  = cal_acks.count(ord('K'))
    n_err = cal_acks.count(ord('C')) + cal_acks.count(ord('E'))
    print(f"[SFL] Calibration done: {n_ok} OK, {n_err} errors "
          f"(raw: {bytes(cal_acks)!r})")
    if n_err > 0:
        print("[SFL] WARNING: calibration errors — upload may be unreliable")

    print(f"[SFL] Uploading {firmware_path} ({total} bytes) to 0x{boot_addr:08x} ...")

    # Use a 2-second ACK timeout per frame — same policy as litex_term --safe.
    # Send one frame, block on ser.read(1) for up to 2 s, retry on error.
    # Do NOT reset_input_buffer() before each send: purging can discard a
    # late-arriving 'K' from the previous retry and cause infinite retries.
    ser.timeout = 2.0

    addr  = boot_addr
    pos   = 0
    frame_num = 0
    while pos < total:
        chunk   = fw[pos : pos + CHUNK]
        payload = addr.to_bytes(4, 'big') + chunk
        frame   = _sfl_frame(_SFL_CMD_LOAD, payload)
        frame_num += 1

        for attempt in range(8):
            ser.write(frame)
            ack = ser.read(1)   # blocks up to 2 s for exactly one ACK byte
            if ack == b'K':
                break
            elif ack == b'C':
                print(f"  [0x{addr:08x} frame#{frame_num} attempt {attempt}] "
                      f"CRC error — retry")
                ser.reset_input_buffer()
            elif ack == b'E':
                print(f"  [0x{addr:08x} frame#{frame_num} attempt {attempt}] "
                      f"BIOS timeout — retry")
                ser.reset_input_buffer()
            else:
                print(f"  [0x{addr:08x} frame#{frame_num} attempt {attempt}] "
                      f"unexpected ACK {ack!r} — retry")
                ser.reset_input_buffer()
        else:
            print(f"[SFL] Too many retries at 0x{addr:08x} (frame#{frame_num})")
            return False

        addr += len(chunk)
        pos  += len(chunk)

        if frame_num % 10 == 0 or pos >= total:
            pct = 100 * pos // total
            print(f"  {pos}/{total} bytes ({pct}%) — frame#{frame_num}")

    print("[SFL] Upload complete.")

    # Drain any stale bytes that might have arrived during the upload,
    # then send the JUMP frame and retry until BIOS acknowledges with 'K'.
    # The BIOS sends 'K' *before* jumping, so 'E' means it timed out reading
    # the frame — simply resend it (the BIOS is back at i=0, no timer running).
    time.sleep(0.05)
    ser.reset_input_buffer()

    jump_frame = _sfl_frame(_SFL_CMD_JUMP, boot_addr.to_bytes(4, 'big'))
    ser.timeout = 2.0
    jumped = False
    for jump_attempt in range(8):
        ser.write(jump_frame)
        ack = ser.read(1)
        if ack == b'K':
            print(f"[SFL] Jump OK (attempt {jump_attempt + 1})")
            jumped = True
            break
        print(f"[SFL] Jump attempt {jump_attempt + 1}: ACK={ack!r} — retry")
        time.sleep(0.05)

    if not jumped:
        print("[SFL] ERROR: BIOS never acknowledged the JUMP frame.")
        return False

    print("[SFL] Waiting for firmware ...")
    return True


def wait_for_ready(ser, timeout: float = 10.0, verbose: bool = False) -> bool:
    """Read lines until 'Ready' appears (firmware started) or timeout."""
    print(f"\n--- Waiting for firmware 'Ready' ({timeout:.0f}s) ---")
    ser.timeout = 0.5
    deadline = time.time() + timeout
    while time.time() < deadline:
        raw = ser.readline()
        if raw:
            line = raw.decode('utf-8', errors='replace').strip()
            if verbose and line:
                print(f"  FW: {line}")
            if line == 'Ready':
                print("Firmware is ready.")
                return True
    print("ERROR: Firmware did not print 'Ready' within the timeout.")
    return False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def find_serial_port():
    ports = list(serial.tools.list_ports.comports())
    candidates = [p.device for p in ports if "USB" in p.device or "ACM" in p.device]
    if not candidates:
        return None
    candidates.sort()
    for c in candidates:
        if "ttyUSB1" in c:
            return c
    return candidates[0]


def bytes_to_hex(data):
    return ' '.join(f'{b:02X}' for b in data)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description='Upload firmware + run accel_all on FPGA and measure time.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_accel_all_and_measure.py --port COM3 --runs 10 --power_val estimate
  python run_accel_all_and_measure.py --port COM3 --runs 10 --verbose
        """
    )
    parser.add_argument('--port',      help='Serial port (e.g. COM3)')
    parser.add_argument('--baud',      type=int,   default=115200)
    parser.add_argument('--timeout_s', type=float, default=60.0,
                        help='Timeout per measurement run in seconds')
    parser.add_argument('--bytesize',  type=int,   default=8,   choices=[5,6,7,8])
    parser.add_argument('--parity',    default='N', choices=['N','E','O','M','S'])
    parser.add_argument('--stopbits',  type=float, default=1,   choices=[1, 1.5, 2])
    parser.add_argument('--xonxoff',   action='store_true')
    parser.add_argument('--rtscts',    action='store_true')
    parser.add_argument('--dsrdtr',    action='store_true')

    parser.add_argument('--runs',      type=int,   default=10)
    parser.add_argument('--out',       default='results_accel_all.csv')
    parser.add_argument('--power_val', default=None,
                        help='Measured power in Watts (float) or "estimate"')

    parser.add_argument('--firmware',  default='firmware.bin',
                        help='Firmware binary to upload (default: firmware.bin)')
    parser.add_argument('--boot_addr', default='0x40000000',
                        help='Boot address (default: 0x40000000)')
    parser.add_argument('--magic_timeout', type=float, default=20.0,
                        help='Seconds to wait for BIOS upload request')

    parser.add_argument('--done_token',       default='Done')
    parser.add_argument('--substring_match',  action='store_true')
    parser.add_argument('--case_insensitive', action='store_true')

    parser.add_argument('--debug_log', default='serial_debug_accel.log')
    parser.add_argument('--verbose',   action='store_true')

    args = parser.parse_args()

    port = args.port
    if not port:
        print("Auto-detecting serial port...")
        port = find_serial_port()
        if not port:
            print("Error: No serial port found. Please specify --port.")
            sys.exit(1)
        print(f"Detected port: {port}")

    print(f"\n--- Opening Serial Port ---")
    print(f"Port: {port}  Baud: {args.baud}")

    try:
        ser = serial.Serial()
        ser.port               = port
        ser.baudrate           = args.baud
        ser.bytesize           = args.bytesize
        ser.parity             = args.parity
        ser.stopbits           = args.stopbits
        ser.timeout            = args.timeout_s
        ser.xonxoff            = args.xonxoff
        ser.rtscts             = args.rtscts
        ser.dsrdtr             = args.dsrdtr
        ser.inter_byte_timeout = 0.1
        ser.open()
    except Exception as e:
        print(f"Error opening {port}: {e}")
        sys.exit(1)

    # ---- firmware upload -----------------------------------------------
    fw_path    = args.firmware
    boot_addr  = int(args.boot_addr, 16)

    if not Path(fw_path).exists():
        print(f"ERROR: firmware file '{fw_path}' not found.")
        print("       Place firmware.bin in the same directory or use --firmware <path>.")
        ser.close()
        sys.exit(1)

    ok = sfl_upload(ser, fw_path, boot_addr=boot_addr,
                    magic_timeout=args.magic_timeout)
    if not ok:
        print("Firmware upload failed.")
        ser.close()
        sys.exit(1)

    fw_ready = wait_for_ready(ser, timeout=15.0, verbose=args.verbose)
    if not fw_ready:
        print("Firmware did not start.  Check that the correct bitstream is loaded.")
        ser.close()
        sys.exit(1)

    # ---- power value -------------------------------------------------------
    if args.power_val:
        if args.power_val.lower() == "estimate":
            power_val = "Estimate (Vivado report_power)"
        else:
            try:
                float(args.power_val)
                power_val = f"{args.power_val} W (Measured)"
            except ValueError:
                power_val = "Estimate (Vivado report_power)"
    else:
        print("\nEnter measured power in Watts, or press Enter to use Estimate.")
        power_str = input("Measured power (W) > ").strip()
        power_val = "Estimate (Vivado report_power)"
        if power_str:
            try:
                float(power_str)
                power_val = f"{power_str} W (Measured)"
            except ValueError:
                pass

    # ---- debug log ---------------------------------------------------------
    debug_log = None
    try:
        debug_log = open(args.debug_log, 'w', encoding='utf-8')
        debug_log.write(f"=== FPGA Accel-All Measurement Debug Log ===\n")
        debug_log.write(f"Port: {port}  Baud: {args.baud}\n")
        debug_log.write(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        debug_log.write("=" * 60 + "\n\n")
        debug_log.flush()
    except Exception as e:
        print(f"Warning: could not open debug log: {e}")

    # ---- measurement runs --------------------------------------------------
    print(f"\n--- Starting {args.runs} Measurement Runs (MODE: DOT8+LUT+GEMV) ---")
    ser.timeout = args.timeout_s

    results      = []   # Python wall-clock (kept for backwards compat / printout)
    fw_cycles    = []   # Firmware-reported CYCLES (authoritative)
    fw_times_s   = []   # CYCLES / 100 MHz, in seconds
    SYS_CLK_HZ   = 100_000_000   # actual hardware clock

    done_token = args.done_token
    if args.case_insensitive:
        done_token = done_token.lower()

    for i in range(args.runs):
        print(f"\nRun {i+1}/{args.runs}...", end='', flush=True)
        ser.reset_input_buffer()

        run_output       = []
        raw_bytes_received = bytearray()

        t0 = time.perf_counter()
        ser.write(b's')

        if debug_log:
            debug_log.write(f"\n=== Run {i+1}/{args.runs} at {time.strftime('%H:%M:%S')} ===\n")
            debug_log.write("Sent: 's'\n")
            debug_log.flush()

        found_done = False
        line_count = 0

        while True:
            line_bytes = ser.readline()
            if line_bytes:
                raw_bytes_received.extend(line_bytes)
                line_count += 1
                try:
                    line = line_bytes.decode('utf-8', errors='replace').strip()
                except Exception:
                    line = "[DECODE ERROR]"
                if line:
                    run_output.append(line)
                    if debug_log:
                        debug_log.write(f"{line}\n")
                        debug_log.flush()
                    if args.verbose:
                        print(f"\n  RX: {line}", end='', flush=True)

                    check_line  = line.lower()  if args.case_insensitive else line
                    check_token = done_token.lower() if args.case_insensitive else done_token
                    if args.substring_match:
                        if check_token in check_line:
                            found_done = True
                            break
                    else:
                        if check_line == check_token:
                            found_done = True
                            break
            else:
                if debug_log:
                    debug_log.write(f"[TIMEOUT after {line_count} lines]\n")
                    debug_log.flush()
                break

        t1 = time.perf_counter()

        if found_done:
            dt = t1 - t0
            results.append(dt)
            # Parse firmware-reported CYCLES from the captured output (authoritative
            # measurement; Python's wall-clock under-measures when bytes are lost).
            run_cycles = None
            for ln in run_output:
                if ln.startswith("CYCLES="):
                    try:
                        run_cycles = int(ln.split("=", 1)[1].strip())
                    except ValueError:
                        run_cycles = None
                    break
            if run_cycles is not None:
                fw_cycles.append(run_cycles)
                fw_time = run_cycles / SYS_CLK_HZ
                fw_times_s.append(fw_time)
                print(f" OK wall={dt:.4f}s  fw={fw_time*1000:.2f}ms (cycles={run_cycles})")
            else:
                print(f" OK wall={dt:.4f}s  (no CYCLES line captured — Python lost data)")
        else:
            print(f" TIMEOUT/ERROR (no '{args.done_token}')")
            print(f"    Received {line_count} lines, {len(raw_bytes_received)} bytes")
            if line_count == 0:
                print(f"    NO DATA — firmware may be stuck (GEMV hw timeout?)")
            else:
                print(f"    Last lines: {run_output[-5:]}")

        time.sleep(0.5)

    if debug_log:
        debug_log.write("\n" + "=" * 60 + "\n")
        debug_log.write(f"Done: {len(results)}/{args.runs} successful\n")
        debug_log.close()

    ser.close()

    if not results:
        print("\nNo successful runs.")
        sys.exit(1)

    import statistics
    avg_wall = statistics.mean(results)
    min_wall = min(results)
    max_wall = max(results)
    std_wall = statistics.stdev(results) if len(results) > 1 else 0.0

    # Firmware-side stats (authoritative)
    have_fw = len(fw_times_s) > 0
    if have_fw:
        avg_fw = statistics.mean(fw_times_s)
        min_fw = min(fw_times_s)
        max_fw = max(fw_times_s)
        std_fw = statistics.stdev(fw_times_s) if len(fw_times_s) > 1 else 0.0
    else:
        avg_fw = min_fw = max_fw = std_fw = 0.0

    print("\n" + "=" * 60)
    print("MEASUREMENT SUMMARY  (MODE: DOT8 + EXP LUT + GEMV)")
    print("=" * 60)
    print(f"Successful runs    : {len(results)}/{args.runs}")
    print(f"Firmware CYCLES captured: {len(fw_times_s)}/{args.runs}")
    print()
    print("FIRMWARE TIMER (authoritative — hardware-measured cycles @ 100 MHz)")
    if have_fw:
        print(f"  Avg : {avg_fw*1000:8.3f} ms   ({avg_fw:.6f} s)")
        print(f"  Min : {min_fw*1000:8.3f} ms")
        print(f"  Max : {max_fw*1000:8.3f} ms")
        print(f"  Std : {std_fw*1000:8.3f} ms")
    else:
        print("  (no CYCLES lines captured — firmware may have crashed)")
    print()
    print("PYTHON WALL-CLOCK (unreliable — may lose serial bytes between runs)")
    print(f"  Avg : {avg_wall*1000:8.3f} ms")
    print(f"  Min : {min_wall*1000:8.3f} ms")
    print(f"  Max : {max_wall*1000:8.3f} ms")
    print(f"  Std : {std_wall*1000:8.3f} ms")
    print()
    print(f"Power : {power_val}")
    print("=" * 60)

    with open(args.out, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Run", "FW_Time_s", "FW_Cycles", "Python_WallClock_s"])
        for idx in range(len(results)):
            fw_t = fw_times_s[idx] if idx < len(fw_times_s) else ""
            fw_c = fw_cycles[idx]   if idx < len(fw_cycles)   else ""
            writer.writerow([idx + 1, fw_t, fw_c, results[idx]])
        writer.writerow([])
        writer.writerow(["Stats (firmware timer @ 100 MHz)", "Value"])
        writer.writerow(["Avg(s)", avg_fw])
        writer.writerow(["Min(s)", min_fw])
        writer.writerow(["Max(s)", max_fw])
        writer.writerow(["Std(s)", std_fw])
        writer.writerow([])
        writer.writerow(["Stats (Python wall-clock — UNRELIABLE)", "Value"])
        writer.writerow(["Avg(s)", avg_wall])
        writer.writerow(["Min(s)", min_wall])
        writer.writerow(["Max(s)", max_wall])
        writer.writerow(["Std(s)", std_wall])
        writer.writerow([])
        writer.writerow(["Power", power_val])
        writer.writerow(["Port", port])
        writer.writerow(["Baud", args.baud])

    print(f"\nResults saved to: {args.out}")


if __name__ == "__main__":
    main()
