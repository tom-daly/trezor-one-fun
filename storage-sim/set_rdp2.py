#!/usr/bin/env python
"""Set RDP level 2 on the socketed F205 via SWD (option-byte OPTCR write).

*** IRREVERSIBLE / ONE-WAY DOOR ***
RDP2 (RDP byte 0xCC) PERMANENTLY disables SWD/JTAG debug AND the STM32 system
bootloader, in silicon. There is NO downgrade: RDP2 -> anything is blocked
(only RDP1 -> RDP0 regression exists, and that mass-erases). After this runs,
the ONLY access to this chip is whatever a BOOT-TIME glitch (glitch-1,
1-recon_glitch_trace.py) transiently grants per power cycle. If that glitch
does not land on this part, the chip is a permanent brick.

Purpose: turn the test chip into a genuine RDP2 target (the real production
Trezor state) to validate the glitch-1 RDP2->RDP1-behaviour bypass.

RDP1 -> RDP2 is an INCREASE in protection: it does NOT mass-erase (only the
1->0 regression erases), so the flashed firmware survives.

Sequence (RM0033): attach SWD in bootloader mode (BOOT0 high, so the core is
not executing protected flash and the DP is open at RDP1), unlock OPTCR via
FLASH_OPTKEYR, write RDP byte 0xCC, set OPTSTRT, poll BSY. The option reload
then activates RDP2 and the debug port drops mid-sequence (expected). Verify
by power-cycling and confirming SWD can no longer attach.

SAFETY: refuses to do anything unless G_CONFIRM_RDP2=IRREVERSIBLE is set
(or argv contains --yes-irreversible). Default run = dry run, no write.
"""
import os
import sys
import time
import gc

import chipwhisperer as cw
from swd.stlink import Stlink
from _practice_guard import require_practice_board

FLASH = 0x40023C00
KEYR, OPTKEYR, SR, CR, OPTCR = (FLASH + 4, FLASH + 8, FLASH + 0xC,
                                FLASH + 0x10, FLASH + 0x14)
OPTKEY1, OPTKEY2 = 0x08192A3B, 0x4C5D6E7F
RDP_L2 = 0xCC          # level 2 - IRREVERSIBLE
RDP_L1 = 0x55


def confirmed():
    if os.environ.get('G_CONFIRM_RDP2') == 'IRREVERSIBLE':
        return True
    if '--yes-irreversible' in sys.argv:
        return True
    return False


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


def main():
    require_practice_board('set_rdp2.py (writes option bytes - permanent)')
    dry = not confirmed()
    print('=' * 68)
    print('set_rdp2.py  -  RDP1 -> RDP2  (PERMANENT, IRREVERSIBLE)')
    if dry:
        print('DRY RUN (no write). To actually set RDP2, re-run with:')
        print('    G_CONFIRM_RDP2=IRREVERSIBLE /home/tdaly/.cwvenv/bin/python '
              'set_rdp2.py')
    else:
        print('CONFIRMED - will write RDP byte 0xCC. This cannot be undone.')
    print('=' * 68)

    cw_bootloader_power_cycle()
    st = Stlink(swd_frequency=480000)
    cur = st.get_mem32(OPTCR)
    rdp = (cur >> 8) & 0xFF
    print(f'OPTCR now    : 0x{cur:08X}  (RDP byte 0x{rdp:02X} = '
          f'{"L0" if rdp == 0xAA else "L1" if rdp == RDP_L1 else "L2" if rdp == RDP_L2 else "?"})')
    if rdp == RDP_L2:
        sys.exit('Already RDP2 - nothing to do.')
    if rdp not in (RDP_L1, 0xAA):
        sys.exit(f'Unexpected RDP state 0x{rdp:02X} - aborting.')

    if dry:
        print('DRY RUN: would unlock OPTCR, set RDP byte -> 0xCC, OPTSTRT.')
        print('DRY RUN: no changes made. Exiting.')
        return

    # --- the irreversible write ---
    st.set_mem32(OPTKEYR, OPTKEY1)
    st.set_mem32(OPTKEYR, OPTKEY2)
    unlocked = st.get_mem32(OPTCR)
    print(f'OPTCR unlock : OPTLOCK={bool(unlocked & 1)} (want False)')
    if unlocked & 1:
        sys.exit('OPTCR did not unlock - aborting (nothing written yet).')

    new = (cur & ~(0xFF << 8)) | (RDP_L2 << 8)   # swap RDP byte -> 0xCC
    new &= ~1                                     # OPTLOCK = 0
    try:
        st.set_mem32(OPTCR, new)
        st.set_mem32(OPTCR, new | 2)             # OPTSTRT -> program + reload
        for _ in range(100):                     # poll BSY (SR bit 16)
            if not st.get_mem32(SR) & (1 << 16):
                break
            time.sleep(0.01)
        after = st.get_mem32(OPTCR)
        print(f'OPTCR after  : 0x{after:08X}  (RDP byte 0x{(after >> 8) & 0xFF:02X})')
    except Exception as e:
        # the option reload activates RDP2 and drops the debug port mid-write -
        # EXPECTED for an RDP2 transition.
        print(f'DP dropped during OPTSTRT ({type(e).__name__}) - expected as '
              'RDP2 activates. Will verify by reconnect.')

    del st
    gc.collect()

    # --- verify: after a power cycle, SWD must NO LONGER attach (= RDP2) ---
    print('verifying (power-cycle, expect SWD to be DEAD)...')
    cw_bootloader_power_cycle()
    try:
        st2 = Stlink(swd_frequency=480000)
        v = st2.get_mem32(OPTCR)
        r2 = (v >> 8) & 0xFF
        if r2 == RDP_L2:
            print(f'SWD still attached but OPTCR RDP=0x{r2:02X} (L2). '
                  'Unexpected: debug up at RDP2 on this part - note it.')
        else:
            print(f'SWD attached, RDP byte 0x{r2:02X} - RDP2 NOT set (write '
                  'did not take). Investigate.')
    except Exception as e:
        print(f'SWD attach FAILED ({type(e).__name__}) == RDP2 CONFIRMED. '
              'Debug port + system bootloader are now permanently disabled.')
        print('Next: glitch-1 (1-recon_glitch_trace.py) is the only entry path.')


if __name__ == '__main__':
    main()
