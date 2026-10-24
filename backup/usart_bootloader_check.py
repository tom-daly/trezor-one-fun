#!/usr/bin/env python3
"""
Check if STM32 is in bootloader mode via USART
"""

import serial
import sys
import time

def check_bootloader_mode(port, baudrate, parity):
    """Check if device is in bootloader mode"""

    parity_map = {
        'E': serial.PARITY_EVEN,
        'N': serial.PARITY_NONE,
        'O': serial.PARITY_ODD
    }

    try:
        ser = serial.Serial(
            port=port,
            baudrate=baudrate,
            bytesize=8,
            parity=parity_map.get(parity, serial.PARITY_EVEN),
            stopbits=1,
            timeout=0.5
        )

        # Clear any pending data
        ser.reset_input_buffer()
        ser.reset_output_buffer()
        time.sleep(0.1)

        # Send sync byte
        ser.write(b'\x7F')
        time.sleep(0.05)

        if ser.in_waiting:
            response = ser.read(ser.in_waiting)
            ser.close()
            return response

        ser.close()
        return None

    except Exception as e:
        return None

def analyze_response(response):
    """Analyze response to determine state"""
    if not response:
        return "NO_RESPONSE", "No response - not in bootloader or wrong settings"

    if response == b'\x79':
        return "BOOTLOADER", "✅ IN BOOTLOADER MODE - Ready for commands"
    elif response == b'\x1F':
        return "NACK", "⚠️ NACK - Bootloader present but rejecting (RDP Level 2?)"
    else:
        hex_str = " ".join(f"{b:02X}" for b in response)
        return "UNKNOWN", f"Unknown response: {hex_str}"

def scan_all_configurations(port):
    """Scan all common configurations"""

    baudrates = [115200, 57600, 38400, 19200, 9600, 4800, 2400, 1200]
    parities = ['E', 'N', 'O']  # Even, None, Odd

    results = []

    print("\n" + "="*70)
    print("SCANNING ALL CONFIGURATIONS")
    print("="*70)

    for baudrate in baudrates:
        for parity in parities:
            parity_name = {'E': 'Even', 'N': 'None', 'O': 'Odd'}[parity]

            print(f"\nTesting {baudrate:6d} baud, {parity_name:4s} parity: ", end="", flush=True)

            # Multiple attempts for reliability
            for attempt in range(3):
                response = check_bootloader_mode(port, baudrate, parity)

                if response:
                    status, msg = analyze_response(response)

                    if status == "BOOTLOADER":
                        print(f"\n  {msg}")
                        print(f"\n  🎯 FOUND BOOTLOADER!")
                        print(f"     Settings: {baudrate} baud, {parity_name} parity")
                        return baudrate, parity
                    elif status == "NACK":
                        print(f"\n  {msg}")
                        results.append((baudrate, parity, "NACK"))
                        break
                    else:
                        if attempt == 0:
                            print(f".", end="", flush=True)
                        time.sleep(0.05)
                else:
                    print(".", end="", flush=True)
                    time.sleep(0.05)

            if not response:
                print(" No response")

    return None, results

def check_application_mode(port, baudrate=115200):
    """Check if device is running application (not bootloader)"""

    print("\n" + "="*70)
    print("CHECKING FOR APPLICATION MODE")
    print("="*70)

    try:
        # Try with no parity (common for applications)
        ser = serial.Serial(
            port=port,
            baudrate=baudrate,
            bytesize=8,
            parity=serial.PARITY_NONE,
            stopbits=1,
            timeout=0.5
        )

        print(f"\nSending test patterns at {baudrate} 8N1...")

        # Send various test patterns
        patterns = [
            b'\x7F',       # Bootloader sync
            b'\r\n',       # Newline
            b'?\r\n',      # Query
            b'help\r\n',   # Help command
            b'\x00',       # Null
            b'\xFF',       # All ones
        ]

        responses = []

        for pattern in patterns:
            ser.reset_input_buffer()
            ser.write(pattern)
            time.sleep(0.1)

            if ser.in_waiting:
                response = ser.read(ser.in_waiting)
                responses.append(response)
                print(f"  Got response: {response[:20]}...")

        ser.close()

        if responses:
            print("\n  📱 Device appears to be running APPLICATION firmware")
            print("     (Getting responses but not bootloader protocol)")
            return True

    except Exception as e:
        pass

    return False

