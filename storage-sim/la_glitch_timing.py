#!/usr/bin/env python
"""LA-timed verification of the stage-2 pulse (idle verification shots).

Per shot: boot+sync happen between captures; inside each capture window
(continues sigrok fx2lafw @ 16 MHz) we fire exactly ONE real
rdp1_glitch_campaign_full_mem_dump.attempt() (ext 1546 / width 40 / rep 25).  Then decode:
  - UART frames on host-TX (0x11) and chip-TX (0x1F) channels;
  - any dip/pulse on a channel without UART frames = the glitch tap;
    report delay vs the 0x11 first falling edge and first rising edge
    (TIO3 reference) and the pulse width.
UI wiring: D0/D1 = FTDI RX/TX as decoded, glitch tap on any other ch.
"""
import subprocess
import sys
import time

import serial

import chipwhisperer as cw

import rdp1_glitch_campaign_full_mem_dump as g2
from serialfind import find_ftdi

SR = 16_000_000
SAMPLES = 12_800_000          # 0.8 s window per shot
EXT, WIDTH, REP = 17800, 5, 4  # current defaults: 178.0us, 40.0ns @ 100MHz
SHOTS = 3
SEARCH_US = (0, 200)           # glitch search window after burst start
UART_CHS = (0, 1)              # D0/D1 = FTDI RX/TX (user wiring)
GLITCH_CH = 2                  # D2 = glitch tap (user wiring 2026-10-27)
LA_CSV = '/tmp/opencode/pulse-timing.csv'


def load_edges(path):
    """Stream sigrok csv (fx2lafw): sample-indexed transitions per ch."""
    trans = [[] for _ in range(8)]
    prev = None
    with open(path) as f:
        rows = f.read().strip().split('\n')
    data = []
    for i, line in enumerate(rows):
        p = line.strip(',\r')
        if not p or not p[0].isdigit():
            continue
        vals = [v == '1' for v in p.split(',')[:8]]
        if len(vals) < 8:
            continue
        data.append(vals)
    prev = None
    trans = [[] for _ in range(8)]
    for idx, vals in enumerate(data):
        if prev is None:
            for ch, v in enumerate(vals):
                trans[ch].append((idx, v))
            prev = vals
            continue
        for ch, v in enumerate(vals):
            if v != prev[ch]:
                trans[ch].append((idx, v))
        prev = vals
    return trans


def decode_frames(edges):
    """8E1 UART decode. Returns [(start_idx, byte), ...] parity-valid."""
    bit = SR / 115200
    half = bit / 2
    out = []
    k = 0
    while k < len(edges):
        idx, v = edges[k]
        if v:
            k += 1
            continue
        data = 0
        parity = 0
        # data bits 1..8 then parity (start bit is n=0)
        for nbit in range(1, 10):
            st = state_at(edges, idx + half + nbit * bit)
            if nbit <= 8:
                data |= (1 << (nbit - 1)) if st else 0
            else:
                parity = 1 if st else 0
        # frame valid only if stop bit (n=10) is idle-high
        stop = state_at(edges, idx + half + 10 * bit)
        if stop and (bin(data).count('1') + parity) % 2 == 0:
            out.append((idx, data))
            # jump past this frame so mid-byte falling edges aren't reused
            adv = idx + half + 9.5 * bit
            while k < len(edges) and edges[k][0] < adv:
                k += 1
        k += 1
    return out


def state_at(edges, t):
    st = False
    for e_i, e_v in edges:
        if e_i > t:
            break
        st = e_v
    return st


