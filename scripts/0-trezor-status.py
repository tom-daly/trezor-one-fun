#!/usr/bin/env python3
"""
Trezor status check — answers two questions: is it powered, and what state?

Reports (read-only if the target is already powered):
  POWER   CW target_pwr switch + chip answering over SWD (real proof)
  SWD     DBGMCU_IDCODE (expect 0x200F6411 = STM32F2, dev id 0x411)
  RDP     level from FLASH_OPTCR (0x40023C14): RDP byte + SPRMOD/PCROP bit
  FLASH   probe read of 0x08000000: AP fault = locked (expected at RDP1)
  STATE   firmware running vs bootloader/system: SRAM samples
          (populated => firmware booted; all-zero => bootloader/early boot)

If unpowered: reports OFF. --power-on powers it for a live check (fresh boot:
BOOT0 decides bootloader vs firmware) and restores OFF afterwards unless
--leave-on. If already powered: never touches the power state.
"""
import os
import sys
import time
import argparse

import chipwhisperer as cw

DBGMCU_IDCODE = 0xE0042000
FLASH_OPTCR   = 0x40023C14
FLASH_BASE    = 0x08000000
SRAM_LOW      = 0x20000000   # .data/.bss end
SRAM_HIGH     = 0x2001F000   # stack end (top of 128 KB)
SRAM_SAMPLE   = 4096

RDP_LEVELS = {
    0: "UNLOCKED (RDP0) — full access, unexpected!",
    1: "read protection — SWD open, flash locked (the expected state)",
    2: "RDP2 — SWD + bootloader PERMANENTLY dead (brick)",
}


def swd_connect():
    os.system("/home/tdaly/.cwvenv/usb_reset > /dev/null 2>&1")
    time.sleep(0.4)
    import swd
    return swd.Swd()


def read32(dev, addr):
    return int.from_bytes(bytes(dev.read_mem(addr, 4)), "little")


def sram_nz(dev, addr):
    sample = bytes(dev.read_mem(addr, SRAM_SAMPLE))
    return sum(1 for b in sample if b not in (0, 0xFF))


def main():
    ap = argparse.ArgumentParser(description="Trezor power + state check")
    ap.add_argument("--power-on", action="store_true",
                    help="power the target for the check if it is off "
                         "(restores OFF afterwards unless --leave-on)")
    ap.add_argument("--leave-on", action="store_true",
                    help="with --power-on: leave the target powered afterwards")
    args = ap.parse_args()

    scope = cw.scope()
    switched_on = False
    try:
        powered = bool(scope.io.target_pwr)
        if not powered and args.power_on:
            scope.io.target_pwr = True
            switched_on = True
            time.sleep(2.5)   # fresh boot: BOOT0 state decides bootloader vs firmware
            powered = True

        print("=" * 62)
        print("TREZOR STATUS")
        print("=" * 62)

        if not powered:
            print("POWER : OFF (CW target_pwr switch is OFF, no power applied)")
            print("         re-run with --power-on for a live check")
            return 0

        print(f"POWER : ON{' (switched on by this check)' if switched_on else ''}")

        # ---- SWD + identity ----
        try:
            dev = swd_connect()
            idcode = read32(dev, DBGMCU_IDCODE)
            dev_id = idcode & 0xFFF
            ok = "LIVE" if dev_id == 0x411 else "unexpected ID"
            print(f"SWD    : {ok} — DBGMCU_IDCODE 0x{idcode:08X} (dev 0x{dev_id:03X}, expect 0x411)")
        except Exception as e:
            print(f"SWD    : NO ANSWER while powered ({type(e).__name__}: {str(e)[:45]})")
            print("         powered but silent: mid-glitch state or RDP2-like —")
            print("         run scripts/1-recon_glitch_trace.py to re-open the debug port")
            return 1

        # ---- RDP + PCROP from OPTCR ----
        try:
            optcr = read32(dev, FLASH_OPTCR)
            rdp = (optcr >> 8) & 0xFF
            sprmod = (optcr >> 31) & 1
            level = 0 if rdp == 0xAA else (2 if rdp == 0xCC else 1)
            print(f"RDP    : LEVEL {level} (OPTCR 0x{optcr:08X}, RDP byte 0x{rdp:02X})")
            print(f"         {RDP_LEVELS[level]}")
            print(f"PCROP  : {'ACTIVE (SPRMOD=1) — reads return zeros!' if sprmod else 'off (SPRMOD=0)'}")
        except Exception as e:
            sprmod = None
            print(f"RDP    : OPTCR read failed ({type(e).__name__}: {str(e)[:40]})")

        # ---- flash probe ----
        try:
            data = bytes(dev.read_mem(FLASH_BASE, 16))
            sp = int.from_bytes(data[0:4], "little")
            rst = int.from_bytes(data[4:8], "little")
            valid = (0x20000000 <= sp <= 0x20020000 and
                     0x08000000 <= rst <= 0x08100000)
            print(f"FLASH  : READABLE at 0x08000000 — "
                  f"{'valid vectors (RDP0-like!)' if valid else data.hex()}")
        except Exception:
            print("FLASH  : locked (AP fault at 0x08000000 — expected at RDP1)")

        # ---- boot-state classification via SRAM samples ----
        try:
            nz_low = sram_nz(dev, SRAM_LOW)
            nz_high = sram_nz(dev, SRAM_HIGH)
            frac = (nz_low + nz_high) / (2 * SRAM_SAMPLE)
            if frac > 0.9:
                state = ("DEAD BOOT / uninitialized SRAM (no image ran — "
                         "check BOOT0 wiring/level; signature: ~98% non-trivial")
            elif nz_low > 16 or nz_high > 16:
                state = "FIRMWARE RUNNING (SRAM populated — BOOT0 was low at last reset)"
            else:
                state = ("BOOTLOADER / system state (SRAM all-zero or minimal — "
                         "BOOT0 high at last reset)")
            print(f"STATE  : {state})")
            print(f"         SRAM non-trivial bytes: low {nz_low}/{SRAM_SAMPLE}, high {nz_high}/{SRAM_SAMPLE} ({frac:.0%})")
        except Exception as e:
            print(f"STATE  : SRAM sample failed ({type(e).__name__})")

        print("SCREEN : visual check is yours — on = firmware, off = bootloader (BOOT0 high)")
        return 0

    finally:
        if switched_on and not args.leave_on:
            scope.io.target_pwr = False
            print("(target powered back OFF — it was off before the check)")
        try:
            scope.dis()
        except Exception:
            pass


if __name__ == "__main__":
    sys.exit(main())