def diagnose_state(port):
    """Main diagnostic function"""

    print("="*70)
    print("STM32 BOOTLOADER MODE DETECTOR")
    print("="*70)

    print(f"\n📡 Port: {port}")

    print("\n" + "="*70)
    print("QUICK CHECK - Standard Settings")
    print("="*70)

    # Quick check with most common settings
    common_configs = [
        (115200, 'E'),
        (57600, 'E'),
        (9600, 'E'),
    ]

    for baudrate, parity in common_configs:
        parity_name = {'E': 'Even', 'N': 'None', 'O': 'Odd'}[parity]
        print(f"\nChecking {baudrate} {parity_name}: ", end="", flush=True)

        response = check_bootloader_mode(port, baudrate, parity)
        status, msg = analyze_response(response)

        print(msg)

        if status == "BOOTLOADER":
            print(f"\n✅ DEVICE IS IN BOOTLOADER MODE")
            print(f"   Use: {baudrate} baud, {parity_name} parity")
            return True

    # Full scan
    print("\nQuick check failed. Scanning all configurations...")
    result, nack_results = scan_all_configurations(port)

    if result:
        baudrate, parity = result
        print(f"\n✅ BOOTLOADER FOUND at {baudrate} baud, parity={parity}")
        return True

    # Check if application is running
    if check_application_mode(port):
        print("\n❌ NOT IN BOOTLOADER MODE")
        print("   Device is running application firmware")
        print("\n   To enter bootloader:")
        print("   1. Set BOOT0 = HIGH (3.3V)")
        print("   2. Set BOOT1 = LOW (GND)")
        print("   3. Press RESET")
        return False

    # Analyze NACK results
    if nack_results:
        print("\n" + "="*70)
        print("⚠️ GETTING NACK RESPONSES")
        print("="*70)
        print("\nDevice responds with NACK (0x1F) at these settings:")
        for br, p, _ in nack_results:
            parity_name = {'E': 'Even', 'N': 'None', 'O': 'Odd'}[p]
            print(f"  - {br} baud, {parity_name} parity")

        print("\nThis indicates:")
        print("  1. Bootloader IS active BUT")
        print("  2. Device is in RDP Level 2 (permanent protection)")
        print("     OR")
        print("  3. Previous failed unlock attempt locked it")

        print("\n⚠️ RDP Level 2 is PERMANENT and IRREVERSIBLE")
        return False

    # No response at all
    print("\n" + "="*70)
    print("❌ NO BOOTLOADER DETECTED")
    print("="*70)

    print("\nPossible causes:")
    print("  1. Not in bootloader mode:")
    print("     - Check BOOT0 = HIGH (3.3V)")
    print("     - Check BOOT1 = LOW (GND)")
    print("     - Reset after setting BOOT pins")
    print()
    print("  2. Connection issues:")
    print("     - TX/RX swapped?")
    print("     - Ground connected?")
    print()
    print("  3. Bootloader disabled:")
    print("     - Option bytes may have disabled it")
    print("     - Custom bootloader installed")
    print()
    print("  4. Hardware issues:")
    print("     - Check voltage levels (3.3V)")
    print("     - Check pull-up resistors")

    return False

def main():
    port = sys.argv[1] if len(sys.argv) > 1 else '/dev/ttyUSB0'

    print("\nThis tool will detect if your STM32 is in bootloader mode")
    print("It will try multiple baudrates and parity settings")

    print("\nStarting detection...")

    in_bootloader = diagnose_state(port)

    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)

    if in_bootloader:
        print("\n✅ Device IS in bootloader mode and responding")
        print("   You can proceed with bootloader commands")
    else:
        print("\n❌ Device is NOT in accessible bootloader mode")
        print("   Check the suggestions above")

    print("\n" + "="*70)

if __name__ == "__main__":
    main()