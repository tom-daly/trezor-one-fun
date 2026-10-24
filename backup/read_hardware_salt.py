#!/usr/bin/env python3
"""
Read Hardware Salt from STM32F205 OTP Memory
Retrieves the hardware salt components used by Trezor for device encryption
"""

import os
import sys
import time
from swd import Swd

# STM32F205 Unique ID register addresses
# The UID is at 0x1FFF7A10 on STM32F2, but let's also try the standard location
UID_BASE = 0x1FFF7A10  # Base address for unique device ID (STM32F2)
UID_BASE_ALT = 0x1FFFF7E8  # Alternative UID location (some STM32 variants)
UID_WORD0 = UID_BASE + 0x00  # First 32 bits of unique ID
UID_WORD1 = UID_BASE + 0x04  # Second 32 bits of unique ID  
UID_WORD2 = UID_BASE + 0x08  # Third 32 bits of unique ID

# OTP (One-Time Programmable) memory addresses
OTP_BASE = 0x1FFF7800  # OTP base address
OTP_BLOCK_SIZE = 32  # Each OTP block is 32 bytes
OTP_BLOCK_RANDOMNESS = 3  # Block 3 contains hardware randomness
OTP_RANDOMNESS_ADDR = OTP_BASE + (OTP_BLOCK_RANDOMNESS * OTP_BLOCK_SIZE)  # 0x1FFF7860

def reset_stlink():
    """Reset the STLink adapter"""
    reset_cmd = "/home/tdaly/.cwvenv/usb_reset"
    os.system(f"{reset_cmd} > /dev/null 2>&1")
    time.sleep(0.5)

def check_rdp_level(swd):
    """Check the Read Protection level of the device"""
    # Option bytes address for STM32F205
    FLASH_OPTCR = 0x40023C14  # Flash option control register
    
    try:
        # Read the option control register
        optcr_bytes = swd.read_mem(FLASH_OPTCR, 4)
        optcr = int.from_bytes(optcr_bytes, 'little')
        
        # RDP level is in bits 15:8
        rdp_value = (optcr >> 8) & 0xFF
        
        # Determine RDP level
        if rdp_value == 0xAA:
            rdp_level = 0
            rdp_desc = "Level 0 (No protection)"
            can_read_flash = True
            can_read_otp = True
        elif rdp_value == 0xCC:
            rdp_level = 2
            rdp_desc = "Level 2 (Full protection)"
            can_read_flash = False
            can_read_otp = False
        else:
            rdp_level = 1
            rdp_desc = "Level 1 (Read protection)"
            can_read_flash = False
            can_read_otp = True
            
        print(f"\n[*] Device Protection Status:")
        print(f"  RDP Level: {rdp_desc}")
        print(f"  RDP Value: 0x{rdp_value:02X}")
        print(f"  OPTCR Register: 0x{optcr:08X}")
        print(f"  Flash readable via SWD: {'✅ Yes' if can_read_flash else '❌ No'}")
        print(f"  OTP readable via SWD: {'✅ Yes' if can_read_otp else '❌ No'}")
        
        # Test flash access
        try:
            flash_test = swd.read_mem(0x08000000, 4)
            print(f"  Flash access test: ✅ Successful (RDP may be bypassed)")
        except:
            print(f"  Flash access test: ❌ Failed (RDP active)")
            
        return rdp_level, can_read_otp
        
    except Exception as e:
        print(f"\n[!] Could not determine RDP level: {e}")
        return None, True  # Assume we can try OTP

