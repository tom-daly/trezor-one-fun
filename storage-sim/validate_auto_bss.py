#!/usr/bin/env python
"""validate_auto_bss.py -- prove the hardware_salt .bss is generated AUTOMATICALLY
by resident firmware on boot, like a real Trezor (no SWD injection).

Flashes a tiny salt-firmware at 0x08000000 that, on reset, reads the chip's own
UID (12 @ 0x1FFF7A10) + OTP block 3 (32 @ 0x1FFF7860) - exactly collect_hw_entropy
- computes SHA256 into a .bss static `hardware_salt[32]`, sets a ready flag, and
spins. Then power-cycles with BOOT0 LOW (boot from flash = this fw, NOT the
bootloader, NO debugger running it), attaches SWD, and reads .bss back:
  - hw_ready == 0xA5  => firmware actually ran on its own
  - hardware_salt     => must equal known-answer.json's hardware_salt

RDP0 only (flash write + the chip must be able to read its own OTP; it always
can). Flashes sector 0 only; the storage sector (2) is untouched. Practice board.
"""
import json
import os
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, '/home/tdaly/trezor-btc')
sys.path.insert(0, '/home/tdaly/trezor-btc/storage-sim')

import chipwhisperer as cw                       # noqa: E402
from swd.stlink import Stlink                     # noqa: E402
from _practice_guard import require_practice_board  # noqa: E402
from plant_storage import (wait_bsy, flash_unlock, erase_sector,  # noqa: E402
                           program_words, CR)

HERE = os.path.dirname(os.path.abspath(__file__))
SRAM_BASE, SRAM_LEN = 0x20000000, 0x20000
FW_BASE, FW_SECTOR = 0x08000000, 0

C_SRC = r'''
#include <stdint.h>
static uint32_t ror(uint32_t x, int n){ return (x>>n)|(x<<(32-n)); }
static const uint32_t K[64]={
0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,
0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,
0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,
0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,
0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,
0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,
0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,
0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2};
static void blk(uint32_t*s,const uint8_t*p){
  uint32_t w[64],a,b,c,d,e,f,g,h,t1,t2; int i;
  for(i=0;i<16;i++) w[i]=(p[i*4]<<24)|(p[i*4+1]<<16)|(p[i*4+2]<<8)|p[i*4+3];
  for(i=16;i<64;i++){ uint32_t s0=ror(w[i-15],7)^ror(w[i-15],18)^(w[i-15]>>3);
    uint32_t s1=ror(w[i-2],17)^ror(w[i-2],19)^(w[i-2]>>10); w[i]=w[i-16]+s0+w[i-7]+s1; }
  a=s[0];b=s[1];c=s[2];d=s[3];e=s[4];f=s[5];g=s[6];h=s[7];
  for(i=0;i<64;i++){ uint32_t S1=ror(e,6)^ror(e,11)^ror(e,25),ch=(e&f)^(~e&g);
    t1=h+S1+ch+K[i]+w[i]; uint32_t S0=ror(a,2)^ror(a,13)^ror(a,22),mj=(a&b)^(a&c)^(b&c);
    t2=S0+mj; h=g;g=f;f=e;e=d+t1;d=c;c=b;b=a;a=t1+t2; }
  s[0]+=a;s[1]+=b;s[2]+=c;s[3]+=d;s[4]+=e;s[5]+=f;s[6]+=g;s[7]+=h;
}
static void sha256(const uint8_t*msg,uint32_t len,uint8_t*out){
  uint32_t s[8]={0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19};
  uint8_t buf[64]; uint32_t i,n=0; uint64_t total=(uint64_t)len*8;
  for(i=0;i<len;i++){ buf[n++]=msg[i]; if(n==64){blk(s,buf);n=0;} }
  buf[n++]=0x80; if(n>56){ while(n<64)buf[n++]=0; blk(s,buf); n=0; }
  while(n<56)buf[n++]=0;
  for(i=0;i<8;i++) buf[56+i]=(uint8_t)(total>>(56-8*i));
  blk(s,buf);
  for(i=0;i<8;i++){ out[i*4]=s[i]>>24; out[i*4+1]=s[i]>>16; out[i*4+2]=s[i]>>8; out[i*4+3]=s[i]; }
}
volatile uint8_t hardware_salt[32];   /* .bss, like storage.c */
volatile uint8_t hw_ready;            /* .bss ready flag */
void Reset_Handler(void){
  uint8_t ent[44]; int i;
  for(i=0;i<12;i++) ent[i]   =*(volatile uint8_t*)(0x1FFF7A10+i); /* UID */
  for(i=0;i<32;i++) ent[12+i]=*(volatile uint8_t*)(0x1FFF7860+i); /* OTP block 3 */
  sha256(ent,44,(uint8_t*)hardware_salt);
  hw_ready=0xA5;
  for(;;){}
}
extern uint32_t _estack;
__attribute__((section(".isr_vector"),used))
const uint32_t vtab[2]={(uint32_t)&_estack,(uint32_t)Reset_Handler};
'''

LD = '''
MEMORY
{
  FLASH (rx)  : ORIGIN = 0x08000000, LENGTH = 16K
  RAM   (rwx) : ORIGIN = 0x20000000, LENGTH = 128K
}
_estack = 0x20010000;
ENTRY(Reset_Handler)
SECTIONS {
  .isr_vector : { KEEP(*(.isr_vector)) } > FLASH
  .text       : { *(.text*) *(.rodata*) } > FLASH
  .bss        : { *(.bss*) *(COMMON) } > RAM
  /DISCARD/   : { *(.ARM.*) *(.comment) *(.note*) }
}
'''


