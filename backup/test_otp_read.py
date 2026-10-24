#!/usr/bin/env python3
"""
Simple OTP memory read test for STM32F205
Tests direct reading of OTP hardware salt at 0x1FFF7860
"""

import os
import sys
import time
from swd import Swd

# OTP Hardware Salt Location
OTP_SALT_ADDR = 0x1FFF7860  # OTP Block 3
OTP_SIZE = 32  # 32 bytes

def reset_stlink():
    """Reset the STLink adapter"""
    reset_cmd = "/home/tdaly/.cwvenv/usb_reset"
    os.system(f"{reset_cmd} > /dev/null 2>&1")
    time.sleep(0.5)

print("="*60)
print("Direct OTP Read Test - STM32F205")
print("="*60)

# Reset STLink
print("\n[*] Resetting STLink...")
reset_stlink()

try:
    # Connect via SWD
    print("[*] Connecting via SWD...")
    swd = Swd()
    version = swd.get_version().str
    print(f"[+] Connected: {version}")
    
    # Try to read OTP hardware salt
    print(f"\n[*] Attempting to read OTP at 0x{OTP_SALT_ADDR:08X}...")
    print(f"    Reading {OTP_SIZE} bytes...")
    
    try:
        # Direct read attempt
        otp_data = swd.read_mem(OTP_SALT_ADDR, OTP_SIZE)
        
        print(f"\n✅ SUCCESS! Read {len(otp_data)} bytes from OTP")
        print("\nOTP Hardware Salt:")
        
        # Display hex dump
        for i in range(0, len(otp_data), 16):
            print(f"  0x{OTP_SALT_ADDR + i:08X}: ", end="")
            for j in range(16):
                if i + j < len(otp_data):
                    print(f"{otp_data[i+j]:02X} ", end="")
            print()
        
        # Save to file
        with open("otp_salt_direct.bin", "wb") as f:
            f.write(bytes(otp_data))
        print(f"\n[+] Saved to otp_salt_direct.bin")
        
        # Check if programmed
        if all(b == 0xFF for b in otp_data):
            print("\n⚠️  WARNING: OTP appears unprogrammed (all 0xFF)")
        elif all(b == 0x00 for b in otp_data):
            print("\n⚠️  WARNING: OTP appears empty (all 0x00)")
        else:
            print("\n✓ OTP contains programmed data")
            
    except Exception as e:
        print(f"\n❌ FAILED to read OTP!")
        print(f"Error: {e}")
        print(f"Error type: {type(e).__name__}")
        print("\nThis suggests OTP is protected at current RDP level")
        
except Exception as e:
    print(f"\n❌ Failed to connect via SWD: {e}")
    sys.exit(1)

print("\n" + "="*60)
print("Test complete")
print("="*60)