#!/usr/bin/env python
"""rd_rdp.py - READ-ONLY: determine the RDP level via SWD. No scope, no writes.

Power-cycle into the system bootloader (BOOT0 high, so the core is off protected
flash and the DP is open at RDP0/1), free the CW handle, attach ST-Link, read the
RDP byte from OPTCR. At RDP2 the debug port is disabled -> SWD attach FAILS, which
is itself the RDP2 signature.
  RDP byte 0xAA = RDP0 | 0x55 (or any non-AA/CC) = RDP1 | 0xCC = RDP2
  SWD won't attach / OPTCR faults = RDP2 (debug disabled) OR chip not responding.
"""
import time, gc, sys
import chipwhisperer as cw
OPTCR = 0x40023C14
s = cw.scope(); s.clock.clkgen_freq = 16e6
s.io.glitch_hp=False; s.io.glitch_lp=False
s.io.tio1 = True            # BOOT0 high -> bootloader
s.io.tio2='high_z'; s.io.tio4='high_z'
s.io.target_pwr=False; time.sleep(1.5); s.io.target_pwr=True; time.sleep(2.5)
s.dis(); del s; gc.collect()
try:
    from swd.stlink import Stlink
    st = Stlink(swd_frequency=480000)
    idc = st.get_mem32(0xE0042000)
    v = st.get_mem32(OPTCR); rdp = (v>>8)&0xFF
    lvl = {0xAA:'RDP0 (level 0 - unlocked)', 0xCC:'RDP2 (level 2)'}.get(rdp, f'RDP1 (level 1)')
    print(f"SWD ATTACHED. DBGMCU_IDCODE=0x{idc:08X} (DEV_ID 0x{idc&0xFFF:03X})")
    print(f"OPTCR=0x{v:08X}  RDP byte=0x{rdp:02X}  ->  {lvl}")
    print("=> chip is ALIVE and debug-accessible (so NOT RDP2).")
except Exception as e:
    print(f"SWD attach/read FAILED ({type(e).__name__}).")
    print("=> consistent with RDP2 (debug port disabled) - expected for an RDP2 chip;")
    print("   can't distinguish RDP2 from not-seated/dead by SWD alone.")
