# ==========================================================================
#  WHAT THIS FILE DOES (in simple words):
#  Regenerates the ROM init file from a compiled BIOS binary using LiteX's
#  get_mem_data - the fix for a ROM-init/BIOS mismatch found during bring-up
#  (FPGA ROM contents must exactly match the BIOS the build expects).
#  BIG PICTURE: Repair tool for the on-chip ROM image.
# ==========================================================================

import os
import sys
from litex.soc.integration.common import get_mem_data

def generate_hex_init(binary_file, output_file):
    print(f"Converting {binary_file} to {output_file}...")
    # VexRiscv is 32-bit, Little Endian
    data = get_mem_data(binary_file, data_width=32, endianness="little")
    
    with open(output_file, "w") as f:
        for word in data:
            f.write(f"{word:08x}\n")
    print(f"Success! Wrote {len(data)} words to {output_file}")

if __name__ == "__main__":
    # Paths
    bios_bin = "hw/build/software/bios/bios.bin"
    bios_crc_bin = "hw/build/software/bios/bios_crc.bin"
    rom_init = "hw/build/gateware/digilent_nexys4ddr_rom.init"

    # 1. Generate CRC-patched binary
    print("Running crcfbigen...")
    cmd = f"{sys.executable} -m litex.soc.software.crcfbigen {bios_bin} --little --output {bios_crc_bin}"
    ret = os.system(cmd)
    if ret != 0:
        print("Error running crcfbigen")
        sys.exit(1)

    # 2. Convert to Hex
    generate_hex_init(bios_crc_bin, rom_init)
