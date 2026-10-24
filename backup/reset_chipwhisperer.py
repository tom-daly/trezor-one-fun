#!/usr/bin/env python3
import chipwhisperer as cw
import time

# Try to disconnect any existing connection
try:
    s = cw.scope()
    s.dis()
    print("Disconnected existing scope")
except:
    pass

time.sleep(1)

# Try to reconnect
try:
    s = cw.scope()
    print(f"✅ Connected: {s.get_name()}")
    s.dis()
except Exception as e:
    print(f"❌ Failed: {e}")
    print("\nTry:")
    print("1. Unplug and replug USB")
    print("2. Run: sudo systemctl restart udev")
    print("3. Check: lsusb | grep 2B3E")