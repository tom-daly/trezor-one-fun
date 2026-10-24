#!/usr/bin/env python
"""Non-intrusive rig sanity check - safe to run WHILE a campaign is live.

Checks (no USB device is opened, no SWD, no serial):
  1. USB enumeration: FTDI (0403:6001), CW (2b3e:*), LA (0925:3881)
  2. Campaign process alive + its CSV/log growing (proves CW+FTDI+target
     actually working end-to-end, since every shot boots+syncs the target)
  3. storage-sim artifacts present (storage.bin, known-answer, scripts)
  4. Latest campaign CSV verdict mix (fresh stats)

For the full hardware probe (SWD, RDP state, flash) use
scripts/0-trezor-status.py - ONLY when no campaign is running.
"""
import glob
import os
import subprocess
import time

HERE = os.path.dirname(os.path.abspath(__file__))


def usb_check():
    try:
        out = subprocess.run(['lsusb'], capture_output=True, text=True,
                             timeout=10).stdout.lower()
    except Exception as e:
        return [f'lsusb failed: {e}']
    findings = []
    for label, pat in (('FTDI (UART)', '0403:6001'),
                       ('ChipWhisperer', '2b3e:'),
                       ('ST-Link', '0483:3748'),
                       ('Logic analyzer', '0925:3881')):
        findings.append(f'  {"OK " if pat in out else "MISSING"} {label}')
    return findings


def campaign_check():
    lines = []
    try:
        out = subprocess.run(['pgrep', '-af', 'glitch2_campaign'],
                             capture_output=True, text=True, timeout=10).stdout
    except Exception:
        out = ''
    procs = [l for l in out.strip().splitlines() if 'pgrep' not in l]
    if not procs:
        lines.append('  no campaign running (rig idle - full status OK to run)')
        return lines, None
    lines.append(f'  campaign alive: pid {procs[0].split()[0]}')
    csvs = sorted(glob.glob(os.path.join(HERE, 'glitch2_*.csv')),
                  key=os.path.getmtime)
    if not csvs:
        lines.append('  WARNING: no CSV appearing')
        return lines, None
    f = csvs[-1]
    age = time.time() - os.path.getmtime(f)
    lines.append(f'  CSV {os.path.basename(f)}: {age:.0f}s since last shot'
                 + ('  <-- STALLED?' if age > 120 else ''))
    try:
        with open(f) as fh:
            rows = [l.strip().split(',') for l in fh if l.strip()][1:]
        from collections import Counter
        c = Counter(r[5] for r in rows if len(r) > 5)
        lines.append(f'  verdicts so far: {dict(c)}')
    except Exception as e:
        lines.append(f'  CSV unreadable: {e}')
    return lines, f


def artifacts_check():
    lines = []
    for name in ('storage.bin', 'known-answer.json', 'make_storage.py',
                 'decrypt_storage.py', 'uart_dump.py', 'glitch2_campaign.py',
                 'set_rdp1.py', 'FINDINGS.md'):
        p = os.path.join(HERE, name)
        lines.append(f'  {"OK " if os.path.exists(p) else "MISSING"} {name}')
    for pat in ('JACKPOT_*.bin', 'uart-dump*.bin'):
        hits = glob.glob(os.path.join(HERE, pat))
        if hits:
            lines.append(f'  *** {pat}: {[os.path.basename(h) for h in hits]}')
    return lines


def main():
    print('=' * 56)
    print('SANITY CHECK (non-intrusive - campaign-safe)')
    print('=' * 56)
    print('USB:')
    print('\n'.join(usb_check()))
    print('CAMPAIGN:')
    clines, _ = campaign_check()
    print('\n'.join(clines))
    print('ARTIFACTS:')
    print('\n'.join(artifacts_check()))
    print('=' * 56)


if __name__ == '__main__':
    main()
