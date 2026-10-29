#!/usr/bin/env python
"""Render an LA capture as a chart: digital waveforms + decoded UART
bytes annotated (the 0x11/0xEE burst, chip 0x1F/0x79 replies) + glitch
events on non-UART channels, with timing deltas vs the burst reference.

Usage:  la_snapshot.py <csv> [--center burst] [--zoom 350] [--out png]
        --center burst|all      (default: centered on the 0x11 start bit)
        --zoom N                (window size in us, default 350)
"""
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

import la_glitch_timing as L
from la_glitch_timing import SR


def step_segments(edges, lo, hi):
    """[(t_start, t_end, state), ...] across [lo,hi] in samples."""
    cur = L.state_at(edges, lo)
    within = [(i, v) for i, v in edges if lo <= i <= hi]
    segs = []
    prev_t = lo
    for i, v in within:
        segs.append((prev_t, i, cur))
        prev_t, cur = i, v
    segs.append((prev_t, hi, cur))
    return segs


def snap(path, out_png, lo_us=None, hi_us=None, title='', glitch_ext=None):
    trans = L.load_edges(path)
    frames = {ch: L.decode_frames(trans[ch])
              for ch in range(8) if len(trans[ch]) > 2}
    label = {0: 'QFP RX (host TX)', 1: 'QFP TX (chip)', 2: 'GLITCH tap'}

    # burst reference: first 0x11 start bit on any channel; fallback =
    # first edge after >5 ms of idle on the most active channel
    b11 = None
    tx_ch = None
    for ch, fr in frames.items():
        got = next((i for i, b in fr if b == 0x11), None)
        if got and (b11 is None or got < b11):
            b11, tx_ch = got, ch
    if b11 is None:
        act = max(range(8), key=lambda c: len(trans[c]))
        b11 = next((i for i, _ in trans[act] if i > 100_000), 0)
        tx_ch = act
    t0 = b11  # samples
    if lo_us is None or hi_us is None:
        lo_s = t0 + int(-40e-6 * SR)
        hi_s = lo_s + int(400e-6 * SR)
        if '--all' in sys.argv:
            lo_s, hi_s = 0, L.load_rows(path)
    else:
        lo_s = t0 + int(lo_us * 1e-6 * SR)
        hi_s = t0 + int(hi_us * 1e-6 * SR)

    fig, ax = plt.subplots(figsize=(14, 6))
    t0_us = t0 / SR * 1e6
    plotted = {}
    for ch in [c for c in range(8)
               if len(trans[c]) > 1]:
        y = len(plotted) * 1.9
        xs, ys = [], []
        for a, b, v in step_segments(trans[ch], lo_s, hi_s):
            xs += [(a - t0) / SR * 1e6, (b - t0) / SR * 1e6]
            ys += [y + (1 if v else 0), y + (1 if v else 0)]
        print(f'    [dbg] D{ch}: {len(trans[ch])} edges, segs across '
              f'{lo_s}..{hi_s} -> xs {xs[:4]}')
        ax.plot(xs, ys, lw=1.2, color='#333')
        name = label.get(ch, f'D{ch}')
        ax.text(0.998, (y + 0.9) / (1.9 * max(1, len(plotted) + 1)),
                name, transform=ax.get_yaxis_transform(),
                ha='right', va='center', fontsize=9,
                color='#1155cc', style='italic')
        plotted[ch] = y

    # annotate UART bytes
    print(f'    [dbg] frames: '
          f'{ {ch: [(f"{i/SR*1e6:.0f}", f"{b:02X}") for i, b in fr[:3]] for ch, fr in frames.items()} }')
    for ch, fr in frames.items():
        if ch not in plotted:
            continue
        yb = plotted[ch] + 1.35
        for idx, byte in fr:
            tus = (idx - t0) / SR * 1e6
            if -100 < tus < (hi_s - t0) / SR * 1e6:
                ax.annotate(f'{byte:02X}', (tus, yb),
                            fontsize=8, color='#aa2222',
                            ha='center', va='bottom', rotation=45)
                ax.annotate('|', (tus, plotted[ch]),
                            fontsize=7, color='#aa2222', va='center')

    # glitch-ish events on channels without UART frames
    for ch in range(8):
        if ch in frames or ch not in plotted or len(trans[ch]) < 2:
            continue
        es = [(i, v) for i, v in trans[ch] if lo_s <= i <= hi_s]
        for idx, v in es:
            nxt = next((j for j, _ in trans[ch] if j > idx), None)
            if nxt is None:
                continue
            dur_us = (nxt - idx) / SR * 1e6
            tus = idx / SR * 1e6 - t0 / SR * 1e6
            ax.annotate(f'{"RISING" if v else "FALLING"} {dur_us:.2f}us'
                        f' @ +{tus:.1f}us',
                        (tus, plotted[ch] + 1.8), fontsize=8,
                        color='#227722' if v == 0 else '#227722',
                        rotation=0, ha='center')

    us0, us1 = lo_s / SR * 1e6 - t0 / SR * 1e6, hi_s / SR * 1e6 - t0 / SR * 1e6

    # computed glitch position: TIO3 locks on the first rising edge inside
    # the 0x11 data field (+8.7us after its start bit); the CW fires
    # ext_offset clkgen cycles later, plus ~2.7us pipeline latency
    if glitch_ext is not None:
        g_us = 8.7 + glitch_ext * 62.5e-3 + 2.7
        if us0 - 5 < g_us < us1 + 5:
            ax.axvspan(g_us - 0.5, g_us + 0.5, color='#cc3333', alpha=.25)
            ax.axvline(g_us, color='#cc3333', lw=1.4, ls='--')
            ax.annotate(f'GLITCH ext={int(glitch_ext)}\n~+{g_us:.1f}us',
                        (g_us, ax.get_ylim()[0] + 0.6), fontsize=9,
                        color='#cc3333', ha='center', va='bottom')
    ax.set_xlim(us0, us1)
    ax.set_ylim(-0.6, 1.9 * len(plotted) + 2.2)
    ax.set_xlabel('µs relative to 0x11 burst start')
    ax.set_yticks([])
    ax.set_title(title or path + ' — UART bytes + glitch events')
    ax.grid(alpha=.25, lw=.4)
    fig.tight_layout()
    fig.savefig(out_png, dpi=115)
    print(f'-> {out_png}')


if __name__ == '__main__':
    path = sys.argv[1]
    if '--sr' in sys.argv:
        _new = int(float(sys.argv[sys.argv.index('--sr') + 1]))
        L.SR = _new
        globals()['SR'] = _new   # rebind this module's imported copy too
    out = sys.argv[sys.argv.index('--out') + 1] if '--out' in sys.argv \
        else path.replace('.csv', '_snap.png')
    zoom = float(sys.argv[sys.argv.index('--zoom') + 1]) \
        if '--zoom' in sys.argv else 400
    lo = -30 if not ('--lo' in sys.argv) else \
        float(sys.argv[sys.argv.index('--lo') + 1])
    gext = None
    if '--glitch-ext' in sys.argv:
        gext = float(sys.argv[sys.argv.index('--glitch-ext') + 1])
    snap(path, out, lo_us=lo, hi_us=lo + zoom, glitch_ext=gext)
