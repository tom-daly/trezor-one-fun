#!/usr/bin/env python3
"""
SWD memory read with glitch - tries to bypass RDP
"""

from swd import Swd
import chipwhisperer as cw

# Connect to ChipWhisperer
print("Setting up ChipWhisperer...")
scope = cw.scope()

# Configure glitch
scope.clock.clkgen_freq = 100E6
scope.glitch.clk_src = "clkgen"
scope.glitch.output = "enable_only"
scope.glitch.trigger_src = "manual"
scope.io.glitch_lp = True
scope.io.glitch_hp = True
scope.glitch.width = 40
scope.glitch.offset = -45
scope.glitch.ext_offset = 0
scope.glitch.repeat = 20

print("Glitch configured")

# Test glitch
print("Testing glitch...")
scope.glitch.manual_trigger()
input("Did you see the glitch? Press Enter to continue...")

# Connect to target via SWD
print("\nConnecting via SWD...")
swd = Swd()

# Try to read 512 bytes from flash with glitch
address = 0x08000000
size = 512

print(f"Attempting to read {size} bytes from 0x{address:08X} with glitch")

for attempt in range(5):
    print(f"\nAttempt {attempt + 1}/5")
    
    try:
        # Trigger glitch just before read
        
        
        # Try to read immediately
        data = bytes(swd.read_mem(address, size))
        scope.glitch.manual_trigger()
        
        print(f"SUCCESS! Read {len(data)} bytes")
        
        # Save to file
        with open("glitch_read.bin", "wb") as f:
            f.write(data)
        print("Saved to glitch_read.bin")
        
        # Show first 16 bytes
        print("First 16 bytes:")
        for i in range(min(16, len(data))):
            print(f"{data[i]:02X} ", end="")
        print()
        break
        
    except Exception as e:
        print(f"Failed: {e}")
        input("Press Enter to try again...")

print("\nDone")