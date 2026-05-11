#!/usr/bin/env bash
set -euo pipefail

# Run the hello_measure program N times via serial boot and collect cycle counts.
# Usage: bash scripts/run_hello_batch.sh <serial-port> [runs]
# Example: bash scripts/run_hello_batch.sh /dev/ttyS0 10

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
RUN_SCRIPT="$PROJECT_ROOT/scripts/run_hello.sh"

if [[ $# -lt 1 ]]; then
    echo "Usage: $0 <serial-port> [runs]"
    exit 1
fi

PORT="$1"
RUNS="${2:-10}"
LOG="$PROJECT_ROOT/build/hello_runs.log"
>"$LOG"

echo "Running hello_measure $RUNS times on port: $PORT"
echo "Logging to: $LOG"

for i in $(seq 1 $RUNS); do
    echo "--- Run #$i ---" | tee -a "$LOG"
    # run_hello.sh will upload the binary and run it once, then exit
    if bash "$RUN_SCRIPT" "$PORT" |& tee -a "$LOG"; then
        echo "Run $i completed" | tee -a "$LOG"
    else
        echo "Run $i failed (see log)" | tee -a "$LOG"
    fi
    # small pause to let UART drain and for manual inspection if needed
    sleep 0.25
done

echo "\nExtracting cycle counts..."
grep -E "^cycles: [0-9]+" "$LOG" | awk '{print $2}' > "$PROJECT_ROOT/build/hello_cycles.txt"

if [[ ! -s "$PROJECT_ROOT/build/hello_cycles.txt" ]]; then
    echo "No cycle measurements found in log. Check $LOG for details." >&2
    exit 2
fi

python3 - <<PY
import sys, statistics
fn = "$PROJECT_ROOT/build/hello_cycles.txt"
with open(fn) as f:
    nums = [int(x.strip()) for x in f if x.strip()]
if not nums:
    print('No values found')
    sys.exit(2)
print('Runs:', len(nums))
print('Values:', nums)
print('Min:', min(nums))
print('Max:', max(nums))
print('Mean:', statistics.mean(nums))
if len(nums) > 1:
    print('Stdev:', statistics.pstdev(nums))
else:
    print('Stdev: 0')
PY

echo "Log: $LOG"
echo "Raw values: $PROJECT_ROOT/build/hello_cycles.txt"

exit 0
