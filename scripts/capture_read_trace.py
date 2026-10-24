#!/usr/bin/env python3
"""
Scope reconnaissance for glitch 2 (the during-read glitch).

Opens the SWD session (glitch 1 @ 17000), then triggers the ChipWhisperer ADC
on SWDIO (tio3) and captures a power trace WHILE issuing a flash read. The flash
access / RDP check shows up as a distinct feature in that window, so you read the
glitch-2 ext_offset off the trace instead of blind-scanning RANGE5.

REQUIRES the MEASURE line wired (1-10 ohm shunt in the VCC rail, MEASURE across
it). If the trace is flat, it will say so.

Captures N traces -> TRACES_READ/, prints the most active region (candidate
glitch-2 timing). Crowbar torn down on exit.
"""
import os, sys, time, signal, atexit
import numpy as np
import chipwhisperer as cw

N_TRACES  = int(os.environ.get("N_TRACES", 10))
SAMPLES   = int(os.environ.get("SAMPLES", 24400))
DECIMATE  = int(os.environ.get("DECIMATE", 10))     # 24400*10/100MHz ~= 2.44ms window
READ_ADDR = int(os.environ.get("READ_ADDR", str(0x08008000)), 0)   # storage region
P1_EXT    = int(os.environ.get("P1_EXT", 17000))
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
signal.signal(signal.SIGINT, _sig); signal.signal(signal.SIGTERM, _sig)

def open_session():
    scope.trigger.triggers = "tio4"
    scope.glitch.width, scope.glitch.offset, scope.glitch.repeat = 40, -45, 20
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

# ---- ADC capture clock ------------------------------------------------------
scope.clock.adc_src = "clkgen_x1"
locked = False
for _ in range(6):
    try: scope.clock.reset_adc()
    except Exception: pass
    time.sleep(0.5)
    if scope.clock.adc_locked:
        locked = True; break
print(f"ADC locked: {locked} (adc_freq={scope.clock.adc_freq})")
if not locked:
    print("⚠ ADC clock not locked — cannot capture."); sys.exit(1)

scope.adc.samples    = SAMPLES
scope.adc.offset     = 0
scope.adc.decimate   = DECIMATE
scope.adc.basic_mode = "rising_edge"
us_per_sample = DECIMATE / 100.0     # 100 MHz -> us per decimated sample
window_us = SAMPLES * us_per_sample
print(f"window: {window_us:.0f} us  ({SAMPLES} samples, decimate {DECIMATE})")

reboot_flush()
print("\n[phase 1] opening session ...")
dev = open_session()
if dev is None:
    print("  could not open session; re-run."); sys.exit(0)
print("  session open.")

print(f"\n[capture] triggering ADC on SWDIO while reading 0x{READ_ADDR:08X} ...")
scope.trigger.triggers = "tio3"
scope.io.tio3 = "high_z"
os.makedirs("TRACES_READ", exist_ok=True)

traces = []
for i in range(N_TRACES):
    scope.arm()
    cls = "?"
    try:
        data = bytes(dev.read_mem(READ_ADDR, 16))   # SWDIO activity triggers capture
        cls = "zero" if all(b == 0 for b in data) else ("ff" if all(b==0xFF for b in data) else "data")
    except Exception:
        cls = "fault"
        try:
            import swd; usb_reset(); time.sleep(0.2); dev = swd.Swd()
        except Exception:
            dev = open_session()
            if dev is None: break
            scope.trigger.triggers = "tio3"; scope.io.tio3 = "high_z"
    timed_out = scope.capture()
    tr = None if timed_out else scope.get_last_trace()
    if tr is not None:
        np.save(f"TRACES_READ/read_{i}_{cls}.npy", tr)
        traces.append(tr)
    print(f"  trace {i}: read={cls}  trig_timeout={timed_out}", flush=True)

if not traces:
    print("\nNo traces captured (trigger never fired on SWDIO, or capture timed out).")
    sys.exit(0)

T = np.array(traces)
mean = T.mean(axis=0)
span = float(mean.max() - mean.min())
print(f"\ncaptured {len(traces)} traces. trace span (max-min) = {span:.4f}")
if span < 0.01:
    print("⚠ trace is ~flat -> MEASURE not wired to a shunt yet. Wire it, then re-run.")
    sys.exit(0)

# locate the most active region (RDP check / flash access candidate)
w = 200
act = np.array([mean[i:i+w].std() for i in range(0, len(mean)-w, w)])
k = int(np.argmax(act))
t_us = k * w * us_per_sample
ext = int(t_us * 100)
print(f"most active region: ~{t_us:.0f} us after SWDIO edge  (ext_offset ~{ext})")
print(f"=> try glitch 2 around ext_offset {ext-500}..{ext+500}, narrow widths")
print("traces saved in TRACES_READ/*.npy")
