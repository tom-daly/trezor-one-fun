#!/usr/bin/env python
"""Decode the la_measure.py capture: find the UART lines, decode the burst
and the NACK, and report the exact decision-window timing that the glitch-2
sweep must target.

Timing reference = the FIRST RISING EDGE of the 0x11 byte on the host-TX
line (the same edge TIO3 triggers on), so numbers translate 1:1 into
ext_offset cycles at 100 MHz clkgen (10 ns each).
"""
import sys

BAUD = 115200


def load(path):
    rows = []
    with open(path) as f:
        for line in f:
            if line.startswith(';') or not line.strip():
                continue
            rows.append(line.rstrip('\n').split(','))
    return rows


def find_active_channels(rows):
    active = {}
    nch = len(rows[0])
    for i in range(nch):
        seen = set(r[i] for r in rows)
        if len(seen) > 1:
            active[i] = seen
    return active


def edges(rows, ch):
    """Yield (sample_idx, new_value) transitions on channel ch.
    Ignores capture-start artifacts (fx2lafw can glitch the first samples)."""
    prev = rows[0][ch]
    for i, r in enumerate(rows):
        v = r[ch]
        if v != prev:
            yield i, v
            prev = v


def decode_uart(rows, ch, samplerate):
    """Decode 8E1 UART frames from transitions on channel ch."""
    half = samplerate / BAUD / 2          # mid-bit sample threshold in samples
    bit = samplerate / BAUD
    out = []
    trans = list(edges(rows, ch))
    k = 0
    while k < len(trans):
        i, v = trans[k]
        if v != '0':                       # wait for falling edge = start bit
            k += 1
            continue
        # sample mid-start-bit
        start = i + half
        data = 0
        parity_ok = True
        b = 0
        for n in range(1, 10):             # 8 data + parity
            t = start + n * bit
            # find transition state at time t
            state = '1'
            for j in range(k, len(trans)):
                if trans[j][0] <= t:
                    state = trans[j][1]
                else:
                    break
            if n <= 8:
                if state == '1':
                    data |= 1 << (n - 1)
            else:
                b = 1 if state == '1' else 0
        ones = bin(data).count('1') + b
        out.append((i, data, ones % 2 == 0))
        k += 1
    return out


def main():
    path = sys.argv[1]
    samplerate = float(sys.argv[2]) if len(sys.argv) > 2 else 2_000_000
    rows = load(path)
    print(f'{len(rows)} samples @ {samplerate/1e6:.0f} MHz '
          f'({len(rows)/samplerate*1000:.0f} ms window)')
    act = find_active_channels(rows)
    if not act:
        sys.exit('no active channels - capture missed the exchange')
    print(f'active channels: {sorted(act)}')

    # identify: the channel carrying 0x11/0xEE = host TX; 0x1F = chip TX
    results = {}
    for ch in act:
        frames = decode_uart(rows, ch, samplerate)
        results[ch] = frames
        print(f'  D{ch}: {len(frames)} frames: '
              + ' '.join(f'{d:02X}{"p" if ok else "P"}@{i}' for i, d, ok in frames[:12]))

    tx_ch = rx_ch = None
    for ch, frames in results.items():
        datas = [d for _, d, _ in frames]
        if 0x11 in datas and 0xEE in datas:
            tx_ch = ch
        if 0x1F in datas:
            rx_ch = ch
    if tx_ch is None:
        sys.exit('burst (11 EE) not found on any channel')
    print(f'\nhost TX = D{tx_ch}' + (f', chip TX = D{rx_ch}' if rx_ch is not None else ', chip TX: no reply captured'))

    bit = samplerate / BAUD               # samples per bit
    txe = list(edges(rows, tx_ch))
    # first rising edge within the 0x11 byte region = TIO3 trigger point
    burst = [f for f in results[tx_ch] if f[1] == 0x11]
    if not burst:
        sys.exit('no 0x11 frame')
    b0 = burst[0][0]
    trig = next((i for i, v in txe if i >= b0 and v == '1'), None)
    ee = [f for f in results[tx_ch] if f[1] == 0xEE][0]
    ee_end = ee[0] + 11 * bit             # start + 8 data + parity + stop

    def us(samples):
        return samples / samplerate * 1e6

    print(f'\n--- timing (from TIO3 trigger = first rising edge of 0x11) ---')
    print(f'TIO3 trigger edge     : {trig} ({us(trig):.2f} us into burst)')
    print(f'0xEE stop bit ends    : +{us(ee_end - trig):.2f} us past trigger')
    if rx_ch is not None:
        nacks = [f for f in results[rx_ch] if f[1] == 0x1F]
        if nacks:
            n = nacks[0][0]
            print(f'NACK 0x1F start bit   : +{us(n - trig):.2f} us past trigger')
            print(f'\nDECISION WINDOW (pair end -> NACK start): '
                  f'{us(n - ee_end):.2f} us')
            print(f'sweep ext_offset: {int((ee_end - trig)/samplerate*1e5)} '
                  f'to {int((n - trig)/samplerate*1e5)+2000} cycles @100MHz '
                  f'({us(ee_end - trig):.0f}-{us(n - trig) + 200:.0f} us)')
        else:
            print('no NACK frame decoded on chip TX (check parity/error)')


if __name__ == '__main__':
    main()
