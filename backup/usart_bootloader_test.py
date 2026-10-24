#!/usr/bin/env python3
"""
USART bootloader test - reads memory regions typically accessible via bootloader
"""

import serial
import sys
import time
import struct

# Memory regions that bootloader typically allows
TEST_REGIONS = [
    {
        "name": "FLASH_START",
        "address": 0x08000000,
        "size": 256,
        "description": "Beginning of flash (bootloader/firmware)"
    },
    {
        "name": "SRAM_START",
        "address": 0x20000000,
        "size": 256,
        "description": "Beginning of SRAM"
    },
    {
        "name": "SYSTEM_MEMORY",
        "address": 0x1FFF0000,
        "size": 256,
        "description": "System memory (bootloader code)"
    },
    {
        "name": "PERIPHERALS_TIM2",
        "address": 0x40000000,
        "size": 16,
        "description": "TIM2 peripheral registers"
    },
    {
        "name": "FLASH_INTERFACE",
        "address": 0x40023C00,
        "size": 16,
        "description": "Flash interface registers"
    },
    {
        "name": "RCC_REGISTERS",
        "address": 0x40023800,
        "size": 16,
        "description": "Reset and Clock Control"
    },
    {
        "name": "UNIQUE_ID_DIRECT",
        "address": 0x1FFF7A10,
        "size": 12,
        "description": "Unique ID (direct attempt)"
    },
    {
        "name": "FLASH_SIZE",
        "address": 0x1FFF7A22,
        "size": 2,
        "description": "Flash size register"
    }
]

class STM32Bootloader:
    """Minimal STM32 bootloader communication"""

    def __init__(self, port='/dev/ttyUSB0', baudrate=9600):
        self.port = port
        self.baudrate = baudrate
        self.ser = None

    def connect(self):
        """Connect and sync with bootloader"""
        try:
            self.ser = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                bytesize=8,
                parity=serial.PARITY_EVEN,
                stopbits=1,
                timeout=2
            )
            self.ser.flush()

            # Sync with bootloader
            print(f"Syncing at {self.baudrate} baud...", end="")
            for i in range(20):
                self.ser.write(b'\x7F')
                time.sleep(0.1)

                if self.ser.in_waiting:
                    response = self.ser.read(1)
                    if response == b'\x79':
                        print(" ✓")
                        return True

                print(".", end="", flush=True)

            print(" ✗")
            return False

        except Exception as e:
            print(f"Error: {e}")
            return False

    def send_command(self, cmd):
        """Send command with checksum"""
        self.ser.write(bytes([cmd, 0xFF ^ cmd]))
        response = self.ser.read(1)
        return response == b'\x79'

    def send_address(self, addr):
        """Send address with checksum"""
        addr_bytes = struct.pack('>I', addr)
        checksum = 0
        for b in addr_bytes:
            checksum ^= b
        self.ser.write(addr_bytes + bytes([checksum]))
        response = self.ser.read(1)
        return response == b'\x79'

    def read_memory(self, address, length):
        """Attempt to read memory"""
        if length > 256:
            length = 256

        # Send read command (0x11)
        if not self.send_command(0x11):
            return None

        # Send address
        if not self.send_address(address):
            return None

        # Send length
        n = length - 1
        self.ser.write(bytes([n, n ^ 0xFF]))

        # Wait for ACK
        if self.ser.read(1) != b'\x79':
            return None

        # Read data
        data = self.ser.read(length)
        return data if len(data) == length else None

    def get_commands(self):
        """Get supported commands"""
        if not self.send_command(0x00):
            return None

        n = self.ser.read(1)
        if not n:
            return None

        data = self.ser.read(n[0] + 1)
        if self.ser.read(1) == b'\x79':
            return data
        return None

def main():
    print("=" * 70)
    print("STM32 Bootloader Memory Access Test")
    print("=" * 70)

    port = sys.argv[1] if len(sys.argv) > 1 else '/dev/ttyUSB0'
    baudrate = int(sys.argv[2]) if len(sys.argv) > 2 else 9600

    print(f"\n📡 Port: {port} @ {baudrate} baud")
    print("\n⚠️  Ensure BOOT0=1, BOOT1=0, then reset")
    print("=" * 70)

    input("\nPress Enter to start...")

    bl = STM32Bootloader(port, baudrate)

    if not bl.connect():
        print("Failed to connect!")
        print("\nTry: 115200, 57600, 38400, 19200, or 9600 baud")
        return

    # Get supported commands
    print("\n📍 Checking bootloader capabilities...")
    cmds = bl.get_commands()
    if cmds:
        print(f"   Version: 0x{cmds[0]:02X}")
        cmd_list = " ".join(f"{c:02X}" for c in cmds[1:])
        print(f"   Commands: {cmd_list}")

        # Check for read command
        if 0x11 in cmds[1:]:
            print("   ✓ Read command (0x11) supported")
        else:
            print("   ✗ Read command not supported!")

    print("\n" + "=" * 70)
    print("Testing memory regions...")
    print("=" * 70)

    accessible = []
    blocked = []

    for region in TEST_REGIONS:
        print(f"\n📍 {region['name']}")
        print(f"   {region['description']}")
        print(f"   Address: 0x{region['address']:08X} ({region['size']} bytes)")
        print("   Reading...", end="")

        data = bl.read_memory(region['address'], region['size'])

        if data:
            print(" ✅ ACCESSIBLE")
            accessible.append(region['name'])

            # Show first 32 bytes
            print("   Data: ", end="")
            for i in range(min(32, len(data))):
                print(f"{data[i]:02X} ", end="")
                if i == 15:
                    print("\n         ", end="")
            if len(data) > 32:
                print("...")
            else:
                print()

            # Special analysis
            if region['name'] == 'UNIQUE_ID_DIRECT':
                print(f"   Full ID: {data.hex()}")
            elif region['name'] == 'FLASH_SIZE':
                if len(data) >= 2:
                    size_kb = struct.unpack('<H', data[:2])[0]
                    print(f"   Flash size: {size_kb} KB")

        else:
            print(" ❌ BLOCKED")
            blocked.append(region['name'])

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    print(f"\n✅ Accessible: {len(accessible)}")
    for name in accessible:
        print(f"   - {name}")

    print(f"\n❌ Blocked: {len(blocked)}")
    for name in blocked:
        print(f"   - {name}")

    if 'UNIQUE_ID_DIRECT' in blocked:
        print("\n⚠️  Unique ID is blocked - bootloader restricts access")
        print("    This is normal behavior for STM32 bootloader")

    print("\n" + "=" * 70)

if __name__ == "__main__":
    main()