#!/usr/bin/env python
"""Set RDP level 1 on the socketed F205 via SWD (option-byte OPTCR write).

RDP0/blank -> RDP1. This is the practice-target lock for glitch-2.

REVERSIBLE (unlike RDP2): RDP1 -> RDP0 is allowed but MASS-ERASES all flash
(set_rdp0.py). RDP0/L1 -> RDP1 is an increase in protection and does NOT erase,
so the planted storage survives. RDP1 keeps SWD alive (SRAM readable; flash/OTP
blocked) and the bootloader answers 0x7F but NACKs Read Memory -- exactly the
real-device readout-protection we glitch past.

Writes RDP byte 0xBB (silicon rule: 0xAA=L0, 0xCC=L2, ANYTHING ELSE=L1). HARD
refuses to ever write 0xAA or 0xCC, so this can neither clear protection nor
brick the part to RDP2.

Sequence (same as set_rdp2 but L1 value): BOOT0-high power cycle (bootloader
running so DP is open), attach SWD, HALT the core (a running bootloader stomps
OPTCR writes), unlock OPTCR via FLASH_OPTKEYR, stage RDP byte, OPTSTRT, poll BSY,
power-cycle to reload, confirm RDP byte reads L1 and SWD still attaches.

Practice board only (G_PRACTICE_BOARD=YES).
"""
import gc
import os
import sys
import time

import chipwhisperer as cw
from swd.stlink import Stlink
try:
    from swd.cortexm import CortexM
except Exception:  # noqa: BLE001
    CortexM = None
from _practice_guard import require_practice_board

FLASH = 0x40023C00
OPTKEYR, SR, OPTCR = FLASH + 8, FLASH + 0xC, FLASH + 0x14
OPTKEY1, OPTKEY2 = 0x08192A3B, 0x4C5D6E7F
RDP_L1 = 0xBB          # any non-AA/non-CC value = Level 1
STORAGE = 0x08008000


def rdp_level(b):
    return 0 if b == 0xAA else 2 if b == 0xCC else 1


def power_cycle_bootloader():
    """Fresh CW open, BOOT0 high (TIO1) / BOOT1 low (TIO2 + pin28 GND), power
    cycle, then free the CW handle before ST-Link opens."""
    s = cw.scope()
    s.io.target_pwr = 'high_z'
    s.clock.clkgen_freq = 16e6
    s.io.glitch_hp = False
    s.io.glitch_lp = False
    s.io.tio1 = True            # BOOT0 high -> system bootloader
    s.io.tio2 = 'gpio_low'      # BOOT1 low
    s.io.tio4 = 'high_z'
    s.io.target_pwr = False
    time.sleep(1.5)
    s.io.target_pwr = True
    time.sleep(2.5)
    s.dis()
    del s
    gc.collect()


def main():
    require_practice_board('set_rdp1.py (writes option bytes -> RDP1)')
    print('=' * 64)
    print('set_rdp1.py  -  RDP0/L1 -> RDP1 (reversible; does NOT erase flash)')
    print('=' * 64)

    power_cycle_bootloader()
    st = Stlink(swd_frequency=480000)
    if CortexM is None:
        sys.exit('swd.cortexm.CortexM unavailable - cannot halt core; aborting.')
    CortexM(st).halt()
    print('[+] SWD up, core halted.')

    cur = st.get_mem32(OPTCR)
    rdp = (cur >> 8) & 0xFF
    lvl = rdp_level(rdp)
    print(f'[+] OPTCR = 0x{cur:08X}  RDP byte 0x{rdp:02X} = L{lvl}')
    if lvl == 2:
        sys.exit('Already RDP2 - cannot and will not touch.')
    if lvl == 1:
        print('Already RDP1 - nothing to do.')
        return

    # unlock
    if cur & 1:
        st.set_mem32(OPTKEYR, OPTKEY1)
        st.set_mem32(OPTKEYR, OPTKEY2)
        cur = st.get_mem32(OPTCR)
    if cur & 1:
        sys.exit('OPTCR did not unlock - aborting (nothing written).')

    new = (cur & ~(0xFF << 8)) | (RDP_L1 << 8)
    new &= ~1                                   # OPTLOCK = 0
    nb = (new >> 8) & 0xFF
    if nb in (0xAA, 0xCC):
        sys.exit(f'REFUSED: computed RDP byte 0x{nb:02X} is L0/L2 - abort.')
    st.set_mem32(OPTCR, new)
    staged = (st.get_mem32(OPTCR) >> 8) & 0xFF
    print(f'[+] staged RDP byte 0x{staged:02X} (pre-OPTSTRT)')
    if staged != RDP_L1:
        sys.exit('[!] OPTCR did not accept the L1 byte - aborting before OPTSTRT.')

    print('[+] OPTSTRT -> programming option byte...')
    st.set_mem32(OPTCR, new | 2)
    for _ in range(200):
        if not st.get_mem32(SR) & (1 << 16):
            break
        time.sleep(0.01)
    after = (st.get_mem32(OPTCR) >> 8) & 0xFF
    print(f'[+] post-OPTSTRT RDP byte 0x{after:02X}')
    try:
        del st
    except Exception:
        pass
    gc.collect()

    # reload via power cycle, then confirm
    print('[+] power-cycle to reload option bytes, then verify...')
    power_cycle_bootloader()
    st = Stlink(swd_frequency=480000)
    CortexM(st).halt()
    v = st.get_mem32(OPTCR)
    r = (v >> 8) & 0xFF
    lvl = rdp_level(r)
    print(f'[+] after reload: OPTCR=0x{v:08X}  RDP byte 0x{r:02X} = L{lvl}')
    # at RDP1, SRAM reads but flash/storage faults
    try:
        _ = st.get_mem32(STORAGE)
        flash_blocked = False
    except Exception:
        flash_blocked = True
    print(f'[+] storage 0x{STORAGE:08X} over SWD: '
          f'{"BLOCKED (fault)" if flash_blocked else "readable"}')
    if lvl == 1 and flash_blocked:
        print('\n[VERDICT] *** RDP1 SET *** flash/OTP protected, SWD+SRAM alive,')
        print('          storage intact. Ready as a glitch-2 practice target.')
    elif lvl == 1:
        print('\n[VERDICT] RDP byte is L1 but flash still read - re-check.')
    else:
        print(f'\n[!] RDP did NOT take (L{lvl}). Nothing locked.')
    sys.exit(0 if lvl == 1 else 1)


if __name__ == '__main__':
    main()
