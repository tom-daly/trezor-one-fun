#!/usr/bin/env python
"""Plot hit maps from campaign CSVs — one chart per CSV (one per config).

Usage:   plot_points.py [campaigns/glitch2_*.csv]   (defaults: newest)
Output:  campaigns/<name>_map.png

Rows = ext offset (µs), cols = pulse width, cell = repeat grid, colour =
verdict (grey dead, blue weird, red/green ack/starred verdict shown).

Test points are only valid within the rig config that produced them, so
charts are never merged across CSVs — each file is its own map.
"""
import csv
import glob
import os
import subprocess
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

HERE = os.path.dirname(os.path.abspath(__file__))
COLOR = {'dead': '#d9d9d9', 'nack': '#a8a8a8', 'weird': '#4477cc'}
RED = '#cc3333'


def draw(path):
    with open(path) as f:
        rows = list(csv.reader(f))
    cfg = rows[0] if rows and rows[0][0] == 'config' else None
    shots = {}
    for r in rows[1:]:
        if len(r) < 6 or r[0] == 'shot':
            continue
        ext, us, w, rep, verdict = r[1], float(r[2]), int(r[3]), int(r[4]), r[5]
        shots.setdefault(us, {}).setdefault(w, {})[rep] = verdict

    if not shots:
        print(f'{os.path.basename(path)}: no shots')
        return
    uses = sorted(shots)
    widths = sorted({w for d in shots.values() for w in d})
    reps = sorted({rep for d in shots.values() for g in d.values()
                   for rep in g})

    fig, ax = plt.subplots(figsize=(2 + len(widths), 4 + len(reps)))
    for ui, us in enumerate(uses):
        for wi, w in enumerate(widths):
            for ri, rep in enumerate(reps):
                v = shots[us][w].get(rep, 'none')
                if v == 'none':
                    continue
                color = COLOR.get(v.split()[0], RED)
                x = wi + 0.13 * (reps.index(rep) % 3 - 1)
                y = ri + 0.13 * ((reps.index(rep) + 1) // 3 - 1)
                ax.scatter(x, y, s=200, c=color, marker='s')
                if not v.startswith(('dead', 'weird', 'nack')):
                    ax.annotate(v, (x, y), ha='center', va='center',
                                fontsize=6, color='white')
    if reps:
        ax.set_yticks(range(len(reps)), [str(r) for r in reps])
    if widths:
        ax.set_xticks(range(len(widths)), [str(w) for w in widths])
    ax.set_xlabel('pulse width (cycles)')
    ax.set_ylabel('repeat count')
    ax.set_title(os.path.basename(path) +
                 (f'\nconfig: clk={cfg[1]} offset={cfg[2]} '
                  f'ext={cfg[5]}..{cfg[6]} tag={cfg[7]}' if cfg else ''))
    ax.invert_yaxis()
    ax.legend(handles=[Line2D([], [], marker='s', ls='', color=c, label=l)
                       for l, c in [('dead (no reply)', COLOR['dead']),
                                    ('nack (RDP active)', COLOR['nack']),
                                    ('weird (corrupted)', COLOR['weird']),
                                    ('ack/other', RED)]])
    ax.grid(alpha=.3, lw=.5)
    out = os.path.join(HERE, 'campaigns',
                       os.path.splitext(os.path.basename(path))[0] + '_map.png')
    fig.tight_layout()
    fig.savefig(out, dpi=110)
    print(f'-> {out}')


def group_configs(paths):
    """Group CSV paths by rig config. Files with a 'config' stamp group by
    that stamp; legacy files group by their observed (us, width, rep)
    signature — same rig setup => same signature."""
    groups = {}
    for p in paths:
        with open(p) as f:
            rows = list(csv.reader(f))
        stamp = None
        if rows and rows[0] and rows[0][0] == 'config':
            stamp = tuple(rows[0][1:8])
            data = rows[1:]
        else:
            data = rows
        sig = set()
        for r in data:
            if len(r) < 6 or r[0] != 'shot' or not r[2][0].isdigit():
                continue
            sig.add((round(float(r[2]), 2), r[3], r[4]))
        key = stamp or tuple(sorted(sig))
        groups.setdefault(key, [stamp, []])[1].append(p)
    return groups


def draw_us(cfg, stamp, paths):
    """Article-style big map: x = ext offset in microns-s... microseconds,
    y = repeat, one panel per pulse width; all same-config sweeps pooled."""
    cells = {}
    for p in paths:
        with open(p) as f:
            rows = list(csv.reader(f))
        for r in rows[1:] if rows and rows[0] and rows[0][0] == 'config' \
                else rows:
            if len(r) < 6 or not r[2][0].isdigit():
                continue
            us, w, rep, v = round(float(r[2]), 2), int(r[3]), int(r[4]), r[5]
            cells.setdefault(w, {}).setdefault((us, rep), {}) \
                 .setdefault(v.split()[0], 0)
            cells[w][(us, rep)][v.split()[0]] += 1

    if not cells:
        return
    PRIORITY = ['ack', 'weird', 'nack', 'dead']
    widths = sorted(cells)
    uses = sorted({u for d in cells.values() for (u, _) in d})
    reps = sorted({rep for d in cells.values() for (_, rep) in d})

    fig, axs = plt.subplots(1, len(widths), figsize=(3.2 * len(widths), 5),
                            sharey=True, squeeze=False)
    for ax, w in zip(axs[0], widths):
        for (us, rep), counts in cells[w].items():
            best = next((v for v in PRIORITY if v in counts), 'other')
            x = ui = uses.index(us)
            y = ri = reps.index(rep)
            c = COLOR.get(best, RED)
            ax.scatter(x, y, s=380, c=c, marker='s')
            n = sum(counts.values())
            if best in ('weird', 'ack') or n > 1:
                ax.annotate(f'{n}', (x, y), ha='center', va='center',
                            fontsize=6.5, color='white')
        ax.set_title(f'width {w}')
        ax.set_xticks(range(len(uses)),
                      [f'{u:.2f}' for u in uses], rotation=45, fontsize=7)
        ax.grid(alpha=.3, lw=.5)
    axs[0][0].set_yticks(range(len(reps)), [str(r) for r in reps])
    axs[0][0].set_ylabel('repeat count')
    for ax in axs[0]:
        ax.set_xlabel('ext offset (µs after readmem)')
        ax.invert_yaxis()
    tag = (stamp[6] if stamp and len(stamp) > 6 else '')
    name = '_'.join(os.path.basename(p).split('_')[1:3]) + (f'_{tag}' if tag else '')
    fig.suptitle(
        f'{name} — {len(paths)} sweep(s), cells pooled'
        + (f'\nconfig: clk={stamp[0]} offset={stamp[1]} '
           f'ext={stamp[4]}..{stamp[5]}' if stamp and len(stamp) > 5 else ''),
        fontsize=10)
    fig.legend(handles=[Line2D([], [], marker='s', ls='', color=c, label=l)
                        for l, c in [('dead (no reply)', COLOR['dead']),
                                     ('nack (RDP active)', COLOR['nack']),
                                     ('weird (corrupted)', COLOR['weird']),
                                     ('ack/other', RED)]],
               loc='upper right', fontsize=8)
    out = os.path.join(HERE, 'campaigns', f'map_{name}_us.png')
    fig.tight_layout()
    fig.savefig(out, dpi=110)
    print(f'-> {out}')


if __name__ == '__main__':
    files = sys.argv[1:] or sorted(glob.glob(os.path.join(HERE, 'campaigns',
                                                          'glitch2_*.csv')))
    groups = group_configs(files)
    for key, (stamp, paths) in groups.items():
        draw_us(None, stamp, paths)
