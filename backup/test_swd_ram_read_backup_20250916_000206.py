#!/usr/bin/env python3
from swd import Swd
import chipwhisperer as cw
import time
s = cw.scope()
s.clock.clkgen_freq = 1000E6
s.io.tio2 = True
#try: print(f"✅ {len(bytes(Swd().read_mem(0x20000000, 32)))} bytes")
try: print(f"✅ {len(bytes(Swd().read_mem(0x1FFF7A10, 32)))} bytes")
except Exception as e: print(f"❌ {e}")
s.io.tio2 = False

#reset target via nRST pin
s.io.nrst = False
time.sleep(0.1)
s.io.nrst = 'high_z'
time.sleep(0.5)