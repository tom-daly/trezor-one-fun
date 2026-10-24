#!/usr/bin/env python3
"""
Direct USART bootloader communication - works even when sync gets NACK
"""

import serial
import sys
import time
import struct
import os

def send_command(ser, cmd):
    """Send command with checksum"""
    ser.write(bytes([cmd, 0xFF ^ cmd]))
    time.sleep(0.2)  # Longer delay for 9600 baud

    # Check for ACK/NACK
    if ser.in_waiting:
        response = ser.read(1)
        if response == b'\x79':
            return True
        elif response == b'\x1F':
            print(" (got NACK)", end="")
            # NACK might mean already in command mode, try to continue
            return False
    return False

def send_address(ser, address):
    """Send 32-bit address with checksum"""
    addr_bytes = struct.pack('>I', address)
    checksum = 0
    for b in addr_bytes:
        checksum ^= b
    ser.write(addr_bytes + bytes([checksum]))
    time.sleep(0.05)

    # Check for ACK
    if ser.in_waiting:
        response = ser.read(1)
        return response == b'\x79'
    return False

def read_memory(ser, address, length):
    """Read memory using bootloader protocol"""
    if length > 256:
        length = 256

    # Clear any pending data
    if ser.in_waiting:
        ser.read(ser.in_waiting)

    # Send READ command (0x11)
    print(f"   Sending READ command...", end="")
    ser.write(bytes([0x11, 0xFF ^ 0x11]))
    time.sleep(0.3)  # Longer wait for 9600 baud

    if not ser.in_waiting:
        print(" no response")
        return None

    resp = ser.read(1)
    if resp == b'\x79':
        print(" ACK", end="")
    elif resp == b'\x1F':
        print(" NACK")
        return None
    else:
        print(f" unexpected: 0x{resp[0]:02X}")
        return None

    # Send address
    print(f", sending address...", end="")
    addr_bytes = struct.pack('>I', address)
    checksum = 0
    for b in addr_bytes:
        checksum ^= b
    ser.write(addr_bytes + bytes([checksum]))
    time.sleep(0.3)

    if not ser.in_waiting:
        print(" no response")
        return None

    resp = ser.read(1)
    if resp == b'\x79':
        print(" ACK", end="")
    elif resp == b'\x1F':
        print(" NACK")
        return None
    else:
        print(f" unexpected: 0x{resp[0]:02X}")
        return None

    # Send length (N-1 format)
    print(f", sending length...", end="")
    n_minus_1 = length - 1
    checksum = n_minus_1 ^ 0xFF
    ser.write(bytes([n_minus_1, checksum]))
    time.sleep(0.3)

    if not ser.in_waiting:
        print(" no response")
        return None

    resp = ser.read(1)
    if resp == b'\x79':
        print(" ACK")
    elif resp == b'\x1F':
        print(" NACK")
        return None
    else:
        print(f" unexpected: 0x{resp[0]:02X}")
        return None

    # Read data
    time.sleep(0.5)  # Give time for data at 9600 baud
    if ser.in_waiting >= length:
        data = ser.read(length)
        return data
    elif ser.in_waiting > 0:
        # Read what we got
        data = ser.read(ser.in_waiting)
        print(f"   Warning: Got {len(data)} bytes, expected {length}")
        return data
    else:
        print("   No data received")
        return None

