#!/usr/bin/env python3
"""Test script to read memory from 0x08008000 using SimpleSerial protocol"""

import chipwhisperer as cw
import time

# Configuration
TARGET_ADDRESS = 0x08008000
READ_LENGTH = 4  # Try to read 4 bytes

def test_memory_read():
    """Test memory read and display any errors"""
    
    print(f"Testing memory read from address 0x{TARGET_ADDRESS:08X}")
    print("=" * 50)
    
    scope = None
    target = None
    
    try:
        # Connect to ChipWhisperer
        print("Connecting to ChipWhisperer...")
        scope = cw.scope()
        target = cw.target(scope)
        
        print(f"Scope: {scope}")
        print(f"Target: {target}")
        print()
        
        # List available methods on target
        print("Available methods on target object:")
        methods = [m for m in dir(target) if not m.startswith('_')]
        for method in sorted(methods):
            if 'read' in method.lower() or 'mem' in method.lower():
                print(f"  - {method}")
        print()
        
        # Try different approaches to read memory
        print(f"Attempting to read {READ_LENGTH} bytes from 0x{TARGET_ADDRESS:08X}...")
        print()
        
        # Method 1: Try using simpleserial_write with 'r' command (common for memory read)
        try:
            print("Method 1: Using SimpleSerial 'r' command...")
            # Format: r<address><length>
            addr_bytes = TARGET_ADDRESS.to_bytes(4, byteorder='little')
            len_bytes = READ_LENGTH.to_bytes(1, byteorder='little')
            
            target.simpleserial_write('r', addr_bytes + len_bytes)
            time.sleep(0.1)
            response = target.simpleserial_read('r', READ_LENGTH, timeout=1)
            
            if response:
                print(f"Success! Data read: {response.hex()}")
                print(f"Raw bytes: {list(response)}")
            else:
                print("No response received")
        except Exception as e:
            print(f"Method 1 failed: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
        
        print()
        
        # Method 2: Try raw serial communication
        try:
            print("Method 2: Using raw serial communication...")
            # Send a memory read command in SimpleSerial format
            cmd = f"r{TARGET_ADDRESS:08x}{READ_LENGTH:02x}\n"
            print(f"Sending command: {cmd.strip()}")
            
            target.flush()
            target.write(cmd.encode())
            time.sleep(0.1)
            
            # Read response
            response = target.read(timeout=1)
            if response:
                print(f"Raw response: {response}")
                print(f"Response hex: {response.hex()}")
            else:
                print("No response received")
        except Exception as e:
            print(f"Method 2 failed: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
    
    except Exception as main_error:
        print(f"Failed to connect or initialize: {main_error}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Clean up
        if target:
            target.dis()
        if scope:
            scope.dis()
        print()
        print("Disconnected from ChipWhisperer")

if __name__ == "__main__":
    test_memory_read()