#!/usr/bin/env python
"""Characterize the actual crowbar pulse train on this rig.

Fat-pulse trick: set clkgen to 10 MHz so width=40 = 4 us pulses the LA can
see cleanly. Reveals the true geometry - pulse count from repeat, spacing,
and the width/offset interaction (which produced ~70ns at 100MHz with
width=40/offset=-45). Geometry scales with the glitch clock, so these
measurements map 1:1 in cycles to the 100 MHz campaign settings.
"""
import subprocess
import sys
import time

import serial

import chipwhisperer as cw

from serialfind import find_ftdi

CONFIGS = [
    # (output, width, offset, repeat) - 4 MHz clkgen, ext 2000 cycles = 500us
    ('enable_only', 40, -45, 1),   # ~85% duty x 250ns = ~213ns pulse
    ('enable_only', 20, -45, 1),   # ~65% x 250ns = ~163ns
    ('enable_only', 10, -45, 1),   # ~55% x 250ns = ~137ns
    ('glitch_only', 40, -45, 1),   # 40% x 250ns = ~100ns
    ('enable_only', 40, -45, 2),   # two 213ns pulses back to back
]


def parse_d2(path, sr):
    rows = []
    for line in open(path):
        if line.startswith(';') or not line.strip():
            continue
        rows.append(line.rstrip('\n').split(','))
    prev = rows[0][2]
    edges = []
    for i, r in enumerate(rows):
        v = r[2]
        if v != prev:
            edges.append((i, v))
            prev = v
    # pulses = intervals high (value '1'), skipping the capture-start artifact
    pulses = []
    k = 0
    while k < len(edges) - 1:
        if edges[k][1] == '1' and edges[k][0] > 10:
            pulses.append((edges[k][0], edges[k + 1][0] - edges[k][0]))
        k += 1
    return [(t / sr * 1e6, w / sr * 1e6) for t, w in pulses]


def main():
    port = find_ftdi()
    scope = cw.scope()
    scope.io.target_pwr = 'high_z'
    scope.clock.clkgen_freq = 4e6            # width = % of cycle: 49.8% = 124ns
    try:
        scope.clock.reset_dcms()
    except Exception:
        pass
    g = scope.glitch
    g.clk_src = 'clkgen'
    g.output = 'enable_only'
    g.trigger_src = 'ext_single'
    scope.trigger.triggers = 'tio3'
    scope.adc.basic_mode = 'rising_edge'
    scope.io.glitch_lp = True
    scope.io.glitch_hp = True
    scope.io.tio3 = 'high_z'
    scope.io.tio1 = True
    scope.io.tio2 = 'high_z'
    scope.io.tio4 = 'high_z'

    ser = serial.Serial(port, 115200, bytesize=8, parity='E', stopbits=1,
                        timeout=0.4)

    for ci, (outmode, width, offset, repeat) in enumerate(CONFIGS):
        # fresh boot + sync per config (fat pulses will likely kill the core)
        scope.io.target_pwr = False
        time.sleep(1.5)
        scope.io.target_pwr = True
        time.sleep(3)
        scope.io.glitch_hp = False; scope.io.glitch_hp = True
        scope.io.glitch_lp = False; scope.io.glitch_lp = True
        ser.reset_input_buffer()
        ser.write(b'\x7f')
        if b'\x79' not in ser.read(16):
            print(f'[{ci}] no sync - skipping config')
            continue

        g.output = outmode
        g.width = width
        g.offset = offset
        g.repeat = repeat
        g.ext_offset = 2000          # 200us @ 10MHz - inside the byte pair
        cap = f'/tmp/opencode/pulse-char-{ci}.csv'
        with open(cap, 'w') as f:
            la = subprocess.Popen(
                ['sigrok-cli', '--driver', 'fx2lafw',
                 '--config', 'samplerate=16000000',
                 '--channels', 'D0,D1,D2', '--triggers', 'D0=f',
                 '--samples', '40000', '-O', 'csv'],
                stdout=f, stderr=subprocess.PIPE)
            # fire several armed bursts; the LA catches the first one after
            # it finishes arming (arming latency varies with USB load).
            # Each burst gets its own glitch, so the captured burst is
            # guaranteed to carry the pulse we want to measure.
            r = b''
            for _ in range(6):
                scope.arm()
                ser.reset_input_buffer()
                ser.write(b'\x11\xee')
                r = ser.read(32)
                try:
                    la.wait(timeout=2)
                    break
                except subprocess.TimeoutExpired:
                    continue
            try:
                la.wait(timeout=5)
            except subprocess.TimeoutExpired:
                la.kill()
                print(f'[{ci}] LA never triggered - skipping config')
                continue

        pulses = parse_d2(cap, 16_000_000)
        print(f'[{ci}] {outmode} width={width} offset={offset} repeat={repeat}: '
              f'{len(pulses)} pulses, reply={r.hex() if r else "dead"}')
        if pulses:
            widths = [round(w, 2) for _, w in pulses]
            gaps = [round(pulses[i+1][0] - pulses[i][0] - pulses[i][1], 2)
                    for i in range(len(pulses) - 1)]
            print(f'     pulse widths (us): {widths}')
            print(f'     pulse starts (us from burst): {[round(t,1) for t,_ in pulses]}')
            print(f'     gaps between pulses (us): {gaps}')
    scope.dis()


if __name__ == '__main__':
    main()
