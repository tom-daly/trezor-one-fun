#!/usr/bin/env python3
"""
USART memory reader - reads memory via STM32 bootloader protocol
Requires target to be in bootloader mode (BOOT0=1, BOOT1=0)
"""

import serial
import sys
import time
import os
import struct
import subprocess

# Memory ranges - same as SWD scripts
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
        "chunk_size": 256,  # Larger chunks for USART efficiency
        "description": "Storage sectors (32KB encrypted mnemonic)"
    }
]

# STM32 Bootloader commands
CMD_GET = 0x00          # Get version and allowed commands
CMD_GET_ID = 0x02       # Get chip ID
CMD_READ = 0x11         # Read memory
CMD_GO = 0x21           # Jump to address
CMD_WRITE = 0x31        # Write memory
CMD_ERASE = 0x43        # Erase memory
CMD_EXTENDED_ERASE = 0x44  # Extended erase
CMD_WRITE_PROTECT = 0x63   # Write protect
CMD_WRITE_UNPROTECT = 0x73  # Write unprotect
CMD_READOUT_PROTECT = 0x82  # Readout protect
CMD_READOUT_UNPROTECT = 0x92  # Readout unprotect

class STM32Bootloader:
    """STM32 USART bootloader protocol implementation"""

    def __init__(self, port='/dev/ttyUSB0', baudrate=9600):
        self.port = port
        self.baudrate = baudrate
        self.ser = None

    def connect(self):
        """Connect to bootloader"""
        try:
            self.ser = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                bytesize=8,
                parity=serial.PARITY_EVEN,
                stopbits=1,
                timeout=1
            )
            self.ser.flush()
            print(f"✓ Serial port opened: {self.port} @ {self.baudrate}")

            # Send init byte (0x7F) to sync with bootloader
            print("Syncing with bootloader...", end="")
            for i in range(10):  # More attempts for slow baudrate
                self.ser.write(b'\x7F')
                time.sleep(0.2)  # Longer delay for 9600 baud

                if self.ser.in_waiting:
                    response = self.ser.read(1)
                    if response == b'\x79':  # ACK
                        print(" ✓ Bootloader ready!")
                        return True
                    elif response == b'\x1F':  # NACK
                        print(" NACK received")

                print(".", end="", flush=True)

            print(" ✗ No response from bootloader")
            return False

        except Exception as e:
            print(f"✗ Failed to connect: {e}")
            return False

    def disconnect(self):
        """Close serial connection"""
        if self.ser:
            self.ser.close()

    def _send_command(self, cmd):
        """Send command with checksum"""
        self.ser.write(bytes([cmd, 0xFF ^ cmd]))
        return self._wait_ack()

    def _wait_ack(self):
        """Wait for ACK/NACK response"""
        response = self.ser.read(1)
        if response == b'\x79':
            return True  # ACK
        elif response == b'\x1F':
            return False  # NACK
        else:
            return None  # Timeout or unexpected

    def _send_address(self, address):
        """Send 32-bit address with checksum"""
        addr_bytes = struct.pack('>I', address)
        checksum = 0
        for b in addr_bytes:
            checksum ^= b
        self.ser.write(addr_bytes + bytes([checksum]))
        return self._wait_ack()

    def get_info(self):
        """Get bootloader version and commands"""
        if not self._send_command(CMD_GET):
            return None

        length = self.ser.read(1)
        if not length:
            return None

        n = length[0] + 1
        data = self.ser.read(n)

        if len(data) == n:
            self._wait_ack()
            return data
        return None

    def get_chip_id(self):
        """Get chip ID"""
        if not self._send_command(CMD_GET_ID):
            return None

        length = self.ser.read(1)
        if not length:
            return None

        n = length[0] + 1
        chip_id = self.ser.read(n)

        if len(chip_id) == n:
            self._wait_ack()
            return chip_id
        return None

    def read_memory(self, address, length):
        """Read memory from address"""
        if length > 256:
            print(f"Warning: Limiting read to 256 bytes (requested {length})")
            length = 256

        # Send read command
        if not self._send_command(CMD_READ):
            return None

        # Send address
        if not self._send_address(address):
            return None

        # Send length (N-1)
        n_minus_1 = length - 1
        checksum = n_minus_1 ^ 0xFF
        self.ser.write(bytes([n_minus_1, checksum]))

        # Wait for ACK
        if not self._wait_ack():
            return None

        # Read data
        data = self.ser.read(length)
        if len(data) == length:
            return data
        return None

    def check_rdp_status(self):
        """Check if RDP is active"""
        # Try to read option bytes
        option_bytes = self.read_memory(0x1FFFC000, 4)
        if option_bytes:
            rdp_level = option_bytes[1]
            if rdp_level == 0xAA:
                return "Level 0 (No protection)"
            elif rdp_level == 0xCC:
                return "Level 2 (No debug, permanent)"
            else:
                return f"Level 1 (Read protection active, RDP=0x{rdp_level:02X})"
        return "Unknown (couldn't read option bytes)"

