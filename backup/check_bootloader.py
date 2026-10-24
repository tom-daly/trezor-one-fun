#!/usr/bin/env python3
"""
Check if STM32 is in bootloader mode via SWD
The bootloader executes from system memory (0x1FFF0000 region)
"""

from swd import Swd
import sys

def check_bootloader_via_swd():
    """Check if bootloader is active by reading PC and checking memory region"""
    try:
        swd = Swd()

        # Read Program Counter to see where code is executing
        # PC is register 15 in ARM Cortex-M
        pc = swd.get_reg(15)
        print(f"Program Counter (PC): 0x{pc:08X}")

        # Bootloader runs from system memory: 0x1FFF0000 - 0x1FFF77FF
        if 0x1FFF0000 <= pc <= 0x1FFF77FF:
            print("✅ BOOTLOADER ACTIVE - PC is in system memory region!")
            return True
        elif 0x08000000 <= pc <= 0x08100000:
            print("❌ Application running - PC is in flash region")
            return False
        elif 0x20000000 <= pc <= 0x20020000:
            print("⚠️  PC is in RAM region - unusual state")
            return False
        else:
            print(f"⚠️  PC in unexpected region: 0x{pc:08X}")
            return False

    except Exception as e:
        print(f"❌ SWD read failed: {e}")
        print("   This might mean RDP is active or SWD is disabled")
        return None

def check_bootloader_via_memory():
    """Alternative: Check by reading from known bootloader addresses"""
    try:
        swd = Swd()

        # Try reading from bootloader region (system memory)
        # 0x1FFF0000 should contain the bootloader stack pointer
        bootloader_sp = swd.read_mem32(0x1FFF0000)
        print(f"Bootloader region (0x1FFF0000): 0x{bootloader_sp:08X}")

        # Stack pointer should be in RAM region (0x20000000+)
        if 0x20000000 <= bootloader_sp <= 0x20020000:
            print("✅ Valid bootloader stack pointer found")

            # Try reading the reset vector
            reset_vector = swd.read_mem32(0x1FFF0004)
            print(f"Bootloader reset vector: 0x{reset_vector:08X}")

            if 0x1FFF0000 <= reset_vector <= 0x1FFF77FF:
                print("✅ Valid bootloader reset vector")
                return True

        # Also check where the current code is executing from
        # Read Vector Table Offset Register (VTOR)
        vtor = swd.read_mem32(0xE000ED08)
        print(f"VTOR (Vector Table): 0x{vtor:08X}")

        if vtor >= 0x1FFF0000 and vtor < 0x1FFF8000:
            print("✅ BOOTLOADER ACTIVE - Vector table in system memory!")
            return True
        elif vtor >= 0x08000000 and vtor < 0x08100000:
            print("❌ Application active - Vector table in flash")
            return False

    except Exception as e:
        print(f"❌ Memory read failed: {e}")
        return None

def check_boot_pins():
    """Check BOOT0 pin state if possible"""
    print("\n📌 BOOT0 Pin Check:")
    print("   BOOT0 = HIGH (1) -> Bootloader mode")
    print("   BOOT0 = LOW  (0) -> Normal flash boot")
    print("   (Physical check required - cannot read via SWD)")

if __name__ == "__main__":
    print("="*60)
    print("STM32 Bootloader Detection")
    print("="*60)

    print("\n[1] Checking via Program Counter...")
    pc_check = check_bootloader_via_swd()

    print("\n[2] Checking via Memory Regions...")
    mem_check = check_bootloader_via_memory()

    check_boot_pins()

    print("\n" + "="*60)
    if pc_check or mem_check:
        print("🎉 BOOTLOADER IS ACTIVE")
        print("   Ready for UART commands on USART1/USART3")
    else:
        print("❌ BOOTLOADER NOT DETECTED")
        print("   - Check BOOT0 pin is HIGH")
        print("   - Reset device while BOOT0 is HIGH")
        print("   - Or use 'Jump to Bootloader' from application")
    print("="*60)