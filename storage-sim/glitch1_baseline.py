#!/usr/bin/env python
"""glitch1_baseline.py - glitch-1's boot/reset sequence WITHOUT the crowbar pull.

Identical rig setup and reboot_flush cadence to glitch1_rdp2_to_rdp1.py (100 MHz
clkgen, BOOT0 on TIO1, NRST drive+self-trigger on TIO4, glitch module armed each
shot at ext_offset) BUT the crowbar FETs (glitch_hp/glitch_lp) are DISARMED, so
no VCAP pull happens. The chip just boots cleanly on every NRST release.

Purpose: scope a clean, repeating boot (same t=0 = NRST-release edge the campaign
triggers on) to find WHERE the BootROM option-byte/RDP read actually happens on
this chip, so we can re-anchor the glitch ext window. No glitch, read-only.

Loops until Ctrl-C / kill. Env: G1_CLKGEN, G1_NRST, G1_BOOT0(low|high),
G1_EXT (where the glitch WOULD fire, for reference), G1_PERIOD (s between resets).
"""
import os, time
import chipwhisperer as cw

CLKGEN   = float(os.environ.get('G1_CLKGEN', 100e6))
NRST     = os.environ.get('G1_NRST', 'tio4').lower()
BOOT0_HI = os.environ.get('G1_BOOT0', 'low').lower() in ('high', '1', 'hi')
EXT      = int(os.environ.get('G1_EXT', 18000))
PERIOD   = float(os.environ.get('G1_PERIOD', 0.3))


def main():
    s = cw.scope()
    s.clock.clkgen_freq = CLKGEN                 # clkgen FIRST (discipline)
    s.adc.samples = 24400
    s.glitch.clk_src = 'clkgen'
    s.glitch.output = 'enable_only'
    s.glitch.trigger_src = 'ext_single'
    s.glitch.width = 40
    s.glitch.offset = -45
    s.glitch.repeat = 20
    s.glitch.ext_offset = EXT
    s.io.glitch_hp = False                        # *** CROWBAR DISARMED - no pull ***
    s.io.glitch_lp = False
    s.trigger.triggers = NRST
    setattr(s.io, NRST, 'high_z')                 # reset released (idle high)
    s.io.tio1 = True if BOOT0_HI else False       # BOOT0
    s.io.tio2 = 'high_z'
    s.io.tio3 = 'high_z'
    s.io.target_pwr = True                        # power on, stays on (NRST-only reboots)
    time.sleep(1.0)

    print(f'[+] BASELINE (NO glitch, crowbar disarmed): clkgen={CLKGEN/1e6:g}MHz  '
          f'BOOT0={"HIGH(bootloader)" if BOOT0_HI else "low(firmware)"}  NRST={NRST}')
    print(f'[+] NRST-release boot every {PERIOD}s. t=0 = NRST rising edge (same as the '
          f'campaign trigger). ext marker would be {EXT} ({EXT/(CLKGEN/1e6):.0f}us).')
    print('[+] Scope the boot and catch the option-load/target. Ctrl-C to stop.')
    n = 0
    try:
        while True:
            setattr(s.io, NRST, 'gpio_low')       # assert reset
            time.sleep(0.02)
            s.arm()                               # arm (internal trigger timing, no pull)
            setattr(s.io, NRST, 'high_z')         # RELEASE -> boot starts (scope t=0)
            n += 1
            print(f'  [{time.strftime("%H:%M:%S")}] boot #{n}  (RST released -> t=0)', flush=True)
            time.sleep(PERIOD)
    except KeyboardInterrupt:
        pass
    finally:
        s.io.glitch_hp = False
        s.io.glitch_lp = False
        s.dis()
        print(f'\n[=] stopped after {n} clean boots.')


if __name__ == '__main__':
    main()
