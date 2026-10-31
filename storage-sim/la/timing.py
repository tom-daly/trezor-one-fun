#!/usr/bin/env python3
"""LA timing — measure the 0x11-command -> NACK latency from a capture.

Why: the RDP decision happens in a narrow window after the Read Memory command
finishes transmitting and before the NACK goes out. If the chip's NACK onset
drifts (temperature, clock), our glitch us-window goes stale. This reads the
command->response latency straight off the UART lines (D0=TX, D1=RX) so we can
compare against the calibration (NACK onset ~= 196.5 us after the 0x11 start).

Runs sigrok-cli to convert the .sr to VCD, then analyses transitions. No glitch
node involved; safe to run anytime.

Usage: timing.py [IN.sr | IN.vcd]
"""
import subprocess
import sys
import re

TX_NAME, RX_NAME = 'D0', 'D1'      # host->chip, chip->host  (this rig)
BURST_GAP_TICKS = 3000             # >300us idle splits UART exchanges
BYTE_US = 95.5                     # one 8E1 byte @115200 (11 bits)


def est_bytes(dur_us):
    """Rough byte count a TX burst spans (duration is pattern-dependent, so
    this is approximate — use decode.sh for the actual bytes)."""
    return max(1, round(dur_us / BYTE_US) + 1)


def load_vcd(path):
    if path.endswith('.sr'):
        vcd = subprocess.run(['sigrok-cli', '-i', path, '-O', 'vcd'],
                             capture_output=True, text=True).stdout
        lines = vcd.splitlines()
    else:
        lines = open(path).read().splitlines()
    ts_ns = 1
    ids = {}                        # vcd id char -> channel name
    body_start = 0
    for i, ln in enumerate(lines):
        if ln.startswith('$timescale'):
            m = re.search(r'(\d+)\s*(\w?s)', ln)
            if m:
                unit = {'s': 1e9, 'ms': 1e6, 'us': 1e3, 'ns': 1}.get(m.group(2), 1)
                ts_ns = int(m.group(1)) * unit
        elif ln.startswith('$var'):
            parts = ln.split()
            ids[parts[3]] = parts[4]           # id char -> D0/D1/...
        elif ln.startswith('$enddefinitions'):
            body_start = i + 1
    return lines[body_start:], ids, ts_ns


def falling_edges(lines, ids, ts_ns, want):
    """Return falling-edge (1->0) times in ns for the named channel."""
    cid = next((c for c, nm in ids.items() if nm == want), None)
    if cid is None:
        return []
    t = 0
    last = {}
    edges = []
    for ln in lines:
        for tok in ln.split():
            if tok.startswith('#'):
                t = int(tok[1:])
            elif len(tok) >= 2 and tok[0] in '01xz':
                v, c = tok[0], tok[1:]
                if c == cid:
                    if last.get(c) == '1' and v == '0':
                        edges.append(t * ts_ns)
                    last[c] = v
    return edges


def bursts(edges, gap_ns):
    """Group edge times into bursts separated by >gap_ns idle."""
    out = []
    for e in edges:
        if not out or e - out[-1][-1] > gap_ns:
            out.append([e])
        else:
            out[-1].append(e)
    return out


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else './la_cap.sr'
    lines, ids, ts_ns = load_vcd(path)
    tx = bursts(falling_edges(lines, ids, ts_ns, TX_NAME), BURST_GAP_TICKS * ts_ns)
    rx = falling_edges(lines, ids, ts_ns, RX_NAME)
    gap = BURST_GAP_TICKS * ts_ns
    print(f'{path}: {len(tx)} TX bursts, {len(rx)} RX edges  (TX={TX_NAME} RX={RX_NAME})')
    print(f'{"t_start_ms":>11} {"tx_dur_us":>10} {"~bytes":>7} {"->resp_us":>10}')
    lat = []
    for b in tx:
        t0, dur_us = b[0], (b[-1] - b[0]) / 1e3
        nb = est_bytes(dur_us)
        nxt = [r for r in rx if r > t0 and r - t0 < 3e6]   # first RX within 3 ms
        resp_us = (min(nxt) - t0) / 1e3 if nxt else float('nan')
        print(f'{t0/1e6:11.3f} {dur_us:10.1f} {nb:7d} {resp_us:10.1f}')
        if nxt:
            lat.append(resp_us)
    if lat:
        lat.sort()
        med = lat[len(lat) // 2]
        print(f'\nTX-start -> RX-response latency over {len(lat)} exchanges: '
              f'min {lat[0]:.1f} / median {med:.1f} / max {lat[-1]:.1f} us')
        print('calibration: 2-byte 0x11 EE command -> NACK onset ~196.5 us; '
              'a latency near that = window still placed right (no drift).')
    else:
        print('\n(no complete TX->RX pairs captured; grab a longer trace)')


if __name__ == '__main__':
    main()
