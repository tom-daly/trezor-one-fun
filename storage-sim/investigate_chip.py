#!/usr/bin/env python
"""investigate_chip.py  --  ONE authoritative, READ-ONLY, MAXIMAL chip report.

Run this whenever the question is "what is this chip / what RDP level / is it
alive / what's readable". It writes NO flash, NO option bytes, NO erase, NO
glitch. The only state it touches is a momentary core halt/resume to snapshot
CPU registers (reversible, no memory changed). Safe on the real device.

Why it exists: a bootloader no-ACK (and a stale OpenOCD read) once got misread
as "not RDP1". The AUTHORITATIVE RDP source is FLASH_OPTCR over SWD, and this
tool CROSS-CHECKS it against actual flash readability so it can't lie. The
bootloader UART ACK is only a SECONDARY signal.

Discovers:
  - ST-Link link: version, target VDD voltage, DAP IDCODE
  - Core: CPUID (Cortex core), DBGMCU DEV_ID/REV_ID (+rev letter), run/halt state
  - CPU register snapshot (halt -> read r0..r15/xPSR -> resume)
  - Option bytes FULL decode: RDP level, write-protected sectors, BOR, resets, WDG
  - Memory-map readability probes (each isolated): SRAM, flash, Trezor storage,
    system ROM (bootloader), OTP, UID, flash-size reg -> maps what RDP allows
  - Bootloader UART 0x7F->0x79 (FTDI, BOOT0 high/BOOT1 low) as a secondary check
  - VERDICT: alive? RDP level (authoritative + cross-check agreement) + summary

Env flags:
  G_DRIVE_BOOT0=1   drive BOOT0 high via TIO1 (enter the bootloader) instead of
                    trusting a jumper / high_z.
  G_OPENOCD=1       also run an independent OpenOCD RDP cross-check (second
                    transport; prints AGREES/DISAGREES vs the authoritative read).

Rig map (rig.md): TIO1=BOOT0, TIO2=BOOT1, TIO3=trigger tap, TIO4=NRST,
glitch SMA=crowbar on VCAP_1 (pin31). UART=FTDI /dev/ttyUSB0 115200 8E1.
Run with /home/tdaly/.cwvenv/bin/python.
"""
import os
import re
import shutil
import subprocess
import sys
import time

sys.path.insert(0, '/home/tdaly/trezor-btc')
sys.path.insert(0, '/home/tdaly/trezor-btc/storage-sim')

import chipwhisperer as cw                    # noqa: E402
from swd.stlink import Stlink                 # noqa: E402

# --- register / memory map (STM32F2 / Cortex-M3) ---
CPUID         = 0xE000ED00
DHCSR         = 0xE000EDF0
DBGMCU_IDCODE = 0xE0042000
FLASH_OPTCR   = 0x40023C14
SRAM_BASE     = 0x20000000
FLASH_BASE    = 0x08000000
STORAGE_BASE  = 0x08008000     # Trezor encrypted storage
SYSROM_BASE   = 0x1FFF0000     # ST system bootloader ROM
OTP_BASE      = 0x1FFF7800     # OTP area
UID_BASE      = 0x1FFF7A10     # 96-bit unique ID (F2)
FSIZE_BASE    = 0x1FFF7A20     # flash size reg at +2 (16-bit, KB)

DBGKEY = 0xA05F0000


def _close(st):
    try:
        st._com._usb = None
        del st
    except Exception:
        pass


def rdp_from_byte(b):
    if b == 0xAA:
        return 0, "no protection"
    if b == 0xCC:
        return 2, "LOCKED (permanent; bootloader + SWD disabled)"
    return 1, "readout protection"


