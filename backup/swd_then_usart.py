#!/usr/bin/env python3
"""
Access SWD first, then immediately try USART bootloader
This leverages the fact that SWD access seems to enable USART
"""

import sys
sys.path.insert(0, '/home/tdaly/.cwvenv/lib/python3.12/site-packages')
from swd import Swd
import serial
import time
import subprocess

def access_swd():
    """Access SWD to put device in a state where USART works"""
    try:
        print("\n📡 Accessing SWD to prepare device...")
        dev = Swd()

        # Read something to establish connection
        version = dev.get_version()
        print(f"   SWD connected: {version.str}")

        # Read a test register (4 bytes aligned)
        DBGMCU_IDCODE = 0xE0042000
        data_gen = dev.read_mem32(DBGMCU_IDCODE, 4)  # Read 4 bytes (aligned)
        data = list(data_gen)  # Convert generator to list
        if data:
            print(f"   Read IDCODE: 0x{data[0]:08X}")
        else:
            print("   Read IDCODE: No data")

        # Clean up SWD
        del dev
        print("   ✓ SWD access complete\n")
        time.sleep(0.5)
        return True

    except Exception as e:
        print(f"   ✗ SWD failed: {e}\n")
        return False

def test_usart():
    """Test USART bootloader communication"""
    try:
        print("📡 Testing USART bootloader...")
        ser = serial.Serial(
            port='/dev/ttyUSB0',
            baudrate=9600,
            bytesize=8,
            parity=serial.PARITY_EVEN,
            stopbits=1,
            timeout=1
        )

        # Send sync byte
        print("   Sending sync byte (0x7F)...")
        ser.write(b'\x7F')
        time.sleep(0.2)

        # Check response
        if ser.in_waiting:
            response = ser.read(1)
            if response == b'\x79':
                print("   ✅ SUCCESS - Got ACK from bootloader!")

                # Try GET command
                print("   Testing GET command...")
                ser.write(b'\x00\xFF')
                time.sleep(0.1)

                if ser.in_waiting:
                    data = ser.read(ser.in_waiting)
                    print(f"   Response: {' '.join(f'{b:02X}' for b in data)}")

                ser.close()
                return True
            else:
                print(f"   Got response: 0x{response[0]:02X} (expected 0x79)")
        else:
            print("   ❌ No response from bootloader")

        ser.close()
        return False

    except Exception as e:
        print(f"   ✗ USART failed: {e}")
        return False

def main():
    print("="*70)
    print("SWD → USART Bridge Test")
    print("="*70)
    print("\n⚠️  Prerequisites:")
    print("   - BOOT0 = 1 (HIGH/3.3V)")
    print("   - BOOT1 = 0 (LOW/GND)")
    print("   - TX/RX properly connected")
    print("="*70)

    # First access SWD
    if access_swd():
        # Then immediately try USART
        time.sleep(0.5)
        if test_usart():
            print("\n✅ SUCCESS: USART working after SWD access!")
            print("\nNow you can run usart_read_mem.py to dump memory")
        else:
            print("\n❌ USART still not working")
            print("Check BOOT pins and connections")
    else:
        print("❌ Could not access SWD")
        print("Check STLink connection")

    print("\n" + "="*70)

if __name__ == "__main__":
    main()