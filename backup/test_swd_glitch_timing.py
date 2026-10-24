#!/usr/bin/env python3
"""
Different approaches to trigger glitch during SWD read
"""

from swd import Swd
import chipwhisperer as cw
import threading
import time

# Setup ChipWhisperer
print("Setting up ChipWhisperer...")
scope = cw.scope()
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

# Connect via SWD
print("Connecting via SWD...")
swd = Swd()

address = 0x08000000
size = 512

print("\n=== APPROACH 1: Glitch in separate thread ===")
def glitch_thread():
    """Trigger glitch after tiny delay"""
    time.sleep(0.000001)  # 1 microsecond delay
    scope.glitch.manual_trigger()
    print("  Glitch triggered from thread")

try:
    # Start glitch thread
    t = threading.Thread(target=glitch_thread)
    t.start()
    
    # Start read immediately
    print("  Starting read...")
    data = bytes(swd.read_mem(address, size))
    t.join()
    print(f"  Success: {len(data)} bytes")
except Exception as e:
    print(f"  Failed: {e}")

input("\nPress Enter for approach 2...")

print("\n=== APPROACH 2: Start read as generator, glitch, then consume ===")
try:
    # Start the read operation (returns generator, doesn't block yet)
    gen = swd.read_mem(address, size)
    
    # Trigger glitch immediately
    scope.glitch.manual_trigger()
    print("  Glitch triggered")
    
    # Now consume the generator (this is when actual read happens)
    data = bytes(gen)
    print(f"  Success: {len(data)} bytes")
except Exception as e:
    print(f"  Failed: {e}")

input("\nPress Enter for approach 3...")

print("\n=== APPROACH 3: Glitch during first byte read ===")
try:
    result = []
    gen = swd.read_mem(address, size)
    
    # Read first byte and trigger glitch
    first_byte = next(gen)
    scope.glitch.manual_trigger()  # Glitch while reading rest
    result.append(first_byte)
    
    # Read remaining bytes
    result.extend(list(gen))
    data = bytes(result)
    print(f"  Success: {len(data)} bytes")
except Exception as e:
    print(f"  Failed: {e}")

input("\nPress Enter for approach 4...")

print("\n=== APPROACH 4: Pre-arm glitch with ext_single trigger ===")
# Reconfigure for external trigger
scope.glitch.trigger_src = "ext_single"
scope.arm()
print("  Glitch armed")

try:
    # Generate trigger signal somehow during read
    # This would need hardware trigger from SWD activity
    data = bytes(swd.read_mem(address, size))
    print(f"  Success: {len(data)} bytes")
except Exception as e:
    print(f"  Failed: {e}")

print("\nDone testing")