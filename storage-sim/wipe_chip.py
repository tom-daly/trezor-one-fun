#!/usr/bin/env python
"""wipe_chip.py -- clear readout protection + full mass-erase.

Uses the ST system bootloader's Readout Unprotect command over the FTDI UART
(AN3155: 0x92 0x6D -> ACK; the chip mass-erases + sets RDP to L0, ACKs, then
resets). This is more reliable on this rig than the SWD option-byte downgrade
(which did not commit the regression). Result: blank part at RDP0.

Rig: BOOT0=TIO1 (driven high), BOOT1=TIO2/pin28 low, UART=FTDI 115200 8E1.
Practice board only (G_PRACTICE_BOARD=YES).
"""
import sys
import time

import chipwhisperer as cw
import serial

sys.path.insert(0, '/home/tdaly/trezor-btc')
sys.path.insert(0, '/home/tdaly/trezor-btc/storage-sim')
from serialfind import find_ftdi                 # noqa: E402
from _practice_guard import require_practice_board  # noqa: E402
try:
    from swd.stlink import Stlink                  # noqa: E402
except Exception:                                  # noqa: BLE001
    Stlink = None


def sync(ser, tries=15):
    for _ in range(tries):
        ser.reset_input_buffer()
        ser.write(b'\x7f')
        if b'\x79' in ser.read(4):
            return True
        time.sleep(0.1)
    return False


def main():
    require_practice_board('wipe_chip.py (Readout Unprotect = MASS ERASE)')
    print('=' * 64)
    print('wipe_chip.py  -  bootloader Readout Unprotect -> RDP0 + mass erase')
    print('=' * 64)
    uart = find_ftdi()

    s = cw.scope()
    s.clock.clkgen_freq = 16e6
    s.io.glitch_hp = False
    s.io.glitch_lp = False
    s.io.tio1 = True            # BOOT0 high
    s.io.tio2 = 'gpio_low'      # BOOT1 low
    s.io.tio4 = 'high_z'
    s.io.target_pwr = False
    time.sleep(1.5)
    s.io.target_pwr = True
    time.sleep(3.0)
    ser = serial.Serial(uart, 115200, bytesize=8, parity='E', stopbits=1,
                        timeout=1.5)
    if not sync(ser):
        ser.close(); s.dis()
        sys.exit('bootloader did not sync (0x7F->0x79) - check BOOT0/UART')
    print('[+] bootloader synced (0x7F->0x79)')

    ser.reset_input_buffer()
    ser.write(bytes([0x92, 0x6D]))                 # Readout Unprotect + checksum
    a1 = ser.read(1)
    print(f'[+] 0x92 Readout-Unprotect ACK: {a1.hex() if a1 else "(none)"}')
    if a1 != b'\x79':
        print('[!] command not ACKed (NACK 0x1F / already L0?) - will verify.')
    a2 = ser.read(1)                               # post-erase ACK (before reset)
    print(f'[+] post-erase ACK: {a2.hex() if a2 else "(none / chip reset)"}')
    ser.close()
    time.sleep(2.5)                                # erase + reset settle
    s.dis()

    if Stlink is None:
        print('[i] pyswd unavailable - verify with investigate_chip.py')
        return
    st = None                                      # retry past the post-reset DP-wait
    for _ in range(6):
        try:
            time.sleep(0.6)
            st = Stlink(swd_frequency=480000)
            break
        except Exception:                          # noqa: BLE001
            continue
    if st is None:
        print('[i] SWD verify attach flaky (DP wait) after the reset - the 0x92 '
              'ACK above means the erase ran; confirm with investigate_chip.py.')
        return
    optcr = st.get_mem32(0x40023C14)
    rdp = (optcr >> 8) & 0xFF
    lvl = 0 if rdp == 0xAA else 2 if rdp == 0xCC else 1
    try:
        s0 = bytes(st.read_mem8(0x08000000, 16))
        ss = bytes(st.read_mem8(0x08008000, 16))
        blank = all(b == 0xFF for b in s0 + ss)
        readable = True
    except Exception as e:                          # noqa: BLE001
        s0 = ss = b''
        blank = readable = False
        print(f'[i] flash read fault: {e!r}')
    print(f'[+] OPTCR=0x{optcr:08X}  RDP 0x{rdp:02X} = L{lvl}')
    if readable:
        print(f'    flash head={s0.hex()}  storage head={ss.hex()}')
    if lvl == 0 and blank:
        print('\n[VERDICT] *** WIPED *** RDP0 + flash all-FF. Blank, ready to '
              're-provision (plant_storage.py).')
    elif lvl == 0:
        print('\n[?] RDP0 but flash read faulted at the heads - run '
              'investigate_chip.py to confirm blank.')
    else:
        print(f'\n[!] still L{lvl} - wipe did NOT take.')
    sys.exit(0 if (lvl == 0 and blank) else 1)


if __name__ == '__main__':
    main()
