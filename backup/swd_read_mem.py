#!/usr/bin/env python3
"""
Bare bones SWD memory reader - no glitching, no ChipWhisperer
"""

from swd import Swd
import sys

# Memory ranges - matching 4-dump_flash.py targets
TARGETS = {
    "STORAGE": {
        "start": 0x08008000,
        "end": 0x0800FFFF,
        "chunk_size": 32,
        "description": "Storage sectors (encrypted mnemonic) - 32KB"
    },
    "OPTION_BYTES": {
        "start": 0x1FFFC000,
        "end": 0x1FFFC00F,
        "chunk_size": 16,
        "description": "Option bytes (RDP settings)"
    },
    "UNIQUE_ID": {
        "start": 0x1FFF7A10,
        "end": 0x1FFF7A1B,
        "chunk_size": 12,
        "description": "96-bit Unique Device ID (for SEK derivation)"
    },
    "OTP": {
        "start": 0x1FFF7800,
        "end": 0x1FFF7A0F,
        "chunk_size": 32,
        "description": "One-Time Programmable area (additional entropy) - 528 bytes"
    },
    "TEST_UNPROTECTED": {
        "start": 0xE0042000,
        "end": 0xE004200B,
        "chunk_size": 4,
        "description": "DBGMCU_IDCODE (should be 0x411FC205 for STM32F205)"
    }
}

def read_memory(address, size):
    """Read memory via SWD"""
    try:
        swd = Swd()
        print(f"Reading {size} bytes from 0x{address:08X}...")

        data = bytes(swd.read_mem(address, size))

        if data:
            print(f"✓ Success! Read {len(data)} bytes")
            return data
        else:
            print(f"✗ Failed - no data returned")
            return None

    except Exception as e:
        print(f"✗ Error: {e}")
        return None

def display_hex(data, address):
    """Display data in hex format"""
    if not data:
        return

    print(f"\nMemory dump from 0x{address:08X}:")
    print("-" * 60)

    for i in range(0, len(data), 16):
        # Address
        print(f"{address + i:08X}: ", end="")

        # Hex bytes
        chunk = data[i:i+16]
        hex_str = " ".join(f"{b:02X}" for b in chunk)
        print(f"{hex_str:<48} ", end="")

        # ASCII representation
        ascii_str = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
        print(f"|{ascii_str}|")

    print("-" * 60)

def save_to_file(data, address, filename=None):
    """Save data to file"""
    if not data:
        return

    if filename is None:
        filename = f"mem_0x{address:08X}.bin"

    with open(filename, 'wb') as f:
        f.write(data)
    print(f"Saved to {filename}")

def main():
    print("=" * 60)
    print("SWD Memory Reader - No Glitch")
    print("=" * 60)

    # Parse arguments
    if len(sys.argv) < 2:
        print("\nUsage: python swd_read_mem.py <target|address> [size]")
        print("\nTargets:")
        for name, info in TARGETS.items():
            print(f"  {name:<12} - {info['description']}")
        print("\nCustom: python swd_read_mem.py 0x20000000 256")
        sys.exit(1)

    arg = sys.argv[1]

    # Check if it's a predefined target
    if arg.upper() in TARGETS:
        target = TARGETS[arg.upper()]
        address = target["start"]
        size = target["end"] - target["start"] + 1
        chunk_size = target["chunk_size"]
        print(f"\nTarget: {arg.upper()} - {target['description']}")
    else:
        # Parse as custom address
        try:
            address = int(arg, 0)  # Auto-detect base (0x for hex)
            size = int(sys.argv[2], 0) if len(sys.argv) > 2 else 256
            chunk_size = min(32, size)  # Default chunk size
        except ValueError:
            print(f"Error: Invalid address '{arg}'")
            sys.exit(1)

    print(f"Address: 0x{address:08X}")
    print(f"Size: {size} bytes")
    print("-" * 60)

    # Read memory
    data = read_memory(address, size)

    if data:
        # Display hex dump
        display_hex(data, address)

        # Save to file
        save_to_file(data, address)

        # Special handling for known targets
        if arg.upper() == "TEST_UNPROTECTED":
            value = int.from_bytes(data[:4], 'little')
            print(f"\nDBGMCU_IDCODE: 0x{value:08X}")
            if value == 0x411FC205:
                print("✓ Correct STM32F205 ID!")
            else:
                print("✗ Unexpected ID value")

        elif arg.upper() == "UNIQUE_ID":
            print(f"\nUnique ID: {data.hex()}")
            if data == b'\x00' * 12 or data == b'\xFF' * 12:
                print("⚠️ WARNING: Likely corrupted (all zeros/FFs)")
            if b'\x11\x00\x77\x24' in data:
                print("⚠️ WARNING: Contains stuck pattern 11 00 77 24")

        elif arg.upper() == "OPTION_BYTES":
            print(f"\nOption Bytes: {data.hex()}")
            if len(data) >= 1 and data[0] == 0xED:
                print("✓ Starts with 0xED (expected user byte)")
            print("Note: Your device OPTCR = 0x0FFFFFED")
    else:
        print("\n✗ Memory read failed")
        print("Possible causes:")
        print("  - RDP (Read Protection) is active")
        print("  - Invalid address")
        print("  - SWD connection issue")
        print("  - Target not powered/connected")

if __name__ == "__main__":
    main()