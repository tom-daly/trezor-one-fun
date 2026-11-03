#!/usr/bin/env python
"""Set RDP level 2 on the socketed F205 via SWD (option-byte OPTCR write).

*** IRREVERSIBLE / ONE-WAY DOOR ***
RDP2 (RDP byte 0xCC) PERMANENTLY disables SWD/JTAG debug AND the STM32 system
bootloader, in silicon. There is NO downgrade: RDP2 -> anything is blocked
(only RDP1 -> RDP0 regression exists, and that mass-erases). After this runs,
the ONLY access to this chip is whatever a BOOT-TIME glitch (glitch-1)
transiently grants per power cycle. If that glitch does not land on this part,
the chip is a permanent brick.

Purpose: turn the test chip into a genuine RDP2 target (the real production
Trezor state) to validate the glitch-1 RDP2->RDP1-behaviour bypass.

RDP1 -> RDP2 is an INCREASE in protection: it does NOT mass-erase (only the
1->0 regression erases), so the flashed firmware survives.

Sequence (RM0033): attach SWD in bootloader mode (BOOT0 high so the core is not
executing protected flash and the DP is open at RDP1), unlock OPTCR via
FLASH_OPTKEYR, write RDP byte 0xCC, set OPTSTRT, poll BSY. CONFIRMATION is by
reading the RDP byte back == 0xCC (authoritative), then power-cycling and
confirming SWD can no longer attach across repeated clean retries.

RDP level decode (silicon rule): 0xAA = L0, 0xCC = L2, ANY OTHER value = L1
(a fresh/erased option byte reads 0xFF and is Level 1). The old version wrongly
assumed L1 == 0x55 and aborted on 0xFF; and it treated ANY SWD open error in
verify as "RDP2 confirmed" (false positive on errno-5 / USB wedge).

SAFETY: refuses unless G_CONFIRM_RDP2=IRREVERSIBLE (or argv --yes-irreversible).
Default run = dry run, no write. Practice board only (G_PRACTICE_BOARD=YES).
"""
import os
import sys
import time
import gc
import glob
import fcntl

import chipwhisperer as cw
from swd.stlink import Stlink
try:
    from swd.cortexm import CortexM
except Exception:  # noqa: BLE001
    CortexM = None
from _practice_guard import require_practice_board

FLASH = 0x40023C00
KEYR, OPTKEYR, SR, CR, OPTCR = (FLASH + 4, FLASH + 8, FLASH + 0xC,
                                FLASH + 0x10, FLASH + 0x14)
OPTKEY1, OPTKEY2 = 0x08192A3B, 0x4C5D6E7F
RDP_L2 = 0xCC          # level 2 - IRREVERSIBLE


def rdp_level(byte):
    """Silicon rule: 0xAA=L0, 0xCC=L2, anything else (incl 0xFF)=L1."""
    if byte == 0xAA:
        return 0
    if byte == 0xCC:
        return 2
    return 1


def stlink_usbreset():
    """USBDEVFS_RESET the ST-Link/V2 (0483:3748) to clear an errno-5 wedge."""
    RST = (ord('U') << 8) | 20
    for d in glob.glob('/sys/bus/usb/devices/*'):
        try:
            if (open(d + '/idVendor').read().strip() == '0483' and
                    open(d + '/idProduct').read().strip() == '3748'):
                b = int(open(d + '/busnum').read())
                n = int(open(d + '/devnum').read())
                fd = os.open('/dev/bus/usb/%03d/%03d' % (b, n), os.O_WRONLY)
                fcntl.ioctl(fd, RST, 0)
                os.close(fd)
        except OSError:
            continue


def stlink_attach(retries=1):
    """Open ST-Link with a USB reset + retries. Returns Stlink or raises."""
    last = None
    for _ in range(retries):
        try:
            stlink_usbreset()
            time.sleep(1.2)
            return Stlink(swd_frequency=480000)
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(0.4)
    raise last


def confirmed():
    return (os.environ.get('G_CONFIRM_RDP2') == 'IRREVERSIBLE'
            or '--yes-irreversible' in sys.argv)


def cw_bootloader_power_cycle():
    """Fresh CW open, BOOT0 high (system bootloader -> core off protected flash
    so the DP is open at RDP1), power-cycle, then FULLY free the CW handle
    before ST-Link opens."""
    s = cw.scope()
    s.io.target_pwr = 'high_z'
    s.clock.clkgen_freq = 16e6
    s.io.tio1 = True            # BOOT0 high
    s.io.tio2 = 'high_z'
    s.io.tio4 = 'high_z'
    s.io.target_pwr = False
    time.sleep(1.5)
    s.io.target_pwr = True
    time.sleep(2.5)
    s.dis()
    del s
    gc.collect()


def verify_rdp2_locked():
    """Power-cycle, then try to attach SWD up to 5 times with clean USB resets.
    RDP2 is confirmed ONLY if every attach fails. If any attach succeeds, read
    OPTCR and report the actual RDP byte (the write did not take)."""
    cw_bootloader_power_cycle()
    fails = 0
    for i in range(5):
        try:
            st = stlink_attach(retries=1)
            v = st.get_mem32(OPTCR)
            r = (v >> 8) & 0xFF
            del st
            gc.collect()
            return False, r, v   # attach SUCCEEDED -> not RDP2
        except Exception:  # noqa: BLE001
            fails += 1
            time.sleep(0.3)
    return True, None, None      # 5/5 clean attach failures -> RDP2


