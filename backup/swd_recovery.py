#!/usr/bin/env python3
"""
SWD Recovery and Connection Test
"""

from swd import Swd
import chipwhisperer as cw
import time

def swd_init():
    """Initialize SWD connection with proper sequence"""
    try:
        print("Initializing SWD...")

        # Reset target first
        scope = cw.scope()
        scope.io.nrst = False
        time.sleep(0.1)
        scope.io.nrst = 'high_z'
        time.sleep(0.5)
        print("✓ Target reset")

        # Create SWD interface
        swd = Swd()
        print("✓ SWD object created")

        # Try to read from a known good address (SRAM)
        test_addr = 0x20000000
        data = bytes(swd.read_mem(test_addr, 4))
        print(f"✓ SWD alive! Read {len(data)} bytes from 0x{test_addr:08X}")
        print(f"  Data: {' '.join(f'{b:02X}' for b in data)}")

        return swd

    except Exception as e:
        print(f"✗ SWD init failed: {e}")
        return None

def test_swd_read():
    """Test basic SWD read from SRAM"""
    swd = swd_init()
    if not swd:
        print("\nSWD is dead. Troubleshooting:")
        print("1. Check SWDIO and SWCLK connections")
        print("2. Verify target power")
        print("3. Try: sudo systemctl restart udev")
        print("4. Unplug/replug ChipWhisperer")
        return False

    # Test multiple reads
    print("\nTesting multiple reads...")
    for i in range(3):
        try:
            addr = 0x20000000 + (i * 4)
            data = bytes(swd.read_mem(addr, 4))
            print(f"  Read #{i+1}: 0x{addr:08X} = {' '.join(f'{b:02X}' for b in data)}")
        except Exception as e:
            print(f"  Read #{i+1} failed: {e}")
            return False

    print("\n✅ SWD is working!")
    return True

if __name__ == "__main__":
    test_swd_read()