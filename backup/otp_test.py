#!/usr/bin/env python3
from swd import Swd
import os, time

os.system("/home/tdaly/.cwvenv/usb_reset > /dev/null 2>&1")
time.sleep(0.5)

swd = Swd()

# Test different memory regions to see responses
test_addresses = [
    (0x1FFF7860, "OTP Block 3 (Hardware Salt)"),
    (0x08000000, "Flash Start (should fail at RDP1)"),
    (0x20000000, "SRAM (should work)"),
    (0x1FFF7A10, "UUID (might fail)")
]

for addr, desc in test_addresses:
    print(f"\n{'='*50}")
    print(f"Testing: {desc}")
    print(f"Address: 0x{addr:08X}")
    try:
        gen = swd.read_mem(addr, 4)  # Just read 4 bytes for test
        data = list(gen)
        print(f"✅ SUCCESS: {bytes(data).hex()}")
    except Exception as e:
        error_msg = str(e)
        print(f"❌ FAILED")
        print(f"Error: {error_msg}")
        
        # Check for specific error types
        if "NACK" in error_msg or "nack" in error_msg:
            print("Response: NACK (Not Acknowledged)")
        elif "DP fault" in error_msg:
            print("Response: DP FAULT (Debug Port fault)")
        elif "AP fault" in error_msg:
            print("Response: AP FAULT (Access Port fault)")
        elif "WAIT" in error_msg:
            print("Response: WAIT (Target needs more time)")
        else:
            print(f"Response type: {type(e).__name__}")