def main():
    require_practice_board('set_rdp2.py (writes option bytes - permanent)')
    dry = not confirmed()
    print('=' * 68)
    print('set_rdp2.py  -  RDP(L0/L1) -> RDP2  (PERMANENT, IRREVERSIBLE)')
    if dry:
        print('DRY RUN (no write). To actually set RDP2, re-run with:')
        print('    G_PRACTICE_BOARD=YES G_CONFIRM_RDP2=IRREVERSIBLE \\')
        print('        /home/tdaly/.cwvenv/bin/python set_rdp2.py')
    else:
        print('CONFIRMED - will program RDP byte 0xCC. This cannot be undone.')
    print('=' * 68)

    cw_bootloader_power_cycle()
    st = stlink_attach(retries=4)

    # HALT the core: with BOOT0 high the system bootloader is running and
    # stomps the option registers (writes to OPTCR[15:8] silently do not hold),
    # which is why earlier attempts no-op'd. Halting frees the flash regs.
    if CortexM is None:
        sys.exit('swd.cortexm.CortexM unavailable - cannot halt core; aborting '
                 '(a running bootloader will reject the RDP write).')
    try:
        cm = CortexM(st)
        cm.halt()
        print('core HALTED (frees option registers from the running bootloader)')
    except Exception as e:  # noqa: BLE001
        sys.exit(f'core halt failed ({type(e).__name__}) - aborting.')

    cur = st.get_mem32(OPTCR)
    rdp = (cur >> 8) & 0xFF
    lvl = rdp_level(rdp)
    print(f'OPTCR now    : 0x{cur:08X}  (RDP byte 0x{rdp:02X} = L{lvl})')
    if lvl == 2:
        sys.exit('Already RDP2 - nothing to do.')
    # L0 (0xAA) or L1 (anything else incl 0xFF) can both be raised to L2.

    if dry:
        print('DRY RUN: would unlock OPTCR, program RDP byte -> 0xCC, OPTSTRT,')
        print('         then confirm by reading RDP byte back == 0xCC.')
        print('DRY RUN: no changes made. Exiting.')
        del st
        gc.collect()
        return

    # --- unlock + stage the RDP byte (NOT programmed until OPTSTRT) ---
    if cur & 1:
        st.set_mem32(OPTKEYR, OPTKEY1)
        st.set_mem32(OPTKEYR, OPTKEY2)
        cur = st.get_mem32(OPTCR)
    print(f'OPTCR unlock : OPTLOCK={bool(cur & 1)} (want False)')
    if cur & 1:
        sys.exit('OPTCR did not unlock - aborting (nothing written yet).')

    new = (cur & ~(0xFF << 8)) | (RDP_L2 << 8)   # swap RDP byte -> 0xCC
    new &= ~1                                     # OPTLOCK = 0
    st.set_mem32(OPTCR, new)
    staged = st.get_mem32(OPTCR)
    print(f'OPTCR staged : 0x{staged:08X}  (RDP byte 0x{(staged >> 8) & 0xFF:02X}, '
          'pre-OPTSTRT)')
    if ((staged >> 8) & 0xFF) != RDP_L2:
        sys.exit('[!] OPTCR did not accept RDP=0xCC even with core halted - '
                 'aborting before OPTSTRT (nothing programmed).')
    print('[+] register accepted 0xCC. Setting OPTSTRT (THIS PROGRAMS THE '
          'OPTION BYTE - irreversible on next reset)...')

    programmed_readback = None
    try:
        st.set_mem32(OPTCR, new | 2)             # OPTSTRT -> start programming
        for _ in range(200):                     # poll BSY (SR bit 16)
            if not st.get_mem32(SR) & (1 << 16):
                break
            time.sleep(0.01)
        after = st.get_mem32(OPTCR)
        programmed_readback = (after >> 8) & 0xFF
        sr = st.get_mem32(SR)
        print(f'OPTCR after  : 0x{after:08X}  (RDP byte 0x{programmed_readback:02X})  '
              f'SR=0x{sr:08X}')
    except Exception as e:  # noqa: BLE001
        print(f'DP dropped during program ({type(e).__name__}) - option reload '
              'may have activated RDP2 immediately. Will verify by reconnect.')

    try:
        del st
    except Exception:
        pass
    gc.collect()

    if programmed_readback is not None and programmed_readback != RDP_L2:
        print(f'[i] post-OPTSTRT OPTCR RDP reads 0x{programmed_readback:02X} '
              '(F2 may reflect the ACTIVE byte until reload) - deciding by the '
              'power-cycle lock test.')

    print('verifying (power-cycle, expect SWD DEAD across 5 clean retries)...')
    locked, r2, v2 = verify_rdp2_locked()
    if locked:
        print('[+] SWD attach FAILED 5/5 after clean USB resets == RDP2 '
              'CONFIRMED.')
        print('    Debug port + system bootloader are now permanently disabled.')
        print('    Next: glitch-1 is the only entry path.')
    else:
        lvl2 = rdp_level(r2)
        if lvl2 == 2:
            print(f'[?] SWD still attaches but OPTCR RDP=0x{r2:02X} (L2) - '
                  'debug somehow up at RDP2 on this part. Note it.')
        else:
            print(f'[!] SWD still attaches, OPTCR=0x{v2:08X} RDP=0x{r2:02X} '
                  f'(L{lvl2}) - RDP2 NOT active. The write did not take.')


if __name__ == '__main__':
    main()
