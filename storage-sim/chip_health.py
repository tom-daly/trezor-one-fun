#!/usr/bin/env python3
"""Between-pass chip health check for the hammer loop.

Full power-cycle boot into the bootloader, then two known-good commands:
  0x7F sync  -> 0x79                       (bootloader alive)
  0x02 GetID -> 79 01 04 11 79             (chip responding, PID 0x411)
  0x11 readmem -> 1f 1f                    (alive AND still RDP1-locked)
Exit code 0 = healthy, 1 = degraded, 2 = dead. Prints one verdict line.
Run: /home/tdaly/.cwvenv/bin/python chip_health.py
"""
import sys
import time

sys.path.insert(0, '/home/tdaly/trezor-btc/storage-sim')
import serial                        # noqa: E402
import chipwhisperer as cw           # noqa: E402
from serialfind import find_ftdi     # noqa: E402

GETID = b'\x02\xfd'                  # Get ID + complement checksum (02^FF)


def main():
    s = cw.scope()                    # note: local name must NOT be 'cw'
    s.io.target_pwr = 'high_z'
    s.io.tio1 = True                # BOOT0 high -> system bootloader
    s.io.tio2 = 'high_z'
    s.io.tio4 = 'high_z'
    s.io.target_pwr = False
    time.sleep(1.5)
    s.io.target_pwr = True
    time.sleep(2.5)
    # NOTE: keep the CW session OPEN through the sync - releasing it
    # unloads the FPGA and can cut target power (proven on this rig)

    ser = serial.Serial(find_ftdi(), 115200, bytesize=8, parity='E',
                        stopbits=1, timeout=0.4)
    try:
        # 1. sync
        alive = False
        for _ in range(10):
            ser.reset_input_buffer()
            ser.write(b'\x7f')
            r = ser.read(4)
            if r and 0x79 in r:
                alive = True
                break
            time.sleep(0.1)
        if not alive:
            print('HEALTH: DEAD - no bootloader sync (0x7F gave nothing)')
            return 2

        # 2. Get ID (known good even at RDP1)
        ser.reset_input_buffer()
        ser.write(GETID)
        gid = ser.read(6)
        # 3. readmem (locked check)
        ser.reset_input_buffer()
        ser.write(b'\x11\xee')
        rm = ser.read(4)

        if gid and gid[0] == 0x79 and b'\x04\x11' in gid:
            lock = 'locked(RDP1)' if 0x1f in rm else \
                   ('*** UNLOCKED?! ***' if 0x79 in rm else 'no-readmem-reply')
            print(f'HEALTH: GOOD - sync 79, GetID {gid.hex()}, '
                  f'readmem {rm.hex() if rm else "(none)"} [{lock}]')
            return 0
        print(f'HEALTH: DEGRADED - sync ok but GetID -> {gid.hex() if gid else "(none)"}')
        return 1
    finally:
        ser.close()
        s.io.target_pwr = True        # leave target powered
        s.dis()


if __name__ == '__main__':
    sys.exit(main())
