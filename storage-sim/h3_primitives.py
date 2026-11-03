#!/usr/bin/env python
"""h3_primitives.py - validate the two make-or-break primitives for an
Obermaier-H3-style SRAM-shellcode attack on F2@RDP1, WITHOUT any precise glitch.

P-WRITE : with flash locked (debugger attached), can we WRITE+verify SRAM?
          (staging the shellcode must be possible.)
P-REMAN : does SRAM survive a fast power-cycle? Sweep power-off duration and
          measure retention. H3 needs: a power-cycle short enough that SRAM
          survives (remanence) but that still clears the debug flash-lock.
          This is also the core of the classic Kraken SRAM-remanence attack.

READ-ONLY w.r.t. non-volatile memory: writes only SRAM + toggles target power.
No flash, no option bytes. Safe at RDP1.
"""
import os, sys, time, glob, fcntl
import chipwhisperer as cw
from swd.stlink import Stlink

SRAM   = 0x20000000
SRAM_LEN = 0x20000              # 128 KB
OPTCR  = 0x40023C14
PAT_OFFS = [0x0000, 0x4000, 0x8000, 0xC000, 0x10000, 0x14000, 0x18000, 0x1C000, 0x1FF00]
OFF_MS = [1, 2, 5, 10, 20, 50, 100, 200, 500]   # power-off durations to sweep


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


def connect():
    for i in range(4):
        try: return Stlink(swd_frequency=1800000)
        except Exception as e:
            usbreset(); time.sleep(0.6)
    raise SystemExit('swd down')


def word(i):
    # deterministic non-trivial pattern per address
    return (0xA5A50000 ^ (i * 0x9E3779B1)) & 0xFFFFFFFF


def main():
    s = cw.scope(); s.clock.clkgen_freq = 16e6
    s.io.glitch_hp=False; s.io.glitch_lp=False
    s.io.tio1=False; s.io.tio2='high_z'; s.io.tio4='high_z'
    s.io.target_pwr=False; time.sleep(0.5); s.io.target_pwr=True; time.sleep(1.0)
    st = connect()
    print(f'[+] IDCODE=0x{st.get_idcode():08x}  RDP=0x{(st.get_mem32(OPTCR)>>8)&0xff:02x}')

    # ---- P-WRITE: can we write SRAM while flash is locked? ----
    print('\n== P-WRITE: stage data into SRAM (flash locked) ==')
    ok = 0
    for off in PAT_OFFS:
        a = SRAM + off; w = word(off)
        try:
            st.set_mem32(a, w)
            rb = st.get_mem32(a)
            good = rb == w
            ok += good
            print(f'    0x{a:08x} <- 0x{w:08x}  readback 0x{rb:08x}  {"OK" if good else "MISMATCH"}')
        except Exception as e:
            print(f'    0x{a:08x} write/verify FAILED: {type(e).__name__}')
    print(f'    => SRAM staging {"WORKS" if ok==len(PAT_OFFS) else "PARTIAL/FAILED"} '
          f'({ok}/{len(PAT_OFFS)})')

    # ---- P-REMAN: SRAM retention across power-off durations ----
    print('\n== P-REMAN: SRAM survival vs power-off duration ==')
    print('    (write full-SRAM pattern, power off T ms, power on, re-read)')
    for off_ms in OFF_MS:
        # write a fresh, dense pattern across all of SRAM
        try:
            # write every 256th word to keep it quick but spatially spread
            for off in range(0, SRAM_LEN, 0x100):
                st.set_mem32(SRAM + off, word(off))
        except Exception as e:
            print(f'    [{off_ms:>3} ms] write failed: {type(e).__name__}'); continue
        # fast power cycle
        try: st.__del__()
        except Exception: pass
        s.io.target_pwr = False
        time.sleep(off_ms / 1000.0)
        s.io.target_pwr = True
        time.sleep(0.3)                      # let rails settle
        st2 = connect()
        # measure retention
        total = correct = 0
        for off in range(0, SRAM_LEN, 0x100):
            total += 1
            try:
                if st2.get_mem32(SRAM + off) == word(off):
                    correct += 1
            except Exception:
                pass
        pct = 100.0 * correct / max(total, 1)
        print(f'    [{off_ms:>3} ms off] retention {pct:6.2f}%  ({correct}/{total} words)')
        st = st2

    s.io.target_pwr = False; s.dis()
    print('\n[done] If SRAM survives a short power-off, H3 staging is feasible: a '
          'power-cycle in that window clears the debug flash-lock while the '
          'shellcode in SRAM persists.')
    return 0


if __name__ == '__main__':
    try: sys.exit(main())
    except KeyboardInterrupt: sys.exit(1)
