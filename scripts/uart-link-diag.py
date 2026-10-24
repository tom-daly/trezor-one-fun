#!/usr/bin/env python3
"""
UART link diagnostic: find where the USB-serial adapter's TX actually lands.

Streams 0x00 bytes continuously (long low pulses at 9600 8E1) while polling
every GPIO input-data register over SWD via the ST-Link. Any pin that
changes state during the stream is a pin the adapter's TX is driving.

Also reports the PA9/PA10 idle states:
  PA9  = bootloader USART1 TX: idle HIGH once the bootloader enables it
  PA10 = bootloader USART1 RX: input pull-up => HIGH unless driven low

Diagnoses, when the bootloader sync (0x7F) gets no ACK:
  - TX on the wrong pin      -> you SEE which pin toggles
  - TX not connected at all  -> nothing toggles anywhere
  - TX/RX orientation        -> PA10 toggling = TX correctly on MCU RX
  - adapter TX on PA9       -> PA9 toggling (it's the MCU TX pin: swap back)
  - bootloader UART not up   -> PA9 LOW (USART1 TX not driven)
  - adapter GND missing     -> typically nothing toggles anywhere
"""
import threading
import time

import serial
from swd.stlink import Stlink

PORT = '/dev/ttyUSB0'
GPIO_IDR = {
    'A': 0x40020010,
    'B': 0x40020410,
    'C': 0x40020810,
    'D': 0x40020C10,
}
SAMPLES = 300
PAUSE_S = 0.004

st = Stlink(swd_frequency=1800000)
ser = serial.Serial(PORT, 9600, parity=serial.PARITY_EVEN, stopbits=1, timeout=0.1)


def read_all():
    return {n: st.get_mem32(a) for n, a in GPIO_IDR.items()}


base = read_all()
print('baseline IDR (low 16 bits):', {n: f'0x{v & 0xFFFF:04X}' for n, v in base.items()})
print(f'streaming 0x00 on {PORT} @ 9600 8E1 for ~{SAMPLES * PAUSE_S:.0f}s while polling SWD...')

stop = False


def tx_stream():
    while not stop:
        ser.write(b'\x00' * 128)


t = threading.Thread(target=tx_stream)
t.start()

seen = {n: set() for n in GPIO_IDR}
for _ in range(SAMPLES):
    v = read_all()
    for n in GPIO_IDR:
        seen[n].add(v[n] & 0xFFFF)
    time.sleep(PAUSE_S)
stop = True
t.join()
ser.close()


def level(port, bit):
    vals = {(v >> bit) & 1 for v in seen[port]}
    if len(vals) > 1:
        return 'TOGGLING'
    return 'HIGH' if vals == {1} else 'LOW'


print()
print('pins that CHANGED during the 0x00 stream (= adapter TX lands here):')
toggles = [(n, b) for n in GPIO_IDR for b in range(16) if level(n, b) == 'TOGGLING']
for n, b in toggles:
    print(f'  P{n}{b}  <-- activity!')
if not toggles:
    print('  NONE — adapter TX is not reaching any GPIO pin')
    print('         => TX wire not connected / wrong strip / adapter GND missing')

pa9, pa10 = level('A', 9), level('A', 10)
print()
if pa9 == 'HIGH':
    print('PA9  (MCU TX):  idle HIGH — bootloader USART1 TX driven: UART ALIVE')
elif pa9 == 'TOGGLING':
    print('PA9  (MCU TX):  TOGGLING — the ADAPTER TX is on PA9 (the MCU TX pin)!')
    print('                 => swap the two signal wires back (TX belongs on PA10)')
else:
    print('PA9  (MCU TX):  LOW — USART1 TX not driven: bootloader UART not on PA9/PA10?')
if pa10 == 'TOGGLING':
    print('PA10 (MCU RX):  TOGGLING — adapter TX reaches the MCU RX: orientation CORRECT')
elif pa10 == 'HIGH':
    print('PA10 (MCU RX):  idle HIGH — pull-up only, not driven by the adapter TX')
else:
    print('PA10 (MCU RX):  LOW — actively pulled low (adapter TX here and stuck?)')

print()
print('If PA9=HIGH and PA10 toggles, the physical link is good at 9600 —')
print('re-run the sync test (usart_force_bootloader.py).')
