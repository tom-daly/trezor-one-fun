#!/usr/bin/env python3
from swd import Swd
import chipwhisperer as cw
import chipwhisperer.common.results.glitch as glitch
import time

try:
    s = cw.scope()
except Exception as e:
    print(f"❌ USB Error: {e}")
    print("Run: python3 reset_chipwhisperer.py")
    exit(1)
s.clock.clkgen_freq = 100E6
s.trigger.triggers = 'tio3'
s.glitch.clk_src = "clkgen"
s.glitch.output = "enable_only"
s.glitch.trigger_src = "ext_single"
s.io.glitch_lp = True
s.io.glitch_hp = True
s.glitch.repeat = 5
s.io.tio3 = 'high_z'

gc = glitch.GlitchController(groups=["success", "failure"], parameters=["width", "offset", "ext_offset"])
gc.set_range("width", 5, 5)
gc.set_range("offset", -10, -10)
gc.set_range("ext_offset", 50, 80000)
gc.set_global_step(1)

for glitch_setting in gc.glitch_values():
    s.glitch.width = glitch_setting[0]
    s.glitch.offset = glitch_setting[1]
    s.glitch.ext_offset = glitch_setting[2]
    print(f"ext_offset: {s.glitch.ext_offset/100:.1f}µs ", end="")
 
    s.arm()
    time.sleep(0.1)
 
    s.io.tio2 = True

    try:
        data = bytes(Swd().read_mem(0x1FFF7A10, 32))
        print(f"✅ {len(data)} bytes")
        break
    except Exception as e:
        print(f"❌")

    # Ensure TIO2 is low after read attempt
    s.io.tio2 = False

    # Reset target using nRST pin (if available)
    s.io.nrst = False
    time.sleep(0.1)
    s.io.nrst = 'high_z'
    time.sleep(0.5)