def openocd_crosscheck():
    """Independent read-only RDP cross-check via OpenOCD (same SWD transport, so
    it can't bypass RDP1 - it's a second opinion, not more access). Requires the
    ST-Link FREE (no pyswd session open) and the target powered. Returns a dict
    with optcr/rdp_byte/level/security_set, or {'error': ...}."""
    cmd = ['openocd', '-f', 'interface/stlink.cfg', '-f', 'target/stm32f2x.cfg',
           '-c', 'init', '-c', 'mdw 0x40023c14',
           '-c', 'catch {stm32f2x options_read 0}',
           '-c', 'catch {mdw 0x20000000 1}',
           '-c', 'catch {mdw 0x08000000 1}', '-c', 'shutdown']
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=45)
    except Exception as e:                        # noqa: BLE001
        return {'error': repr(e)}
    out = p.stdout + p.stderr
    m = re.search(r'0x40023c14:\s*([0-9a-fA-F]+)', out)
    optcr = int(m.group(1), 16) if m else None
    rdp = ((optcr >> 8) & 0xFF) if optcr is not None else None
    lvl = (rdp_from_byte(rdp)[0] if rdp is not None else None)
    return {'optcr': optcr, 'rdp_byte': rdp, 'level': lvl,
            'security_set': 'Device Security Bit Set' in out}


def probe(addr, nwords=1):
    """Read nwords 32-bit words at addr on a FRESH link, so a protected-region
    DP fault is fully isolated and can't poison later reads. Returns a list of
    ints, or ('fault', exc)."""
    st = None
    try:
        st = Stlink(swd_frequency=480000)
        vals = [st.get_mem32(addr + 4 * i) for i in range(nwords)]
        _close(st)
        return vals
    except Exception as e:
        if st is not None:
            _close(st)
        return ('fault', e)


def line(c='-'):
    print(c * 64)


