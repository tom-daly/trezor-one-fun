#!/usr/bin/env python
"""Measure the UART-domain jitter structure of the live hammer stream.

Captures N burst+NACK exchanges (LA on D0=host TX, D1=chip TX; passive - does
not touch the glitch node), decodes t(NACK start) - t(burst start) per shot,
and reports the distribution + shot-to-shot correlation.

If neighboring delays are correlated (slow drift), triggering the glitch off
the previous NACK (tee chip TX -> TIO2) would self-aim each shot and hugely
boost per-shot odds. If uncorrelated, volume hammering is the only path.
"""
import subprocess
import sys

BAUD = 115200
SR = 24_000_000
CAP = '/tmp/opencode/jitter-cap.csv'
N = int(sys.argv[1]) if len(sys.argv) > 1 else 30


def capture_once():
    with open(CAP, 'w') as f:
        subprocess.run(['sigrok-cli', '--driver', 'fx2lafw',
                        '--config', f'samplerate={SR}', '--channels', 'D0,D1',
                        '--triggers', 'D0=f', '--samples', '8000',
                        '-O', 'csv'], stdout=f, stderr=subprocess.DEVNULL,
                       timeout=60)
    rows = []
    for line in open(CAP):
        if line.startswith(';') or not line.strip():
            continue
        rows.append(line.rstrip('\n').split(','))
    return rows


def first_falling_past(rows, ch, start=10):
    prev = rows[start][ch]
    for i in range(start, len(rows)):
        if rows[i][ch] != prev and rows[i][ch] == '0':
            return i
        prev = rows[i][ch]
    return None


def first_rising_in(rows, ch, after):
    prev = rows[after][ch]
    for i in range(after, len(rows)):
        if rows[i][ch] != prev and rows[i][ch] == '1':
            return i
        prev = rows[i][ch]
    return None


def main():
    delays = []
    for n in range(N):
        try:
            rows = capture_once()
            if len(rows) < 100:
                continue
            b0 = first_falling_past(rows, 0)          # burst start bit
            n1 = first_falling_past(rows, 1, start=100)   # NACK start bit
            if b0 is None or n1 is None:
                continue
            d_us = (n1 - b0) / SR * 1e6
            delays.append(d_us)
            print(f'  pair {n + 1}: NACK at burst+{d_us:.2f} us', flush=True)
        except Exception as e:
            print(f'  pair {n + 1}: capture issue ({type(e).__name__})')
    if len(delays) < 4:
        sys.exit('not enough captures')
    import statistics as st
    mean = st.mean(delays)
    dev = st.stdev(delays)
    print(f'\nN={len(delays)}  mean={mean:.2f}us  stdev={dev:.2f}us  '
          f'min={min(delays):.2f}  max={max(delays):.2f}')
    # lag-1 correlation: are neighbors similar (drift) or independent?
    pairs = list(zip(delays, delays[1:]))
    n = len(pairs)
    mx = sum(a for a, _ in pairs) / n
    my = sum(b for _, b in pairs) / n
    cov = sum((a - mx) * (b - my) for a, b in pairs) / n
    sx = (sum((a - mx) ** 2 for a, _ in pairs) / n) ** 0.5
    sy = (sum((b - my) ** 2 for _, b in pairs) / n) ** 0.5
    r1 = cov / (sx * sy) if sx and sy else 0
    print(f'lag-1 correlation r1 = {r1:+.2f}')
    if r1 > 0.5:
        print('>>> CORRELATED (slow drift) - NACK-triggered self-aiming '
              'would be a major odds multiplier. Wire chip TX -> TIO2!')
    elif r1 < 0.2:
        print('>>> UNCORRELATED - per-shot jitter is random; volume '
              'hammering remains the path.')
    else:
        print('>>> weakly correlated - partial benefit possible.')


if __name__ == '__main__':
    main()
