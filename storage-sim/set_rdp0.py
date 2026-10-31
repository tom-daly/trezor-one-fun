#!/usr/bin/env python3
"""RDP1 -> RDP0 + guaranteed mass erase on the socketed F205 (Trezor twin).

End state after a PASS: RDP == level 0 AND flash all-FF.

Paths:
  - RDP1 -> unlock OPTCR, program RDP byte 0xAA. The built-in mass erase
    fires on option reload (power cycle), wiping all flash.
  - Already RDP0: the storage sector may still hold the plant; we erase
    via the system bootloader's Extended Erase (0x44, global mass erase),
    which is the one wipe verified reliable on this chip. SWD sector
    erase is inconsistent here (F2 art-cache masks reads + BSY quirks)

Afterwards run plant_storage.py (SWD word programming - the bootloader
Write Memory path NACKs on this chip) and uart_rdp0_test.py.
"""
import functools
import sys
import time

sys.path.insert(0, '/home/tdaly/trezor-btc')
from swd.stlink import Stlink          # noqa: E402
import chipwhisperer as cw             # noqa: E402
import serial                          # noqa: E402
from _practice_guard import require_practice_board  # noqa: E402
sys.path.insert(0, '/home/tdaly/trezor-btc/storage-sim')
from serialfind import find_ftdi       # noqa: E402

FLASH = 0x40023C00
KEYR, OPTKEYR, SR, CR, OPTCR = (FLASH + 4, FLASH + 8, FLASH + 0xC,
                                FLASH + 0x10, FLASH + 0x14)
OPTKEY1, OPTKEY2 = 0x08192A3B, 0x4C5D6E7F
STORAGE_ADDR = 0x08008000


def wait_bsy(st, mask=1 << 16):
    for _ in range(2000):
        if st.get_mem32(SR) & mask == 0:
            return True
        time.sleep(0.005)
    return False


def read_rdp(st):
    return (st.get_mem32(OPTCR) >> 8) & 0xFF


def rdp_downgrade_via_options(st):
    st.set_mem32(OPTKEYR, OPTKEY1)
    st.set_mem32(OPTKEYR, OPTKEY2)
    if st.get_mem32(OPTCR) & 1:
        sys.exit('option lock did not open')
    new = (st.get_mem32(OPTCR) & ~(0xFF << 8)) | (0xAA << 8)
    new &= ~1                    # OPTLOCK = 0 for the write
    st.set_mem32(OPTCR, new)
    st.set_mem32(OPTCR, new | 2)  # OPTSTRT
    for _ in range(20):          # BSY may read oddly mid-erase
        if st.get_mem32(SR) & (1 << 16) == 0:
            break
        time.sleep(0.5)
    print(f'    RDP0 written, OPTCR now: 0x{st.get_mem32(OPTCR):08X} - '
          'mass erase runs on option reload')


def power_cycle(off=2.0, on=3.0):
    import gc
    s = cw.scope()
    s.io.target_pwr = False
    time.sleep(off)
    s.io.target_pwr = True
    time.sleep(on)
    s.dis()
    del s
    gc.collect()          # CW handle must be fully free before Stlink opens


def sync_bootloader(ser, tries=10):
    for _ in range(tries):
        ser.reset_input_buffer()
        ser.write(b'\x7f')
        r = ser.read(8)
        if r and 0x79 in r:
            return True
        time.sleep(0.05)
    return False


def uart_mass_erase_in_session(ser):
    """Extended Erase (0x44/0xBB), payload FF FF 00 = global mass erase.
    MUST run inside the session that synced - a fresh 0x7F on a reopened
    port does not re-sync this bootloader."""
    ser.write(b'\x44\xbb')
    r = ser.read(2)
    if not r or r[0] != 0x79:
        sys.exit(f'extended erase cmd refused: {r.hex()}')
    ser.write(bytes([0xFF, 0xFF, 0x00]))
    ser.timeout = 60
    r = ser.read(2)
    if not r or r[0] != 0x79:
        sys.exit(f'mass erase failed: {r.hex()}')
    print('    uart mass erase ACK (OK)')
    ser.timeout = 1.0


def main():
    require_practice_board('set_rdp0.py (RDP1->RDP0 regression = MASS ERASE)')
    power_cycle()
    st = Stlink(swd_frequency=480000)
    cur = read_rdp(st)
    print(f'[1] RDP byte: 0x{cur:02X} '
          f'(level {"0" if cur == 0xAA else "1" if cur == 0x55 else "?"})')
    if cur == 0xCC:
        st._com._usb = None        # let go before any exit()
        del st
        sys.exit('!! RDP level 2 - nothing safe to do')

    if cur != 0xAA:
        rdp_downgrade_via_options(st)
        del st
        power_cycle()
    else:
        del st
    st = Stlink(swd_frequency=480000)
    rdp = read_rdp(st)
    if rdp != 0xAA:
        del st
        sys.exit(f'RDP still 0x{rdp:02X} - aborting')
    del st

    # is flash already clean? (power-cycled reads are cold-cache; read via
    # UART readmem to bypass any DAP/ART caching)
    port = find_ftdi()
    ser = serial.Serial(port, 115200, bytesize=8, parity='E', stopbits=1,
                        timeout=1.0)
    if not sync_bootloader(ser):
        sys.exit('sync failed')
    n = 8
    ser.write(b'\x11\xee')
    r1 = ser.read(1)
    if r1 != b'\x79':
        sys.exit(f'readmem refused: {r1.hex() if r1 else "(none)"}')
    ab = STORAGE_ADDR.to_bytes(4, 'big')
    ser.write(ab + bytes([functools.reduce(int.__xor__, ab)]))
    if ser.read(1) != b'\x79':
        sys.exit('addr stage refused')
    ser.write(bytes([n - 1, (n - 1) ^ 0xFF]))
    r = ser.read(n + 1)
    head = r[1:n + 1] if (r and len(r) == n + 1 and r[0] == 0x79) else None
    if head is None:
        ser.close()
        sys.exit('could not read flash head - aborting')
    if all(b == 0xFF for b in head):
        print('[2] flash head all-FF - nothing to erase')
        ser.close()
    else:
        print(f'[2] flash head {head.hex()} - mass erase (same session)')
        uart_mass_erase_in_session(ser)
        ser.close()

    power_cycle()   # fresh boot so post-state reads are cold-cache

    # final SWD verification exactly like the original state check
    st = Stlink(swd_frequency=480000)
    rdp = read_rdp(st)
    got = bytes(st.read_mem8(STORAGE_ADDR, 32))
    del st
    erased = all(b == 0xFF for b in got)
    print(f'[3] final check: RDP 0x{rdp:02X}, head {got.hex()} '
          f'({"mass-erased OK" if erased else "NOT erased"})')
    ok = rdp == 0xAA and erased
    print('\n==== SET_RDP0', 'PASS' if ok else 'FAIL', '====')
    if ok:
        print('next: plant_storage.py, then uart_rdp0_test.py')


if __name__ == '__main__':
    main()
