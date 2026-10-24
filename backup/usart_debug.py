#!/usr/bin/env python3
"""
USART bootloader debug - diagnose communication issues
"""

import serial
import sys
import time
import struct

def hex_dump(data, prefix=""):
    """Display hex dump of data"""
    if not data:
        print(f"{prefix}(no data)")
        return

    print(f"{prefix}", end="")
    for i, b in enumerate(data):
        print(f"{b:02X} ", end="")
        if (i + 1) % 16 == 0:
            print(f"\n{prefix}", end="")
    print()

def test_baudrate(port, baudrate):
    """Test a specific baudrate"""
    print(f"\n{'='*60}")
    print(f"Testing {baudrate} baud")
    print(f"{'='*60}")

    try:
        ser = serial.Serial(
            port=port,
            baudrate=baudrate,
            bytesize=8,
            parity=serial.PARITY_EVEN,
            stopbits=1,
            timeout=0.5
        )

        # Clear buffers
        ser.reset_input_buffer()
        ser.reset_output_buffer()

        print("Sending sync bytes (0x7F)...")

        # Try multiple sync attempts
        for attempt in range(5):
            print(f"\nAttempt {attempt + 1}:")

            # Send sync byte
            ser.write(b'\x7F')
            print(f"  Sent: 0x7F")

            # Wait and check for response
            time.sleep(0.1)

            if ser.in_waiting:
                response = ser.read(ser.in_waiting)
                print(f"  Received ({len(response)} bytes): ", end="")
                for b in response:
                    if b == 0x79:
                        print(f"0x{b:02X} (ACK!) ", end="")
                    elif b == 0x1F:
                        print(f"0x{b:02X} (NACK) ", end="")
                    else:
                        print(f"0x{b:02X} ", end="")
                print()

                if 0x79 in response:
                    print("  ✅ SUCCESS - Got ACK!")

                    # Try to get version
                    print("\n  Testing GET command (0x00)...")
                    ser.write(bytes([0x00, 0xFF]))
                    print(f"  Sent: 0x00 0xFF")

                    time.sleep(0.1)
                    response = ser.read(ser.in_waiting)
                    if response:
                        print(f"  Response: ", end="")
                        hex_dump(response, "            ")

                    ser.close()
                    return True
                elif 0x1F in response:
                    print("  ⚠️ Got NACK - bootloader rejected sync")
            else:
                print("  No response")

            time.sleep(0.2)

        ser.close()

    except Exception as e:
        print(f"Error: {e}")

    return False

def test_raw_communication(port, baudrate):
    """Test raw byte communication without protocol"""
    print(f"\n{'='*60}")
    print(f"Raw communication test at {baudrate} baud")
    print(f"{'='*60}")

    try:
        # Try different parity settings
        parity_modes = [
            (serial.PARITY_EVEN, "Even"),
            (serial.PARITY_NONE, "None"),
            (serial.PARITY_ODD, "Odd")
        ]

        for parity, parity_name in parity_modes:
            print(f"\nTesting with {parity_name} parity:")

            ser = serial.Serial(
                port=port,
                baudrate=baudrate,
                bytesize=8,
                parity=parity,
                stopbits=1,
                timeout=0.5
            )

            # Send various test patterns
            test_patterns = [
                (b'\x7F', "Sync byte"),
                (b'\x00\xFF', "GET command"),
                (b'\xFF', "0xFF"),
                (b'\x00', "0x00"),
            ]

            for pattern, description in test_patterns:
                ser.reset_input_buffer()
                print(f"  Sending {description}: ", end="")
                hex_dump(pattern, "")

                ser.write(pattern)
                time.sleep(0.1)

                if ser.in_waiting:
                    response = ser.read(ser.in_waiting)
                    print(f"    Response: ", end="")
                    hex_dump(response, "")

                    # Interpret response
                    if 0x79 in response:
                        print(f"    ✅ Contains ACK (0x79)")
                    if 0x1F in response:
                        print(f"    ⚠️ Contains NACK (0x1F)")
                else:
                    print(f"    No response")

                time.sleep(0.1)

            ser.close()

    except Exception as e:
        print(f"Error: {e}")

def check_rdp_state(port, baudrate):
    """Try to determine actual RDP state"""
    print(f"\n{'='*60}")
    print("Checking RDP state indicators")
    print(f"{'='*60}")

    print("\nNACK (0x1F) on sync can indicate:")
    print("  1. RDP Level 2 (permanent protection)")
    print("  2. Wrong baudrate/parity")
    print("  3. Bootloader disabled via option bytes")
    print("  4. Not in bootloader mode (check BOOT pins)")
    print("  5. Previous command left bootloader in bad state")

    print("\nTo verify RDP Level 2:")
    print("  - Check if SWD/JTAG is completely disabled")
    print("  - Device would be permanently locked")

def main():
    print("=" * 70)
    print("USART Bootloader Debug Tool")
    print("=" * 70)

    port = sys.argv[1] if len(sys.argv) > 1 else '/dev/ttyUSB0'

    print(f"\n📡 Port: {port}")
    print("\n⚠️  Prerequisites:")
    print("  1. BOOT0 = 1 (HIGH/3.3V)")
    print("  2. BOOT1 = 0 (LOW/GND)")
    print("  3. Reset device after setting BOOT pins")
    print("  4. TX/RX properly connected (crossed)")

    input("\nPress Enter to start diagnosis...")

    # Test common baudrates
    baudrates = [9600, 19200, 38400, 57600, 115200]

    print("\n" + "=" * 70)
    print("Testing standard baudrates with EVEN parity")
    print("=" * 70)

    working_baudrate = None
    for br in baudrates:
        if test_baudrate(port, br):
            working_baudrate = br
            print(f"\n✅ Found working baudrate: {br}")
            break

    if not working_baudrate:
        print("\n❌ No working baudrate found with standard protocol")
        print("\nTrying raw communication test...")

        # Test raw communication at 9600
        test_raw_communication(port, 9600)

        # Check RDP implications
        check_rdp_state(port, 9600)

        print("\n" + "=" * 70)
        print("Troubleshooting suggestions:")
        print("=" * 70)
        print("\n1. Verify BOOT pins:")
        print("   - Measure BOOT0 pin: should be 3.3V")
        print("   - Measure BOOT1 pin: should be 0V")
        print("   - Reset AFTER setting BOOT pins")

        print("\n2. Check connections:")
        print("   - Device TX -> USB-UART RX")
        print("   - Device RX -> USB-UART TX")
        print("   - Common GND connected")

        print("\n3. Possible protection:")
        print("   - Constant NACK (0x1F) suggests RDP Level 2")
        print("   - Or bootloader disabled in option bytes")

        print("\n4. Try power cycle:")
        print("   - Disconnect all power")
        print("   - Set BOOT pins")
        print("   - Power on")
        print("   - Should enter bootloader immediately")

    print("\n" + "=" * 70)

if __name__ == "__main__":
    main()