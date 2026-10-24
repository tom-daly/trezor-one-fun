#!/usr/bin/env python3
"""
Use SWD to read memory (which seems to enable USART bootloader)
Then immediately test USART
"""

import sys
sys.path.insert(0, '/home/tdaly/.cwvenv/lib/python3.12/site-packages')
from swd import Swd
import serial
import time

def extensive_swd_read():
    """Perform extensive SWD memory reading like swd_read_all.py"""
    try:
        print("\n📡 Performing extensive SWD memory read...")
        dev = Swd()
        print(f"   Connected: {dev.get_version().str}")

        # Read multiple memory regions like swd_read_all does
        regions = [
            ("DBGMCU_IDCODE", 0xE0042000, 12),
            ("UNIQUE_ID", 0x1FFF7A10, 12),
            ("OPTION_BYTES", 0x1FFFC000, 16),
            ("OTP_START", 0x1FFF7800, 32),  # Just first 32 bytes
            ("STORAGE_START", 0x08008000, 32),  # Just first 32 bytes
        ]

        for name, addr, size in regions:
            print(f"   Reading {name} at 0x{addr:08X}...", end="")
            data = bytearray()

            # Read in 4-byte aligned chunks
            for offset in range(0, size, 4):
                remaining = size - offset
                read_size = min(4, remaining)
                if read_size == 4:
                    chunk_gen = dev.read_mem32(addr + offset, 4)
                    chunk = list(chunk_gen)
                    if chunk:
                        data.extend(chunk[0].to_bytes(4, 'little'))

            if data:
                print(f" ✓ ({len(data)} bytes)")
                # Show first few bytes
                hex_str = ' '.join(f'{b:02X}' for b in data[:8])
                print(f"      Data: {hex_str}...")
            else:
                print(" ✗")

        print("   ✓ Extensive SWD read complete")

        # Important: delete the SWD object to release the interface
        del dev
        time.sleep(0.5)  # Give time for interface to release
        return True

    except Exception as e:
        print(f"   ✗ SWD failed: {e}")
        return False

def test_usart_bootloader():
    """Test USART bootloader with multiple baudrates"""
    baudrates = [9600, 115200, 57600, 38400, 19200]

    print("\n📡 Testing USART bootloader...")

    for baud in baudrates:
        print(f"\n   Testing {baud} baud...")
        try:
            ser = serial.Serial(
                port='/dev/ttyUSB0',
                baudrate=baud,
                bytesize=8,
                parity=serial.PARITY_EVEN,
                stopbits=1,
                timeout=0.5
            )

            # Clear any pending data
            ser.reset_input_buffer()
            ser.reset_output_buffer()

            # Send sync byte
            ser.write(b'\x7F')
            time.sleep(0.1)

            if ser.in_waiting:
                response = ser.read(1)
                if response == b'\x79':
                    print(f"   ✅ SUCCESS at {baud} baud - Got ACK!")

                    # Test GET command
                    print("   Testing GET command...")
                    ser.write(b'\x00\xFF')
                    time.sleep(0.1)

                    if ser.in_waiting:
                        # Read all available data
                        data = ser.read(ser.in_waiting)
                        print(f"   Response: {' '.join(f'{b:02X}' for b in data)}")

                    ser.close()
                    return True
                elif response == b'\x1F':
                    print(f"   Got NACK (0x1F)")
                else:
                    print(f"   Got unexpected: 0x{response[0]:02X}")
            else:
                print(f"   No response")

            ser.close()

        except Exception as e:
            print(f"   Error at {baud}: {e}")

    return False

def main():
    print("="*70)
    print("SWD Memory Read → USART Bootloader Enable")
    print("="*70)
    print("\nThis script replicates the successful sequence:")
    print("1. Use SWD to read memory extensively")
    print("2. Immediately test USART bootloader")
    print("\n⚠️  Prerequisites:")
    print("   - BOOT0 = 1 (HIGH/3.3V)")
    print("   - BOOT1 = 0 (LOW/GND)")
    print("   - TX/RX properly connected (crossed)")
    print("="*70)

    # Step 1: Extensive SWD memory read
    if not extensive_swd_read():
        print("\n❌ SWD read failed")
        print("Check STLink connection and try again")
        return

    # Step 2: Immediately test USART
    print("\n" + "="*70)
    print("SWD complete. Now testing USART...")
    print("="*70)

    if test_usart_bootloader():
        print("\n" + "="*70)
        print("✅ SUCCESS! USART bootloader is now active!")
        print("\nYou can now run:")
        print("   python3 usart_read_mem.py")
        print("to dump memory via USART bootloader")
        print("="*70)
    else:
        print("\n" + "="*70)
        print("❌ USART bootloader still not responding")
        print("\nPossible issues:")
        print("1. BOOT pins not set correctly")
        print("2. TX/RX not connected properly")
        print("3. Device needs physical reset after BOOT pin change")
        print("="*70)

if __name__ == "__main__":
    main()