def read_hardware_salt():
    """Read the complete hardware salt from the device"""
    
    print("="*60)
    print("STM32F205 Hardware Salt Reader")
    print("="*60)
    
    # Reset STLink
    print("\n[*] Resetting STLink adapter...")
    reset_stlink()
    
    try:
        # Connect via SWD
        print("[*] Connecting to target via SWD...")
        swd = Swd()
        version = swd.get_version().str
        print(f"[+] Connected! SWD Version: {version}")
        
        # Check RDP level first
        rdp_level, can_read_otp = check_rdp_level(swd)
        
        if rdp_level == 2 and can_read_otp == False:
            print("\n❌ ERROR: Device is at RDP Level 2!")
            print("   OTP memory cannot be read via SWD at this protection level.")
            print("   A successful glitch attack is required to bypass RDP2.")
            return None
            
        if rdp_level == 1:
            print("\n✅ RDP Level 1 detected - OTP is readable, flash is protected")
            print("   Hardware salt can be extracted, but flash requires glitching.\n")
        elif rdp_level == 0:
            print("\n✅ RDP Level 0 detected - Full access available\n")
        
        # Component 1: Read UUID (12 bytes)
        print("\n[*] Reading UUID (Unique Device ID)...")
        
        # Try to read UUID - it might be protected or at a different address
        uuid_bytes = []
        uid_word0, uid_word1, uid_word2 = 0, 0, 0
        
        try:
            # Try primary location
            uid_word0_bytes = swd.read_mem(UID_WORD0, 4)
            uid_word1_bytes = swd.read_mem(UID_WORD1, 4)
            uid_word2_bytes = swd.read_mem(UID_WORD2, 4)
            
            # Convert bytes to integers for display
            uid_word0 = int.from_bytes(uid_word0_bytes, 'little')
            uid_word1 = int.from_bytes(uid_word1_bytes, 'little')
            uid_word2 = int.from_bytes(uid_word2_bytes, 'little')
            
            # UUID bytes are already in the correct format
            uuid_bytes = list(uid_word0_bytes) + list(uid_word1_bytes) + list(uid_word2_bytes)
            print(f"  ✅ UUID read from primary location (0x{UID_BASE:08X})")
            
        except Exception as e:
            print(f"  ⚠️ Could not read UUID from 0x{UID_BASE:08X}: {e}")
            print(f"  Trying alternative location...")
            
            try:
                # Try alternative location
                uid_word0_bytes = swd.read_mem(UID_BASE_ALT, 4)
                uid_word1_bytes = swd.read_mem(UID_BASE_ALT + 4, 4)
                uid_word2_bytes = swd.read_mem(UID_BASE_ALT + 8, 4)
                
                uid_word0 = int.from_bytes(uid_word0_bytes, 'little')
                uid_word1 = int.from_bytes(uid_word1_bytes, 'little')
                uid_word2 = int.from_bytes(uid_word2_bytes, 'little')
                
                uuid_bytes = list(uid_word0_bytes) + list(uid_word1_bytes) + list(uid_word2_bytes)
                print(f"  ✅ UUID read from alternative location (0x{UID_BASE_ALT:08X})")
                
            except Exception as e2:
                print(f"  ⚠️ Could not read UUID from 0x{UID_BASE_ALT:08X}: {e2}")
                print(f"  UUID may be protected at RDP Level 1")
                print(f"  Using placeholder UUID (all zeros)")
                uuid_bytes = [0] * 12
        
        print(f"  UUID Address: 0x{UID_BASE:08X}")
        print(f"  Word0: 0x{uid_word0:08X}")
        print(f"  Word1: 0x{uid_word1:08X}")
        print(f"  Word2: 0x{uid_word2:08X}")
        print(f"  UUID Bytes (12): ", end="")
        for b in uuid_bytes:
            print(f"{b:02X} ", end="")
        print()
        
        # Component 2: Read OTP Randomness Block (32 bytes)
        print(f"\n[*] Reading OTP Block {OTP_BLOCK_RANDOMNESS} (Hardware Randomness)...")
        print(f"  OTP Address: 0x{OTP_RANDOMNESS_ADDR:08X}")
        
        # Read entire OTP block at once
        otp_bytes = list(swd.read_mem(OTP_RANDOMNESS_ADDR, OTP_BLOCK_SIZE))
        
        print(f"  OTP Randomness (32 bytes):")
        for i in range(0, len(otp_bytes), 16):
            print(f"    0x{OTP_RANDOMNESS_ADDR + i:08X}: ", end="")
            for j in range(16):
                if i + j < len(otp_bytes):
                    print(f"{otp_bytes[i+j]:02X} ", end="")
            print()
        
        # Combine both components for complete hardware salt
        hardware_salt = bytes(uuid_bytes + otp_bytes)
        
        print("\n" + "="*60)
        if len(uuid_bytes) == 12 and not all(b == 0 for b in uuid_bytes):
            print("COMPLETE HARDWARE SALT (44 bytes)")
        else:
            print("PARTIAL HARDWARE SALT (OTP only, UUID unavailable)")
        print("="*60)
        print(f"Total Size: {len(hardware_salt)} bytes")
        print(f"UUID Component: {len(uuid_bytes)} bytes {'(placeholder)' if all(b == 0 for b in uuid_bytes) else ''}")
        print(f"OTP Component: {len(otp_bytes)} bytes")
        print("\nHex representation:")
        
        # Display in formatted hex
        for i in range(0, len(hardware_salt), 16):
            print(f"  {i:04X}: ", end="")
            for j in range(16):
                if i + j < len(hardware_salt):
                    print(f"{hardware_salt[i+j]:02X} ", end="")
            print()
        
        # Save to file
        output_file = "hardware_salt.bin"
        with open(output_file, 'wb') as f:
            f.write(hardware_salt)
        print(f"\n[+] Hardware salt saved to: {output_file}")
        
        # Also save as hex text
        output_hex = "hardware_salt.hex"
        with open(output_hex, 'w') as f:
            f.write("# STM32F205 Hardware Salt\n")
            f.write(f"# Total: {len(hardware_salt)} bytes\n")
            f.write(f"# UUID: {len(uuid_bytes)} bytes (offset 0-11)\n")
            f.write(f"# OTP: {len(otp_bytes)} bytes (offset 12-43)\n\n")
            f.write("# UUID Component:\n")
            f.write("".join(f"{b:02X}" for b in uuid_bytes) + "\n\n")
            f.write("# OTP Randomness Component:\n")
            f.write("".join(f"{b:02X}" for b in otp_bytes) + "\n\n")
            f.write("# Complete Salt:\n")
            f.write("".join(f"{b:02X}" for b in hardware_salt) + "\n")
        print(f"[+] Hardware salt (hex) saved to: {output_hex}")
        
        # Check if OTP is all 0xFF (unprogrammed)
        if all(b == 0xFF for b in otp_bytes):
            print("\n⚠️  WARNING: OTP Block appears unprogrammed (all 0xFF)")
            print("    The device may not have had its hardware salt initialized.")
        elif all(b == 0x00 for b in otp_bytes):
            print("\n⚠️  WARNING: OTP Block appears empty (all 0x00)")
            print("    This is unusual and may indicate an issue.")
        else:
            print("\n✓ OTP Block contains programmed data")
        
        return hardware_salt
        
    except Exception as e:
        print(f"\n❌ Error reading hardware salt: {e}")
        return None

def main():
    """Main entry point"""
    salt = read_hardware_salt()
    
    if salt:
        print("\n" + "="*60)
        print("✅ Successfully retrieved hardware salt!")
        print("="*60)
    else:
        print("\n" + "="*60)
        print("❌ Failed to retrieve hardware salt")
        print("="*60)
        sys.exit(1)

if __name__ == "__main__":
    main()