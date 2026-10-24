#!/usr/bin/env python3
"""
STM32 Bootloader communication using Waveshare USB-to-TTL adapter
Simple TX test - sends sync byte and Get ID command

Hardware connections:
- Waveshare TX -> PA10 (STM32 USART1_RX)
- Waveshare RX -> PA9 (STM32 USART1_TX)
- Waveshare GND -> STM32 GND
"""

import serial
import time
import sys

# Configuration - adjust this to match your USB-to-TTL device
# Common device names:
# - Linux: /dev/ttyUSB0, /dev/ttyUSB1, /dev/ttyACM0
# - macOS: /dev/tty.usbserial-*, /dev/tty.SLAB_USBtoUART
# - Windows: COM3, COM4, etc.

def find_serial_port():
    """Try to find the USB-to-TTL adapter automatically"""
    import serial.tools.list_ports

    print("[*] Searching for USB-to-TTL adapters...")
    ports = serial.tools.list_ports.comports()

    for port in ports:
        print(f"   Found: {port.device} - {port.description}")
        # Common USB-to-TTL adapter chips
        if any(x in port.description.lower() for x in ['ch340', 'cp210', 'ft232', 'pl2303', 'usb']):
            print(f"   → Using {port.device}")
            return port.device

    # If not found automatically, ask user
    if ports:
        print("\n[!] Could not auto-detect USB-to-TTL adapter")
        print("Available ports:")
        for i, port in enumerate(ports):
            print(f"  {i}: {port.device} - {port.description}")
        try:
            idx = int(input("Select port number: "))
            return ports[idx].device
        except:
            pass

    # Default fallback
    return "/dev/ttyUSB0"

print("=" * 60)
print("STM32 Bootloader - Using Waveshare USB-to-TTL")
print("=" * 60)

# Find serial port
SERIAL_PORT = find_serial_port()

print(f"\n[*] Using serial port: {SERIAL_PORT}")
print("[*] Configuring UART...")

try:
    # Open serial port with STM32 bootloader settings
    # STM32 bootloader uses: 9600 8E1 (8 bits, even parity, 1 stop bit)
    ser = serial.Serial(
        port=SERIAL_PORT,
        baudrate=9600,
        bytesize=serial.EIGHTBITS,
        parity=serial.PARITY_EVEN,
        stopbits=serial.STOPBITS_ONE,
        timeout=1,
        write_timeout=1
    )

    print(f"[+] Serial port opened: {ser.name}")
    print(f"    Baud: 9600")
    print(f"    Format: 8E1 (8 bits, even parity, 1 stop)")
    print(f"    TX: Waveshare TX -> PA10 (STM32 RX)")
    print(f"    RX: Waveshare RX <- PA9 (STM32 TX)")

except serial.SerialException as e:
    print(f"❌ Could not open {SERIAL_PORT}: {e}")
    print("\nTroubleshooting:")
    print("  1. Check if device is connected")
    print("  2. Check permissions: sudo chmod 666 /dev/ttyUSB0")
    print("  3. Or add user to dialout group: sudo usermod -a -G dialout $USER")
    print("  4. Then logout and login again")
    sys.exit(1)

# Clear any pending data
ser.reset_input_buffer()
ser.reset_output_buffer()

print("\n[*] Sending STM32 bootloader sync byte...")

# Send sync byte (0x7F)
ser.write(bytes([0x7F]))
print(f"[+] Sent: 0x7F (no checksum)")

# Wait for response
print("[*] Waiting for response...")
time.sleep(0.1)  # Give bootloader time to respond

response = ser.read(1)  # Read 1 byte

if response and len(response) > 0:
    resp_byte = response[0]
    print(f"\n✅ Response received: 0x{resp_byte:02X}")

    if resp_byte == 0x79:
        print("🎉 SUCCESS: Got ACK - STM32 system bootloader is active!")
        print("    Bootloader communication established!")
    elif resp_byte == 0x1F:
        print("❌ Got NACK - bootloader rejected sync")
    else:
        print(f"⚠️ Unexpected response: 0x{resp_byte:02X}")
else:
    print("⚠️ No response to sync byte - bootloader might already be active")
    print("    Proceeding to Get ID command anyway...")

# Wait before Get ID command
print("\n[*] Waiting 0.25 seconds...")
time.sleep(0.25)

# Try Get ID command to check activation (regardless of sync response)
print("[*] Sending Get ID command (0x02) to verify activation...")
ser.write(bytes([0x02, 0xFD]))  # Get ID command with checksum

resp = ser.read(1)
if resp and resp[0] == 0x79:
    print("[+] Get ID ACK received - bootloader is active!")

    # Read the response
    n = ser.read(1)  # Number of bytes
    if n:
        pid_len = n[0] + 1
        pid = ser.read(pid_len)  # Product ID
        ack = ser.read(1)  # Final ACK
        if pid:
            print(f"[+] Product ID: {pid.hex()}")

            # Decode PID for STM32F205
            if len(pid) >= 2:
                pid_val = (pid[0] << 8) | pid[1]
                if pid_val == 0x0413:
                    print("    ✅ Confirmed: STM32F205 detected!")
elif resp:
    print(f"❌ Get ID failed - response: 0x{resp[0]:02X}")
else:
    print("❌ No response to Get ID - bootloader not active")

# Clean up
ser.close()
print("\n[+] Serial port closed")
print("[+] Done")

print("\n" + "=" * 60)
print("Next steps if bootloader is active:")
print("  1. Read memory: Use Read Memory command (0x11)")
print("  2. Write memory: Use Write Memory command (0x31)")
print("  3. Jump to app: Use Go command (0x21)")
print("=" * 60)