def main():
    R = {}
    drive_boot0 = bool(os.environ.get('G_DRIVE_BOOT0'))
    s = cw.scope()
    s.clock.clkgen_freq = 16e6                 # discipline: clkgen FIRST
    s.io.glitch_hp = False                     # crowbar OFF (read-only)
    s.io.glitch_lp = False
    # TIO1=BOOT0: 'high_z' trusts the 3V3 jumper; G_DRIVE_BOOT0=1 drives it high
    # BOOT0=TIO1, BOOT1=TIO2 (driven by CW, not jumpers). For the system
    # bootloader we need BOOT0=1, BOOT1=0. Use explicit gpio strings (boolean
    # False did NOT reliably drive a low) and read them back.
    s.io.tio1 = 'gpio_high' if drive_boot0 else 'high_z'   # BOOT0
    s.io.tio2 = 'gpio_low'                                  # BOOT1 low
    s.io.tio4 = 'high_z'                                    # NRST released
    print(f"[boot] set TIO1(BOOT0)={s.io.tio1!r}  TIO2(BOOT1)={s.io.tio2!r}")
    # BOOT pins latch only at a REAL power-on reset. A short dip leaves the
    # chip alive on its caps (+ ST-Link back-power) so the pins never re-latch.
    # Use the campaign's proven timing: 1.5 s off (full drain), then settle.
    s.io.target_pwr = False
    time.sleep(1.5)
    s.io.target_pwr = True
    time.sleep(1.0)

    line('=')
    print("INVESTIGATE CHIP  (read-only, maximal)")
    line('=')
    print(f"[power] io.target_pwr={s.io.target_pwr}  "
          f"(VCAP_1/pin31 ~1.2V = core LDO alive is a DMM check)")

    # ================= SWD safe reads (one link) =================
    print("\n[SWD] attaching ST-Link...")
    st = None
    try:
        st = Stlink(swd_frequency=480000)
        R['swd'] = 'ATTACHED'
        print("  attached.")
    except Exception as e:
        R['swd'] = f'FAILED: {e!r}'
        print(f"  !! attach FAILED: {e!r}")
        print("  => port dead == RDP2 (permanent lock) OR unpowered/dead chip.")

    if st is not None:
        try:
            print(f"  ST-Link ver   : {st.get_version().str}")
        except Exception as e:
            print(f"  ST-Link ver   : ? ({e!r})")
        try:
            v = st.get_target_voltage()
            R['vdd'] = v
            print(f"  TARGET VDD    : {v:.2f} V   (ST-Link measured)")
        except Exception as e:
            print(f"  TARGET VDD    : ? ({e!r})")
        try:
            print(f"  DAP IDCODE    : 0x{st.get_idcode():08X}")
        except Exception as e:
            print(f"  DAP IDCODE    : ? ({e!r})")

        try:
            cpuid = st.get_mem32(CPUID)
            part = (cpuid >> 4) & 0xFFF
            core = {0xC20: "Cortex-M0", 0xC23: "Cortex-M3",
                    0xC24: "Cortex-M4", 0xC27: "Cortex-M7"}.get(part, "?")
            print(f"  CPUID         : 0x{cpuid:08X}  ({core})")
        except Exception as e:
            print(f"  CPUID         : ? ({e!r})")

        try:
            idc = st.get_mem32(DBGMCU_IDCODE)
            dev_id = idc & 0xFFF
            rev_id = (idc >> 16) & 0xFFFF
            R['dev_id'] = dev_id
            fam = {0x411: "STM32F2xx", 0x413: "STM32F40x/41x",
                   0x419: "STM32F42x/43x", 0x431: "STM32F411"}.get(dev_id, "?")
            rev = {0x1000: "A", 0x1001: "Z", 0x2000: "B",
                   0x2001: "Y", 0x2003: "X", 0x200F: "V"}.get(rev_id, hex(rev_id))
            print(f"  DBGMCU IDCODE : 0x{idc:08X}  DEV_ID=0x{dev_id:03X}"
                  f" ({fam})  REV={rev}")
        except Exception as e:
            print(f"  DBGMCU IDCODE : ? ({e!r})")

        try:
            dhcsr = st.get_mem32(DHCSR)
            R['lockup'] = bool(dhcsr & (1 << 19))
            st8 = "HALTED" if dhcsr & (1 << 17) else "running"
            lock = " LOCKUP" if dhcsr & (1 << 19) else ""
            print(f"  DHCSR         : 0x{dhcsr:08X}  core {st8}{lock}")
        except Exception as e:
            print(f"  DHCSR         : ? ({e!r})")

        # ----- option bytes (authoritative RDP) -----
        try:
            optcr = st.get_mem32(FLASH_OPTCR)
            R['optcr'] = optcr
            rdp_byte = (optcr >> 8) & 0xFF
            lvl, desc = rdp_from_byte(rdp_byte)
            R['rdp_level'] = lvl
            nwrp = (optcr >> 16) & 0xFFF            # 0 = sector write-protected
            prot = [i for i in range(12) if not (nwrp >> i) & 1]
            bor = (optcr >> 2) & 0x3
            print("\n  --- OPTION BYTES (OPTCR = 0x%08X) ---" % optcr)
            print(f"  RDP byte      : 0x{rdp_byte:02X}  => RDP LEVEL {lvl} "
                  f"({desc})   <-- AUTHORITATIVE")
            print(f"  write-protect : nWRP=0x{nwrp:03X}  "
                  f"{'sectors '+str(prot)+' PROTECTED' if prot else 'none'}")
            print(f"  BOR_LEV={bor}  WDG_SW={(optcr>>5)&1}  "
                  f"nRST_STOP={(optcr>>6)&1}  nRST_STDBY={(optcr>>7)&1}  "
                  f"OPTLOCK={optcr&1}")
        except Exception as e:
            print(f"  OPTION BYTES  : read FAILED ({e!r})")

        # ----- CPU register snapshot (halt -> read -> resume) -----
        try:
            st.set_mem32(DHCSR, DBGKEY | 0x3)      # C_DEBUGEN | C_HALT
            time.sleep(0.02)
            regs = st.get_reg_all()
            names = ['r0', 'r1', 'r2', 'r3', 'r4', 'r5', 'r6', 'r7',
                     'r8', 'r9', 'r10', 'r11', 'r12', 'SP', 'LR', 'PC']
            print("\n  --- CPU REGISTERS (core halted) ---")
            pc = regs[15] if len(regs) > 15 else None
            sp = regs[13] if len(regs) > 13 else None
            lr = regs[14] if len(regs) > 14 else None
            R['pc'] = pc
            R['sp'] = sp
            print(f"  PC=0x{pc:08X}  SP=0x{sp:08X}  LR=0x{lr:08X}")
            region = ("system-bootloader ROM" if pc is not None and
                      0x1FFF0000 <= pc <= 0x1FFF8000 else
                      "main flash (firmware)" if pc is not None and
                      0x08000000 <= pc <= 0x08100000 else
                      "SRAM" if pc is not None and
                      0x20000000 <= pc <= 0x20020000 else "?")
            print(f"  -> PC is executing in: {region}")
            st.set_mem32(DHCSR, DBGKEY | 0x1)      # resume (C_DEBUGEN only)
        except Exception as e:
            print(f"  CPU REGISTERS : snapshot skipped ({e!r})")
            try:
                st.set_mem32(DHCSR, DBGKEY | 0x1)
            except Exception:
                pass
        finally:
            _close(st)

    # ================= memory-map readability probes =================
    if R.get('swd') == 'ATTACHED':
        print("\n  --- MEMORY MAP readability (each probe isolated) ---")
        probes = [
            ("SRAM     0x20000000", SRAM_BASE, 1),
            ("FLASH    0x08000000", FLASH_BASE, 2),
            ("STORAGE  0x08008000", STORAGE_BASE, 1),
            ("SYS ROM  0x1FFF0000", SYSROM_BASE, 1),
            ("OTP      0x1FFF7800", OTP_BASE, 1),
            ("UID      0x1FFF7A10", UID_BASE, 3),
            ("FSIZEreg 0x1FFF7A20", FSIZE_BASE, 1),
        ]
        readable = {}
        for label, addr, n in probes:
            res = probe(addr, n)
            if isinstance(res, tuple) and res and res[0] == 'fault':
                readable[label] = False
                print(f"  {label} : FAULT (blocked)")
            else:
                readable[label] = True
                hexv = ' '.join(f'{x:08X}' for x in res)
                extra = ''
                if label.startswith('FSIZE'):
                    extra = f'  -> {(res[0] >> 16) & 0xFFFF} KB flash'
                if label.startswith('SRAM'):
                    R['sram0'] = res[0]
                print(f"  {label} : {hexv}{extra}")
        R['readable'] = readable

    # ================= bootloader UART (secondary) =================
    print("\n[UART] system-bootloader autobaud cross-check (FTDI)...")
    try:
        import serial
        from serialfind import find_ftdi
        uart = find_ftdi()
        s.io.tio1 = True                 # BOOT0 high
        s.io.tio2 = False                # BOOT1 low (required for bootloader)
        s.io.tio4 = 'high_z'
        s.io.target_pwr = False
        time.sleep(1.0)
        s.io.target_pwr = True
        time.sleep(3.0)
        ser = serial.Serial(uart, 115200, bytesize=8, parity='E',
                             stopbits=1, timeout=0.3)
        ser.reset_input_buffer()
        ack, rx_any = False, b''
        for _ in range(30):
            ser.write(b'\x7f')
            r = ser.read(8)
            if r:
                rx_any = r
                if b'\x79' in r:
                    ack = True
                    break
            time.sleep(0.1)
        ser.close()
        R['uart_ack'] = ack
        if ack:
            print("  0x7F -> 0x79 ACK: bootloader ALIVE, FTDI UART good.")
        elif rx_any:
            print(f"  no 0x79 but RX={rx_any.hex()} (baud/parity? garbled).")
        else:
            print("  RX silent. At RDP1 the bootloader SHOULD ACK -> silence =")
            print("  BOOT0 not high at pin / UART wiring; NOT an RDP statement.")
    except Exception as e:
        R['uart_ack'] = f'skipped: {e!r}'
        print(f"  skipped: {e!r}")

    # ========== OpenOCD independent cross-check (opt-in) ==========
    if os.environ.get('G_OPENOCD') and shutil.which('openocd'):
        print("\n[OpenOCD] independent RDP cross-check (same transport)...")
        oc = openocd_crosscheck()
        R['openocd'] = oc
        if oc.get('error'):
            print(f"  openocd error: {oc['error']}")
        elif oc.get('optcr') is not None:
            print(f"  OPTCR=0x{oc['optcr']:08X}  RDP byte 0x{oc['rdp_byte']:02X} "
                  f"=> L{oc['level']}  security_bit="
                  f"{'SET' if oc['security_set'] else 'clear'}")
        else:
            print("  openocd ran but OPTCR not parsed (see security_bit): "
                  f"{'SET' if oc.get('security_set') else 'clear'}")

    try:
        s.dis()
    except Exception:
        pass

    # ================= VERDICT =================
    print()
    line('=')
    print("VERDICT")
    line('=')
    if R.get('swd') != 'ATTACHED':
        print(f"  SWD        : {R.get('swd')}")
        print("  RDP LEVEL  : unreadable over SWD -> RDP2 or dead/unpowered.")
    else:
        print(f"  CHIP       : alive  DEV_ID=0x{R.get('dev_id',0):03X}"
              f"  VDD={R.get('vdd','?'):.2f}V" if isinstance(R.get('vdd'), float)
              else f"  CHIP       : alive  DEV_ID=0x{R.get('dev_id',0):03X}")
        lvl = R.get('rdp_level', '?')
        print(f"  RDP LEVEL  : {lvl}  (option bytes = authoritative)")
        oc = R.get('openocd')
        if oc and not oc.get('error') and oc.get('level') is not None:
            agree = oc['level'] == lvl
            print(f"  OpenOCD xck: L{oc['level']} (OPTCR 0x{oc['optcr']:08X}) "
                  f"-> {'AGREES' if agree else 'DISAGREES!'} (independent)")
        rd = R.get('readable', {})
        fl = next((v for k, v in rd.items() if k.startswith('FLASH')), None)
        if fl is not None:
            agree = (fl and lvl == 0) or ((not fl) and lvl == 1)
            print(f"  cross-chk  : flash {'readable' if fl else 'blocked'} "
                  f"-> {'AGREES' if agree else 'MISMATCH!'} with L{lvl}")
            ok = [k.split()[0] for k, v in rd.items() if v]
            no = [k.split()[0] for k, v in rd.items() if not v]
            print(f"  readable   : {', '.join(ok) or 'none'}")
            print(f"  blocked    : {', '.join(no) or 'none'}")
        pc = R.get('pc')
        sp = R.get('sp')
        sram0 = R.get('sram0')
        in_sram = sp is not None and 0x20000000 <= sp <= 0x20020000
        if R.get('lockup') and in_sram and sram0 is not None and sp != sram0:
            # SP is a clean SRAM address that is NOT SRAM[0] -> this is the ST
            # bootloader's own SP (stable across runs). The lockup/PC=0 is the
            # ST-Link halting into RDP1-protected bootloader code, not a boot
            # failure. Boot pins (BOOT0=1,BOOT1=0) are OK.
            print(f"  CORE STATE : SP=0x{sp:08X} is the ST bootloader SP "
                  f"(!= SRAM[0]=0x{sram0:08X}).")
            print("               => LIKELY IN THE BOOTLOADER (BOOT0=1,BOOT1=0).")
            print("               The LOCKUP is a debug-halt artifact at RDP1.")
            print("               If UART still silent -> UART WIRING, not boot.")
        elif R.get('lockup') and in_sram:
            print("  CORE STATE : LOCKUP, SP tracks SRAM[0] -> SRAM boot "
                  "(BOOT1 HIGH). Fix BOOT1 (PB2/pin28 -> GND).")
        elif R.get('lockup'):
            print("  CORE STATE : LOCKUP, SP all-FF -> blank-FLASH boot "
                  "(BOOT0 LOW). Fix BOOT0 (pin60/TIO1 -> high).")
        elif pc is not None and 0x1FFF0000 <= pc <= 0x1FFF8000:
            print("  CORE STATE : in SYSTEM BOOTLOADER (BOOT0=1,BOOT1=0 OK).")
        ua = R.get('uart_ack')
        print(f"  BOOTLOADER : {'ACK' if ua is True else ua} (secondary; "
              f"needs BOOT0 high + UART wiring)")
    line('=')


if __name__ == '__main__':
    main()
