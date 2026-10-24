#!/usr/bin/env python3
"""
Boot Mode Detection Script
Checks if the device is in a state where SWD access is available,
indicating successful boot mode bypass.
"""

import os
import time
import sys
from datetime import datetime

def check_swd_access():
    """
    Check if SWD access is available to the target device.
    Returns the SWD version string if successful, None otherwise.
    """
    try:
        import swd
        
        # Reset STLink adapter
        reset_cmd = "/home/tdaly/.cwvenv/usb_reset"
        print("🔄 Resetting USB STLink adapter...")
        os.system(f"{reset_cmd} > /dev/null 2>&1")
        time.sleep(0.5)  # Give device time to reinitialize
        
        # Attempt SWD connection
        print("🔍 Attempting SWD connection...")
        dev = swd.Swd()
        version = dev.get_version().str
        
        # If we get here, SWD access was successful
        return version
        
    except Exception as e:
        # SWD access failed - this is expected in normal boot mode
        return None
    finally:
        # Clean up
        try:
            del swd
        except:
            pass

def continuous_check(interval=1.0):
    """
    Continuously check for boot mode at specified interval.
    """
    print("\n" + "="*60)
    print("🎯 BOOT MODE DETECTION - CONTINUOUS MONITORING")
    print("="*60)
    print(f"Checking every {interval} seconds...")
    print("Press Ctrl+C to stop\n")
    
    check_count = 0
    start_time = datetime.now()
    
    try:
        while True:
            check_count += 1
            timestamp = datetime.now().strftime("%H:%M:%S")
            
            # Check SWD access
            version = check_swd_access()
            
            if version:
                # SUCCESS - Boot mode bypassed!
                print("\n" + "🎉"*30)
                print(f"[{timestamp}] 💥 SUCCESS! BOOT MODE BYPASSED!")
                print(f"   SWD Version: {version}")
                print(f"   Check #{check_count}")
                print(f"   Time elapsed: {datetime.now() - start_time}")
                print("🎉"*30 + "\n")
                
                # Optional: Sound alert
                os.system("espeak 'Boot mode bypass successful!' 2>/dev/null &")
                
                return True
            else:
                # Normal boot mode - no SWD access
                print(f"[{timestamp}] Check #{check_count}: ❌ Normal boot mode (no SWD access)")
            
            time.sleep(interval)
            
    except KeyboardInterrupt:
        print("\n\n⏹️  Monitoring stopped by user")
        print(f"   Total checks: {check_count}")
        print(f"   Time elapsed: {datetime.now() - start_time}")
        return False

def single_check():
    """
    Perform a single boot mode check.
    """
    print("\n" + "="*60)
    print("🎯 BOOT MODE DETECTION - SINGLE CHECK")
    print("="*60)
    
    version = check_swd_access()
    
    if version:
        print("\n✅ Boot mode BYPASSED - SWD access available!")
        print(f"   SWD Version: {version}")
        return True
    else:
        print("\n❌ Normal boot mode - No SWD access")
        print("   Device is operating normally with security enabled")
        return False

def main():
    """
    Main function - parse arguments and run appropriate check.
    """
    print("\n🔧 Boot Mode Detection Tool")
    print("   Checks if SWD debug access is available\n")
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "--continuous" or sys.argv[1] == "-c":
            # Continuous monitoring mode
            interval = float(sys.argv[2]) if len(sys.argv) > 2 else 1.0
            continuous_check(interval)
        elif sys.argv[1] == "--help" or sys.argv[1] == "-h":
            print("Usage:")
            print("  python3 detect_boot_mode.py           # Single check")
            print("  python3 detect_boot_mode.py -c        # Continuous monitoring (1s interval)")
            print("  python3 detect_boot_mode.py -c 0.5    # Continuous monitoring (0.5s interval)")
        else:
            print(f"Unknown option: {sys.argv[1]}")
            print("Use --help for usage information")
    else:
        # Default: single check
        single_check()
    
    print("\n" + "="*60 + "\n")

if __name__ == "__main__":
    main()