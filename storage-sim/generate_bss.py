#!/usr/bin/env python
"""generate_bss.py -- plant a fake `.bss` hardware_salt in SRAM (practice).

On a real Trezor the firmware computes hardware_salt = SHA256(UID || OTP3) and
keeps it in a file-scope static (storage.c) -> it lives in .bss (SRAM) the whole
runtime. At RDP1 SWD can read SRAM but not flash/OTP, so the salt is recovered
by dumping SRAM and locating that 32-byte window.

This tool reproduces that .bss for the practice clone WITHOUT the full firmware:
it compiles a tiny stub whose .bss array is the salt, loads it into SRAM and
RUNS it over SWD (set SP/PC -> run), so the stub writes the salt into .bss just
like firmware. Runs via the debugger (no SRAM-boot), so it doesn't need BOOT1
high and won't fight a pin28->GND tie. Then it verifies the salt is resident and
can optionally dump SRAM.

Salt source (first match): --salt HEX | --uid/--otp3 (SHA256) | --known-answer
(reads "hardware_salt", default chips/chip-c/known-answer.json).

SRAM-only: no flash/option/erase writes. Safe at RDP0 and RDP1.

Env/args:
  --known-answer PATH   json with hardware_salt (default chips/chip-c/known-answer.json)
  --salt HEX            32-byte salt hex (overrides json)
  --uid HEX --otp3 HEX  compute salt = SHA256(uid||otp3) (overrides json)
  --bss-name NAME       symbol name for the .bss array (default hardware_salt)
  --dump PATH           after planting, dump full 128KB SRAM to PATH
  --leave-running       leave the core running (salt resident) instead of halting
"""
import argparse
import hashlib
import json
import os
import struct
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, '/home/tdaly/trezor-btc')
sys.path.insert(0, '/home/tdaly/trezor-btc/storage-sim')

import chipwhisperer as cw                 # noqa: E402
from swd.stlink import Stlink              # noqa: E402
from swd.cortexm import CortexM            # noqa: E402

SRAM_BASE = 0x20000000
SRAM_LEN = 0x20000                         # 128 KB (F205)
ESTACK = 0x20010000
HERE = os.path.dirname(os.path.abspath(__file__))

C_STUB = r'''
#include <stdint.h>
#define N 32
volatile uint8_t %(name)s[N] __attribute__((used));   /* .bss - fake hardware_salt */
static const uint8_t SRC[N] = { %(bytes)s };
void Reset_Handler(void){
    for (int i = 0; i < N; i++) %(name)s[i] = SRC[i];  /* runtime .bss write, like fw */
    for (;;) { }                                       /* keep salt resident */
}
extern uint32_t _estack;
__attribute__((section(".isr_vector"), used))
const uint32_t vtab[2] = { (uint32_t)&_estack, (uint32_t)Reset_Handler };
'''

LD_SCRIPT = '''
MEMORY { RAM (rwx) : ORIGIN = 0x20000000, LENGTH = 128K }
_estack = 0x20010000;
ENTRY(Reset_Handler)
SECTIONS {
  .isr_vector : { KEEP(*(.isr_vector)) } > RAM
  .text       : { *(.text*) *(.rodata*) } > RAM
  .data       : { *(.data*) } > RAM
  .bss        : { *(.bss*) *(COMMON) } > RAM
  /DISCARD/   : { *(.ARM.*) *(.comment) *(.note*) }
}
'''


def resolve_salt(a):
    if a.salt:
        b = bytes.fromhex(a.salt)
    elif a.uid:
        b = hashlib.sha256(bytes.fromhex(a.uid) + bytes.fromhex(a.otp3)).digest()
    else:
        ka = json.load(open(a.known_answer))
        b = bytes.fromhex(ka['hardware_salt'])
    if len(b) != 32:
        sys.exit(f'salt must be 32 bytes, got {len(b)}')
    return b


