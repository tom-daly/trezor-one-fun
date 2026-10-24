#!/usr/bin/env python3
"""
Direct SRAM dumper for STM32F205 using pyswd
No OpenOCD or GDB required - uses ST-Link directly
"""

import sys
import time
from swd.stlink import Stlink

# STM32F205 SRAM configuration
SRAM_START = 0x20000000
SRAM_SIZE = 0x20000  # 128KB (131072 bytes)
CHUNK_SIZE = 1024    # Max transfer size for read_mem32

def dump_sram(output_file="sram_direct.bin", show_progress=True, start_addr=None, size=None):
    """
    Dump STM32F205 SRAM directly via SWD
    
    Args:
        output_file: Where to save the dump
        show_progress: Show progress bar
        start_addr: Override start address
        size: Override size
    
    Returns:
        True if successful, False otherwise
    """
    # Use provided values or defaults
    sram_start = start_addr if start_addr is not None else SRAM_START
    sram_size = size if size is not None else SRAM_SIZE
    print("STM32F205 Direct SRAM Dumper")
    print("=" * 40)
    
    try:
        # Connect to target
        print("[*] Connecting to ST-Link...")
        stlink = Stlink(swd_frequency=1800000)
        
        # Get version and voltage
        version = stlink.get_version()
        voltage = stlink.get_target_voltage()
        print(f"[+] Connected: {version}")
        print(f"[+] Target voltage: {voltage:.2f}V")
        
        if voltage < 1.5:
            print("[-] Warning: Target voltage too low!")
            return False
        
        # Try to halt the target (may fail if protected)
        try:
            # Read DHCSR to check if we can halt
            DHCSR = 0xE000EDF0
            dhcsr_val = stlink.get_mem32(DHCSR)
            print(f"[*] DHCSR: 0x{dhcsr_val:08X}")
            
            # Try to halt
            DHCSR_HALT = 0xA05F0003
            stlink.set_mem32(DHCSR, DHCSR_HALT)
            time.sleep(0.1)
            
            # Check if halted
            dhcsr_val = stlink.get_mem32(DHCSR)
            if dhcsr_val & 0x00020000:  # S_HALT bit
                print("[+] Target halted")
            else:
                print("[!] Could not halt target (may still work)")
        except Exception as e:
            print(f"[!] Could not halt target: {e}")
            print("    Continuing anyway...")
        
        # Start dumping SRAM
        print(f"\n[*] Dumping {sram_size} bytes from 0x{sram_start:08X}")
        print(f"[*] Reading in {CHUNK_SIZE}-byte chunks...")
        
        data = bytearray()
        start_time = time.time()
        
        # Read SRAM in chunks
        for offset in range(0, sram_size, CHUNK_SIZE):
            try:
                # Calculate chunk size (last chunk might be smaller)
                current_chunk_size = min(CHUNK_SIZE, sram_size - offset)
                address = sram_start + offset
                
                # Read chunk (read_mem32 returns bytes)
                chunk = stlink.read_mem32(address, current_chunk_size)
                data.extend(chunk)
                
                # Show progress
                if show_progress:
                    progress = (offset + current_chunk_size) / sram_size * 100
                    bytes_read = offset + current_chunk_size
                    print(f"\r[*] Progress: {progress:5.1f}% ({bytes_read:6d}/{sram_size} bytes)", end="")
                    
            except Exception as e:
                print(f"\n[-] Error reading at 0x{address:08X}: {e}")
                print(f"    Read {len(data)} bytes before error")
                break
        
        print()  # New line after progress
        
        # Calculate dump time
        dump_time = time.time() - start_time
        print(f"[+] Read {len(data)} bytes in {dump_time:.2f} seconds")
        
        # Save to file
        print(f"[*] Saving to {output_file}...")
        with open(output_file, "wb") as f:
            f.write(data)
        
        # Verify
        if len(data) == sram_size:
            print(f"[+] Success! Full SRAM dumped to {output_file}")
            print(f"[+] Dump rate: {len(data)/dump_time/1024:.1f} KB/s")
            
            # Ask if user wants to view the file
            print("\n" + "="*40)
            try:
                response = input("View hexdump? (y/n or bytes count, e.g. '4096'): ").strip().lower()
                
                if response == 'n':
                    pass  # Skip
                else:
                    import subprocess
                    # Determine how many bytes to show
                    if response == 'y':
                        bytes_to_show = 4096  # Default to 4KB instead of 512
                    elif response.isdigit():
                        bytes_to_show = min(int(response), len(data))
                    elif response == 'all':
                        bytes_to_show = len(data)
                    else:
                        bytes_to_show = 4096  # Default
                    
                    print(f"\nShowing first {bytes_to_show} bytes of {len(data)} total:")
                    print("-" * 40)
                    subprocess.run(["hexdump", "-C", output_file, "-n", str(bytes_to_show)])
                    print("-" * 40)
                    
                    # Always run strings to find interesting data
                    print("\nSearching for strings (min 8 chars)...")
                    print("-" * 40)
                    result = subprocess.run(["strings", "-n", "8", output_file], 
                                          capture_output=True, text=True)
                    strings_found = result.stdout.strip()
                    if strings_found:
                        lines = strings_found.split('\n')
                        print(f"Found {len(lines)} strings. First 50:")
                        for line in lines[:50]:
                            print(f"  {line}")
                        if len(lines) > 50:
                            print(f"  ... and {len(lines)-50} more")
                    else:
                        print("  No strings found (dump may be empty or encrypted)")
                    print("-" * 40)
            except KeyboardInterrupt:
                print("\nSkipping hexdump")
            except Exception as e:
                print(f"Could not show hexdump: {e}")
            
            return True
        else:
            print(f"[!] Warning: Expected {sram_size} bytes but got {len(data)}")
            print(f"[!] Partial dump saved to {output_file}")
            return False
            
    except Exception as e:
        print(f"\n[-] Error: {e}")
        print("\nTroubleshooting:")
        print("  1. Check ST-Link connection")
        print("  2. Verify target is powered")
        print("  3. Ensure glitch was successful (SWD access enabled)")
        return False

def main():
    """Main function with argument parsing"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Direct SRAM dumper for STM32F205")
    parser.add_argument("-o", "--output", default="sram_direct.bin",
                       help="Output file (default: sram_direct.bin)")
    parser.add_argument("-s", "--start", type=lambda x: int(x, 0), 
                       default=SRAM_START,
                       help=f"Start address (default: 0x{SRAM_START:08X})")
    parser.add_argument("-l", "--length", type=lambda x: int(x, 0),
                       default=SRAM_SIZE,
                       help=f"Length in bytes (default: {SRAM_SIZE})")
    parser.add_argument("-q", "--quiet", action="store_true",
                       help="Don't show progress")
    
    args = parser.parse_args()
    
    # Run dump with custom parameters
    success = dump_sram(
        output_file=args.output, 
        show_progress=not args.quiet,
        start_addr=args.start,
        size=args.length
    )
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())