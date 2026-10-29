#!/usr/bin/env python
"""Campaign driver + LA snooping: every shot fires inside an LA capture
window so the WIRE timing can be verified against the intended ext_offset.

Channels (user wiring 2026-10-27): D0 = host TX (the FTDI TX tee = the
TIO3 trigger reference), D1 = chip TX, D2 = glitch tap.

Per shot: LA window up -> one gated campaign attempt (same env config,
baseline gate and verdict logic as rdp1_glitch_campaign_full_mem_dump)
-> LA window down -> decode:
  - t0 = 0x11 start bit on D0 (same edge TIO3 triggers on)
  - chip response on D1: start time vs t0, edge count, strict frames
  - expected glitch moment = ext/clkgen after t0
  - D2 transitions in the window
CAVEAT: a <62.5ns glitch pulse is UNDER the 16 MHz LA sample period - D2
silence is not no-fire evidence; D1's response (presence/timing/garble)
is the verifiable signal.

Run with the SAME G_* env knobs as the campaign driver, plus LA_* knobs.
Example - 45ns over the extended window, 40 shots:
  G_REPEATS=5 G_CLKGEN=111110000 G_US_MIN=175 G_US_MAX=185 \
  LA_SHOTS=40 G_TAG=lasnoop45 \
  /home/tdaly/.cwvenv/bin/python la_campaign_snoop.py
Pace ~3-5 s/shot (LA window + decode) - a verification instrument, not a
hammer: use the real driver for big sweeps, this to verify timing.
CSV -> campaigns/lasnoop_<tag>_<ts>.csv
"""
import csv
import os
import subprocess
import sys
import time
from datetime import datetime

import serial

import chipwhisperer as cw

import la_glitch_timing as lat          # load_edges / decode_frames
import rdp1_glitch_campaign_full_mem_dump as g2
from serialfind import find_ftdi

SR = int(os.environ.get('LA_SR', 16_000_000))
WIN_S = float(os.environ.get('LA_WIN', 0.8))       # LA window per shot
SAMPLES = int(SR * WIN_S)
UART_CHS, GLITCH_CH = (0, 1), 2
SHOTS = int(os.environ.get('LA_SHOTS', 2))
LA_CSV = '/tmp/opencode/la_snoop.csv'
RESP_AFTER_US = 150       # chip response expected >150us after burst start

SIGROK = ['sigrok-cli', '--driver', 'fx2lafw',
          '--config', f'samplerate={SR}', '--samples', str(SAMPLES),
          '-O', 'csv']


def setup():
    """Same CW bring-up as the campaign driver main()."""
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
    g.output = g2.OUTPUT
    g.trigger_src = 'ext_single'
    g2.scope.trigger.triggers = 'tio3'
    g2.scope.adc.basic_mode = 'rising_edge'
    if g2.CROWBAR:
        g2.scope.io.glitch_hp = True
        if g2.LP_ARM:
            g2.scope.io.glitch_lp = True
    g2.scope.io.tio3 = 'high_z'
    g2.ser = serial.Serial(g2.UART, 115200, bytesize=8, parity='E',
                           stopbits=1, timeout=0.4)
    g2.LAST_W = g2.LAST_O = None
    print(f'[+] STRENGTH: {g2.OUTPUT} @ {g2.CLKGEN/1e6:g} MHz, '
          f'FETs hp{"+lp" if g2.LP_ARM else ""}, '
          + ', '.join(f'rep{r}={r / g2.CLKGEN * 1e9:.1f}ns'
                      for r in g2.REPEATS))
    if not g2.boot_and_sync(fast=False):
        sys.exit('no sync to start')
    print('[+] synced - LA snooping ready')


def analyze():
    """Decode the last capture. Returns a dict of wire measurements."""
    trans = lat.load_edges(LA_CSV)
    frames = {ch: lat.decode_frames(trans[ch]) for ch in UART_CHS}
    tx = next((ch for ch in UART_CHS
               if any(b == 0x11 for _, b in frames[ch])), UART_CHS[0])
    if not trans[tx]:
        return {'error': 'burst not on D0/D1'}
    t0 = trans[tx][0][0]                       # 0x11 start-bit edge
    out = {'resp_us': None, 'resp_edges': 0, 'frames_ok': 0, 'd2_edges': 0}
    rx = next(ch for ch in UART_CHS if ch != tx)
    resp = [(i, v) for i, v in trans[rx]
            if t0 + RESP_AFTER_US * SR / 1e6 < i < t0 + 3000 * SR / 1e6]
    if resp:
        out['resp_us'] = (resp[0][0] - t0) / SR * 1e6
        out['resp_edges'] = len(resp)
    out['frames_ok'] = len(frames[rx])
    d2 = [(i, v) for i, v in trans[GLITCH_CH]
          if t0 - 20 * SR / 1e6 < i < t0 + 500 * SR / 1e6]
    out['d2_edges'] = len(d2)
    if d2:
        out['d2_first_us'] = (d2[0][0] - t0) / SR * 1e6
    return out


