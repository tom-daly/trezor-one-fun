#!/usr/bin/env python
"""Craft a Trezor-legacy (v4 storage format) norcow image with a generated
seed and chosen PIN, for the F205 socket-board practice target.

Everything follows the real 1.13.1 source (storage-sim/reference/):
  - norcow blockwise format: 16 B blocks, small items <=12 B, KEY|LEN LE
  - sector magic 0x3243524E ('NRC2'), ~version word, items from offset 8
  - hardware_salt = SHA256(UID(12) || OTP block 3 (32))   [trezor.c collect_hw_entropy]
  - v4 KDF: PBKDF2-HMAC-SHA256(pin_bytes, hw_salt||random_salt, 10000, 44)
    -> KEK(32) || KEIV(12)   [storage.c derive_kek_v4, PIN_ITER_COUNT 20000/2 blocks]
  - EKEYS = ChaCha20Poly1305(KEK, KEIV, aad=b'') over DEK(32)||SAK(16)
  - PVC = tag[:8]
  - protected entries: IV(12) || ENCR || TAG(16), AAD = u16 key LE
  - STORAGE_TAG (APP=0,KEY=5) = HMAC-SHA256(SAK, XOR of per-key HMACs)[:16]

Output: storage.bin (16 KB sector image for 0x08008000) + known-answer.json
"""
import argparse
import hashlib
import hmac
import json
import os
import struct

from Crypto.Cipher import ChaCha20_Poly1305


NORCOW_MAGIC = 0x3243524E          # 'NRC2' little-endian in flash
NORCOW_LAYOUT_VERSION = 5          # norcow format version (word 1 = ~version)
STORAGE_VERSION = 4                # the (0,4) VERSION entry -> v4 KDF path
CONFIG_VERSION = 11                # legacy config schema (KEY_VERSION under APP=1)
SECTOR_SIZE = 16 * 1024
BLOCK = 16
SMALL_ITEM_MAX = 12                # BLOCK - 4

# APP=0 (private) keys
K_PIN_LOGS   = 0x0001
K_EDEK_PVC   = 0x0002
K_PIN_NOT_SET= 0x0003
K_VERSION    = 0x0004
K_STORAGE_TAG= 0x0005
# APP=1 (legacy config)
K_UUID       = 0x0100   # public, 12 random bytes
K_CFG_VERSION= 0x0101   # protected, u32 = CONFIG_VERSION
K_MNEMONIC   = 0x0102   # protected, the mnemonic string
K_NEEDS_BKUP = 0x0107   # protected, bool TRUE_BYTE
K_INITIALIZED= 0x010E   # public, u32 TRUE_WORD

TRUE_BYTE = 0x01
TRUE_WORD = 0xC35A69A5


def pad_ff(data: bytes, size: int) -> bytes:
    return data + b'\xff' * (size - len(data))


def encode_item(key: int, data: bytes) -> bytes:
    """One norcow blockwise item, 0xFF padded."""
    out = b''
    hdr = struct.pack('<HH', key, len(data))
    if len(data) <= SMALL_ITEM_MAX:
        out += pad_ff(hdr + data, BLOCK)
    else:
        out += hdr + b'\xff' * 12          # first block: header only
        nfull = len(data) // BLOCK
        out += data[:nfull * BLOCK]
        rest = data[nfull * BLOCK:]
        if rest:
            # partial last block: data + VALID flag 0xFF + pad
            out += pad_ff(rest + b'\xff', BLOCK)
        else:
            out += b'\xff' * BLOCK          # flag alone in the next block
    return out


def chacha(key: bytes, nonce: bytes, aad: bytes, data: bytes):
    c = ChaCha20_Poly1305.new(key=key, nonce=nonce)
    c.update(aad)
    ct = c.encrypt(data)
    return ct, c.digest()


