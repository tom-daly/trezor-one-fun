#!/usr/bin/env python3
"""
STM32F205 Option Bytes Reader
Reads and decodes all option bytes including RDP, BOR, WDG, and PCROP.
Enhanced to detect PCROP (SPRMOD bit) which causes zero reads during glitching.
"""

import sys
import csv
from datetime import datetime
from swd.stlink import Stlink

# STM32F205 Option Bytes Registers
FLASH_OPTCR = 0x40023C14  # Option control register
FLASH_OPTCR1 = 0x40023C18  # Option control register 1

def decode_optcr(optcr):
    """Decode FLASH_OPTCR register"""
    print(f"\nFLASH_OPTCR: 0x{optcr:08X}")
    print("=" * 40)

    # CRITICAL: Check SPRMOD bit (bit 31) for PCROP
    sprmod = (optcr >> 31) & 0x1
    print(f"\n{'='*50}")
    print(f"🔴 PCROP Status Check (SPRMOD bit 31):")
    if sprmod:
        print(f"  ⚠️  PCROP IS ACTIVE! - Proprietary Code Read Protection enabled")
        print(f"  ⚠️  This causes all memory reads to return ZEROS!")
        print(f"  ⚠️  Even if RDP is bypassed, reads will fail!")
    else:
        print(f"  ✅ PCROP is inactive - Normal read access possible")
    print(f"{'='*50}\n")

    # Extract fields
    rdp = (optcr >> 8) & 0xFF
    nwrp = (optcr >> 16) & 0xFFF
    user = optcr & 0xFF
    
    # RDP Level
    print(f"RDP (Read Protection):")
    print(f"  Raw value: 0x{rdp:02X}")
    if rdp == 0xAA:
        print(f"  Level: 0 - No protection")
    elif rdp == 0xCC:
        print(f"  Level: 2 - PERMANENT protection")
    else:
        print(f"  Level: 1 - Read protection active")
    
    # Write Protection
    print(f"\nnWRP (Write Protection):")
    print(f"  Raw value: 0x{nwrp:03X}")
    if nwrp == 0xFFF:
        print(f"  Status: No sectors write protected")
    else:
        print(f"  Status: Some sectors are write protected")
        for i in range(12):
            if not (nwrp & (1 << i)):
                print(f"    Sector {i}: Write Protected")
    
    # User Options
    print(f"\nUser Options: 0x{user:02X}")
    
    # BOR Level
    bor_level = (user >> 2) & 0x3
    bor_settings = {
        0b11: "Level 0: Reset threshold 1.8V",
        0b10: "Level 1: Reset threshold 2.1V", 
        0b01: "Level 2: Reset threshold 2.4V",
        0b00: "Level 3: Reset threshold 2.7V"
    }
    print(f"  BOR_LEV: {bor_settings.get(bor_level, 'Unknown')}")
    
    # Reset options
    print(f"  nRST_STDBY: {'1 (No reset when entering Standby)' if user & 0x80 else '0 (Reset when entering Standby)'}")
    print(f"  nRST_STOP:  {'1 (No reset when entering Stop)' if user & 0x40 else '0 (Reset when entering Stop)'}")
    
    # Watchdog
    print(f"  WDG_SW:     {'1 (Software watchdog)' if user & 0x20 else '0 (Hardware watchdog)'}")
    
    # FLASH_OPTCR lock
    lock = (optcr >> 0) & 0x1
    optstart = (optcr >> 1) & 0x1
    print(f"\nControl bits:")
    print(f"  OPTLOCK: {'1 (Locked)' if lock else '0 (Unlocked)'}")
    print(f"  OPTSTRT: {'1' if optstart else '0'}")

    # Show all bits for debugging
    print(f"\nBit breakdown of OPTCR:")
    print(f"  Bit 31 (SPRMOD/PCROP): {sprmod}")
    print(f"  Bits 16-27 (nWRP):     0x{nwrp:03X}")
    print(f"  Bits 8-15 (RDP):       0x{rdp:02X}")
    print(f"  Bits 0-7 (USER):       0x{user:02X}")

