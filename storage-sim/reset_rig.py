#!/usr/bin/env python3
"""Total rig reset - the recovery ladder for a wedged/dead session.

Ladder (everything we have proven on this rig):
  1. fresh CW open (re-opens USB, reloads FPGA), BOOT0-high power cycle,
     UART sync probe                 - fixes ~90% of "dead" states
  2. NRST (TIO4) pulse + retry       - clears simple hangs
  3. repeated power cycles (5x)     - clears core lockup via POR
  4. (not available right now: SWD SYSRESETREQ - the proven deep recovery
     for core lockup, needs the ST-Link; currently disconnected)
Prints a verdict line. Exit 0 = recovered, 1 = needs physical intervention.
Run: /home/tdaly/.cwvenv/bin/python reset_rig.py
"""
import sys
import time

sys.path.insert(0, '/home/tdaly/trezor-btc/storage-sim')
import serial                        # noqa: E402
import chipwhisperer as cw           # noqa: E402
from serialfind import find_ftdi     # noqa: E402


def fresh_cw():
    s = cw.scope()                    # fresh open re-inits USB + FPGA
    s.io.target_pwr = 'high_z'
    s.clock.clkgen_freq = 16e6
    s.io.tio1 = True                 # BOOT0 high
    s.io.tio2 = 'high_z'
    s.io.tio4 = 'high_z'
    return s


def try_sync(ser):
    for _ in range(10):
        ser.reset_input_buffer()
        ser.write(b'\x7f')
        r = ser.read(4)
        if r and 0x79 in r:
            return True
        time.sleep(0.1)
    return False


def main():
    # L1: fresh CW + power cycle + sync
    try:
        s = fresh_cw()
    except Exception as e:
        print(f'RESET: FAILED at CW open ({type(e).__name__}) - '
              'PHYSICAL: unplug/replug the CW USB, then rerun')
        return 1
    s.io.target_pwr = False; time.sleep(1.5)
    s.io.target_pwr = True;  time.sleep(2.5)

    ser = serial.Serial(find_ftdi(), 115200, bytesize=8, parity='E',
                        stopbits=1, timeout=0.4)
    try:
        if try_sync(ser):
            print('RESET: OK (L1 - power-cycle boot, bootloader synced)')
            return 0

        # L2: NRST pulse + sync
        s.io.tio4 = 'gpio_low'; time.sleep(0.05); s.io.tio4 = 'high_z'
        time.sleep(1.0)
        if try_sync(ser):
            print('RESET: OK (L2 - NRST pulse, bootloader synced)')
            return 0

        # L3: repeated power cycles
        for i in range(5):
            s.io.target_pwr = False; time.sleep(1.5)
            s.io.target_pwr = True;  time.sleep(2.5)
            if try_sync(ser):
                print(f'RESET: OK (L3 - power cycle #{i+1} cleared it)')
                return 0

        print('RESET: FAILED after full ladder - PHYSICAL checklist:\n'
              '  1. unplug/replug CW USB (wedged USB throws on open)\n'
              '  2. reseat the CW 20-pin power feed + FTDI TX/RX clips\n'
              '  3. if ST-Link/SWD is reconnected: SWD SYSRESETREQ is the\n'
              '     proven lockup recovery (see FINDINGS 2026-10-26)\n'
              '  4. last resort: full board power-off for 10s')
        return 1
    finally:
        ser.close()
        s.io.target_pwr = True        # leave the target powered
        s.dis()


if __name__ == '__main__':
    sys.exit(main())
