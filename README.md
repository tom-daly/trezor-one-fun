# STM32F205 Glitching and Memory Extraction Tools

This toolkit provides utilities for voltage glitching STM32F205 microcontrollers to bypass Read Protection (RDP) and extract memory contents.

## Prerequisites
- ST-Link V2 debugger connected to target STM32F205 device
- Python 3.x with required packages (swd library)
- Target device powered and connected via SWD interface

## Usage Instructions

### Step 1: Apply Voltage Glitch
```bash
python trezor_fun.py
```
This script performs voltage glitching attacks to attempt bypassing RDP Level 1 protection. The glitch disrupts the option byte loading during boot, potentially allowing debug access.

### Step 2: Verify Security Status
```bash
python check_option_bytes.py
```
Check the current RDP level and option byte configuration. Initially, this should show **RDP Level 1** (Read Protection Active) with a value like 0xFF. After a successful glitch, the RDP may appear as Level 0 or the option bytes may be in an undefined state allowing debug access.

### Step 3: Extract SRAM Contents
```bash
python dump_sram_direct.py
```
If glitch was successful, dump the SRAM contents which may contain sensitive data like encryption keys, passwords, or other runtime secrets.

### Step 4: Extract Flash Contents (Work in Progress)
```bash
python glitch_flash_dump.py
```
**Current Status:** Development in progress. Flash memory is protected by RDP Level 1, which blocks direct reads even after bypassing debug access. This script attempts to bypass the RDP check during memory read operations by:
- Triggering a precisely-timed voltage glitch during the SWD read transaction
- Using IO3 pin to signal when read commands are issued (for oscilloscope monitoring)
- Manual glitch triggering 100µs after read command initiation
- Reading flash in 256-byte chunks to build complete 128KB dump

**Note:** Timing is critical - the glitch must disrupt the RDP check without corrupting the actual data transfer. Adjust timing parameters based on oscilloscope observations.

## STM32F205 RDP (Read Protection) Levels

The STM32F205 uses RDP (Read Protection) to secure flash memory contents. The RDP level is stored in the option bytes at address 0x40023C14 (FLASH_OPTCR register), bits [15:8].

| RDP Level | Option Byte Value | Protection Status | Description |
|-----------|------------------|-------------------|-------------|
| **Level 0** | 0xAA | No Protection | - Full access to flash memory<br>- Debug features enabled<br>- Flash can be read via debug interface |
| **Level 1** | Any value except<br>0xAA or 0xCC | Read Protection Active | - Flash memory cannot be read via debug interface<br>- Code still executes normally from flash<br>- SRAM accessible when booted from flash<br>- Can be reverted to Level 0 (triggers mass erase) |
| **Level 2** | 0xCC | Permanent Protection | - **IRREVERSIBLE** - Cannot be changed<br>- Debug interface permanently disabled<br>- JTAG/SWD fuse blown<br>- No external access to flash or SRAM<br>- Device is permanently locked |

### Current Device Status
Run `python check_option_bytes.py` to check the current RDP level and other option byte settings on your connected STM32F205 device.

## Trezor Flash Storage Structure

The Trezor organizes its flash storage in "entries" that can be identified by their app-value and key-value pairs.

### PIN Storage Entry
The entry containing the encrypted PIN and related cryptographic material is located at:
- **App value:** 0
- **Key value:** 2
- **Header:** `0x02 0x00 0x3C 0x00` (always starts with these 4 bytes)
- **Total size:** 64 bytes

#### Entry Structure (64 bytes total):
| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0x00 | 4 bytes | Header | Always `0x02 0x00 0x3C 0x00` |
| 0x04 | 4 bytes | Salt | Random salt generated during provisioning |
| 0x08 | 32 bytes | EDEK | Encrypted Data Encryption Key |
| 0x28 | 16 bytes | ESAK | Encrypted Storage Authentication Key |
| 0x38 | 8 bytes | PVC | PIN Verification Code |

### Additional Requirements for PIN Recovery
To decrypt the PIN storage entry, you also need:
1. **Hardware Salt**: 44 bytes from OTP (One-Time Programmable) memory at address `0x1FFF7800-0x1FFF782B`
2. **PIN Derivation**: Uses PBKDF2-SHA256 with 10,000 iterations
3. **Encryption**: ChaCha20-Poly1305 for EDEK/ESAK decryption

### Memory Locations
- **Flash Storage**: Entries stored in main flash memory (0x08000000+)
- **OTP Memory**: Hardware salt at 0x1FFF7800 (44 bytes)
- **Option Bytes**: RDP settings at 0x40023C14 (not related to PIN storage)






https://docs.trezor.io/trezor-firmware/storage/index.html