def display_hex(data, address, max_lines=8):
    """Display data in hex format"""
    if not data:
        return

    lines_shown = 0
    for i in range(0, len(data), 16):
        if lines_shown >= max_lines and i < len(data) - 16:
            print(f"    ... ({len(data) - i} more bytes) ...")
            break

        print(f"    {address + i:08X}: ", end="")
        chunk = data[i:i+16]
        hex_str = " ".join(f"{b:02X}" for b in chunk)
        print(f"{hex_str:<48} ", end="")
        ascii_str = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
        print(f"|{ascii_str}|")
        lines_shown += 1

def save_to_file(data, name, address):
    """Save data to file"""
    if not data:
        return

    if not os.path.exists('USART_DUMPS'):
        os.makedirs('USART_DUMPS')

    filename = f"USART_DUMPS/{name}_0x{address:08X}.bin"
    with open(filename, 'wb') as f:
        f.write(data)
    return filename

def analyze_data(name, data):
    """Analyze specific memory regions"""
    if not data:
        return

    if name == "TEST_UNPROTECTED":
        if len(data) >= 4:
            value = int.from_bytes(data[:4], 'little')
            print(f"  📊 DBGMCU_IDCODE: 0x{value:08X}", end="")
            if value == 0x411FC205:
                print(" ✓ Correct STM32F205 ID!")
            else:
                print(" ✗ Unexpected ID value")

    elif name == "UNIQUE_ID":
        print(f"  📊 Unique ID: {data.hex()}")
        if data == b'\x00' * 12:
            print("  ⚠️  All zeros - corrupted!")
        elif data == b'\xFF' * 12:
            print("  ⚠️  All FFs - erased!")
        else:
            print("  ✓ Appears valid")

    elif name == "OPTION_BYTES":
        print(f"  📊 Option Bytes: {data.hex()}")
        if len(data) >= 2:
            rdp_byte = data[1]
            print(f"  📊 RDP Byte: 0x{rdp_byte:02X}", end="")
            if rdp_byte == 0xAA:
                print(" (Level 0 - No protection)")
            elif rdp_byte == 0xCC:
                print(" (Level 2 - Permanent)")
            else:
                print(" (Level 1 - Read protection active)")