def main():
    print("=" * 70)
    print("Direct USART Memory Reader (No Sync Required)")
    print("=" * 70)

    # Open serial port
    ser = serial.Serial(
        port='/dev/ttyUSB0',
        baudrate=9600,
        bytesize=8,
        parity=serial.PARITY_EVEN,
        stopbits=1,
        timeout=1
    )

    print("\n📡 Testing bootloader communication...")

    # Try multiple sync bytes to reset bootloader state
    print("   Resetting bootloader state...", end="")
    got_response = False
    for i in range(5):
        ser.write(b'\x7F')
        time.sleep(0.1)
        if ser.in_waiting:
            resp = ser.read(ser.in_waiting)  # Read all available
            if b'\x79' in resp:
                print(" got ACK!")
                got_response = True
                break
            elif b'\x1F' in resp:
                if i == 0:
                    print(" got NACK (already synced)", end="")
                # Continue trying

    if not got_response:
        print(" trying to continue anyway...")

    # Try GET command directly
    print("   Sending GET command...", end="")
    if send_command(ser, 0x00):
        print(" ✅ ACK")

        # Read GET response
        time.sleep(0.1)
        if ser.in_waiting:
            data = ser.read(ser.in_waiting)
            print(f"   Bootloader version: 0x{data[0]:02X}")
            print(f"   Supported commands: {' '.join(f'{b:02X}' for b in data[1:-1])}")
    else:
        print(" ❌ NACK or no response")
        print("\n⚠️  Bootloader not in expected state")
        print("   Try running swd_quick_check.py first")
        ser.close()
        return

    # Try GET ID command
    print("\n   Sending GET ID command...", end="")
    if send_command(ser, 0x02):
        print(" ✅ ACK")

        time.sleep(0.1)
        if ser.in_waiting:
            length = ser.read(1)[0] + 1
            chip_id = ser.read(length)
            id_value = int.from_bytes(chip_id, 'big')
            print(f"   Chip ID: 0x{id_value:04X}", end="")
            if id_value == 0x0413:
                print(" (STM32F405/407/415/417)")
            elif id_value == 0x0411:
                print(" (STM32F205/215/207/217)")
            else:
                print()

            # Read final ACK
            if ser.in_waiting:
                ser.read(1)

    print("\n" + "=" * 70)
    print("Memory Read Tests")
    print("=" * 70)

    # Test memory regions - matching 4-dump_flash.py targets
    test_regions = [
        ("TEST_UNPROTECTED", 0xE0042000, 12),  # DBGMCU_IDCODE
        ("UNIQUE_ID", 0x1FFF7A10, 12),  # 96-bit Unique Device ID
        ("OPTION_BYTES", 0x1FFFC000, 16),  # RDP settings
        ("OTP", 0x1FFF7800, 528),  # One-Time Programmable area
        ("STORAGE", 0x08008000, 32768),  # 32KB storage sectors (encrypted mnemonic)
    ]

    for name, addr, size in test_regions:
        print(f"\n📍 Reading {name} at 0x{addr:08X} ({size} bytes)...")

        # For large regions, read in chunks
        if size > 256:
            all_data = bytearray()
            success = True

            for offset in range(0, size, 256):
                chunk_size = min(256, size - offset)
                chunk_addr = addr + offset

                if size > 1024:  # Show progress for very large reads
                    print(f"\n   Reading chunk at 0x{chunk_addr:08X} ({offset}/{size} bytes)...")

                chunk_data = read_memory(ser, chunk_addr, chunk_size)

                if chunk_data:
                    all_data.extend(chunk_data)
                else:
                    success = False
                    break

            if success and len(all_data) > 0:
                print(f"   ✅ Success: Read {len(all_data)} bytes total")

                # Display first few lines of hex for large data
                max_display = min(64, len(all_data))  # Show first 64 bytes max
                for i in range(0, max_display, 16):
                    print(f"   {addr + i:08X}: ", end="")
                    chunk = all_data[i:i+16]
                    hex_str = " ".join(f"{b:02X}" for b in chunk)
                    print(f"{hex_str:<48}", end="")
                    ascii_str = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
                    print(f" |{ascii_str}|")

                if len(all_data) > max_display:
                    print(f"   ... ({len(all_data) - max_display} more bytes)")

                # Save to file for large dumps
                if len(all_data) > 256:
                    if not os.path.exists('USART_DUMPS'):
                        os.makedirs('USART_DUMPS')
                    filename = f"USART_DUMPS/{name}_0x{addr:08X}.bin"
                    with open(filename, 'wb') as f:
                        f.write(all_data)
                    print(f"   💾 Saved to {filename}")
            else:
                print(f"   ❌ Failed to read")
        else:
            # Small region - single read
            data = read_memory(ser, addr, size)

            if data:
                print(f"   ✅ Success: Read {len(data)} bytes")

                # Display hex
                for i in range(0, len(data), 16):
                    print(f"   {addr + i:08X}: ", end="")
                    chunk = data[i:i+16]
                    hex_str = " ".join(f"{b:02X}" for b in chunk)
                    print(f"{hex_str:<48}", end="")
                    ascii_str = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
                    print(f" |{ascii_str}|")
            else:
                print(f"   ❌ Failed to read")

    # Try to reset bootloader state before closing
    print("\n📡 Resetting bootloader for next run...")

    # Method 1: Send multiple sync bytes to clear state
    for i in range(3):
        ser.write(b'\x7F')
        time.sleep(0.05)
        if ser.in_waiting:
            ser.read(ser.in_waiting)  # Clear any response

    # Method 2: Try sending an invalid command to force reset
    ser.write(b'\xFF\x00')  # Invalid command
    time.sleep(0.1)
    if ser.in_waiting:
        ser.read(ser.in_waiting)  # Clear NACK

    # Clear any remaining data
    time.sleep(0.1)
    if ser.in_waiting:
        ser.read(ser.in_waiting)

    ser.close()

    print("\n" + "=" * 70)
    print("✅ USART bootloader is working!")
    print("\nYou can now use usart_read_mem.py to dump full memory")
    print("=" * 70)

if __name__ == "__main__":
    main()