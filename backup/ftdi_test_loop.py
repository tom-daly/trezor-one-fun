#!/usr/bin/env python3
"""
Simple continuous transmit for FTDI testing with logic analyzer
"""

import serial
import time

print("FTDI Continuous Transmit Test")
print("=" * 40)

ser = serial.Serial('/dev/ttyUSB0', 9600, parity=serial.PARITY_EVEN)
print(f"Opened {ser.name} at 9600 baud, 8E1")
print("Sending 0xAA (10101010) continuously...")
print("Watch TX pin with logic analyzer")
print("Press Ctrl+C to stop\n")

try:
    count = 0
    while True:
        ser.write(bytes([0xAA]))  # 10101010 - alternating pattern
        count += 1
        print(f"\rSent: {count} bytes", end="", flush=True)
        time.sleep(0.01)  # 10ms between bytes

except KeyboardInterrupt:
    print(f"\n\nStopped after {count} bytes")
    ser.close()
    print("Port closed")