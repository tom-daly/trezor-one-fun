#!/usr/bin/env python
"""Fire one Read Memory exchange inside a logic-analyzer capture window.

Boots the bootloader, syncs, launches sigrok-cli (fx2lafw) as a subprocess,
waits for it to arm, then sends the 0x11 0xEE command pair so the capture
contains: burst bytes (host TX) and the NACK (chip TX). Output CSV path is
printed for la_decode.py.
"""
import subprocess
import sys
import time

import serial

import chipwhisperer as cw

from serialfind import find_ftdi


def main():
    out_csv = sys.argv[1] if len(sys.argv) > 1 else '/tmp/opencode/la-run.csv'
    port = find_ftdi()
    print(f'[+] FTDI on {port}')

    scope = cw.scope()
    scope.io.tio1 = True
    scope.io.tio2 = 'high_z'
    scope.io.tio4 = 'high_z'
    scope.io.target_pwr = False
    time.sleep(1.5)
    scope.io.target_pwr = True
    time.sleep(3)

    ser = serial.Serial(port, 115200, bytesize=8, parity='E', stopbits=1,
                        timeout=0.2)
    ser.reset_input_buffer()
    ser.write(b'\x7f')
    r = ser.read(1)
    if r != b'\x79':
        scope.dis(); sys.exit(f'sync failed (got {r.hex() if r else "nothing"})')
    print('[+] synced')

    cmd = ['sigrok-cli', '--driver', 'fx2lafw',
           '--config', 'samplerate=2000000', '--samples', '3000000',
           '-O', 'csv']
    print(f'[+] launching capture -> {out_csv} (1.5 s @ 2 MHz)')
    with open(out_csv, 'w') as f:
        la = subprocess.Popen(cmd, stdout=f, stderr=subprocess.PIPE)
        time.sleep(0.7)          # let it arm; burst fires well inside window
        t0 = time.time()
        ser.write(b'\x11\xee')   # the Read Memory command pair
        r1 = ser.read(1)
        time.sleep(0.1)
        rest = ser.read(16)
        print(f'[+] burst sent at t0, response: {(r1 + rest).hex() or "(nothing)"}')
        la.wait(timeout=30)
        print(f'[+] capture done ({time.time() - t0:.1f}s), {out_csv}')
    ser.close()
    scope.dis()


if __name__ == '__main__':
    main()
