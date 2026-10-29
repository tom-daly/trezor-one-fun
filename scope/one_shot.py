#!/usr/bin/env python3
"""Fire ONE glitch train from the CW - with the scope set up front.

If the Siglent scope (10.11.13.220) is reachable, configures it to the
settings that caught the glitch (ch1 84mV/div, 100ns/div, SINGLE trigger
on a rising edge), then fires one manual CW pulse train, then checks
whether the scope froze and saves the frame.

Usage:
  /home/tdaly/.cwvenv/bin/python scope/one_shot.py                # scope first (if on)
  /home/tdaly/.cwvenv/bin/python scope/one_shot.py --no-scope     # fire only, no scope
  /home/tdaly/.cwvenv/bin/python scope/one_shot.py <clkgen_hz> <width> <offset> <repeat>
  /home/tdaly/.cwvenv/bin/python scope/one_shot.py --hard         # max energy: 1 MHz,
                                                                  #   rep 4096 (~4 ms train)
  /home/tdaly/.cwvenv/bin/python scope/one_shot.py --loop 5       # 5 back-to-back trains
                                                                  # (--loop COMBINES with --hard)
  /home/tdaly/.cwvenv/bin/python scope/one_shot.py --glitch-hp   # ARM the crowbar MOSFET!
                                                                  # (glitch_lp available too;
                                                                  #  without them fires go nowhere)

Defaults: 4 MHz, width 49, offset -45, repeat 100 (~12 us train).
--hard:   1 MHz clkgen = 4x longer pulses, rep 4096 = ~40x more train
          (total delivered energy ~160x a default shot).
Positional args still override the preset (incl. --hard's).
Scope frame lands at /tmp/opencode/scope_glitch_check.png when caught.
"""
import sys
import time

import chipwhisperer as cw

SCOPE_HOST = '10.11.13.220'
_raw = sys.argv[1:]
NO_SCOPE = '--no-scope' in _raw
HARD = '--hard' in _raw
# The glitch SMA is a CROWBAR (MOSFET pulling the rail to GND) - the FPGA
# glitch signal only reaches it when glitch_hp/glitch_lp is ENABLED
# (source: rtfm.newae.com CW1173, "Using Glitch Port"). Without these the
# fire toggles a signal routed to nothing - that caused the entire dead
# night of mV-scale catches and ~6000 harmless NACK shots.
GLITCH_HP = '--glitch-hp' in _raw
GLITCH_LP = '--glitch-lp' in _raw
LOOP = 1
if '--loop' in _raw:
    LOOP = int(_raw[_raw.index('--loop') + 1])
# positional args = everything that isn't a flag or a flag's value
_argv, _skip = [], False
for tok in _raw:
    if _skip:
        _skip = False
        continue
    if tok == '--loop':
        _skip = True
        continue
    if tok.startswith('--'):
        continue
    _argv.append(tok)

_DEFAULTS = (1e6, 49, -45, 4096) if HARD else (4e6, 49, -45, 100)
CLKGEN = float(_argv[0]) if len(_argv) > 0 else _DEFAULTS[0]
WIDTH = int(_argv[1]) if len(_argv) > 1 else _DEFAULTS[1]
OFFSET = int(_argv[2]) if len(_argv) > 2 else _DEFAULTS[2]
REPEAT = int(_argv[3]) if len(_argv) > 3 else _DEFAULTS[3]
TRAIN_US = REPEAT / CLKGEN * 1e6   # total on-time of one train


def setup_scope():
    """Configure the scope to the VERIFIED glitch-catch settings (the CW
    output is MILLIVOLT-scale on the SMA - invisible at normal scales).
    Returns None if the scope is off/unreachable."""
    try:
        import vxi11
        inst = vxi11.Instrument(SCOPE_HOST)   # NO timeout kwarg (TypeError!)
        inst.timeout = 5000                    # set after creation instead
        inst.write('C2:OFF')
        inst.write('C1:OFST 0V')
        inst.write('C1:VDIV 500UV')       # user-verified catch recipe
        inst.write('C1:CPL D1M')
        inst.write('TDIV 50NS')
        inst.write('C1:TRSL NEG')       # DOWN edge (slope first)
        inst.write('TRSE EDGE,SR,C1,LT,OFF')
        inst.write('C1:TRLV -1.30MV')   # user-specified level
        inst.write('TRDL 12NS')
        inst.write('TRMD AUTO')          # clear any old STOP state
        time.sleep(0.3)
        inst.write('TRMD SINGLE')        # arm
        time.sleep(0.3)
        v = inst.ask('C1:VDIV?').strip()
        m = inst.ask('TRMD?').strip()
        print(f'[+] scope armed at VERIFIED catch settings '
              f'({v}, {inst.ask("TDIV?").strip()}, {m})')
        return inst
    except Exception as e:
        print(f'[.] scope not available ({type(e).__name__}) - firing blind')
        return None


def grab_frame(inst):
    try:
        m = inst.ask('TRMD?').strip()
        print(f'[+] scope after fire: {m}')
        if 'STOP' in m:
            bmp = '/tmp/opencode/scope_glitch_check.bmp'
            with open(bmp, 'wb') as f:
                f.write(inst.ask_raw(b'SCDP'))
            from PIL import Image
            Image.open(bmp).convert('RGB').save(
                '/tmp/opencode/scope_glitch_check.png')
            print('[+] *** CAUGHT - frame saved: '
                  '/tmp/opencode/scope_glitch_check.png ***')
        else:
            print('[.] no trigger - nothing crossed the level')
    except Exception as e:
        print(f'[.] frame grab failed: {type(e).__name__}')


def main():
    inst = None if NO_SCOPE else setup_scope()

    s = cw.scope()
    s.io.target_pwr = 'high_z'
    s.clock.clkgen_freq = CLKGEN
    g = s.glitch
    g.clk_src = 'clkgen'
    g.output = 'enable_only'
    g.trigger_src = 'manual'
    g.ext_offset = 0
    g.width = WIDTH
    g.offset = OFFSET
    g.repeat = REPEAT
    time.sleep(0.3)
    if GLITCH_HP:
        s.io.glitch_hp = True
    if GLITCH_LP:
        s.io.glitch_lp = True
    if GLITCH_HP or GLITCH_LP:
        print(f'[+] crowbar ARMED: hp={str(GLITCH_HP).lower()} '
              f'lp={str(GLITCH_LP).lower()}')
    print(f'[+] CW armed: clkgen {CLKGEN/1e6:g} MHz, w{WIDTH} '
          f'off{OFFSET} rep{REPEAT} -> train {TRAIN_US/1e3:.3f} ms '
          f'(rearm gap ~{1e6/CLKGEN:.0f} us)'
          + (f' x{LOOP} trains' if LOOP > 1 else ' [MAX ENERGY]' if HARD else ''))
    time.sleep(0.5)

    for n in range(LOOP):
        print(f'[+] >>> FIRING NOW ({n + 1}/{LOOP}) <<<')
        g.manual_trigger()
        print('*** FIRED ***')
        if n < LOOP - 1:
            time.sleep(0.3)
    # errata: crowbar MOSFETs can stick ON - always release after firing
    if GLITCH_HP or GLITCH_LP:
        s.io.vglitch_reset()
        print('[+] crowbar released (vglitch_reset)')
    time.sleep(0.8)

    if inst is not None:
        grab_frame(inst)
        inst.close()
    s.dis()


if __name__ == '__main__':
    main()
