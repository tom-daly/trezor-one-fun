#!/usr/bin/env python3
"""
Check if STM32 is in bootloader mode using ST-LINK tools
"""

import subprocess
import re

def check_with_stlink():
    """Use st-info to check if device is accessible and what's running"""
    print("="*60)
    print("STM32 Bootloader Check via ST-LINK")
    print("="*60)

    # Try to get device info
    try:
        result = subprocess.run(['st-info', '--probe'], capture_output=True, text=True)
        print("\n[1] Device Detection:")
        if "Found" in result.stdout:
            print("✅ STM32 detected via ST-LINK")
            print(result.stdout)
        else:
            print("❌ No STM32 detected")
            return

    except FileNotFoundError:
        print("❌ st-info not found. Install with: sudo apt install stlink-tools")
        return

    # Try to read PC register using st-util/gdb or OpenOCD
    print("\n[2] Checking execution region:")
    print("   If code is running from:")
    print("   • 0x1FFF0000-0x1FFF77FF = BOOTLOADER (system memory)")
    print("   • 0x08000000-0x080FFFFF = APPLICATION (flash)")
    print("   • 0x20000000-0x2001FFFF = RAM")

    # Try to dump some memory to check
    try:
        # Read first word from system memory (bootloader region)
        print("\n[3] Attempting to read bootloader region (0x1FFF0000)...")
        result = subprocess.run(['st-flash', 'read', '/tmp/bootloader_test.bin', '0x1FFF0000', '4'],
                              capture_output=True, text=True)

        if "wrote" in result.stderr.lower() or result.returncode == 0:
            print("✅ Can read system memory - bootloader accessible")

            # Check the actual content
            with open('/tmp/bootloader_test.bin', 'rb') as f:
                data = f.read(4)
                value = int.from_bytes(data, 'little')
                print(f"   Stack pointer at 0x1FFF0000: 0x{value:08X}")
                if 0x20000000 <= value <= 0x20020000:
                    print("   ✅ Valid bootloader stack pointer!")

    except Exception as e:
        print(f"⚠️  Could not read memory: {e}")

    print("\n[4] Manual verification steps:")
    print("   a) Check BOOT0 pin - should be HIGH for bootloader")
    print("   b) Try UART on PA9/PA10 with 9600 8E1")
    print("   c) Send 0x7F and look for 0x79 response")

    print("\n[5] Force bootloader entry:")
    print("   • Set BOOT0 = HIGH (3.3V)")
    print("   • Reset the device")
    print("   • Device will enter bootloader")
    print("="*60)

if __name__ == "__main__":
    check_with_stlink()