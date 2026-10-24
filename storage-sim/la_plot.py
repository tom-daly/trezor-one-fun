#!/usr/bin/env python
"""Render a logic-analyzer snapshot as a timing diagram PNG.

Usage: la_plot.py <csv> <out.png> [samplerate]
Expects fx2lafw CSV (D0=host TX, D1=chip TX, others as wired). Annotates the
burst bytes, the NACK, and the key glitch-2 timings (CW TIO3 trigger = first
rising edge of 0x11, +182.0us pair end, +183.0us NACK).
"""
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

BAUD = 115200


def load(path):
    rows = []
    for line in open(path):
        if line.startswith(';') or not line.strip():
            continue
        rows.append(line.rstrip('\n').split(','))
    return rows


def transitions(rows, ch):
    prev = rows[0][ch]
    out = [(0, prev)]
    for i, r in enumerate(rows):
        v = r[ch]
        if v != prev:
            out.append((i, v))
            prev = v
    return out


def main():
    path, out = sys.argv[1], sys.argv[2]
    sr = float(sys.argv[3]) if len(sys.argv) > 3 else 2_000_000
    rows = load(path)
    n = len(rows)
    nch = len(rows[0])
    t_us = [i / sr * 1e6 for i in range(n)]
    print(f'{n} samples @ {sr/1e6:.0f}MHz = {n/sr*1e3:.1f}ms')

    labels = {0: 'D0 host TX (burst)', 1: 'D1 chip TX (replies)'}
    for ch in range(2, nch):
        tr = transitions(rows, ch)
        if len(tr) > 2:
            labels[ch] = f'D{ch} (ACTIVE - {len(tr)} edges)'
            print(f'  D{ch} active: {len(tr)} transitions')
        else:
            labels[ch] = f'D{ch} (idle)'

    fig, axes = plt.subplots(nch, 1, figsize=(14, 2.2 * nch), sharex=True)
    if nch == 1:
        axes = [axes]
    bit_us = 1e6 / BAUD

    for ch, ax in enumerate(axes):
        tr = transitions(rows, ch)
        xs = [p / sr * 1e6 for p, _ in tr]
        ys = [1 if v == '1' else 0 for _, v in tr]
        ax.step(xs, ys, where='post', linewidth=1.2)
        ax.set_ylabel(labels.get(ch, f'D{ch}'), rotation=0, ha='right', va='center')
        ax.set_yticks([0, 1])
        ax.set_ylim(-0.2, 1.3)
        for s in ('top', 'right', 'left'):
            ax.spines[s].set_visible(False)

    ax = axes[0]
    # key timings (only meaningful on the TX panel but annotate on the plot)
    burst0 = transitions(rows, 0)
    trig = next((p for p, v in burst0 if v == '1'), None)
    if trig is not None:
        for axx in axes:
            for x_us, txt, col in (
                (trig / sr * 1e6, 'TIO3 trigger\n(first rising edge)', 'tab:red'),
                (trig / sr * 1e6 + 182.0, 'pair end\n+182.0us', 'tab:orange'),
                (trig / sr * 1e6 + 183.0, 'NACK\n+183.0us', 'tab:green'),
            ):
                axx.axvline(x_us, color=col, linestyle='--', linewidth=0.8, alpha=0.7)

    # zoom x-range: burst + ~120us (whole decision + double-NACK region)
    if trig is not None:
        x0 = trig / sr * 1e6 - 20
        x1 = trig / sr * 1e6 + 320
    else:
        x0, x1 = 0, t_us[-1]
    axes[-1].set_xlim(x0, x1)
    axes[-1].set_xlabel('us from capture start (trigger = burst start bit)')
    fig.suptitle('Glitch-2 UART exchange snapshot (115200 8E1)', y=0.98)
    fig.tight_layout(rect=[0.12, 0, 1, 0.96])
    fig.savefig(out, dpi=110)
    print(f'wrote {out}')


if __name__ == '__main__':
    main()
