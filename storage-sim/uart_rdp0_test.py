#!/usr/bin/env python3
"""UART bootloader test at RDP0 - the jackpot's downstream path.

With read protection cleared (set_rdp0.py has run):
  sync 0x7F               -> ACK 0x79
  readmem 0x11ee          -> ACK 0x79   (at RDP1 this is NACKed)
  read 16 KB @ 0x08008000 -> data, 255-bit chunks
Reports protection state + what the storage region contains:
  all-FF  = mass-erased (plant gone), NRC2 = planted storage intact.
"""
import sys
import time

import serial
import chipwhisperer as cw

from serialfind import find_ftdi

STORAGE_ADDR = 0x08008000
LEN = 0x1000
CANARY = bytes.fromhex('4e524332')


def sync_bootloader(ser, tries=10):
    for i in range(tries):
        ser.reset_input_buffer()
        ser.write(b'\x7f')
        r = ser.read(8)
        if r and 0x79 in r:
            if i:
                print(f'    synced after {i + 1} attempts')
            return True
        time.sleep(0.05)
    return False


def read_chunk(ser, addr, n, state=False):
    """One complete Read Memory transaction.
    Returns bytes (data), or with state=True: ('ok', bytes) /
    ('nack', None) if readmem was NACKed (protection) / ('refused', None).
    A NACKed readmem aborts the session cleanly, so a resync is needed."""
    ab = addr.to_bytes(4, 'big')
    ser.write(b'\x11\xee')
    r = ser.read(1)                     # ack is exactly 1 byte
    if not r:
        return ('no-reply', None) if state else None
    if r[0] == 0x1F:
        return ('nack', None) if state else None
    if r[0] != 0x79:
        return ('refused', None) if state else None
    ser.write(ab + bytes([ab[0] ^ ab[1] ^ ab[2] ^ ab[3]]))
    r = ser.read(1)
    if not r or r[0] != 0x79:
        return ('refused', None) if state else None
    k = n - 1
    ser.write(bytes([k, k ^ 0xFF]))
    r = ser.read(n + 1)                 # 0x79 + n data bytes
    if not r or r[0] != 0x79:
        return ('refused', None) if state else None
    data = r[1:1 + n]
    return ('ok', data) if state else data


def main():
    s = cw.scope()
    s.io.target_pwr = True
    time.sleep(2)
    s.io.target_pwr = False
    time.sleep(2)
    s.io.target_pwr = True
    time.sleep(3)
    s.dis()

    ser = serial.Serial(find_ftdi(), 115200, bytesize=8, parity='E',
                        stopbits=1, timeout=2.0)
    if not sync_bootloader(ser):
        print('SYN FAIL - bootloader not alive')
        sys.exit(1)
    print('[1] sync 0x79 OK')

    # state classification through the SAME completed transaction - no
    # partial readmem probe (a leftover handshake poisons the session).
    st, first = read_chunk(ser, STORAGE_ADDR, 255, state=True)
    if st == 'nack':
        print('[2] readmem NACKed -> RDP still level 1, nothing readable.')
        sys.exit(2)
    if st != 'ok':
        print(f'[2] readmem refused ({st}) after sync - resyncing and retrying')
        if not sync_bootloader(ser):
            sys.exit(2)
        st, first = read_chunk(ser, STORAGE_ADDR, 255, state=True)
        if st != 'ok':
            print(f'[2] still {st} after resync')
            sys.exit(2)
    print(f'[2] readmem ACKed -> RDP UNPROTECTED, first chunk OK')

    got = b''
    refused = False
    for off in range(0, LEN, 255):
        chunk = first if off == 0 else read_chunk(ser, STORAGE_ADDR + off, 255)
        tries = 0
        while chunk is None and tries < 3:
            tries += 1
            if not sync_bootloader(ser):
                break
            chunk = read_chunk(ser, STORAGE_ADDR + off, 255)
        if chunk is None:
            print(f'[3] read failed at +{off:#x}')
            sys.exit(3)
        got += chunk
    got = got[:LEN]
    head = got[:16]
    print(f'[3] dumped {len(got)} B, head: {head.hex()}')
    if got.startswith(b'\xff' * 8):
        verdict = 'mass-erased (plant gone)'
    elif got.startswith(CANARY):
        verdict = 'CANARY NRC2 - planted storage intact'
    else:
        verdict = 'data present (unexpected content)'
    print('[4] storage state:', verdict)
    if '--out' in sys.argv:
        out = open(sys.argv[sys.argv.index('--out') + 1], 'wb').write(got)
        print(f'[5] saved {len(got)} B')


if __name__ == '__main__':
    main()
