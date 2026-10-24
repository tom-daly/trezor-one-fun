#!/usr/bin/env python3
"""
Test different SWD speeds and their impact
"""

from swd import Swd
import time

# Test different SWD speeds
test_speeds = [
    480000,   # 480 kHz
    950000,   # 950 kHz
    1200000,  # 1.2 MHz
    1800000,  # 1.8 MHz
    4000000,  # 4.0 MHz
]

test_address = 0x20000000  # SRAM (should be accessible)
test_size = 32

print("SWD Speed Test")
print("="*50)

for speed in test_speeds:
    print(f"\nTesting {speed/1000:.0f} kHz:")

    try:
        # Create SWD with specific frequency
        swd = Swd(swd_frequency=speed)

        # Time a read operation
        start_time = time.time()
        data = bytes(swd.read_mem(test_address, test_size))
        read_time = time.time() - start_time

        if len(data) == test_size:
            print(f"  ✅ Success: {len(data)} bytes in {read_time*1000:.2f}ms")
            print(f"  Speed: {test_size/read_time:.0f} bytes/sec")
        else:
            print(f"  ❌ Failed: Only read {len(data)} bytes")

    except Exception as e:
        print(f"  ❌ Error: {e}")

print("\n" + "="*50)
print("Current default speed test:")

try:
    # Test with no speed specified (default)
    swd = Swd()
    start_time = time.time()
    data = bytes(swd.read_mem(test_address, test_size))
    read_time = time.time() - start_time

    if len(data) == test_size:
        print(f"✅ Default: {len(data)} bytes in {read_time*1000:.2f}ms")
        print(f"Speed: {test_size/read_time:.0f} bytes/sec")

        # Try to determine speed based on timing
        estimated_speed = "Unknown"
        if read_time > 0.01:
            estimated_speed = "~480kHz (slow)"
        elif read_time > 0.005:
            estimated_speed = "~950kHz-1.2MHz"
        elif read_time > 0.002:
            estimated_speed = "~1.8MHz"
        else:
            estimated_speed = "~4MHz (fast)"
        print(f"Estimated speed: {estimated_speed}")
    else:
        print(f"❌ Default failed: Only read {len(data)} bytes")

except Exception as e:
    print(f"❌ Default error: {e}")