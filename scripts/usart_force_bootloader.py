#!/usr/bin/env python3
"""
Force bootloader entry with reset control
"""

import serial
import time
import sys

def force_bootloader_entry(port='/dev/ttyUSB0'):
    """Try to force bootloader entry with different methods"""

    print("=" * 70)
    print("FORCE BOOTLOADER ENTRY")
    print("=" * 70)

    baudrates = [115200, 57600, 38400, 19200, 9600]

    for baudrate in baudrates:
        print(f"\n{'='*60}")
        print(f"Testing {baudrate} baud with Even parity")
        print(f"{'='*60}")

        try:
            ser = serial.Serial(
                port=port,
                baudrate=baudrate,
                bytesize=8,
                parity=serial.PARITY_EVEN,
                stopbits=1,
                timeout=0.2,
                rtscts=False,
                dsrdtr=False
            )

            # Method 1: Standard sync
            print("\n1. Standard sync (0x7F):")
            ser.reset_input_buffer()
            ser.reset_output_buffer()

            for i in range(10):
                ser.write(b'\x7F')
                time.sleep(0.05)

                if ser.in_waiting:
                    response = ser.read(ser.in_waiting)
                    print(f"   Response: {' '.join(f'{b:02X}' for b in response)}")
                    if 0x79 in response:
                        print(f"   ✅ SUCCESS! ACK received at {baudrate} baud!")
                        return True
                    elif 0x1F in response:
                        print(f"   ⚠️ NACK received - bootloader present but rejecting")
                else:
                    print(f"   Attempt {i+1}: No response", end="\r")

            print()

            # Method 2: Pattern break
            print("\n2. Pattern break (alternating 0x00/0xFF):")
            ser.reset_input_buffer()

            for i in range(5):
                ser.write(b'\x00\xFF')
                time.sleep(0.01)

            ser.write(b'\x7F')
            time.sleep(0.1)

            if ser.in_waiting:
                response = ser.read(ser.in_waiting)
                print(f"   Response: {' '.join(f'{b:02X}' for b in response)}")
            else:
                print("   No response")

            # Method 3: Auto-baud sequence
            print("\n3. Auto-baud detection pattern:")
            patterns = [
                b'\x7F',
                b'\xF0\x0F',
                b'\xAA\x55',
                b'\x00\xFF\x00\xFF',
                b'\x7E\x7E\x7E\x7F'
            ]

            for pattern in patterns:
                ser.reset_input_buffer()
                ser.write(pattern)
                time.sleep(0.05)

                if ser.in_waiting:
                    response = ser.read(ser.in_waiting)
                    print(f"   Pattern {pattern.hex()}: {' '.join(f'{b:02X}' for b in response)}")
                    if 0x79 in response:
                        print(f"   ✅ Found working pattern!")
                        return True

            ser.close()

        except Exception as e:
            print(f"   Error: {e}")

    return False

def check_wiring():
    """Provide wiring check instructions"""
    print("\n" + "=" * 70)
    print("WIRING CHECK")
    print("=" * 70)

    print("\n📌 STM32 Bootloader USART Connections:")
    print("\nFor STM32F205 (Trezor One):")
    print("  USART1: PA9 (TX), PA10 (RX)")
    print("  USART2: PA2 (TX), PA3 (RX)")
    print("  USART3: PB10 (TX), PB11 (RX)")

    print("\n⚠️ Connection checklist:")
    print("  □ STM32 TX  → USB-UART RX")
    print("  □ STM32 RX  → USB-UART TX")
    print("  □ STM32 GND → USB-UART GND")
    print("  □ BOOT0 = HIGH (3.3V)")
    print("  □ BOOT1 = LOW (GND)")

    print("\n🔧 Reset sequence:")
    print("  1. Hold BOOT0 HIGH")
    print("  2. Press and release RESET")
    print("  3. Device should enter bootloader")
    print("  4. Run this script within 1 second")

def test_loopback(port='/dev/ttyUSB0'):
    """Test if TX/RX are shorted (loopback test)"""
    print("\n" + "=" * 70)
    print("LOOPBACK TEST")
    print("=" * 70)

    print("\n🔄 Testing if TX/RX are connected together...")

    try:
        ser = serial.Serial(port, 9600, timeout=0.1)
        ser.reset_input_buffer()

        test_data = b'TEST123'
        ser.write(test_data)
        time.sleep(0.05)

        if ser.in_waiting:
            response = ser.read(ser.in_waiting)
            if response == test_data:
                print("   ⚠️ TX and RX appear to be shorted together!")
                print("   This means you're reading your own transmission")
                print("   Check your wiring!")
                return True
            else:
                print(f"   Got different data: {response}")
        else:
            print("   ✓ No loopback detected (good)")

        ser.close()
    except Exception as e:
        print(f"   Error: {e}")

    return False

def main():
    port = sys.argv[1] if len(sys.argv) > 1 else '/dev/ttyUSB0'

    print(f"Using port: {port}")

    # Test for loopback first
    if test_loopback(port):
        print("\n❌ Fix the loopback issue first!")
        check_wiring()
        return

    # Try to force bootloader entry
    success = force_bootloader_entry(port)

    if not success:
        check_wiring()

        print("\n" + "=" * 70)
        print("ALTERNATIVE APPROACHES")
        print("=" * 70)

        print("\n1. Try SWD-to-USART bridge:")
        print("   Some devices expose bootloader via SWD")

        print("\n2. Check if custom firmware is running:")
        print("   Device might have custom bootloader")

        print("\n3. Verify USART pins:")
        print("   STM32F205 might use different USART")
        print("   Check PCB traces from STM32 USART pins")

        print("\n4. Oscilloscope/Logic Analyzer:")
        print("   Monitor USART pins during reset")
        print("   Verify device is transmitting")

if __name__ == "__main__":
    main()