def reset_target_with_chipwhisperer():
    """Reset target using ChipWhisperer to ensure clean state"""
    try:
        print("\n🔄 Resetting target with ChipWhisperer...")
        result = subprocess.run(['/home/tdaly/.cwvenv/bin/python3', '/home/tdaly/.cwvenv/reset_toggle.py'],
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print("   ✓ Target reset complete")
            time.sleep(0.5)  # Allow bootloader to initialize
            return True
        else:
            print(f"   ✗ Reset failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"   ✗ Could not reset: {e}")
        return False

def main():
    print("=" * 70)
    print("USART Memory Reader - STM32 Bootloader Protocol")
    print("=" * 70)

    # Parse arguments
    port = '/dev/ttyUSB0'
    baudrate = 9600  # Slower default for reliability
    auto_reset = False  # Flag for automatic reset

    if len(sys.argv) > 1:
        if sys.argv[1] == "--reset":
            auto_reset = True
            if len(sys.argv) > 2:
                port = sys.argv[2]
            if len(sys.argv) > 3:
                baudrate = int(sys.argv[3])
        else:
            port = sys.argv[1]
            if len(sys.argv) > 2:
                baudrate = int(sys.argv[2])

    print(f"\nConfiguration:")
    print(f"  Port: {port}")
    print(f"  Baudrate: {baudrate} (slow for reliability)")
    print(f"  Parity: Even")
    print(f"  Auto-reset: {'Yes' if auto_reset else 'No'}")
    print("\n⚠️  Target must be in bootloader mode:")
    print("    - BOOT0 = 1 (connect to VCC)")
    print("    - BOOT1 = 0 (connect to GND)")
    print("    - Reset the target (or use --reset flag)")
    print("=" * 70)

    # Perform automatic reset if requested
    if auto_reset:
        if not reset_target_with_chipwhisperer():
            print("\n⚠️  Reset failed, but continuing anyway...")
            print("    You may need to manually reset the target")

    print("\nStarting bootloader communication...")

    # Connect to bootloader
    bl = STM32Bootloader(port, baudrate)

    if not bl.connect():
        print("\n✗ Failed to connect to bootloader")
        print("\nTroubleshooting:")
        print("  1. Check BOOT0=1, BOOT1=0")
        print("  2. Reset target after setting BOOT pins")
        print("  3. Check USART connections (TX/RX crossed)")
        print("  4. Try different baudrate (115200, 57600, 38400, 19200)")
        print("  5. Default is 9600 for reliability - can override with 2nd argument")
        sys.exit(1)

    # Get bootloader info
    print("\n📍 Bootloader Information")
    info = bl.get_info()
    if info:
        print(f"   Version: 0x{info[0]:02X}")
        print(f"   Commands: {' '.join(f'{b:02X}' for b in info[1:])}")

    # Get chip ID
    chip_id = bl.get_chip_id()
    if chip_id:
        id_value = int.from_bytes(chip_id, 'big')
        print(f"   Chip ID: 0x{id_value:04X}", end="")
        if id_value == 0x0413:
            print(" (STM32F405/407/415/417)")
        elif id_value == 0x0411:
            print(" (STM32F205/215/207/217)")
        else:
            print()

    # Check RDP status
    print(f"\n📍 RDP Status")
    rdp_status = bl.check_rdp_status()
    print(f"   {rdp_status}")

    print("\n" + "=" * 70)

    results = []

    # Read each target section
    for target in TARGETS:
        name = target["name"]
        start = target["start"]
        end = target["end"]
        chunk_size = min(256, target["chunk_size"])  # USART limited to 256 bytes
        size = end - start + 1

        print(f"\n📍 {name}")
        print(f"   {target['description']}")
        print(f"   Address: 0x{start:08X} - 0x{end:08X} ({size} bytes)")

        all_data = bytearray()
        success = True

        # Read in chunks
        for offset in range(0, size, chunk_size):
            remaining = size - offset
            read_size = min(chunk_size, remaining)
            current_addr = start + offset

            if size > 256:  # Show progress for large reads
                print(f"   Reading 0x{current_addr:08X} ({offset}/{size} bytes)...", end="")
            else:
                print("   Reading...", end="")

            chunk_data = bl.read_memory(current_addr, read_size)

            if chunk_data:
                all_data.extend(chunk_data)
                if size > 256:
                    print(" ✓")
                else:
                    print("", end="")
            else:
                print(" ✗ Failed")
                success = False
                break

        if success and len(all_data) > 0:
            data = bytes(all_data)
            print(f"\n   ✅ SUCCESS: Read {len(data)} bytes")

            # Display hex dump
            display_hex(data, start, max_lines=4)

            # Analyze data
            analyze_data(name, data)

            # Save to file
            filename = save_to_file(data, name, start)
            if filename:
                print(f"   💾 Saved to {filename}")

            results.append((name, True, len(data)))
        else:
            print(f"\n   ❌ FAILED: Could not read (RDP protected or invalid address)")
            results.append((name, False, 0))

        print("   " + "-" * 65)

        # Small delay between reads
        time.sleep(0.1)

    # Disconnect
    bl.disconnect()

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    successful = sum(1 for _, success, _ in results if success)
    total = len(results)

    print(f"\n📊 Results: {successful}/{total} regions read successfully\n")

    for name, success, size in results:
        status = "✅ Success" if success else "❌ Failed"
        size_str = f"({size} bytes)" if success else "(Protected)"
        print(f"  {name:<20} {status:<12} {size_str}")

    if successful < total:
        print("\n⚠️  Some regions are protected by RDP")
        print("    Bootloader respects RDP - glitching required for protected areas")

    print("\n" + "=" * 70)

if __name__ == "__main__":
    main()