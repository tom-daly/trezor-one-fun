#!/usr/bin/env python3

import sys
from trezorlib import client, transport, device
from trezorlib.client import TrezorClient
from trezorlib.tools import parse_path

def check_trezor_firmware():
    try:
        print("Searching for Trezor devices...")
        
        # Find all connected Trezor devices
        devices = transport.enumerate_devices()
        
        if not devices:
            print("No Trezor devices found. Please connect your device.")
            return False
        
        print(f"Found {len(devices)} device(s)")
        
        # Connect to the first device
        transport_obj = devices[0]
        print(f"\nConnecting to: {transport_obj}")
        
        # Create client
        client = TrezorClient(transport_obj)
        
        # Get device features/information
        features = client.features
        
        print("\n=== Trezor Device Information ===")
        print(f"Vendor: {features.vendor}")
        print(f"Model: {features.model}")
        print(f"Device ID: {features.device_id}")
        print(f"Label: {features.label if features.label else 'Not set'}")
        
        print("\n=== Firmware Information ===")
        print(f"Firmware Version: {features.major_version}.{features.minor_version}.{features.patch_version}")
        print(f"Bootloader Mode: {features.bootloader_mode}")
        print(f"Firmware Present: {features.firmware_present}")
        
        if hasattr(features, 'fw_vendor'):
            print(f"Firmware Vendor: {features.fw_vendor}")
        if hasattr(features, 'fw_vendor_keys'):
            print(f"Firmware Vendor Keys: {features.fw_vendor_keys}")
        
        print("\n=== Security Features ===")
        print(f"PIN Protection: {features.pin_protection}")
        print(f"Passphrase Protection: {features.passphrase_protection}")
        print(f"Initialized: {features.initialized}")
        print(f"Needs Backup: {features.needs_backup if hasattr(features, 'needs_backup') else 'N/A'}")
        print(f"Unfinished Backup: {features.unfinished_backup if hasattr(features, 'unfinished_backup') else 'N/A'}")
        
        if hasattr(features, 'capabilities'):
            print(f"\nDevice Capabilities: {features.capabilities}")
        
        # Close the connection
        client.close()
        
        print("\n✅ Successfully connected and retrieved firmware information")
        return True
        
    except Exception as e:
        print(f"\n❌ Error connecting to Trezor: {e}")
        print("\nTroubleshooting:")
        print("1. Make sure your Trezor is connected via USB")
        print("2. Check if you have the necessary permissions (may need sudo or udev rules)")
        print("3. Ensure the device is unlocked (enter PIN if required)")
        print("4. Make sure no other application is using the device")
        return False

if __name__ == "__main__":
    print("Trezor Firmware Check Tool")
    print("=" * 40)
    
    success = check_trezor_firmware()
    sys.exit(0 if success else 1)