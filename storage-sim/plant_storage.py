#!/usr/bin/env python3
"""Re-plant storage.bin at 0x08008000 via SWD word programming.

Run AFTER set_rdp0.py (region must be mass-erased/all-FF; the script
asserts that before programming). Programs with FLASH_CR PG + PSIZE=word
+ BSY pacing per word, then verifies via byte reads.

Note: the bootloader Write Memory (0x31) path NACKs on this chip - see
FINDINGS.md - so planting must go over SWD, not UART.
"""
import sys
import time

sys.path.insert(0, '/home/tdaly/trezor-btc/storage-sim')
import chipwhisperer as cw  # noqa: E402
from swd.stlink import Stlink  # noqa: E402

FLASH = 0x40023C00
KEYR, SR, CR = FLASH + 4, FLASH + 0xC, FLASH + 0x10
STORAGE = 0x08008000


def main():
    data = open('/home/tdaly/trezor-btc/storage-sim/storage.bin', 'rb').read()
    if len(data) != 0x4000:
        sys.exit(f'storage.bin is {len(data)} B - expected 16384')

    # power-on fresh (avoids stale-DP wedges)
    s = cw.scope()
    s.io.target_pwr = True
    time.sleep(2)
    s.io.target_pwr = False
    time.sleep(2)
    s.io.target_pwr = True
    time.sleep(3)
    s.dis()

    st = Stlink(swd_frequency=480000)

    # sanity: region must be all-FF (mass-erased) before programming
    got = b''
    base = bytes(st.read_mem8(STORAGE, 64))
    if any(b != 0xFF for b in base):
        sys.exit(f'storage region not erased (head {base[:16].hex()}) - '
                 'run set_rdp0.py first')
    print('[1] region all-FF, OK to program')

    st.set_mem32(KEYR, 0x45670123)
    st.set_mem32(KEYR, 0xCDEF89AB)
    st.set_mem32(CR, 0x201)          # PG (bit0) + PSIZE = word (bits 9:8 = 10)
    for off in range(0, len(data), 4):
        st.write_mem32(STORAGE + off, data[off:off + 4])
        for _ in range(1000):
            if st.get_mem32(SR) & 1 == 0:
                break
            time.sleep(0.01)
        if off % 4096 == 0:
            print(f'    programmed {off / len(data) * 100:.0f}%', flush=True)
    st.set_mem32(CR, 0)

    # full byte-exact readback verify
    got = b''
    while len(got) < len(data):
        n = min(64, len(data) - len(got))
        got += bytes(st.read_mem8(STORAGE + len(got), n))
    ok = got == data
    del st
    print('[2] readback == storage.bin:', 'PASS' if ok else 'FAIL')
    if not ok:
        i = next(i for i, (a, b) in enumerate(zip(got, data)) if a != b)
        print(f'    first diff at {i:#x}: got {got[i:i+8].hex()} '
              f'want {data[i:i+8].hex()}')
        sys.exit(1)
    print('[3] verify next with uart_rdp0_test.py (expect CANARY NRC2)')


if __name__ == '__main__':
    main()
