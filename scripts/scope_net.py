#!/usr/bin/env python3
"""Siglent SDS1202X-E network (SCPI over TCP port 5555) reader.

Usage:
  python3 scope_net.py --ip 192.168.1.99 info
  python3 scope_net.py --ip 192.168.1.99 screenshot [--out FILE]
  python3 scope_net.py --ip 192.168.1.99 scpi 'MEASure:VPP? C1'
  python3 scope_net.py --ip 192.168.1.99 screen-data --out FILE.csv   # display-memory waveform (CH1/CH2) as CSV
"""
import argparse
import os
import socket
import struct
import sys
import time

PORT = 5555  # Siglent raw SCPI socket
DEFAULT_IP = '10.11.13.220'
SCPI_PORT = 5025  # Siglent newer firmware raw SCPI port (5555 closed on this unit)
DEFAULT_SNAPSHOT_DIR = 'scope'  # relative to cwd

# DIALECT NOTE (verified live on this unit, fw 1.3.27):
#   This scope only speaks Siglent's LEGACY command set over port 5025.
#   Modern-SCPI commands (':TIMEbase:SCALe?' etc.) are swallowed (QYE / *ESR? = 32).
#   Verified working legacy commands:
#     TDIV? / TDIV <val>            timebase (e.g. 'TDIV 5E-3' = 5 ms/div)
#     C1:VDIV? / C2:VDIV?           volts/div
#     C1:OFST? / <ch>:OFST <val>    vertical offset
#     C1:COUPLING?                  coupling (D1M = DC 1M)
#     SCDP                          screenshot (raw BMP, no TMC header, trailing '\n')
#     *IDN? / *OPC? / *ESR?         common commands
#   Legacy queries echo the command name, e.g. 'TDIV 2.00E-02S', 'C1:VDIV 5.00E-01V'.

def scpi(ip, cmd, port=SCPI_PORT, timeout=5.0, quiet=0.4):
    """Send one command, return raw response bytes (reads until device goes quiet)."""
    s = socket.create_connection((ip, port), timeout=timeout)
    s.settimeout(0.1)
    try:
        s.sendall(cmd.encode() + b'\n')
        data = b''
        last_rx = time.time()
        while True:
            try:
                chunk = s.recv(65536)
                if chunk:
                    data += chunk
                    last_rx = time.time()
            except socket.timeout:
                pass
            if time.time() - last_rx > quiet:
                break
            if time.time() > timeout + 20:
                break
        return data
    finally:
        s.close()

def cmd_info(ip):
    r = scpi(ip, '*IDN?', quiet=0.6)
    print(r.strip().decode(errors='replace'))

def cmd_screenshot(ip, out):
    """Grab screen bitmap via SCDP. If out is empty, save
    scope/snapshot-YYYYMMDD-HHMMSS.{bmp,png} next to cwd."""
    d = scpi(ip, 'SCDP', quiet=0.8, timeout=30.0)
    body = d.rstrip(b'\n')
    if body[:1] == b'#':  # TMC-styled header (some firmware) — unlikely over 5025, be safe
        raw = _tmc_body(body)
    else:
        raw = body
    if raw[:2] != b'BM':
        print('unexpected payload:', d[:64], file=sys.stderr)
        return 1
    if b'\n' in raw:
        cb = int.from_bytes(raw[2:6], 'little')
        raw = raw[:cb]    if not out:
        os.makedirs(DEFAULT_SNAPSHOT_DIR, exist_ok=True)
        ts = time.strftime('%Y%m%d-%H%M%S')
        out = os.path.join(DEFAULT_SNAPSHOT_DIR, f'snapshot-{ts}.bmp')
    open(out, 'wb').write(raw)
    print(f'wrote {out} ({len(raw)} bytes)')
    if out.endswith('.bmp'):
        try:
            from PIL import Image
            png = out[:-4] + '.png'
            Image.open(out).save(png)
            print(f'wrote {png}')
        except ImportError:
            pass
    return 0

