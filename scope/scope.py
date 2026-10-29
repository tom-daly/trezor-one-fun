#!/usr/bin/env python3
"""Siglent SDS1202X-E driver (VXI-11 over direct ethernet).

Usage (from repo root):
  python scope/scope.py setup      # configure for glitch-node capture, arm single
  python scope/scope.py shot       # grab screen PNG + ch1 waveform after a shot
  python scope/scope.py cwcal      # CW glitch output calibration (see below)
Run with: /home/tdaly/.cwvenv/bin/python (has python-vxi11)
"""
import sys
import time

import vxi11

HOST = '10.11.13.220'


def conn():
    return vxi11.Instrument(HOST)


def ask(inst, cmd):
    return inst.ask(cmd).strip()


def cw_scope_calibration(clkgen=4e6, width=40, offset=-45, repeat=100,
                         vdiv='1V', tdiv='5US', fires=5, save=True):
    """Calibrate/verify the CW glitch SMA output against scope ch1.

    Connect the scope ch1 DIRECTLY to the CW GLITCH SMA (proper coax, no
    clips). Sets the CW to manual-trigger mode (no UART/TIO3/chip in the
    loop), fires `fires` manual pulses, and measures whether ch1 moves.

    Method (both proven 2026-10-27):
      1. AUTO mode frame-diff before/after firing -> alive? (robust even
         when the pulse is too fast/odd for a clean single trigger)
      2. If moving, measure the trace swing from the after-frame pixels
         (ground-marker method) -> volts
    Returns dict: {alive, swing_V, hi_V, lo_V, frames}
    Requires chipwhisperer (import here to keep module import light).
    """
    from PIL import Image

    inst = conn()
    inst.write('C1:OFST 0V')
    inst.write(f'C1:VDIV {vdiv}')
    inst.write('C1:CPL D1M')
    inst.write(f'TDIV {tdiv}')
    inst.write('TRMD AUTO')
    time.sleep(0.4)

    import chipwhisperer as cw
    s = cw.scope()
    s.io.target_pwr = 'high_z'
    s.clock.clkgen_freq = clkgen
    g = s.glitch
    g.clk_src = 'clkgen'
    g.output = 'enable_only'
    g.trigger_src = 'manual'
    g.ext_offset = 0
    g.width = width
    g.offset = offset
    g.repeat = repeat

    before = '/tmp/opencode/cwcal_before.bmp'
    after = '/tmp/opencode/cwcal_after.bmp'
    open(before, 'wb').write(inst.ask_raw(b'SCDP'))

    for _ in range(fires):
        g.manual_trigger()
        time.sleep(0.4)

    open(after, 'wb').write(inst.ask_raw(b'SCDP'))
    s.dis()

    # 1. frame diff
    ia, ib = Image.open(before).convert('L'), Image.open(after).convert('L')
    pa, pb = ia.load(), ib.load()
    diff = sum(1 for x in range(100, 700, 2) for y in range(50, 430, 2)
               if abs(pa[x, y] - pb[x, y]) > 40)
    alive = diff > 500

    # 2. swing from the after-frame (ground-marker pixel method)
    im = Image.open(after).convert('RGB')
    px = im.load()
    gy = [y for x in range(15, 40) for y in range(20, 460)
          if px[x, y][0] > 190 and px[x, y][1] > 170 and px[x, y][2] < 120]
    tr = {}
    for x in range(60, 780):
        ys = [y for y in range(20, 460)
              if px[x, y][0] > 190 and px[x, y][1] > 170 and px[x, y][2] < 130]
        if ys:
            tr[x] = (min(ys), max(ys))
    v_per_px = float(vdiv.replace('V', '')) / 50.0
    if gy and tr:
        ground = sum(gy) / len(gy)
        v = lambda y: (ground - y) * v_per_px
        xs = sorted(tr)
        lo_v, hi_v = v(max(tr[x][1] for x in xs)), v(min(tr[x][0] for x in xs))
        swing = hi_v - lo_v
    else:
        lo_v = hi_v = swing = None

    out = {'alive': alive, 'diff_px': diff, 'swing_V': swing,
           'hi_V': hi_v, 'lo_V': lo_v,
           'frames': (before, after) if save else None}
    print(f"[cwcal] alive={alive} (diff {diff}px) "
          f"swing={swing if swing is None else round(swing, 2)}V "
          f"({hi_v if hi_v is None else round(hi_v, 2)} .. "
          f"{lo_v if lo_v is None else round(lo_v, 2)} V)")
    inst.close()
    return out


def setup():
    inst = conn()
    # ch1 = glitch node (SMA T at QFP VCAP): 500 mV/div, DC 1M
    inst.write('C1:VDIV 500MV')
    inst.write('C1:CPL D1M')
    # ch2 = VDD 3V3 at chip: 1 V/div
    inst.write('C2:VDIV 1V')
    inst.write('C2:CPL D1M')
    # timebase: whole ~800 ns train visible with context
    inst.write('TDIV 100NS')
    # trigger: ch1, falling edge, ~300 mV below the ~1.2 V idle level
    inst.write('C1:TRSL NEG')
    inst.write('C1:TRLV 0.9V')
    inst.write('TRMD SINGLE')
    time.sleep(0.3)
    for c in ('C1:VDIV?', 'C2:VDIV?', 'TDIV?', 'C1:TRSL?', 'C1:TRLV?', 'TRMD?'):
        print(f'  {c:12s} {ask(inst, c)}')
    inst.close()
    print('[+] scope configured and armed in SINGLE')


def shot(png_out='/tmp/opencode/scope_shot.png'):
    inst = conn()
    trig = ask(inst, 'TRMD?')
    print(f'  trigger mode now: {trig}  (STOP = we caught something)')
    # screen dump
    raw = inst.ask_raw(b'SCDP')
    with open(png_out, 'wb') as f:
        f.write(raw)
    print(f'  screen -> {png_out} ({len(raw)} bytes)')
    # waveform: ch1, full 14k points
    w = inst.ask('C1:WF? DAT2')
    print(f'  C1:WF? -> {len(w)} bytes; head {w[:40]!r}')
    with open('/tmp/opencode/scope_ch1.bin', 'wb') as f:
        f.write(w.encode('latin-1', 'ignore'))
    inst.close()
    return png_out


if __name__ == '__main__':
    mode = sys.argv[1] if len(sys.argv) > 1 else 'setup'
    if mode == 'setup':
        setup()
    elif mode == 'shot':
        shot(sys.argv[2] if len(sys.argv) > 2 else '/tmp/opencode/scope_shot.png')
    elif mode == 'cwcal':
        # usage: scope.py cwcal [clkgen_hz] [width] [offset] [repeat]
        args = [float(x) for x in sys.argv[2:6]] if len(sys.argv) > 5 else []
        kw = {}
        if args:
            kw = dict(clkgen=args[0], width=int(args[1]),
                      offset=int(args[2]), repeat=int(args[3]))
        cw_scope_calibration(**kw)
