#!/usr/bin/env python3
"""
Simple STM32 bootloader test with Waveshare USB-to-TTL
"""

import serial
import time

# CHANGE THIS to match your device
SERIAL_PORT = "/dev/ttyUSB0"  # or /dev/ttyUSB1, /dev/ttyACM0, etc.

# Open serial port (9600 8E1 for STM32 bootloader)
ser = serial.Serial(
    port=SERIAL_PORT,
    baudrate=9600,
    parity=serial.PARITY_EVEN,
    timeout=1
)

print(f"Opened {SERIAL_PORT}")

# Send sync byte
ser.write(bytes([0x7F]))
print("Sent: 0x7F")

# Read response
resp = ser.read(1)
if resp:
    print(f"Got: 0x{resp[0]:02X}")
    if resp[0] == 0x79:
        print("✅ Bootloader active!")
else:
    print("No response")

ser.close()