def build_fw():
    d = tempfile.mkdtemp(prefix='saltfw_')
    c, ld, elf, binf = (os.path.join(d, f) for f in ('f.c', 'f.ld', 'f.elf', 'f.bin'))
    open(c, 'w').write(C_SRC)
    open(ld, 'w').write(LD)
    subprocess.run(['arm-none-eabi-gcc', '-mcpu=cortex-m3', '-mthumb', '-Os',
                    '-nostdlib', '-ffreestanding', '-fno-builtin', '-T', ld,
                    '-o', elf, c], check=True)
    subprocess.run(['arm-none-eabi-objcopy', '-O', 'binary', elf, binf], check=True)
    blob = open(binf, 'rb').read()
    nm = subprocess.run(['arm-none-eabi-nm', elf], capture_output=True, text=True).stdout
    sym = {}
    for line in nm.splitlines():
        p = line.split()
        if len(p) == 3 and p[2] in ('hardware_salt', 'hw_ready'):
            sym[p[2]] = int(p[0], 16)
    return blob, sym


def power(tio1, on=1.2):
    s = cw.scope()
    s.clock.clkgen_freq = 16e6
    s.io.glitch_hp = False
    s.io.glitch_lp = False
    s.io.tio1 = tio1
    s.io.tio2 = 'gpio_low'
    s.io.tio4 = 'high_z'
    s.io.target_pwr = False
    time.sleep(1.5)
    s.io.target_pwr = True
    time.sleep(on)
    s.dis()


def main():
    require_practice_board('validate_auto_bss.py (flashes firmware @0x08000000)')
    ka = json.load(open(os.path.join(HERE, 'chips/chip-c/known-answer.json')))
    want = bytes.fromhex(ka['hardware_salt'])
    print(f'[+] known-answer hardware_salt = {want.hex()}')
    blob, sym = build_fw()
    print(f'[+] salt-firmware built: {len(blob)} B; '
          f"hardware_salt@0x{sym['hardware_salt']:08X} hw_ready@0x{sym['hw_ready']:08X}")

    # ---- flash the firmware at 0x08000000 (BOOT0 high -> bootloader, halt via SWD) ----
    power(True)                                    # BOOT0 high to flash safely
    st = Stlink(swd_frequency=480000)
    rdp = (st.get_mem32(0x40023C14) >> 8) & 0xFF
    if rdp != 0xAA:
        sys.exit(f'RDP 0x{rdp:02X} != L0 - need RDP0 to flash. (wipe/keep-blank first)')
    head = bytes(st.read_mem8(FW_BASE, 16))
    if any(b != 0xFF for b in head):
        print(f'[+] sector 0 not blank ({head.hex()}) - erasing')
        erase_sector(st, FW_SECTOR)
    program_words(st, FW_BASE, blob)
    rb = b''
    while len(rb) < len(blob):
        n = min(64, len(blob) - len(rb))
        rb += bytes(st.read_mem8(FW_BASE + len(rb), n))
    if rb != blob:
        sys.exit('[!] firmware readback MISMATCH')
    print('[+] firmware flashed @ 0x08000000, readback PASS')
    try:
        st._com._usb = None
        del st
    except Exception:
        pass

    # ---- boot it AUTOMATICALLY: BOOT0 LOW -> run from flash, no debugger ----
    print('[+] power-cycle with BOOT0 LOW -> firmware auto-runs from flash...')
    power(False)                                   # BOOT0 low -> boot the firmware
    time.sleep(0.3)

    # ---- read .bss back over SWD (firmware is spinning) ----
    st = Stlink(swd_frequency=480000)
    ready = bytes(st.read_mem8(sym['hw_ready'], 1))[0]
    salt = bytes(st.read_mem8(sym['hardware_salt'], 32))
    print(f'[+] hw_ready @ .bss = 0x{ready:02X}  '
          f'({"firmware RAN" if ready == 0xA5 else "did NOT run"})')
    print(f'[+] hardware_salt @ .bss = {salt.hex()}')

    # ---- scan SRAM for the salt too (dump-and-find, like the real recovery) ----
    data = bytearray()
    chunk = min(1024, st.maximum_32bit_data)
    chunk -= chunk % 4
    off = 0
    while off < SRAM_LEN:
        nn = min(chunk, SRAM_LEN - off)
        data += bytes(st.read_mem32(SRAM_BASE + off, nn))
        off += nn
    at = bytes(data).find(salt)

    ok = (ready == 0xA5) and (salt == want)
    print()
    print('=' * 60)
    if ok:
        print('[VALIDATED] .bss hardware_salt was generated AUTOMATICALLY by')
        print('            firmware on boot (BOOT0 low, no injection) and MATCHES')
        print(f'            the known answer. Found in SRAM dump @ 0x{SRAM_BASE+at:08X}.')
        print('            This is the real-device mechanism: fw reads its own')
        print('            UID+OTP, derives the salt into .bss -> recover from SRAM.')
    else:
        print('[!] NOT validated: '
              + ('firmware did not run; ' if ready != 0xA5 else '')
              + ('salt != known answer' if salt != want else ''))
    print('=' * 60)
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