def _tmc_body(d):
    """Strip Siglent '#9NNNNNNNNN' block header if present."""
    if d[:1] == b'#':
        hdr_digits = int(d[1:2])
        n = int(d[2:2 + hdr_digits])
        return d[2 + hdr_digits:2 + hdr_digits + n]
    return d

def cmd_scpi(ip, text):
    r = scpi(ip, text)
    printable = r.decode(errors='replace')
    # strip binary garbage: show hex if it looks non-text
    sample = printable[:400]
    if sum(c.isprintable() for c in sample) / max(len(sample), 1) < 0.8:
        print(r[:200].hex())
    else:
        print(printable.strip())

def cmd_screen_data(ip, out):
    """Pull display-memory waveform for CH1/CH2 (Siglent "screen data") and save CSV.

    Scaling per channel comes from YINC/YORIGIN queries; x-axis from XINC,
    centered on t=0 at the trigger position.
    """
    head = scpi(ip, 'DATA:WAVE:SCREEN:HEAD?').strip().decode(errors='replace')
    print('HEAD:', head)

    vals_by_ch = {}
    yinc_by_ch = {}
    yorg_by_ch = {}
    xinc = None
    for ch in (1, 2):
        on = scpi(ip, f'DISPlay:CHAN{ch}:STAT?').strip().upper()
        if on in (b'0', b'OFF'):
            continue
        yinc = float(scpi(ip, f'DATA:WAVE:SCREEN:{ch}:YINC?').strip())
        yorg = float(scpi(ip, f'DATA:WAVE:SCREEN:{ch}:YORIGIN?').strip())
        raw = _tmc_body(scpi(ip, f'DATA:WAVE:SCREEN:ACT{ch}?', quiet=0.8, timeout=20.0))
        vals_by_ch[ch] = raw
        yinc_by_ch[ch] = yinc
        yorg_by_ch[ch] = yorg
        print(f'CH{ch}: {len(raw)} pts  scale {yinc:.3e} V/byte, origin {yorg:.3f} V')
        if xinc is None:
            xinc = float(scpi(ip, 'DATA:WAVE:SCREEN:XINC?').strip())

    if not vals_by_ch:
        print('no channels enabled', file=sys.stderr)
        return 1

    nvals = min(len(v) for v in vals_by_ch.values())
    with open(out, 'w') as f:
        header = 'x_ms,' + ','.join(f'c{ch}' for ch in sorted(vals_by_ch))
        f.write(header + '\n')
        for i in range(nvals):
            row = [f'{(i - nvals // 2) * xinc:.9g}']
            for ch in sorted(vals_by_ch):
                row.append(f'{vals_by_ch[ch][i] * yinc_by_ch[ch] + yorg_by_ch[ch]:.6g}')
            f.write(','.join(row) + '\n')
    print(f'wrote {out} ({nvals} rows; columns: {header})')
    return 0

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--ip', default=DEFAULT_IP, help='scope IP (default 10.11.13.220 on the direct link)')
    ap.add_argument('--port', type=int, default=SCPI_PORT, help='SCPI port (5025 on this firmware)')
    sub = ap.add_subparsers(dest='op', required=True)
    sub.add_parser('info')
    p = sub.add_parser('screenshot'); p.add_argument('--out', default=None,
        help='output path; default scope/snapshot-YYYYMMDD-HHMMSS.bmp (+png)')
    p = sub.add_parser('scpi'); p.add_argument('text')
    p = sub.add_parser('screen-data'); p.add_argument('--out', default='scope_wave.csv')
    a = ap.parse_args()

    if a.op == 'info':
        return cmd_info(a.ip)
    if a.op == 'screenshot':
        return cmd_screenshot(a.ip, a.out)
    if a.op == 'scpi':
        return cmd_scpi(a.ip, a.text)
    if a.op == 'screen-data':
        return cmd_screen_data(a.ip, a.out)
    return 2

if __name__ == '__main__':
    sys.exit(main())
