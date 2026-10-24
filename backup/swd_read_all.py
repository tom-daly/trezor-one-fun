#!/usr/bin/env python3
"""
SWD memory reader - reads all memory sections automatically
"""

import sys
sys.path.insert(0, '/home/tdaly/.cwvenv/lib/python3.12/site-packages')
from swd import Swd
import time
import os

# Memory ranges - matching 4-dump_flash.py targets
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
        "end": 0x1FFF7A0F,
        "chunk_size": 32,
        "description": "One-Time Programmable area (528 bytes)"
    },
    {
        "name": "STORAGE",
        "start": 0x08008000,
        "end": 0x0800FFFF,
        "chunk_size": 32,
        "description": "Storage sectors (32KB encrypted mnemonic)"
    }
]

def read_memory_chunk(swd, address, size):
    """Read a chunk of memory via SWD"""
    try:
        data = bytes(swd.read_mem(address, size))
        return data if data else None
    except Exception as e:
        return None

def display_hex(data, address, max_lines=8):
    """Display data in hex format (limited lines for readability)"""
    if not data:
        return

    lines_shown = 0
    for i in range(0, len(data), 16):
        if lines_shown >= max_lines and i < len(data) - 16:
            print(f"    ... ({len(data) - i} more bytes) ...")
            break

        # Address
        print(f"    {address + i:08X}: ", end="")

        # Hex bytes
        chunk = data[i:i+16]
        hex_str = " ".join(f"{b:02X}" for b in chunk)
        print(f"{hex_str:<48} ", end="")

        # ASCII representation
        ascii_str = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
        print(f"|{ascii_str}|")

        lines_shown += 1

def save_to_file(data, name, address):
    """Save data to file"""
    if not data:
        return

    # Create dumps directory if it doesn't exist
    if not os.path.exists('SWD_DUMPS'):
        os.makedirs('SWD_DUMPS')

    filename = f"SWD_DUMPS/{name}_0x{address:08X}.bin"
    with open(filename, 'wb') as f:
        f.write(data)
    return filename

def analyze_data(name, data):
    """Analyze and report on specific memory regions"""
    if not data:
        return

    if name == "TEST_UNPROTECTED":
        value = int.from_bytes(data[:4], 'little')
        print(f"  📊 DBGMCU_IDCODE: 0x{value:08X}", end="")
        if value == 0x411FC205:
            print(" ✓ Correct STM32F205 ID!")
        else:
            print(" ✗ Unexpected ID value")

    elif name == "UNIQUE_ID":
        print(f"  📊 Unique ID: {data.hex()}")
        if data == b'\x00' * 12:
            print("  ⚠️  WARNING: All zeros - likely corrupted!")
        elif data == b'\xFF' * 12:
            print("  ⚠️  WARNING: All FFs - likely erased/corrupted!")
        elif b'\x11\x00\x77\x24' in data:
            print("  ⚠️  WARNING: Contains stuck pattern '11 00 77 24'")
        else:
            print("  ✓ Appears to be valid unique ID")

    elif name == "OPTION_BYTES":
        print(f"  📊 Option Bytes: {data.hex()}")
        if len(data) >= 1:
            if data[0] == 0xED:
                print("  ✓ User byte is 0xED (matches OPTCR = 0x0FFFFFED)")
            else:
                print(f"  ⚠️  User byte is 0x{data[0]:02X} (expected 0xED)")

    elif name == "STORAGE":
        # Check for patterns indicating issues
        if data[:32] == b'\x00' * 32:
            print("  ⚠️  WARNING: First 32 bytes are all zeros")
        elif data[:32] == b'\xFF' * 32:
            print("  ⚠️  WARNING: First 32 bytes are all FFs (erased)")
        else:
            print(f"  📊 First 4 bytes: {data[:4].hex()}")

def main():
    print("=" * 70)
    print("SWD Memory Dump - All Sections")
    print("=" * 70)

    # Initialize SWD
    print("\n🔌 Connecting to target via SWD...")
    try:
        swd = Swd()
        print("✓ SWD connection established")
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
        chunk_size = target["chunk_size"]
        size = end - start + 1

        print(f"\n📍 {name}")
        print(f"   {target['description']}")
        print(f"   Address: 0x{start:08X} - 0x{end:08X} ({size} bytes)")

        # For large regions, read in chunks
        if name == "STORAGE":
            print(f"   Reading {size} bytes in {chunk_size}-byte chunks...")
            all_data = bytearray()
            success = False

            # Try to read just the first chunk as a test
            print("   Testing first chunk...", end="")
            test_data = read_memory_chunk(swd, start, chunk_size)
            if test_data:
                print(" ✓ Success")
                all_data.extend(test_data)
                success = True

                # If first chunk worked, offer to read rest
                if size > chunk_size:
                    response = input(f"   Continue reading remaining {size - chunk_size} bytes? (y/n): ")
                    if response.lower() == 'y':
                        for offset in range(chunk_size, size, chunk_size):
                            remaining = size - offset
                            read_size = min(chunk_size, remaining)
                            print(f"   Reading 0x{start + offset:08X} ({offset}/{size} bytes)...", end="")

                            chunk_data = read_memory_chunk(swd, start + offset, read_size)
                            if chunk_data:
                                all_data.extend(chunk_data)
                                print(" ✓")
                            else:
                                print(" ✗ Failed")
                                break
            else:
                print(" ✗ Failed (RDP active)")

            data = bytes(all_data) if success else None

        elif name == "OTP":
            # OTP is 528 bytes, read in chunks
            print(f"   Reading {size} bytes in {chunk_size}-byte chunks...")
            all_data = bytearray()
            success = False

            for offset in range(0, size, chunk_size):
                remaining = size - offset
                read_size = min(chunk_size, remaining)
                chunk_data = read_memory_chunk(swd, start + offset, read_size)
                if chunk_data:
                    all_data.extend(chunk_data)
                    print(".", end="", flush=True)
                else:
                    print(" ✗", end="")
                    break

            print()
            data = bytes(all_data) if len(all_data) == size else None
            success = data is not None

        else:
            # Small regions - read in one go
            print("   Reading...", end="")
            data = read_memory_chunk(swd, start, size)
            success = data is not None

        if success:
            print(f"\n   ✅ SUCCESS: Read {len(data)} bytes")

            # Display hex dump (limited)
            display_hex(data, start, max_lines=4)

            # Analyze data
            analyze_data(name, data)

            # Save to file
            filename = save_to_file(data, name, start)
            if filename:
                print(f"   💾 Saved to {filename}")

            results.append((name, True, len(data)))
        else:
            print(f"\n   ❌ FAILED: Could not read (RDP protection active)")
            results.append((name, False, 0))

        print("   " + "-" * 65)

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    successful = sum(1 for _, success, _ in results if success)
    total = len(results)

    print(f"\n📊 Results: {successful}/{total} regions read successfully\n")

    for name, success, size in results:
        status = "✅ Success" if success else "❌ Failed"
        size_str = f"({size} bytes)" if success else "(RDP protected)"
        print(f"  {name:<20} {status:<12} {size_str}")

    if successful < total:
        print("\n⚠️  Some regions are RDP protected and require glitching to read")
        print("    Use the glitching scripts to bypass RDP for protected regions")

    print("\n" + "=" * 70)

if __name__ == "__main__":
    main()