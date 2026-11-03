#!/usr/bin/env python3
"""Erase the storage sector (sector 2 = 0x08008000, 16 KB) via SWD, so
plant_storage.py can re-plant. Practice-board only. RDP0 required (SWD flash
access). Leaves the sector all-FF.
"""
import sys, time
sys.path.insert(0, '/home/tdaly/trezor-btc/storage-sim')
import chipwhisperer as cw
from swd.stlink import Stlink
from _practice_guard import require_practice_board

FLASH = 0x40023C00
KEYR, SR, CR = FLASH + 4, FLASH + 0xC, FLASH + 0x10
KEY1, KEY2 = 0x45670123, 0xCDEF89AB
STORAGE, SECTOR = 0x08008000, 2

def main():
    require_practice_board('erase_storage.py (flash sector erase)')
    s = cw.scope()
    s.io.target_pwr = True; time.sleep(2)
    s.io.target_pwr = False; time.sleep(2)
    s.io.target_pwr = True; time.sleep(3)
    s.dis()
    st = Stlink(swd_frequency=480000)
    def wait_bsy():
        for _ in range(4000):
            if st.get_mem32(SR) & (1 << 16) == 0: return True
            time.sleep(0.005)
        return False
    st.set_mem32(KEYR, KEY1); st.set_mem32(KEYR, KEY2)   # unlock FLASH_CR
    if st.get_mem32(CR) & (1 << 31):
        sys.exit('FLASH_CR still locked after KEYR')
    wait_bsy()
    cr = (1 << 1) | (SECTOR << 3) | (2 << 8)             # SER | SNB=2 | PSIZE=word
    st.set_mem32(CR, cr)
    st.set_mem32(CR, cr | (1 << 16))                     # STRT
    if not wait_bsy(): sys.exit('erase BSY timeout')
    st.set_mem32(CR, 0)
    head = bytes(st.read_mem8(STORAGE, 64))
    ok = all(b == 0xFF for b in head)
    print(f'sector {SECTOR} @ 0x{STORAGE:08X} head={head[:16].hex()} '
          f'-> {"ALL-FF (erased)" if ok else "NOT ERASED"}')
    sys.exit(0 if ok else 1)

if __name__ == '__main__':
    main()