def gen_mnemonic(strength_bits: int = 128) -> str:
    words = open(os.path.join(os.path.dirname(__file__), 'bip39-english.txt')).read().split()
    ent = os.urandom(strength_bits // 8)
    chk = hashlib.sha256(ent).digest()
    bits = strength_bits + strength_bits // 32
    acc = int.from_bytes(ent, 'big') << (strength_bits // 32)
    acc |= int.from_bytes(chk, 'big') >> (256 - strength_bits // 32)
    n = strength_bits // 32 * 33
    out = []
    for i in range(bits // 11):
        out.append(words[(acc >> (bits - 11 * (i + 1))) & 0x7FF])
    return ' '.join(out)


def build(pin: str, mnemonic: str, uid: bytes, otp3: bytes) -> tuple:
    # --- keys ---
    hw_entropy = uid + otp3                       # 44 bytes
    hardware_salt = hashlib.sha256(hw_entropy).digest()
    random_salt = os.urandom(4)
    kdf_salt = hardware_salt + random_salt
    dk = hashlib.pbkdf2_hmac('sha256', pin.encode(), kdf_salt, 10000, dklen=44)
    kek, keiv = dk[:32], dk[32:44]
    dek = os.urandom(32)
    sak = os.urandom(16)
    ekeys, tag = chacha(kek, keiv, b'', dek + sak)
    pvc = tag[:8]
    edek_entry = random_salt + ekeys + pvc        # 4 + 48 + 8 = 60

    # --- protected entry helper (AAD = u16 key LE) ---
    def protect(key: int, data: bytes) -> bytes:
        iv = os.urandom(12)
        ct, tg = chacha(dek, iv, struct.pack('<H', key), data)
        return iv + ct + tg

    # --- pin log entry (fresh: guard key + all-ones logs) ---
    guard_key = 0xAAAAAAAA                          # cosmetic; decryptor ignores
    pin_logs = struct.pack('<I', guard_key) + b'\xff' * 128

    # --- protected entries + storage authentication tag ---
    protected = [
        (K_CFG_VERSION, struct.pack('<I', CONFIG_VERSION)),
        (K_MNEMONIC, mnemonic.encode()),
        (K_NEEDS_BKUP, struct.pack('<B', TRUE_BYTE)),
    ]
    auth_sum = bytearray(32)
    for key, _ in protected:
        t = hmac.new(sak, struct.pack('<H', key), hashlib.sha256).digest()
        for i in range(32):
            auth_sum[i] ^= t[i]
    storage_tag = hmac.new(sak, bytes(auth_sum), hashlib.sha256).digest()[:16]

    # --- assemble the sector image ---
    img = struct.pack('<II', NORCOW_MAGIC, ~NORCOW_LAYOUT_VERSION & 0xFFFFFFFF)
    img += encode_item(K_EDEK_PVC, edek_entry)
    img += encode_item(K_PIN_LOGS, pin_logs)
    img += encode_item(K_PIN_NOT_SET, struct.pack('<B', 0x00))
    img += encode_item(K_VERSION, struct.pack('<I', STORAGE_VERSION))
    img += encode_item(K_STORAGE_TAG, storage_tag)
    img += encode_item(K_UUID, os.urandom(12))
    for key, data in protected:
        img += encode_item(key, protect(key, data))
    img += encode_item(K_INITIALIZED, struct.pack('<I', TRUE_WORD))
    assert len(img) <= SECTOR_SIZE
    img = pad_ff(img, SECTOR_SIZE)

    answer = {
        'pin': pin,
        'mnemonic': mnemonic,
        'uid': uid.hex(),
        'otp3': otp3.hex(),
        'random_salt': random_salt.hex(),
        'kek': kek.hex(), 'keiv': keiv.hex(),
        'dek': dek.hex(), 'sak': sak.hex(),
        'hardware_salt': hardware_salt.hex(),
        'storage_version': STORAGE_VERSION,
    }
    return img, answer


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--pin', default='4179')
    ap.add_argument('--mnemonic', default=None, help='12/24 words; default: generated')
    ap.add_argument('--uid', default='3e0031001547333032303138',
                    help='12-byte unique ID @0x1FFF7A10 (this socket chip)')
    ap.add_argument('--otp3', default='ff' * 32,
                    help='OTP block 3 (32 B) @0x1FFF7860; blank chip = all FF')
    ap.add_argument('--out', default='storage.bin')
    args = ap.parse_args()

    mnemonic = args.mnemonic or gen_mnemonic()
    img, answer = build(args.pin, mnemonic, bytes.fromhex(args.uid),
                        bytes.fromhex(args.otp3))
    here = os.path.dirname(os.path.abspath(__file__))
    open(os.path.join(here, args.out), 'wb').write(img)
    open(os.path.join(here, 'known-answer.json'), 'w').write(
        json.dumps(answer, indent=2))
    print(f'wrote {args.out} ({len(img)} B) and known-answer.json')
    print(f'  pin      = {args.pin}')
    print(f'  mnemonic = {mnemonic}')


if __name__ == '__main__':
    main()
