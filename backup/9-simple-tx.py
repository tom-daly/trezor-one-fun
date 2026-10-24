#!/usr/bin/env python3
"""
Use ChipWhisperer's built-in serial interface for STM32 bootloader

ChipWhisperer default USART pin mapping:
- TIO1 = serial_rx (receives data)
- TIO2 = serial_tx (sends data)

Hardware connections:
- TIO1 (Blue wire) <- PA9/TX (STM32 USART1_TX)
- TIO2 (Yellow wire) -> PA10/RX (STM32 USART1_RX)
"""

import chipwhisperer as cw
import time

print("=" * 60)
print("STM32 Bootloader - Using ChipWhisperer USART")
print("=" * 60)

# Connect to ChipWhisperer
scope = cw.scope()
print("[+] ChipWhisperer connected")

# Get the built-in USART from the scope
print("\n[*] Setting up ChipWhisperer USART...")
print("    Default CW mapping: TIO1=RX, TIO2=TX")

# Access the USART using the correct method
usart = scope._get_usart()

# Initialize USART with STM32 bootloader settings
# STM32 bootloader uses: 9600 8E1 (even parity)
# No need to configure TIO pins - ChipWhisperer uses defaults:
#   - TIO1 as serial_rx (input)
#   - TIO2 as serial_tx (output)
usart.init(baud=9600, stopbits=1, parity='even')

print(f"[+] USART configured:")
print(f"    Baud: 9600")
print(f"    Format: 8E1 (8 bits, even parity, 1 stop)")
print(f"    TX: TIO2 -> PA10 (USART1_RX) [Yellow wire]")
print(f"    RX: TIO1 <- PA9 (USART1_TX) [Blue wire]")

# Clear any pending data
usart.flush()

print("\n[*] Sending STM32 bootloader sync byte...")

# Send sync byte (0x7F) - try without checksum first
usart.write([0x7F])
print(f"[+] Sent: 0x7F (no checksum)")

# Optionally try with checksum if you suspect it's needed
#usart.write([0x7F, 0x80])  # 0x7F XOR 0xFF = 0x80
#print(f"[+] Sent: 0x7F 0x80 (with checksum)")

# Wait for response
print("[*] Waiting for response...")
time.sleep(0.1)  # Give bootloader time to respond

response = usart.read(1, timeout=1000)  # 1 second timeout

if response and len(response) > 0:
    resp_byte = response[0]
    print(f"\n✅ Response received: 0x{resp_byte:02X}")

    if resp_byte == 0x79:
        print("🎉 SUCCESS: Got ACK - STM32 system bootloader is active!")
        print("    RDP2->RDP1 bypass confirmed!")
    elif resp_byte == 0x1F:
        print("❌ Got NACK - bootloader rejected sync")
    else:
        print(f"⚠️ Unexpected response: 0x{resp_byte:02X}")
else:
    print("⚠️ No response to sync byte - bootloader might already be active")
    print("    Proceeding to Get ID command anyway...")

# Wait 1 second before Get ID command
print("\n[*] Waiting 1 second...")
time.sleep(.1)

# Try Get ID command to check activation (regardless of sync response)
print("[*] Sending Get ID command (0x02) to verify activation...")
usart.write([0x02, 0xFD])  # Get ID command

resp = usart.read(1, timeout=1000)
if resp and resp[0] == 0x79:
    print("[+] Get ID ACK received - bootloader is active!")
    # Read the response
    n = usart.read(1, timeout=1000)  # Number of bytes
    if n:
        pid_len = n[0] + 1
        pid = usart.read(pid_len, timeout=1000)  # Product ID
        ack = usart.read(1, timeout=1000)  # Final ACK
        if pid:
            print(f"[+] Product ID: {bytes(pid).hex()}")
elif resp:
    print(f"❌ Get ID failed - response: 0x{resp[0]:02X}")
else:
    print("❌ No response to Get ID - bootloader not active")

# Clean up
scope.dis()
print("\n[+] Done")