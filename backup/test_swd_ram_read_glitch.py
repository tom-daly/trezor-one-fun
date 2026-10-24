#!/usr/bin/env python3
from swd import Swd
import chipwhisperer as cw
import time

s = cw.scope()
s.clock.clkgen_freq = 100E6
s.trigger.triggers = 'tio3'
s.glitch.clk_src = "clkgen"
s.glitch.output = "enable_only"
s.glitch.trigger_src = "ext_single"
s.io.glitch_lp = True
s.io.glitch_hp = True
s.glitch.width = 5
s.glitch.offset = -10
s.glitch.ext_offset = 70000  # 700µs
s.glitch.repeat = 5
s.io.tio3 = 'high_z'  # Monitor SWDIO
s.arm()
time.sleep(0.1)
s.io.tio2 = True
try: print(f"✅ {len(bytes(Swd().read_mem(0x1FFF7A10, 32)))} bytes")
except Exception as e: print(f"❌ {e}")
s.io.tio2 = False