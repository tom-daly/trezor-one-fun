#!/usr/bin/env python3
"""plant_storage.py - provision + plant a Trezor-v4 storage image on the
socketed F205, keyed to THE CHIP'S OWN identity, mirroring the real first-boot
hardware_salt derivation.

Real firmware (trezor-firmware-legacy-v1.13.1/legacy/firmware/trezor.c
collect_hw_entropy + storage/storage.c):
  HW_ENTROPY   = UID(12 @ 0x1FFF7A10)  ||  OTP block 3 (32 @ 0x1FFF7860)
  hardware_salt = SHA256(HW_ENTROPY)                       -> storage.c .bss static
  First boot: if OTP block 3 is UNLOCKED -> write 32 RANDOM bytes + LOCK it
              (lock byte 0x00 @ 0x1FFF7A00+3 = 0x1FFF7A03).
So the real salt depends on a random, locked, debug-unreadable OTP block: it can
only be recovered from firmware .bss in SRAM, never recomputed offline. This
script reproduces that provisioning so the clone is faithful.

Flow (RDP0 only - SWD flash + OTP writes; practice board only):
  1. read the chip's real UID over SWD (always readable at RDP0).
  2. OTP block 3: keep as-is (blank=FF on a fresh chip), or provision + lock
     (G_OTP=random mirrors real fw; or a 64-hex value). OTP writes are ONE-TIME
     and permanent per chip.
  3. hardware_salt = SHA256(UID || OTP3) from the chip's ACTUAL values.
  4. build the v4 storage image for that salt + chosen PIN/mnemonic
     (make_storage.build), erase the storage sector, program it, verify.
  5. write known-answer.json (uid/otp/salt/pin/mnemonic/keys).

Env:
  G_OTP      keep (default) | random | <64 hex>   OTP block 3 provisioning
  G_PIN      PIN string (default: random 6-digit)
  G_MNEMONIC BIP39 words (default: generated 24-word)
  G_OUT      known-answer.json path (default ./known-answer.json)
  G_STORAGE_OUT  storage image path (default ./storage.bin)
"""
import hashlib
import json
import os
import secrets
import struct
import sys
import time

sys.path.insert(0, '/home/tdaly/trezor-btc')
sys.path.insert(0, '/home/tdaly/trezor-btc/storage-sim')

import chipwhisperer as cw                       # noqa: E402
from swd.stlink import Stlink                     # noqa: E402
from _practice_guard import require_practice_board  # noqa: E402
import make_storage                               # noqa: E402

# flash controller
FLASH = 0x40023C00
KEYR, SR, CR = FLASH + 4, FLASH + 0xC, FLASH + 0x10
KEY1, KEY2 = 0x45670123, 0xCDEF89AB
STORAGE = 0x08008000
STORAGE_SECTOR = 2
# identity (matches real firmware)
UID_ADDR = 0x1FFF7A10
OTP_BASE = 0x1FFF7800
OTP_LOCK_BASE = 0x1FFF7A00
OTP_BLOCK = 3                                     # FLASH_OTP_BLOCK_RANDOMNESS
OTP_BLOCK_SIZE = 32
OTP3_ADDR = OTP_BASE + OTP_BLOCK * OTP_BLOCK_SIZE   # 0x1FFF7860
OTP3_LOCK = OTP_LOCK_BASE + OTP_BLOCK               # 0x1FFF7A03


def wait_bsy(st):
    for _ in range(4000):
        if st.get_mem32(SR) & (1 << 16) == 0:
            return True
        time.sleep(0.002)
    return False


def flash_unlock(st):
    # Only unlock if currently LOCKED - writing KEYR while already unlocked
    # faults the DP. Makes every flash op's unlock idempotent.
    if st.get_mem32(CR) & (1 << 31):
        st.set_mem32(KEYR, KEY1)
        st.set_mem32(KEYR, KEY2)


def erase_sector(st, sector):
    flash_unlock(st)
    wait_bsy(st)
    cr = (1 << 1) | (sector << 3) | (2 << 8)      # SER | SNB | PSIZE=word
    st.set_mem32(CR, cr)
    st.set_mem32(CR, cr | (1 << 16))              # STRT
    wait_bsy(st)
    st.set_mem32(CR, 0)


def program_words(st, addr, data):
    flash_unlock(st)
    wait_bsy(st)
    st.set_mem32(CR, (2 << 8) | 1)                # PG | PSIZE=word
    for off in range(0, len(data), 4):
        st.set_mem32(addr + off, struct.unpack('<I', data[off:off + 4])[0])
        wait_bsy(st)
    st.set_mem32(CR, 0)


def program_bytes(st, addr, data):
    """Byte programming (PSIZE=byte) - OTP + lock, exactly as flash_program_byte."""
    flash_unlock(st)
    wait_bsy(st)
    st.set_mem32(CR, (0 << 8) | 1)                # PG | PSIZE=byte
    for i, b in enumerate(data):
        st.write_mem8(addr + i, bytes([b]))
        wait_bsy(st)
    st.set_mem32(CR, 0)


def otp_is_locked(st):
    return bytes(st.read_mem8(OTP3_LOCK, 1))[0] == 0x00


