#!/usr/bin/env python3
"""
Simple SWD memory read test - reads 512 bytes from flash
"""

from swd import Swd

# Connect to target
print("Connecting via SWD...")
swd = Swd()

# Read 512 bytes from flash start (0x08000000)
address = 0x08000000
size = 512

print(f"Reading {size} bytes from 0x{address:08X}")

try:
    # read_mem returns a generator, convert to bytes
    data = bytes(swd.read_mem(address, size))
    print(f"Successfully read {len(data)} bytes")
    
    # Save to file
    with open("test_read.bin", "wb") as f:
        f.write(data)
    print("Saved to test_read.bin")
    
    # Show first 16 bytes as hex
    print("\nFirst 16 bytes:")
    for i in range(min(16, len(data))):
        print(f"{data[i]:02X} ", end="")
    print()
    
except Exception as e:
    print(f"Read failed: {e}")

print("Done")