def main():
    # --- CW setup copied from rdp1_glitch_campaign_full_mem_dump.main() ---
    g2.scope = cw.scope()
    g2.scope.io.target_pwr = 'high_z'
    try:
        import zipfile as _zf
        _fw = g2.scope.scopetype.getFWConfig()
        _z = _zf.ZipFile(_fw.loader._bsBuiltinData)
        with open('/tmp/opencode/cwlite_interface.bit', 'wb') as _bf:
            _bf.write(_z.read('cwlite_interface.bit'))
        g2.scope.scopetype.reload_fpga('/tmp/opencode/cwlite_interface.bit')
        print('[+] FPGA reloaded')
    except Exception as e:
        print(f'[!] FPGA reload skipped: {type(e).__name__}')
    g2.scope.clock.clkgen_freq = g2.CLKGEN
    g = g2.scope.glitch
    g.clk_src = 'clkgen'
    g.output = 'enable_only'
    g.trigger_src = 'ext_single'
    g2.scope.trigger.triggers = 'tio3'
    g2.scope.adc.basic_mode = 'rising_edge'
    g2.scope.io.glitch_lp = True
    g2.scope.io.glitch_hp = True
    g2.scope.io.tio3 = 'high_z'
    g2.ser = serial.Serial(g2.UART, 115200, bytesize=8, parity='E',
                           stopbits=1, timeout=0.4)
    g2.LAST_W = g2.LAST_O = None

    if not g2.boot_and_sync(fast=False):
        sys.exit('no sync to start')
    print('[+] synced (nulling glitch config at ext 0 to keep idle lines '
          'quiet until armed... no: armed inside window)')

    cmd = ['sigrok-cli', '--driver', 'fx2lafw',
           '--config', f'samplerate={SR}',
           '--samples', str(SAMPLES), '-O', 'csv']

    for shot in range(SHOTS):
        print(f'=== shot {shot + 1} ===')
        with open(LA_CSV, 'w') as f:
            la = subprocess.Popen(cmd, stdout=f, stderr=subprocess.DEVNULL)
            time.sleep(0.25)                    # let fx2 arm
            t0 = time.time()
            verdict, data, note = g2.attempt(EXT, WIDTH, REP)
            print(f'[+] attempt(): {verdict} {(note or "")[:20]}  '
                  f'({time.time() - t0:.2f}s)')
            time.sleep(max(0.05, 0.75 - (time.time() - t0)))
            la.wait(timeout=40)

        # decode
        trans = load_edges(LA_CSV)
        frames = {}
        for ch in UART_CHS:
            fr = decode_frames(trans[ch])
            if len(fr) >= 2:
                frames[ch] = fr
        tx = next((ch for ch, fr in frames.items()
                   if any(b == 0x11 for _, b in fr)), None)
        if tx is None:
            print('!! burst not seen on D0/D1; frames:', frames)
            continue
        txe = trans[tx]
        b11 = next(i for i, b in frames[tx] if b == 0x11)
        t_start = b11 / SR * 1e6        # us since capture start
        t_exp = EXT / g2.CLKGEN * 1e6   # expected glitch moment after 0x11
        pulse_ns = REP / g2.CLKGEN * 1e9

        print(f'  D{tx} = host TX, 0x11 start @ +0 (self)')
        rx = next((ch for ch in UART_CHS if ch != tx), None)
        if rx is not None and rx in frames and \
                any(b == 0x1F for _, b in frames[rx]):
            i1f = next(i for i, b in frames[rx] if b == 0x1F)
            print(f'  D{rx} = chip TX, NACK 0x1F @ '
                  f'+{i1f / SR * 1e6 - t_start:.2f}us'
                  f'  -> chip ALIVE at {pulse_ns:.0f}ns')
        elif rx is not None and len(trans[rx]) > 2:
            first_r = next(i for i, _ in trans[rx]) / SR * 1e6 - t_start
            print(f'  D{rx} = chip TX: {len(trans[rx])} transitions from '
                  f'+{first_r:.2f}us (frames failed strict decode - likely '
                  f'the back-to-back 1f1f NACK pair) -> chip ALIVE, '
                  f'response on the wire')
        else:
            print(f'  D{rx} = chip TX electrically silent in window'
                  f'  -> chip DEAD at {pulse_ns:.0f}ns')
        # D2 glitch tap: report every transition in the search window
        es = [e for e in trans[GLITCH_CH]
              if SEARCH_US[0] <= e[0] / SR * 1e6 - t_start <= SEARCH_US[1]]
        if es:
            print(f'  D2 = GLITCH TAP: {len(es)} transitions '
                  f'(glitch expected ~+{t_exp:.1f}us):')
            for idx, v in es[:6]:
                nxt = next((j for j, _ in trans[GLITCH_CH] if j > idx), None)
                dur = ((nxt - idx) / SR * 1e9) if nxt else -1
                print(f'    +{idx / SR * 1e6 - t_start:8.2f}us  '
                      f'{"rise" if v else "fall"}  width {dur:.0f}ns')
        else:
            print('  D2 = GLITCH TAP: silent in window '
                  f'(glitch expected ~+{t_exp:.1f}us; a {pulse_ns:.0f}ns '
                  f'pulse is under the 62.5ns LA period - silence is NOT '
                  f'proof of no-fire)')
    g2.teardown()


if __name__ == '__main__':
    main()