def log_pcrop_status(optcr, rdp, pcrop_active):
    """Log PCROP and option byte status to CSV file"""
    log_file = 'pcrop_log.csv'

    # Create header if file doesn't exist
    try:
        with open(log_file, 'r'):
            pass
    except FileNotFoundError:
        with open(log_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Timestamp', 'OPTCR_Hex', 'RDP_Level', 'PCROP_Active', 'SPRMOD_Bit'])

    # Append current status
    with open(log_file, 'a', newline='') as f:
        writer = csv.writer(f)
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        rdp_val = (optcr >> 8) & 0xFF
        rdp_level = 0 if rdp_val == 0xAA else (2 if rdp_val == 0xCC else 1)
        sprmod = (optcr >> 31) & 0x1

        writer.writerow([timestamp, f'0x{optcr:08X}', rdp_level, pcrop_active, sprmod])

    print(f"\n📝 Status logged to {log_file}")

def quick_pcrop_check():
    """Quick function to just check PCROP status - useful during glitching"""
    try:
        stlink = Stlink(swd_frequency=1800000)
        optcr = stlink.get_mem32(FLASH_OPTCR)
        sprmod = (optcr >> 31) & 0x1
        rdp = (optcr >> 8) & 0xFF

        if sprmod:
            print(f"🚫 PCROP ACTIVE! OPTCR=0x{optcr:08X}")
            return True
        else:
            print(f"✅ PCROP inactive. OPTCR=0x{optcr:08X}")
            return False
    except Exception as e:
        print(f"Error checking PCROP: {e}")
        return None

def main():
    """Read and decode option bytes"""
    print("STM32F205 Option Bytes Reader")
    print("=" * 40)
    
    try:
        # Connect to target
        print("\n[*] Connecting to ST-Link...")
        stlink = Stlink(swd_frequency=1800000)
        
        version = stlink.get_version()
        voltage = stlink.get_target_voltage()
        print(f"[+] Connected: {version}")
        print(f"[+] Voltage: {voltage:.2f}V")
        
        # Read FLASH_OPTCR
        optcr = stlink.get_mem32(FLASH_OPTCR)
        decode_optcr(optcr)

        # Log PCROP status
        sprmod = (optcr >> 31) & 0x1
        rdp = (optcr >> 8) & 0xFF
        log_pcrop_status(optcr, rdp, sprmod == 1)
        
        # Try to read FLASH_OPTCR1 (might not be accessible)
        try:
            optcr1 = stlink.get_mem32(FLASH_OPTCR1)
            print(f"\nFLASH_OPTCR1: 0x{optcr1:08X}")
            nwrp1 = (optcr1 >> 16) & 0xFFF
            if nwrp1 != 0xFFF:
                print(f"  Extended write protection active: 0x{nwrp1:03X}")
        except:
            print("\n[!] Could not read FLASH_OPTCR1")
        
        # Try to read actual option bytes from flash
        print("\n" + "=" * 40)
        print("Trying to read option bytes from flash...")
        try:
            # STM32F2 option bytes at 0x1FFFC000
            opt_addr = 0x1FFFC000
            opt_data = []
            for offset in range(0, 16, 4):
                val = stlink.get_mem32(opt_addr + offset)
                opt_data.append(val)
                print(f"  0x{opt_addr + offset:08X}: 0x{val:08X}")
        except Exception as e:
            print(f"  Could not read from flash: {e}")
        
        # Read some other interesting registers
        print("\n" + "=" * 40)
        print("Other security-related registers:")
        
        # Device ID
        try:
            dbgmcu_idcode = stlink.get_mem32(0xE0042000)
            dev_id = dbgmcu_idcode & 0xFFF
            rev_id = (dbgmcu_idcode >> 16) & 0xFFFF
            print(f"\nDBGMCU_IDCODE: 0x{dbgmcu_idcode:08X}")
            print(f"  Device ID: 0x{dev_id:03X}")
            print(f"  Revision: 0x{rev_id:04X}")
        except:
            pass
        
        # Flash size
        try:
            flash_size_addr = 0x1FFF7A22
            flash_size_raw = stlink.get_mem32(flash_size_addr & 0xFFFFFFFC)
            flash_size = (flash_size_raw >> ((flash_size_addr & 0x3) * 8)) & 0xFFFF
            print(f"\nFlash size: {flash_size} KB")
        except:
            pass
        
        # Unique device ID (96 bits)
        try:
            print("\nUnique Device ID (96-bit):")
            uid1 = stlink.get_mem32(0x1FFF7A10)
            uid2 = stlink.get_mem32(0x1FFF7A14)
            uid3 = stlink.get_mem32(0x1FFF7A18)
            print(f"  UID: {uid3:08X}-{uid2:08X}-{uid1:08X}")
        except:
            pass
            
    except Exception as e:
        print(f"\n[-] Error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    # Check if quick PCROP check is requested
    if len(sys.argv) > 1 and sys.argv[1] == '--quick':
        quick_pcrop_check()
    else:
        sys.exit(main())