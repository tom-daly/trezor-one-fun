#!/usr/bin/env python3
"""
Quick SWD memory check - non-interactive version
Just reads initial memory regions to prepare device for USART
"""

import sys
sys.path.insert(0, '/home/tdaly/.cwvenv/lib/python3.12/site-packages')
from swd import Swd
import time
import os

# Memory ranges for initial check only
TARGETS = [
    {
        "name": "TEST_UNPROTECTED",
        "start": 0xE0042000,
        "end": 0xE004200B,
        "chunk_size": 4,
        "description": "DBGMCU_IDCODE (should work even with RDP)"
    },
    {
        "name": "UNIQUE_ID",
        "start": 0x1FFF7A10,
        "end": 0x1FFF7A1B,
        "chunk_size": 12,
        "description": "96-bit Unique Device ID (for SEK derivation)"
    },
    {
        "name": "OPTION_BYTES",
        "start": 0x1FFFC000,
        "end": 0x1FFFC00F,
        "chunk_size": 16,
        "description": "Option bytes (RDP settings)"
    },
    {
        "name": "OTP",
        "start": 0x1FFF7800,
        "end": 0x1FFF781F,  # Just first 32 bytes
        "chunk_size": 32,
        "description": "One-Time Programmable area (first 32 bytes)"
    },
    {
        "name": "STORAGE",
        "start": 0x08008000,
        "end": 0x0800801F,  # Just first 32 bytes
        "chunk_size": 32,
        "description": "Storage sectors (first 32 bytes)"
    }
]

def read_memory_chunk(swd, address, size):
    """Read memory chunk"""
    try:
        data = bytearray()
        # Read in 4-byte aligned chunks
        for offset in range(0, size, 4):
            remaining = size - offset
            read_size = min(4, remaining)

            if read_size == 4:
                chunk_gen = swd.read_mem32(address + offset, 4)
                chunk = list(chunk_gen)
                if chunk:
                    # Convert to bytes (little-endian)
                    data.extend(chunk[0].to_bytes(4, 'little'))

        return bytes(data) if len(data) == size else None
    except Exception as e:
        return None

def display_hex(data, address, max_lines=2):
    """Display data in hex format (limited output)"""
    if not data:
        return

    for i in range(0, min(len(data), max_lines * 16), 16):
        print(f"    {address + i:08X}: ", end="")
        chunk = data[i:i+16]
        hex_str = " ".join(f"{b:02X}" for b in chunk)
        print(f"{hex_str:<48} ", end="")
        ascii_str = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
        print(f"|{ascii_str}|")

def analyze_data(name, data):
    """Quick analysis of specific memory regions"""
    if not data:
        return

    if name == "TEST_UNPROTECTED":
        if len(data) >= 4:
            value = int.from_bytes(data[:4], 'little')
            print(f"  📊 DBGMCU_IDCODE: 0x{value:08X}")

    elif name == "UNIQUE_ID":
        print(f"  📊 Unique ID: {data.hex()}")
        if data != b'\x00' * 12 and data != b'\xFF' * 12:
            print("  ✓ Valid unique ID detected")

    elif name == "OPTION_BYTES":
        if len(data) >= 2:
            rdp_byte = data[1]
            print(f"  📊 RDP Level: 0x{rdp_byte:02X}", end="")
            if rdp_byte == 0xAA:
                print(" (Level 0 - No protection)")
            elif rdp_byte == 0xCC:
                print(" (Level 2 - Permanent)")
            else:
                print(" (Level 1 - Read protection)")

def main():
    print("=" * 70)
    print("SWD Quick Memory Check (Non-Interactive)")
    print("=" * 70)

    # Connect to target
    print("\n🔌 Connecting to target via SWD...")
    try:
        swd = Swd()
        version = swd.get_version()
        print(f"✓ Connected: {version.str}")
    except Exception as e:
        print(f"✗ Failed to connect: {e}")
        sys.exit(1)

    print("\n" + "=" * 70)

    results = []

    # Read each target section
    for target in TARGETS:
        name = target["name"]
        start = target["start"]
        end = target["end"]
        size = end - start + 1

        print(f"\n📍 {name}")
        print(f"   Address: 0x{start:08X} - 0x{end:08X} ({size} bytes)")
        print("   Reading...", end="")

        data = read_memory_chunk(swd, start, size)

        if data:
            print(f" ✅ ({len(data)} bytes)")

            # Display first line of hex
            display_hex(data, start, max_lines=1)

            # Quick analysis
            analyze_data(name, data)

            results.append((name, True, len(data)))
        else:
            print(" ❌ (Protected)")
            results.append((name, False, 0))

        print("   " + "-" * 65)

    # Cleanup
    del swd

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    successful = sum(1 for _, success, _ in results if success)
    total = len(results)

    print(f"\n📊 Results: {successful}/{total} regions read successfully")

    if successful == total:
        print("\n✅ All memory regions accessible - device ready for USART")
    else:
        print("\n⚠️  Some regions protected - USART may not work")

    print("\n" + "=" * 70)

if __name__ == "__main__":
    main()