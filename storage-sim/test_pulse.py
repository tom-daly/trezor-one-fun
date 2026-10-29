#!/usr/bin/env python
"""Isolation test: does the CW glitch stage fire AT ALL?

No UART, no bootloader. Three glitchManual() strobes, 150 ms apart,
inside one LA capture (D0..D7 watched; the glitch tap idles LOW on D2 by
earlier analysis). Success = D2 shows short pulses ~96.6 us after each
strobe (ext_offset 1546 @ 16 MHz clkgen, width 40, repeat 25).
"""
import subprocess
import sys
import time

import chipwhisperer as cw
import la_glitch_timing as L
import serial

from serialfind import find_ftdi

SR = 16_000_000
SAMPLES = 16_000_000      # 1.0 s window
EXT, WIDTH, REP = 1546, 40, 25
N_FIRES = 3
GAP = 0.25
LA_CSV = '/tmp/opencode/pulse-test.csv'
MODE = sys.argv[1] if len(sys.argv) > 1 else 'manual'


def setup_cw():
    scope = cw.scope()
    scope.io.target_pwr = 'high_z'
    try:
        import zipfile as _zf
        _fw = scope.scopetype.getFWConfig()
        _z = _zf.ZipFile(_fw.loader._bsBuiltinData)
        with open('/tmp/opencode/cwlite_interface.bit', 'wb') as _bf:
            _bf.write(_z.read('cwlite_interface.bit'))
        scope.scopetype.reload_fpga('/tmp/opencode/cwlite_interface.bit')
        print('[+] FPGA reloaded')
    except Exception as e:
        print(f'[!] FPGA reload skipped: {type(e).__name__}')
    scope.clock.clkgen_freq = 16e6
    g = scope.glitch
    g.clk_src = 'clkgen'
    g.output = 'enable_only'
    g.trigger_src = MODE
    g.ext_offset = EXT
    g.width = WIDTH
    g.offset = 0
    g.repeat = REP
    scope.trigger.triggers = 'tio3'
    scope.adc.basic_mode = 'rising_edge' if MODE == 'ext_single' else 'default'
    scope.io.tio3 = 'high_z'
    scope.io.glitch_lp = True
    scope.io.glitch_hp = True
    dcm = scope.glitch.readStatus()
    print(f'[+] DCM status (phase1, phase2, lock1, lock2): {dcm}, '
          f'mmcm_locked={scope.glitch.mmcm_locked}')
    return scope


def main():
    scope = setup_cw()
    cmd = ['sigrok-cli', '--driver', 'fx2lafw',
           '--config', f'samplerate={SR}',
           '--samples', str(SAMPLES), '-O', 'csv']
    with open(LA_CSV, 'w') as f:
        la = subprocess.Popen(cmd, stdout=f, stderr=subprocess.DEVNULL)
        time.sleep(0.25)
        if MODE == 'manual':
            print('[+] firing 3x manual_trigger()', GAP * 1000, 'ms apart')
        elif MODE == 'ext_single':
            print('[+] 3 armed shots: arm() then 0x11ee burst')
            ser = serial.Serial(find_ftdi(), 115200, bytesize=8, parity='E',
                                stopbits=1, timeout=0.2)
        t_start = time.time()
        for i in range(N_FIRES):
            if MODE == 'manual':
                scope.glitch.manual_trigger()
                print(f'    fire {i + 1} at +{(time.time() - t_start) * 1000:.0f}ms')
            else:
                scope.arm()
                time.sleep(0.02)
                ser.reset_input_buffer()
                ser.write(b'\x11\xee')
                r = ser.read(8)
                print(f'    shot {i + 1} at +{(time.time() - t_start) * 1000:.0f}ms'
                      f' resp={r.hex() if r else "(none)"}')
            if i < N_FIRES - 1:
                time.sleep(GAP)
        if MODE != 'manual':
            ser.close()
        print(f'[+] burst done in ~{time.time() - t_start:.2f}s')
        la.wait(timeout=60)
    scope.dis()
    del scope

    # LA analysis: short pulses on any channel
    trans = L.load_edges(LA_CSV)
    print(f'[+] capture rows: '
          f'{sum(len(v) for v in trans[0])}+ rows loaded')
    for ch in range(8):
        es = trans[ch]
        if len(es) < 2:
            if len(es) == 1:
                print(f'  D{ch}: single-state start only ({es[0][1]})')
            continue
        durs = []
        for j, (idx, v) in enumerate(es[:-1]):
            nxt = es[j + 1][0]
            durs.append(((nxt - idx) / SR * 1e3, v))
        print(f'  D{ch}: {len(es)} edges '
              f'first: {[(f"{t:.3f}ms", int(v)) for t, v in durs[:6]]}')


if __name__ == '__main__':
    main()
