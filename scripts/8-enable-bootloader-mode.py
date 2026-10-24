#!/usr/bin/env python3
"""
Enable STM32 System Bootloader Mode
Drives BOOT0 high (TIO1 -> lifted pin 60) + BOOT1 low (TIO2 -> pin 28),
then soft-resets: BOOT pins are sampled at every reset edge -> bootloader.
No glitch needed: this chip is RDP1 at rest (glitch 2 is only for flash
READS via the bootloader). UART via the FTDI on /dev/ttyUSB0 (115200 8E1).
"""

import time

import chipwhisperer as cw

print("=" * 60)
print("STM32 System Bootloader Enabler")
print("=" * 60)

try:
    scope = cw.scope()
    print("[+] ChipWhisperer connected")
except Exception as e:
    print(f"[-] Failed to connect to ChipWhisperer: {e}")
    raise SystemExit(1)

# Define both boot pins BEFORE the reset (they are sampled at reset edge)
scope.io.tio1 = True    # BOOT0 high (lifted pin 60)
scope.io.tio2 = False   # BOOT1 low  (pin 28) -- floats if unset: coin flip
print("[+] TIO1=HIGH (BOOT0), TIO2=LOW (BOOT1)")

# Soft reset -> BootROM samples BOOT pins -> system bootloader
print("[*] Soft reset (nRST pulse)...")
scope.io.nrst = False
time.sleep(0.1)
scope.io.nrst = "high_z"
time.sleep(0.5)

print("[+] Done - STM32 should now be in the system bootloader")
print("    (screen stays off; PA9 idles high but that is ambiguous -")
print("     run usart_force_bootloader.py / the sync hammer for proof)")
print("[i] The bootloader waits for the 0x7F sync indefinitely - no rush")

scope.dis()
