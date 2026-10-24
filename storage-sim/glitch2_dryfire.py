#!/usr/bin/env python
"""Glitch-2 dry-fire: validate the glitch path on the SOCKET-board rig.

The proven glitch-1 params (1-recon_glitch_trace.py) were tuned on the old
Trezor-chip rig. This board + PIN31-label wire + floating VCAP is new, so
first prove a fat pulse through it actually disturbs the core: sync the
bootloader, fire escalating crowbar pulses into VCAP (pad 31), then re-probe
the UART. Bootloader death = path works.

No trigger needed for this - manual trigger, manualTrigger() call.
"""
import time

import serial

import chipwhisperer as cw


def boot_and_sync(scope, ser):
    scope.io.tio1 = True     # BOOT0=1 -> bootloader
    scope.io.tio2 = 'high_z'
    scope.io.tio4 = 'high_z'
    scope.io.target_pwr = False
    time.sleep(1.5)
    scope.io.target_pwr = True
    time.sleep(3)
    ser.reset_input_buffer()
    ser.write(b'\x7f')
    return b'\x79' in ser.read(16)


def main():
    scope = cw.scope()
    scope.io.target_pwr = 'high_z'
    scope.clock.clkgen_freq = 100e6          # 10 ns per ext_offset/width cycle
    g = scope.glitch
    g.clk_src = 'clkgen'
    g.output = 'enable_only'
    g.trigger_src = 'manual'
    g.offset = -45                           # proven fine-phase
    g.repeat = 20                            # proven burst count
    scope.io.glitch_lp = True
    scope.io.glitch_hp = True

    ser = serial.Serial('/dev/ttyUSB0', 115200, bytesize=8,
                        parity='E', stopbits=1, timeout=1.0)

    if not boot_and_sync(scope, ser):
        scope.dis(); raise SystemExit('no sync before firing')
    print('[+] bootloader synced')

    for width in (40, 45, 49):
        g.width = width
        print(f'[~] firing width={width} repeat=20 ...')
        g.manualTrigger()
        time.sleep(0.2)
        ser.reset_input_buffer()
        ser.write(b'\x7f')
        r = ser.read(16)
        alive = b'\x79' in r
        print(f'    -> after pulse: {"ALIVE" if alive else "DEAD (no response)"}')
        if not alive:
            # distinguish crash vs total reset: re-sync once after settling
            time.sleep(0.5)
            ser.reset_input_buffer()
            ser.write(b'\x7f')
            r2 = ser.read(16)
            print(f'    -> re-probe: {"alive again (self-recovered)" if b"\x79" in r2 else "still dead"}')
            print('[+] GLITCH PATH CONFIRMED on the socket rig - core is being hit')
            scope.dis()
            return
        time.sleep(0.15)   # cooldown between shots

    print('[-] bootloader survived max pulses - check the PIN31 glitch wire path')
    scope.dis()


if __name__ == '__main__':
    main()
