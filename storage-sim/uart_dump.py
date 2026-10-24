#!/usr/bin/env python
"""STM32F2 system-bootloader UART dry run (no glitch) on the socket chip.

Protocol (ST AN3155): 0x7F autobaud -> ACK 0x79; every command byte is
followed by its XOR checksum. Read Memory = 0x11: address MSB-first plus
XOR-of-address checksum, then N-1 and ~(N-1), reply ACK + N bytes.

Wiring: FTDI TX->chip RX (PA10, 'U1 RX' spot), RX<-chip TX (PA9, 'U1 TX'),
GND common, NO VCC. BOOT0 driven by CW TIO1 (high), BOOT1 jumpered to 0.
Target power from CW (target_pwr cycle reboots into the bootloader).
"""
import argparse
import sys
import time

import serial

import chipwhisperer as cw

ACK, NACK = 0x79, 0x1F
UART = '/dev/ttyUSB0'


def boot_into_bootloader():
    scope = cw.scope()
    scope.io.tio1 = True     # BOOT0=1
    scope.io.tio2 = 'high_z' # BOOT1 held low by board jumper
    scope.io.tio4 = 'high_z'
    scope.io.target_pwr = False
    time.sleep(1.5)
    scope.io.target_pwr = True
    time.sleep(2)
    return scope


class Bl:
    def __init__(self, port=UART, baud=115200):
        self.ser = serial.Serial(port, baud, bytesize=8, parity='E',
                                 stopbits=1, timeout=1.0)

    def xfer(self, data: bytes, n=64) -> bytes:
        self.ser.reset_input_buffer()
        self.ser.write(data)
        return self.ser.read(n)

    def sync(self) -> bool:
        r = self.xfer(b'\x7f', 16)
        return ACK in r

    def cmd(self, c: int, payload: bytes = b'', n=64) -> bytes:
        r = self.xfer(bytes([c, c ^ 0xFF]) + payload, n)
        if not r or r[0] != ACK:
            raise RuntimeError(f'cmd 0x{c:02X}: no ACK (got {r.hex()})')
        return r[1:]

    def read_mem(self, addr: int, n: int) -> bytes:
        # 0x11 -> ACK; addr+cks -> ACK; N-1 + ~(N-1) -> ACK + data
        r = self.xfer(bytes([0x11, 0xEE]), 8)
        if not r or r[0] != ACK:
            raise RuntimeError(f'read_mem: no ACK (got {r.hex()})')
        ab = addr.to_bytes(4, 'big')
        r = self.xfer(ab + bytes([ab[0] ^ ab[1] ^ ab[2] ^ ab[3]]), 8)
        if not r or r[0] != ACK:
            raise RuntimeError(f'read_mem addr: no ACK (got {r.hex()})')
        n1 = n - 1
        r = self.xfer(bytes([n1, n1 ^ 0xFF]), n + 16)
        if not r or r[0] != ACK:
            raise RuntimeError(f'read_mem len: no ACK (got {r.hex()})')
        return r[1:1 + n]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--addr', default='0x08008000')
    ap.add_argument('--len', type=int, default=256)
    ap.add_argument('--out', default=None)
    args = ap.parse_args()
    addr, n = int(args.addr, 0), args.len

    scope = boot_into_bootloader()
    bl = Bl()
    if not bl.sync():
        scope.dis(); sys.exit('sync failed - no ACK to 0x7F')
    print('[+] synced (0x7F -> 0x79)')

    r = bl.cmd(0x02)                       # GET ID
    pid = r[1:2 + r[0]]
    print(f'[+] GET-ID: product ID 0x{pid.hex()}  (F205 = 0x411)')

    data = b''
    while len(data) < n:                   # 256 B max per read
        chunk = min(256, n - len(data))
        data += bl.read_mem(addr + len(data), chunk)
        print(f'\r[+] read {len(data)}/{n}', end='')
    print()
    print(f'[+] first 16 bytes @ {args.addr}: {data[:16].hex()}')
    if data[:4] == bytes.fromhex('0243324e'):
        pass
    canary = data[8:12]
    print(f'    canary @+0x08 (02 00 3C 00 expected): {canary.hex()}')
    if args.out:
        open(args.out, 'wb').write(data)
        print(f'[+] wrote {len(data)} B to {args.out}')
    scope.dis()


if __name__ == '__main__':
    main()
