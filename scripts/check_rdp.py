#!/usr/bin/env python3
"""
STM32F205 RDP Checker (Trezor One)
Simple tool to check Read Protection level
"""

import sys
from swd.stlink import Stlink

# STM32F205 specific addresses
FLASH_OPTCR = 0x40023C14  # Flash option control register

def main():
    """Check RDP level on STM32F205"""
    print("STM32F205 RDP Checker")
    print("=" * 30)
    
    try:
        # Connect to target
        stlink = Stlink(swd_frequency=1800000)
        print(f"✓ Connected: {stlink.get_version()}")
        print(f"✓ Voltage: {stlink.get_target_voltage():.2f}V")
        
        # Read FLASH_OPTCR register
        optcr = stlink.get_mem32(FLASH_OPTCR)
        rdp_byte = (optcr >> 8) & 0xFF
        
        print(f"\nFLASH_OPTCR: 0x{optcr:08X}")
        print(f"RDP Byte: 0x{rdp_byte:02X}")
        print("-" * 30)
        
        # Check RDP level
        if rdp_byte == 0xAA:
            print("✅ Level 0 - No protection")
        elif rdp_byte == 0xCC:
            print("🔒 Level 2 - PERMANENT lock")
        else:
            print("⚠️  Level 1 - Read protected")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\nPossible reasons:")
        print("- Device is locked (RDP Level 2)")
        print("- Connection issue")
        print("- No power to target")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())