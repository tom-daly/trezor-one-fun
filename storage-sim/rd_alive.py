#!/usr/bin/env python
"""rd_alive.py  -  READ-ONLY aliveness check for the (RDP2) real device.

At RDP2 the SWD debug port AND the STM32 system bootloader are both disabled,
so the usual "is it alive" probes (SWD IDCODE, UART 0x7F sync) FAIL on a
perfectly healthy chip - do NOT read those failures as "dead".

The valid non-invasive signal is the POWER RAILS: a seated, powered STM32 with
its core LDO running shows VCAP ~= 1.2 V (CH1) and VDD ~= 3.3 V (CH2).

This script: power the target via the CW (BOOT0 low = normal firmware boot,
crowbar OFF), then read VCAP/VDD off the Siglent. NO writes, NO glitch, NO
option-byte/RDP touch. Safe on the real device.
"""
import time
import gc

import chipwhisperer as cw

SCOPE_IP = '10.11.13.220'


def power_on():
    s = cw.scope()
    s.clock.clkgen_freq = 16e6         # discipline: clkgen first
    s.io.glitch_hp = False             # crowbar OFF - no accidental glitch
    s.io.glitch_lp = False
    s.io.tio1 = False                  # BOOT0 low -> normal firmware boot
    s.io.tio2 = 'high_z'
    s.io.tio4 = 'high_z'
    s.io.target_pwr = True             # power the chip (read-only)
    return s


def rail(inst, ch):
    try:
        return inst.ask(f'{ch}:PAVA? MEAN').strip()   # e.g. "C1:PAVA MEAN,1.21V"
    except Exception as e:
        return f'(read failed: {type(e).__name__})'


def main():
    s = power_on()
    time.sleep(1.0)                    # rails settle / firmware boots
    print('[+] target powered: BOOT0 low, crowbar OFF, no writes.')
    try:
        import vxi11
        inst = vxi11.Instrument(SCOPE_IP)
        idn = inst.ask('*IDN?')
        print(f'[+] scope: {idn.split(",")[1] if "," in idn else idn}')
        print(f'    VCAP (CH1) = {rail(inst, "C1")}   (alive ~= 1.0-1.3 V)')
        print(f'    VDD  (CH2) = {rail(inst, "C2")}   (alive ~= 3.3 V)')
        print('\n[verdict] VCAP regulating ~1.2 V + VDD ~3.3 V => chip ALIVE.')
        print('          VCAP ~0 V => not powered / not seated / dead.')
    except Exception as e:
        print(f'[!] scope not reachable ({type(e).__name__}: {e}).')
        print('    Eyeball manually: VCAP (CH1) ~1.2 V, VDD (CH2) ~3.3 V, or a DMM on VCAP.')
    print('[i] RDP2 reminder: SWD + bootloader are OFF - those failing is EXPECTED, not "dead".')
    s.dis(); del s; gc.collect()
    print('[+] done (target left powered).')


if __name__ == '__main__':
    main()
