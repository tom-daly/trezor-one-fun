#!/usr/bin/env python
"""Empirical width-knob test: does the kill threshold respond to width?

The LA on the GLITCH pad is unreliable (VCAP idles at the LA's input
threshold), so use the target as the detector: boot + sync the bootloader,
fire single shots at increasing width (fixed repeat), and check alive/dead.
If kills begin at a width that moves with settings, the width knob is live.

Grid: at 4 MHz clkgen (49.8% = 124 ns nominal) and a 100 MHz comparison row.
"""
import time

import serial

import chipwhisperer as cw

from serialfind import find_ftdi

GRIDS = [
    # (clkgen_hz, [(width, offset, repeat), ...])
    (4e6, [(w, -45, 1) for w in (5, 10, 20, 30, 40, 49)]),
    (4e6, [(w, -45, 2) for w in (5, 10, 20, 30, 40, 49)]),
    (4e6, [(w, -45, 4) for w in (5, 10, 20, 30, 40, 49)]),
    # comparison: the known kill config from the dry-fire (100 MHz)
    (100e6, [(40, -45, 20)]),
]


def boot_sync(scope, ser):
    scope.io.tio1 = True
    scope.io.tio2 = 'high_z'
    scope.io.tio4 = 'high_z'
    scope.io.target_pwr = False
    time.sleep(1.5)
    scope.io.target_pwr = True
    time.sleep(3)
    scope.io.glitch_hp = False; scope.io.glitch_hp = True
    scope.io.glitch_lp = False; scope.io.glitch_lp = True
    ser.reset_input_buffer()
    ser.write(b'\x7f')
    return b'\x79' in ser.read(16)


def main():
    ser = serial.Serial(find_ftdi(), 115200, bytesize=8, parity='E',
                        stopbits=1, timeout=0.4)
    scope = cw.scope()
    scope.io.target_pwr = 'high_z'
    g = scope.glitch
    g.clk_src = 'clkgen'
    g.output = 'enable_only'
    g.trigger_src = 'manual'
    scope.io.glitch_lp = True
    scope.io.glitch_hp = True

    for clk, combos in GRIDS:
        scope.clock.clkgen_freq = clk
        print(f'--- clkgen {clk/1e6:.0f} MHz ---')
        for width, offset, repeat in combos:
            if not boot_sync(scope, ser):
                print('  (resync failed, retrying)')
                if not boot_sync(scope, ser):
                    print('  LOST TARGET'); return
            g.width = width
            g.offset = offset
            g.repeat = repeat
            g.manualTrigger()
            time.sleep(0.2)
            ser.reset_input_buffer()
            ser.write(b'\x7f')
            r = ser.read(16)
            alive = b'\x79' in r
            print(f'  width={width:2d} offset={offset} repeat={repeat}: '
                  f'{"ALIVE" if alive else "DEAD"}')
            time.sleep(0.15)
    scope.dis()


if __name__ == '__main__':
    main()
