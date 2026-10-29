#!/usr/bin/env python3
"""Fire the CW crowbar glitch train every N seconds, forever (Ctrl-C stops).

You catch the drop manually on the scope - this script only pulses the
rail at a steady, announced pace. No scope automation inside.

Usage:
  /home/tdaly/.cwvenv/bin/python scope/fire_30s.py               # gentle train every 30 s
  /home/tdaly/.cwvenv/bin/python scope/fire_30s.py 10            # every 10 s
  /home/tdaly/.cwvenv/bin/python scope/fire_30s.py 30 --hard     # max-energy train
  /home/tdaly/.cwvenv/bin/python scope/fire_30s.py 30 <clkgen_hz> <width> <offset> <repeat>
  --lp      also arm glitch_lp (hp+lp = strongest pull)
  --no-hp   fire WITHOUT the crowbar (debug only - goes nowhere)

Defaults (4 MHz, w49, off-45, rep100 = ~25 us enable_only train) are the
sanctioned gentle crowbar shot. glitch_hp is armed by default: without it
the fire signal never reaches the MOSFETs (FINDINGS.md, 2026-10-27).
"""
import os
import signal
import sys
import time

import chipwhisperer as cw

_raw = sys.argv[1:]
HARD = '--hard' in _raw
LP = '--lp' in _raw
HP = '--no-hp' not in _raw
_argv = [t for t in _raw if not t.startswith('--')]

INTERVAL = float(_argv[0]) if len(_argv) > 0 else 30.0
_DEFAULTS = (1e6, 49, -45, 4096) if HARD else (4e6, 49, -45, 100)
CLKGEN = float(_argv[1]) if len(_argv) > 1 else _DEFAULTS[0]
WIDTH = int(_argv[2]) if len(_argv) > 2 else _DEFAULTS[1]
OFFSET = int(_argv[3]) if len(_argv) > 3 else _DEFAULTS[2]
REPEAT = int(_argv[4]) if len(_argv) > 4 else _DEFAULTS[3]
TRAIN_US = REPEAT / CLKGEN * 1e6      # enable_only: ONE pulse, repeat cycles long
TRAIN_WAIT = 1e-3 + TRAIN_US / 1e6    # let the train finish before FET release

s = None


def teardown(*_):
    if s is not None:
        try:
            s.io.vglitch_reset()       # errata: crowbar MOSFETs can stick ON
            s.io.glitch_hp = False
            s.io.glitch_lp = False
        except Exception:
            pass
        try:
            s.dis()
        except Exception:
            pass
    print('\n[+] stopped - crowbar released, CW closed', flush=True)
    os._exit(0)   # FINDINGS quirk: soft teardown alone leaves loops running


signal.signal(signal.SIGINT, teardown)
signal.signal(signal.SIGTERM, teardown)


def setup():
    """Open CW with the rig discipline: clkgen FIRST, then glitch params."""
    sc = cw.scope()
    sc.io.target_pwr = 'high_z'
    sc.clock.clkgen_freq = CLKGEN
    g = sc.glitch
    g.clk_src = 'clkgen'
    g.output = 'enable_only'
    g.trigger_src = 'manual'
    g.ext_offset = 0
    g.width = WIDTH
    g.offset = OFFSET
    g.repeat = REPEAT
    time.sleep(0.3)
    if HP:
        sc.io.glitch_hp = True
    if LP:
        sc.io.glitch_lp = True
    time.sleep(0.2)
    return sc


def wait_until(deadline):
    """1 s ticks until the deadline, announcing the last 3 s."""
    while True:
        left = deadline - time.time()
        if left <= 0:
            return
        if left <= 3.05:
            print(f'   firing in {int(round(left))}...', flush=True)
        time.sleep(min(1.0, left))


def main():
    global s
    s = setup()
    print(f'[+] CW up: clkgen {CLKGEN/1e6:g} MHz, w{WIDTH} off{OFFSET} '
          f'rep{REPEAT} -> train ~{TRAIN_US:.1f} us, every {INTERVAL:g} s',
          flush=True)
    print(f'[+] crowbar {"ARMED (hp" + ("+lp" if LP else "") + ")" if HP else "DISARMED (--no-hp) - pulses go nowhere"}',
          flush=True)
    print('[+] Ctrl-C to stop', flush=True)

    n = 0
    next_fire = time.time() + INTERVAL
    while True:
        wait_until(next_fire)
        n += 1
        print(f'[{time.strftime("%H:%M:%S")}] shot {n} FIRED', flush=True)
        s.glitch.manual_trigger()
        time.sleep(TRAIN_WAIT)         # train completes before we release
        s.io.vglitch_reset()
        next_fire += INTERVAL


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f'[-] fatal: {type(e).__name__}: {e}', flush=True)
        teardown()
