#!/usr/bin/env python
"""d1b_variants_probe.py - exhaust the non-glitch SWD readout avenues on F2@RDP1.

Follow-up to d1b_exception_read.py (halted NMI vector fetch = BLOCKED). Tests the
variants that could still flip it:

  P1 readability map  : get_mem32 on SRAM / system-bootloader / OTP / user-flash.
                        Tells us whether debug-attach locks EVERYTHING (H3's
                        premise) or only user flash is protected.
  P2 access size      : read_mem8/16/32 on storage - does a non-32-bit access leak?
  P3 running leak     : core NEVER pre-halted. VTOR->flash, pend NMI, DEMCR
                        VC_HARDERR, run(). CPU takes NMI -> fetches flash vector
                        into PC -> executes garbage -> HardFault -> vector-catch
                        halts. The STACKED PC (SP+0x18) = the fetched flash word.
                        If flash is only locked by C_HALT (not C_DEBUGEN), this
                        leaks where the halted/step variant could not.

READ-ONLY: volatile SRAM/core-regs/VTOR/DEMCR only. Safe at RDP1.
"""
import os, sys, time, glob, fcntl
import chipwhisperer as cw
from swd.stlink import Stlink
from swd.cortexm import CortexM

STORAGE  = 0x08008000
VTOR     = 0xE000ED08
ICSR     = 0xE000ED04
DHCSR    = 0xE000EDF0
DEMCR    = 0xE000EDFC
NMIPEND  = 1 << 31
VC_HARDERR = 1 << 10
TRCENA     = 1 << 24
DHCSR_RUN  = 0xA05F0001      # DBGKEY | C_DEBUGEN, C_HALT=0
OPTCR    = 0x40023C14


def usbreset():
    RST = (ord('U') << 8) | 20
    for d in glob.glob('/sys/bus/usb/devices/*'):
        try:
            if open(d+'/idVendor').read().strip()=='0483' and \
               open(d+'/idProduct').read().strip()=='3748':
                b=int(open(d+'/busnum').read()); n=int(open(d+'/devnum').read())
                fd=os.open(f'/dev/bus/usb/{b:03d}/{n:03d}', os.O_WRONLY)
                fcntl.ioctl(fd, RST, 0); os.close(fd); print('[+] stlink usbreset')
                return
        except OSError:
            continue


def power_on():
    s = cw.scope(); s.clock.clkgen_freq = 16e6
    s.io.glitch_hp=False; s.io.glitch_lp=False
    s.io.tio1=False; s.io.tio2='high_z'; s.io.tio4='high_z'
    s.io.target_pwr=False; time.sleep(0.5); s.io.target_pwr=True; time.sleep(1.0)
    return s


def connect():
    for i in range(3):
        try: return Stlink(swd_frequency=1800000)
        except Exception as e:
            print(f'[!] swd try{i+1}: {type(e).__name__}'); usbreset(); time.sleep(0.6)
    raise SystemExit('swd down')


def rd(st, addr, label):
    try:
        v = st.get_mem32(addr); print(f'    {label:<22} 0x{addr:08x}: 0x{v:08x}  READABLE'); return v
    except Exception as e:
        print(f'    {label:<22} 0x{addr:08x}: BLOCKED ({type(e).__name__})'); return None


def main():
    gt = open(os.path.join(os.path.dirname(os.path.abspath(__file__)),'storage.bin'),'rb').read()
    exp8 = int.from_bytes(gt[8:12],'little')
    scope = power_on(); st = connect(); cmx = CortexM(st)
    print(f'[+] IDCODE=0x{st.get_idcode():08x}')
    optcr = st.get_mem32(OPTCR); print(f'[+] RDP=0x{(optcr>>8)&0xff:02x}')

    print('\n== P1: readability map (what debug CAN read at RDP1) ==')
    rd(st, 0x20000000, 'SRAM')
    rd(st, 0x1FFF0000, 'system bootloader')
    rd(st, 0x1FFF7800, 'OTP')
    rd(st, 0x1FFF7A10, 'UID')
    rd(st, 0x08000000, 'user flash head')
    rd(st, STORAGE,    'storage (0x8008000)')

    print('\n== P2: access-size sensitivity on storage ==')
    for sz, fn in (('8-bit', st.read_mem8), ('16-bit', st.read_mem16), ('32-bit', st.read_mem32)):
        try:
            data = bytes(fn(STORAGE, 4))
            leak = (data == gt[0:4])
            print(f'    {sz:<7} read[0:4] = {data.hex()}  truth={gt[0:4].hex()}  '
                  f'{"*** LEAK ***" if leak else "no"}')
        except Exception as e:
            print(f'    {sz:<7} BLOCKED ({type(e).__name__})')

    print('\n== P3: RUNNING-CPU NMI vector-catch leak (never pre-halted) ==')
    cmx.halt()                                  # momentary, to set up state
    st.set_mem32(0x20000100, 0xE7FEE7FE)        # 'b .' loop
    st.set_mem32(VTOR, STORAGE)
    cmx.set_reg('SP', 0x2000FF00)
    cmx.set_reg('PC', 0x20000101)
    cmx.set_reg('PSR', 0x01000000)
    st.set_mem32(DEMCR, TRCENA | VC_HARDERR)    # catch hardfault
    st.set_mem32(ICSR, NMIPEND)                 # pend NMI
    st.set_mem32(DHCSR, DHCSR_RUN)              # RUN (C_HALT cleared)
    halted = False
    for _ in range(50):
        time.sleep(0.02)
        if st.get_mem32(DHCSR) & (1 << 17):     # S_HALT
            halted = True; break
    if not halted:
        print('    core did not halt (no fault caught) - inconclusive; forcing halt')
        cmx.halt()
    sp = cmx.get_reg('SP'); pc = cmx.get_reg('PC')
    try:
        stacked_pc = st.get_mem32(sp + 0x18)    # stacked PC in the HF frame
    except Exception as e:
        stacked_pc = None
    print(f'    after run: PC=0x{pc:08x} SP=0x{sp:08x}')
    if stacked_pc is not None:
        leak = (stacked_pc & ~1) == (exp8 & ~1)
        print(f'    stacked PC (faulting addr) = 0x{stacked_pc:08x}  '
              f'expected flash[0x{STORAGE+8:08x}]=0x{exp8:08x}  '
              f'{"*** LEAK ***" if leak else "no leak"}')
    else:
        print('    could not read stack frame')

    cmx.run(); scope.io.target_pwr=False; scope.dis()
    print('\n[done] If every probe says BLOCKED/no leak, the debug-readout avenue '
          'is exhausted on F2 and glitch (H3 or our UART glitch) is required.')
    return 0


if __name__ == '__main__':
    try: sys.exit(main())
    except KeyboardInterrupt: sys.exit(1)