def build_stub(salt, name):
    d = tempfile.mkdtemp(prefix='bss_')
    c, ld, elf, binf = (os.path.join(d, f) for f in ('s.c', 's.ld', 's.elf', 's.bin'))
    open(c, 'w').write(C_STUB % {
        'name': name,
        'bytes': ', '.join(f'0x{x:02x}' for x in salt)})
    open(ld, 'w').write(LD_SCRIPT)
    subprocess.run(['arm-none-eabi-gcc', '-mcpu=cortex-m3', '-mthumb', '-Os',
                    '-nostdlib', '-ffreestanding', '-fno-builtin', '-T', ld,
                    '-o', elf, c], check=True)
    subprocess.run(['arm-none-eabi-objcopy', '-O', 'binary', elf, binf], check=True)
    blob = open(binf, 'rb').read()
    nm = subprocess.run(['arm-none-eabi-nm', elf], capture_output=True, text=True).stdout
    bss_addr = None
    for line in nm.splitlines():
        parts = line.split()
        if len(parts) == 3 and parts[2] == name:
            bss_addr = int(parts[0], 16)
    if bss_addr is None:
        sys.exit(f'could not find .bss symbol {name} in stub')
    return blob, bss_addr


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--known-answer',
                    default=os.path.join(HERE, 'chips/chip-c/known-answer.json'))
    ap.add_argument('--salt')
    ap.add_argument('--uid')
    ap.add_argument('--otp3', default='ff' * 32)
    ap.add_argument('--bss-name', default='hardware_salt')
    ap.add_argument('--dump')
    ap.add_argument('--leave-running', action='store_true')
    a = ap.parse_args()

    salt = resolve_salt(a)
    print(f'[+] salt = {salt.hex()}')
    blob, bss_addr = build_stub(salt, a.bss_name)
    print(f'[+] stub built: {len(blob)} B; .bss "{a.bss_name}" @ 0x{bss_addr:08X}')

    # power-cycle the target (real POR); run via SWD so boot pins don't matter.
    s = cw.scope()
    s.clock.clkgen_freq = 16e6
    s.io.glitch_hp = False
    s.io.glitch_lp = False
    s.io.tio1 = False          # BOOT0 low (irrelevant; we drive the core via SWD)
    s.io.tio2 = 'gpio_low'
    s.io.tio4 = 'high_z'
    s.io.target_pwr = False
    time.sleep(1.5)
    s.io.target_pwr = True
    time.sleep(1.0)
    s.dis()

    st = Stlink(swd_frequency=1800000)
    cm = CortexM(st)
    cm.halt()
    print(f'[+] SWD up; RDP=0x{(st.get_mem32(0x40023C14) >> 8) & 0xFF:02X}; core halted')

    # stage blob in SRAM
    for i in range(0, len(blob), 4):
        st.set_mem32(SRAM_BASE + i,
                     struct.unpack('<I', blob[i:i + 4].ljust(4, b'\0'))[0])
    # zero the .bss salt region first so a match proves the stub ran
    for i in range(0, 32, 4):
        st.set_mem32(bss_addr + i, 0)

    sp = struct.unpack('<I', blob[0:4])[0]
    pc = struct.unpack('<I', blob[4:8])[0]
    cm.set_reg('SP', sp)
    cm.set_reg('PC', pc & ~1)
    cm.set_reg('PSR', 0x01000000)          # Thumb bit
    print(f'[+] entry: SP=0x{sp:08X} PC=0x{pc & ~1:08X} -> run')
    cm.run()
    time.sleep(0.1)
    cm.halt()

    got = bytes(st.read_mem8(bss_addr, 32))
    ok = got == salt
    print(f'[+] .bss @ 0x{bss_addr:08X} = {got.hex()}')
    print(f'[{"+" if ok else "!"}] {"MATCH - fake .bss planted in SRAM" if ok else "MISMATCH - stub did not write salt"}')

    if a.dump and ok:
        chunk = min(1024, st.maximum_32bit_data)
        chunk -= chunk % 4
        data = bytearray()
        off = 0
        while off < SRAM_LEN:
            n = min(chunk, SRAM_LEN - off)
            data += bytes(st.read_mem32(SRAM_BASE + off, n))
            off += n
        data = bytes(data)
        open(a.dump, 'wb').write(data)
        at = data.find(salt)
        print(f'[+] SRAM dumped -> {a.dump} ({len(data)} B); salt found at '
              f'offset 0x{at:05X} (0x{SRAM_BASE + at:08X})' if at >= 0
              else f'[!] SRAM dumped -> {a.dump}; salt NOT found in dump')

    if a.leave_running:
        cm.run()
        print('[+] core left RUNNING (salt resident in .bss)')
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