def main():
    setup()
    tag = os.environ.get('G_TAG', '')
    log_path = os.path.join(
        'campaigns', f'lasnoop_{datetime.now():%Y%m%d_%H%M%S}'
        + (f'_{tag}' if tag else '') + '.csv')
    os.makedirs('campaigns', exist_ok=True)
    logf = open(log_path, 'w', newline='')
    logw = csv.writer(logf)
    logw.writerow(['config', g2.CLKGEN, g2.OUTPUT, ','.join(map(str, g2.WIDTHS)),
                   ','.join(map(str, g2.REPEATS)), g2.EXT_MIN, g2.EXT_MAX, tag])
    logw.writerow(['shot', 'ext', 'us', 'pulse_ns', 'verdict',
                   'resp_us', 'resp_edges', 'frames_ok', 'd2_edges', 'note'])

    shot = 0
    for ext in range(g2.EXT_MIN, g2.EXT_MAX + 1, g2.STEP):
        for width in g2.WIDTHS:
            for repeat in g2.REPEATS:
                for _sample in range(g2.SAMPLES):
                    if shot >= SHOTS or shot >= g2.SHOTS_MAX:
                        g2.teardown(); return
                    with open(LA_CSV, 'w') as f:
                        la = subprocess.Popen(SIGROK, stdout=f,
                                              stderr=subprocess.DEVNULL)
                        time.sleep(0.25)          # let fx2lafw arm
                        try:
                            verdict, payload, note = g2.baseline_then_shot(
                                ext, width, repeat)
                        except Exception as e:
                            la.kill()
                            print(f'[!] rig drop {type(e).__name__} -> '
                                  'stopping (rerun to continue)', flush=True)
                            g2.teardown(); sys.exit(1)
                        # keep the whole exchange inside the window
                        time.sleep(max(0.05, WIN_S - 0.25 - 0.5))
                        la.wait(timeout=40)
                    shot += 1
                    m = analyze()
                    pulse_ns = repeat / g2.CLKGEN * 1e9
                    exp_us = ext / g2.CLKGEN * 1e6
                    print(f'  [{datetime.now():%H:%M:%S}] #{shot} '
                          f'ext={ext} ({exp_us:.2f}us expected) '
                          f'w{width} r{repeat}={pulse_ns:.0f}ns '
                          f'-> {verdict}'
                          + (f' | LA: resp +{m["resp_us"]:.2f}us '
                             f'{m["resp_edges"]}e {m["frames_ok"]}f'
                             if m.get('resp_us') is not None
                             else ' | LA: no response')
                          + (f' D2:{m["d2_edges"]}e'
                             f'(+{m["d2_first_us"]:.2f}us)'
                             if m.get('d2_edges') else ' D2:flat'),
                          flush=True)
                    logw.writerow([shot, ext, round(exp_us, 2),
                                   round(pulse_ns, 1), verdict,
                                   m.get('resp_us'), m.get('resp_edges'),
                                   m.get('frames_ok'), m.get('d2_edges'),
                                   note or ''])
                    logf.flush()
                    if verdict == 'SUCCESS':
                        out = f'JACKPOT_{datetime.now():%H%M%S}.bin'
                        open(out, 'wb').write(payload)
                        print(f'\n[***] SUCCESS ext={ext} ({exp_us:.2f}us) '
                              f'r{repeat}={pulse_ns:.0f}ns -> {out}'
                              + ('  CANARY MATCH!' if payload[:4]
                                 == g2.CANARY_MAGIC else ''), flush=True)
                        logf.flush(); g2.teardown(); return
                    if verdict in ('dead', 'weird', 'ACK_NO_DATA'):
                        try:
                            ok = g2.boot_and_sync(fast=True) or \
                                g2.boot_and_sync(fast=False)
                        except Exception:
                            ok = False
                        if not ok:
                            print('[!] target lost after resync', flush=True)
                            g2.teardown(); sys.exit(1)
                    time.sleep(g2.COOLDOWN)
    print(f'[.] snoop pass done, {shot} shots -> {log_path}', flush=True)
    g2.teardown()


if __name__ == '__main__':
    main()