def main():
    require_practice_board('plant_storage.py (provisions OTP + programs flash)')
    otp_mode = os.environ.get('G_OTP', 'keep')
    pin = os.environ.get('G_PIN') or f'{secrets.randbelow(1000000):06d}'
    mnem = os.environ.get('G_MNEMONIC') or make_storage.gen_mnemonic(256)  # 24 words
    out_json = os.environ.get('G_OUT', 'known-answer.json')
    out_bin = os.environ.get('G_STORAGE_OUT', 'storage.bin')

    # power-on fresh (avoids stale-DP wedges), run via SWD (boot pins irrelevant)
    s = cw.scope()
    s.io.target_pwr = True
    time.sleep(2)
    s.io.target_pwr = False
    time.sleep(2)
    s.io.target_pwr = True
    time.sleep(3)
    s.dis()
    st = Stlink(swd_frequency=480000)

    rdp = (st.get_mem32(0x40023C14) >> 8) & 0xFF
    if rdp != 0xAA:
        sys.exit(f'RDP byte 0x{rdp:02X} != 0xAA (L0) - flash/OTP writes need RDP0. '
                 'Run set_rdp0.py (mass-erase) first, or use a blank chip.')

    # --- 1. read the chip's real UID (address-order bytes = HW_ENTROPY[0:12]) ---
    uid = bytes(st.read_mem8(UID_ADDR, 12))
    print(f'[1] UID @ 0x{UID_ADDR:08X} = {uid.hex()}')

    # --- 2. OTP block 3 provisioning ---
    locked = otp_is_locked(st)
    cur_otp = bytes(st.read_mem8(OTP3_ADDR, OTP_BLOCK_SIZE))
    print(f'[2] OTP block 3 @ 0x{OTP3_ADDR:08X} locked={locked} '
          f'cur={cur_otp.hex()}')
    blank_otp = all(b == 0xFF for b in cur_otp)
    if otp_mode == 'keep':
        otp3 = cur_otp
        print('    G_OTP=keep -> using current OTP (no write)')
    elif locked:
        otp3 = cur_otp
        print('    OTP block 3 already LOCKED -> using existing value.')
    else:
        if not blank_otp:
            # OTP already written (e.g. an interrupted run). OTP is ONE-TIME
            # (bits only FF->0), so DO NOT rewrite - keep it, just lock it.
            otp3 = cur_otp
            print(f'    OTP already written ({otp3.hex()}) + unlocked -> '
                  'keeping it, locking.')
        else:
            if otp_mode == 'random':
                otp3 = secrets.token_bytes(OTP_BLOCK_SIZE)    # mirror real fw
            else:
                otp3 = bytes.fromhex(otp_mode)
                if len(otp3) != OTP_BLOCK_SIZE:
                    sys.exit('G_OTP hex must be 32 bytes (64 hex).')
            print(f'    writing OTP3 <- {otp3.hex()} (then LOCK), like '
                  'collect_hw_entropy...')
            program_bytes(st, OTP3_ADDR, otp3)
        program_bytes(st, OTP3_LOCK, bytes([0x00]))           # lock the block
        back = bytes(st.read_mem8(OTP3_ADDR, OTP_BLOCK_SIZE))
        if back != otp3 or not otp_is_locked(st):
            sys.exit(f'OTP provision FAILED (readback {back.hex()} '
                     f'locked={otp_is_locked(st)})')
        print('    OTP3 provisioned + locked (one-time, permanent).')

    # --- 3. hardware_salt from the chip's ACTUAL identity ---
    hw_salt = hashlib.sha256(uid + otp3).digest()
    print(f'[3] hardware_salt = SHA256(UID||OTP3) = {hw_salt.hex()}')

    # --- 4. build the v4 storage image keyed to this salt + chosen PIN/seed ---
    img, answer = make_storage.build(pin, mnem, uid, otp3)
    assert bytes.fromhex(answer['hardware_salt']) == hw_salt, 'salt mismatch!'
    open(out_bin, 'wb').write(img)

    # erase sector then program
    head = bytes(st.read_mem8(STORAGE, 16))
    if any(b != 0xFF for b in head):
        print(f'[4] storage not blank ({head.hex()}) - erasing sector '
              f'{STORAGE_SECTOR}')
        erase_sector(st, STORAGE_SECTOR)
    program_words(st, STORAGE, img)
    got = b''
    while len(got) < len(img):
        n = min(64, len(img) - len(got))
        got += bytes(st.read_mem8(STORAGE + len(got), n))
    if got != img:
        sys.exit('[!] storage readback MISMATCH')
    print(f'[4] storage programmed @ 0x{STORAGE:08X} ({len(img)} B), readback PASS')

    # --- 5. record ---
    open(out_json, 'w').write(json.dumps(answer, indent=2))
    print(f'[5] known-answer.json -> {out_json}')
    print(f'    PIN      = {pin}')
    print(f'    mnemonic = {mnem}')
    print(f'    uid={uid.hex()}  otp3={otp3.hex()}')
    print('[+] DONE. Faithful clone: storage keyed to the chip\'s real '
          'UID+OTP. Salt lives only as SHA256(UID||OTP) - lift it from .bss '
          '(generate_bss.py / real fw) to decrypt.')

    try:
        st._com._usb = None
        del st
    except Exception:
        pass


if __name__ == '__main__':
    main()
