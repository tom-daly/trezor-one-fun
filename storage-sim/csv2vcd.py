#!/usr/bin/env python
"""Convert a sigrok-cli CSV capture into a VCD file PulseView opens.

Usage:  csv2vcd.py <in.csv> [out.vcd]      (samplerate fixed at 16 MHz)
"""
import sys

import la_glitch_timing as L

SR = 16_000_000
PS = 62_500                      # sample period in picoseconds


def main():
    src = sys.argv[1]
    dst = sys.argv[2] if len(sys.argv) > 2 else \
        src.rsplit('.', 1)[0] + '.vcd'
    rows = L.load_edges(src)
    n = max((i for ch in rows for i, _ in ch), default=0)
    states = {}
    with open(dst, 'w') as f:
        f.write('$date 2026 $end\n$version csv2vcd $end\n'
                '$timescale 1ps $end\n$scope module la $end\n')
        for ch in range(8):
            f.write(f'$var wire 1 y{ch} D{ch} $end\n')
        f.write('$upscope $end\n$enddefinitions $end\n')
        # initial states at t=0
        init = [rows[ch][0][1] if rows[ch] else False
                for ch in range(8)]
        f.write('$dumpvars\n')
        for ch, v in enumerate(init):
            f.write(f'{1 if v else 0}y{ch}\n')
        f.write('$end\n')
        # transitions
        events = sorted((i, ch, v) for ch, es in enumerate(rows)
                        for i, v in es[1:])
        cur_t = 0
        for i, ch, v in events:
            if i != cur_t:
                f.write(f'#{i * PS}\n')
                cur_t = i
            f.write(f'{1 if v else 0}y{ch}\n')
    print(f'-> {dst}')


if __name__ == '__main__':
    main()
