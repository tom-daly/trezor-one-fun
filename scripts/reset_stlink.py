#!/usr/bin/env python3
"""
Reset ST-Link USB device
"""

import subprocess
import re
import sys

def find_stlink():
    """Find ST-Link device in lsusb output"""
    try:
        result = subprocess.run(['lsusb'], capture_output=True, text=True)
        
        # ST-Link V2 vendor:product IDs
        stlink_ids = [
            '0483:3748',  # ST-Link V2
            '0483:374b',  # ST-Link V2.1
            '0483:3752',  # ST-Link V3
        ]
        
        for line in result.stdout.split('\n'):
            for vid_pid in stlink_ids:
                if vid_pid in line:
                    # Extract bus and device numbers
                    match = re.match(r'Bus (\d+) Device (\d+):', line)
                    if match:
                        bus = match.group(1).zfill(3)
                        device = match.group(2).zfill(3)
                        return bus, device, line.strip()
        
        return None, None, None
    except Exception as e:
        print(f"Error finding ST-Link: {e}")
        return None, None, None

def reset_usb_device(bus, device):
    """Reset USB device by unbinding and rebinding the driver"""
    try:
        import time
        import os
        import glob
        
        # Convert bus and device to integers (remove leading zeros)
        bus_int = int(bus)
        dev_int = int(device)
        
        print(f"Looking for ST-Link at Bus {bus_int} Device {dev_int}")
        
        # Method 1: Try using unbind/bind on the USB driver
        # Find the device in sysfs by vendor:product ID
        stlink_patterns = [
            '/sys/bus/usb/devices/*/idVendor',
        ]
        
        for vendor_file in glob.glob('/sys/bus/usb/devices/*/idVendor'):
            try:
                with open(vendor_file, 'r') as f:
                    vendor = f.read().strip()
                
                if vendor == '0483':  # STMicroelectronics
                    device_dir = os.path.dirname(vendor_file)
                    product_file = os.path.join(device_dir, 'idProduct')
                    
                    with open(product_file, 'r') as f:
                        product = f.read().strip()
                    
                    if product in ['3748', '374b', '3752']:  # ST-Link products
                        # Found ST-Link, reset it
                        print(f"Found ST-Link at {device_dir}")
                        
                        # Try authorize method
                        auth_file = os.path.join(device_dir, 'authorized')
                        if os.path.exists(auth_file):
                            print("Resetting via authorize...")
                            try:
                                with open(auth_file, 'w') as f:
                                    f.write('0')
                                time.sleep(0.5)
                                with open(auth_file, 'w') as f:
                                    f.write('1')
                                print("✅ ST-Link reset successfully")
                                return True
                            except PermissionError:
                                print("❌ Permission denied. Run with sudo.")
                                return False
                        
                        # Try remove/rescan method
                        remove_file = os.path.join(device_dir, 'remove')
                        if os.path.exists(remove_file):
                            print("Resetting via remove...")
                            with open(remove_file, 'w') as f:
                                f.write('1')
                            time.sleep(0.5)
                            # Rescan USB bus
                            rescan_file = '/sys/bus/usb/drivers/usb/bind'
                            device_name = os.path.basename(device_dir)
                            with open(rescan_file, 'w') as f:
                                f.write(device_name)
                            print("✅ ST-Link reset successfully")
                            return True
                            
            except Exception as e:
                continue
        
        print("❌ Could not find ST-Link in sysfs")
        return False
        
    except PermissionError:
        print("❌ Permission denied. Run with sudo.")
        return False
    except Exception as e:
        print(f"❌ Reset failed: {e}")
        return False

def reset_using_usbreset(bus, device):
    """Alternative method using usbreset command"""
    try:
        # Try using usbreset command (if available)
        device_path = f"/dev/bus/usb/{bus}/{device}"
        result = subprocess.run(['sudo', 'usbreset', device_path], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ ST-Link reset successfully using usbreset")
            return True
        else:
            print(f"❌ usbreset failed: {result.stderr}")
            return False
    except FileNotFoundError:
        print("usbreset command not found")
        return False
    except Exception as e:
        print(f"❌ Reset failed: {e}")
        return False

def main():
    # Find ST-Link
    bus, device, info = find_stlink()
    
    if not bus:
        print("❌ No ST-Link device found")
        print("Make sure ST-Link is connected")
        return 1
    
    print(f"Found: {info}")
    
    # Try reset using /sys method first
    if reset_usb_device(bus, device):
        return 0  # Success, exit
    
    # If failed, try usbreset command
    print("Trying alternative method...")
    if reset_using_usbreset(bus, device):
        return 0
    
    return 1  # All methods failed

if __name__ == "__main__":
    sys.exit(main())