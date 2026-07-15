# Phase 4: User Program (hello_measure)

## Overview

This phase demonstrates running a minimal bare-metal RISC-V program on the LiteX SoC that:
1. Prints "hello" via UART
2. Reads the `mcycle` CSR (machine cycle counter) 
3. Measures execution time of a loop in CPU cycles
4. Prints the cycle count via UART

## Files

- `sw/hello_measure/main.c` - Standalone RISC-V program (no libc dependency)
- `scripts/build_sw_hello.sh` - Build script (compile → link → binary)
- `scripts/run_hello.sh` - Serial boot loader script

## Building

```bash
cd /media/sf_Final_Project/litex-nexys4ddr
bash scripts/build_sw_hello.sh
```

Output files:
- `sw/hello_measure/build/hello_measure.elf` - ELF executable
- `sw/hello_measure/build/hello_measure.bin` - Binary for serial boot (1.6 KB)

## Running

**Important: Close PuTTY first** (litex_term manages the serial port)

Option 1 - Using run script (auto-detects port):
```bash
source .venv/bin/activate
bash scripts/run_hello.sh /dev/ttyS0  # Replace with your actual port
```

Option 2 - Manual command:
```bash
source .venv/bin/activate
python -m litex.tools.litex_term /dev/ttyS0 --speed 115200 \
    --kernel sw/hello_measure/build/hello_measure.bin --serial-boot
```

## Expected Output

The FPGA BIOS will detect the serial boot request and load/execute the program:

```
LiteX BIOS> ... (BIOS output)
Booting from serial...
hello
cycles: 487
```

The cycle count will vary based on loop execution time at 100 MHz clock.

## Program Details

### Source Code Features

- **No libc dependency** - Fully standalone assembly of UART I/O and number conversion
- **Direct UART access** - Memory-mapped I/O at 0x60000000
- **CSR reading** - Inline assembly: `csrr <reg>, mcycle`
- **Minimal runtime** - Only main() + entry point, < 2KB binary

### UART I/O

```c
#define UART_BASE 0x60000000UL
#define UART_RXTX ((volatile unsigned int *)(UART_BASE + 0x00))  // TX/RX data
#define UART_TXFULL ((volatile unsigned int *)(UART_BASE + 0x04)) // TX full flag
```

Poll `UART_TXFULL` before writing to `UART_RXTX`.

### Memory Map

- ROM:  0x00000000 - 0x0001FFFF (128 KB)
- SRAM: 0x10000000 - 0x10001FFF (8 KB)
- CSR:  0xF0000000 - 0xF000FFFF (64 KB)

Program loads at ROM base (0x00000000) via serial boot.

## Troubleshooting

**"No sections" error during objcopy:**
- Ensure linker flags include `-nostdlib -nostartfiles`
- Verify entry point is defined (check `_start` symbol)

**Undefined reference to `__udivdi3` or `__umoddi3`:**
- Link against libcompiler_rt: `-L/path/to/libcompiler_rt` and `-lcompiler_rt`
- These provide 64-bit division for unsigned long long operations

**Serial port not found:**
- Use `ls /dev/ttyS*` or `ls /dev/ttyUSB*` to list ports
- Most common: `/dev/ttyS0` or `/dev/ttyUSB0`

**UART output not appearing:**
- Verify BIOS is running correctly first (use PuTTY to test)
- Check binary size is reasonable (~1.6 KB)
- Ensure program runs after serial boot (BIOS should print "Booting from serial...")

## Next Steps

- Modify main() to test different hardware features
- Add more complex calculations to measure cycle overhead
- Implement memory test patterns
- Add timer-based I/O delays

