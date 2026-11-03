#!/usr/bin/env python
"""rdp1_uart_test.py  -  READ-ONLY bootloader/UART baseline at RDP1.

No glitch, no writes, no option-byte/RDP touch. Safe to run any time; it is
the clean baseline to confirm the UART path + bootloader are healthy BEFORE a
glitch campaign, and to confirm RDP1 is actually engaged.

Sequence (all over the FTDI UART, chip in the STM32 system bootloader):
  1. Power the chip into the bootloader: BOOT0 HIGH (CW TIO1), crowbar OFF,
     full power cycle (BOOT0-high reset is the only reliable bootloader entry).
  2. Autobaud sync  : 0x7F        -> expect 0x79 (ACK)   = bootloader alive
  3. Get            : 0x00 0xFF   -> bootloader version + supported command set
  4. Get ID         : 0x02 0xFD   -> chip product ID (0x411 = STM32F2)
  5. Read Memory    : 0x11 0xEE   -> at RDP1 this is NACKed (0x1F). That NACK
                                     is the PROTECTION we glitch past; seeing it
                                     here (unglitched) CONFIRMS RDP1 is engaged.

Verdict:
  sync ACK + Get/GetID ACK + Read-Memory NACK  => UART healthy, RDP1 engaged.
  sync ACK + Read-Memory ACK                   => chip is at RDP0 (not RDP1!).
  no sync ACK                                  => not in bootloader / UART path
                                                  broken / chip not powered.

Env:
  G_LEAVE_POWERED=0   cut target power on exit (default: leave powered)
"""
import os
import sys
import time
import gc

import chipwhisperer as cw

from serialfind import find_ftdi

UART = find_ftdi()
scope = None
ser = None


def power_into_bootloader():
    """Full power cycle with BOOT0 HIGH, crowbar OFF. Returns the scope."""
    s = cw.scope()
    s.clock.clkgen_freq = 16e6        # discipline: clkgen first
    s.io.glitch_hp = False            # crowbar OFF - this is read-only
    s.io.glitch_lp = False
    s.io.tio1 = True                  # BOOT0 HIGH -> system bootloader
    s.io.tio2 = 'high_z'
    s.io.tio4 = 'high_z'              # NRST released
    s.io.target_pwr = False           # power cycle
    time.sleep(1.0)
    s.io.target_pwr = True
    time.sleep(1.0)                   # rails settle, bootloader autobaud waits
    return s


def sync():
    for _ in range(8):
        ser.reset_input_buffer()
        ser.write(b'\x7f')
        if b'\x79' in ser.read(8):
            return True
        time.sleep(0.05)
    return False


def cmd(code):
    """Send a bootloader command [code, ~code]; return the raw reply bytes."""
    ser.reset_input_buffer()
    ser.write(bytes([code, code ^ 0xFF]))
    time.sleep(0.05)
    return ser.read(64)


def main():
    global scope, ser
    print(f'[+] FTDI UART = {UART}')
    scope = power_into_bootloader()
    print('[+] powered into bootloader: BOOT0 HIGH, crowbar OFF, no glitch.')

    ser = serial_open()
    ok = sync()
    if not ok:
        print('[!] NO 0x79 ACK to 0x7F autobaud.')
        print('    => not in bootloader / UART path broken / chip unpowered.')
        return finish(1)
    print('[+] SYNC ok: 0x7F -> 0x79 (bootloader ALIVE).')

    # Get (0x00): ACK, N, version, N command bytes, ACK
    r = cmd(0x00)
    if r and r[0] == 0x79:
        n = r[1] if len(r) > 1 else 0
        ver = r[2] if len(r) > 2 else None
        cmds = r[3:3 + n] if len(r) > 3 else b''
        vs = f'{ver >> 4}.{ver & 0xF}' if ver is not None else '?'
        print(f'[+] Get (0x00): ACK  bootloader v{vs}  '
              f'cmds=[{" ".join(f"{c:02x}" for c in cmds)}]')
    else:
        print(f'[!] Get (0x00): {r.hex() if r else "(nothing)"}')

    # Get ID (0x02): ACK, N(=1), PID hi, PID lo, ACK
    r = cmd(0x02)
    if r and r[0] == 0x79 and len(r) >= 4:
        pid = (r[2] << 8) | r[3]
        part = {0x411: 'STM32F2xx', 0x413: 'STM32F4xx'}.get(pid, 'unknown')
        print(f'[+] Get ID (0x02): ACK  PID=0x{pid:03x} ({part})')
    else:
        print(f'[!] Get ID (0x02): {r.hex() if r else "(nothing)"}')

    # Read Memory (0x11): the protected command. RDP1 -> NACK (0x1F).
    r = cmd(0x11)
    if not r:
        print('[!] Read Memory (0x11): (no reply)')
        verdict = 'UART path flaky - command stage silent'
    elif r[0] == 0x1F:
        print('[+] Read Memory (0x11): NACK (0x1F) -> RDP1 ENGAGED (protected).')
        verdict = 'UART HEALTHY + RDP1 ENGAGED (ready to glitch).'
    elif r[0] == 0x79:
        print('[!] Read Memory (0x11): ACK (0x79) -> chip is at RDP0, NOT RDP1!')
        verdict = 'Chip is UNPROTECTED (RDP0) - Read Memory already open.'
    else:
        print(f'[?] Read Memory (0x11): unexpected {r.hex()}')
        verdict = f'unexpected Read Memory reply {r.hex()}'

    print(f'\n[VERDICT] {verdict}')
    return finish(0)


def serial_open():
    import serial
    return serial.Serial(UART, 115200, bytesize=8, parity='E',
                         stopbits=1, timeout=0.3)


def finish(rc):
    try:
        if ser:
            ser.close()
    except Exception:
        pass
    try:
        scope.io.glitch_hp = False
        scope.io.glitch_lp = False
        if os.environ.get('G_LEAVE_POWERED', '1') == '0':
            scope.io.target_pwr = False
            print('[+] target power cut.')
        else:
            print('[+] target left powered (G_LEAVE_POWERED=0 to cut).')
        scope.dis()
    except Exception:
        pass
    gc.collect()
    return rc


if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        finish(1)
        sys.exit(1)
