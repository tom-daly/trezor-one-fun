#!/usr/bin/env python3
"""
Simplest possible FTDI test - just open and send one byte
"""

import serial
import time

print("Opening /dev/ttyUSB0...")
try:
    ser = serial.Serial('/dev/ttyUSB0', 9600)
    print(f"✓ Opened {ser.name}")

    print("Sending 0x55 (01010101)...")
    ser.write(bytes([0x55]))
    print("✓ Sent")

    # Keep sending for 5 seconds
    print("Sending 0x55 every 100ms for 5 seconds...")
    for i in range(50):
        ser.write(bytes([0x55]))
        print(".", end="", flush=True)
        time.sleep(0.1)

    print("\n✓ Done")
    ser.close()

except Exception as e:
    print(f"Error: {e}")
    print("\nTry:")
    print("  sudo chmod 666 /dev/ttyUSB0")
    print("  or")
    print("  sudo python3 ftdi_simple_test.py")