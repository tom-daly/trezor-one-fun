#!/usr/bin/env python3
"""Test script to read memory from 0x08008000 and show raw error"""

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
        
        # Try to read memory
        print(f"Attempting to read {READ_LENGTH} bytes from 0x{TARGET_ADDRESS:08X}...")
        print()
        
        try:
            data = target.read_mem(TARGET_ADDRESS, READ_LENGTH)
            print(f"Success! Data read: {data.hex()}")
            print(f"Raw bytes: {list(data)}")
        except Exception as e:
            print("ERROR occurred during memory read:")
            print(f"Exception type: {type(e).__name__}")
            print(f"Error message: {str(e)}")
            print()
            print("Full exception details:")
            import traceback
            traceback.print_exc()
            
            # Try to get more details if available
            if hasattr(e, '__dict__'):
                print()
                print("Exception attributes:")
                for key, value in e.__dict__.items():
                    print(f"  {key}: {value}")
    
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