#!/usr/bin/env python
"""Set RDP level 1 on the socketed F205 via SWD (option-byte OPTCR write).

F2 sequence (RM0033): unlock OPTCR via FLASH_OPTKEYR, write new OPTCR with
RDPRT != 0xAA (level 1), set OPTSTRT, poll BSY, power-cycle, verify readback.

Note: RDP 0->1 keeps flash intact (planted storage survives). Reverting
RDP1->RDP0 later mass-erases the chip.
"""
import sys
import time

from swd.stlink import Stlink

FLASH = 0x40023C00
KEYR, OPTKEYR, SR, CR, OPTCR = (FLASH + 4, FLASH + 8, FLASH + 0xC,
                                 FLASH + 0x10, FLASH + 0x14)
OPTKEY1, OPTKEY2 = 0x08192A3B, 0x4C5D6E7F
RDP_L1 = 0x55          # any value != 0xAA (L0) and != 0xCC (L2)


def main():
    st = Stlink(swd_frequency=480000)
    cur = st.get_mem32(OPTCR)
    print(f'OPTCR before : 0x{cur:08X}  (RDP byte 0x{(cur >> 8) & 0xFF:02X})')
    if (cur >> 8) & 0xFF != 0xAA:
        sys.exit('RDP is not level 0 - aborting, unexpected state')

    st.set_mem32(OPTKEYR, OPTKEY1)
    st.set_mem32(OPTKEYR, OPTKEY2)
    unlocked = st.get_mem32(OPTCR)
    print(f'OPTCR unlock: OPTLOCK={bool(unlocked & 1)} (want False)')
    if unlocked & 1:
        sys.exit('OPTCR did not unlock')

    new = (cur & ~(0xFF << 8)) | (RDP_L1 << 8)   # swap RDP byte
    new &= ~1                                     # OPTLOCK = 0
    st.set_mem32(OPTCR, new)
    st.set_mem32(OPTCR, new | 2)                 # OPTSTRT -> program
    for _ in range(100):                         # poll BSY (SR bit 16)
        if not st.get_mem32(SR) & (1 << 16):
            break
        time.sleep(0.01)
    after = st.get_mem32(OPTCR)
    print(f'OPTCR after  : 0x{after:08X}  (RDP byte 0x{(after >> 8) & 0xFF:02X})')
    print('RDP1 SET' if (after >> 8) & 0xFF == RDP_L1 else 'FAILED')


if __name__ == '__main__':
    main()
