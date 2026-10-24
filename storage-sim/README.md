# Storage simulation — Trezor v4 on the F205 socket rig

Synthetic Trezor-legacy storage with a **known seed and PIN**, flashed to the
clean F205 at `0x08008000` — a fully verifiable rehearsal target for the
dump → offline-decrypt pipeline before the locked device's real dump.

## Files

| File | Purpose |
|---|---|
| `make_storage.py` | Generator: PIN + mnemonic + UID/OTP → norcow sector image + `known-answer.json` |
| `decrypt_storage.py` | Offline decryptor: parse image, PIN check (known or brute-force), mnemonic recovery |
| `uart_dump.py` | Bootloader UART dry run: sync → GET-ID → Read Memory (the no-glitch rehearsal of glitch-2's dump) |
| `uart-dump-storage.bin` | Full 16 KB storage sector read over UART — byte-identical to `storage.bin` |
| `storage.bin` | Generated 16 KB sector image (flash at `0x08008000`) |
| `known-answer.json` | The ground truth (PIN, seed, keys) — for verification only |
| `bip39-english.txt` | BIP39 wordlist (mnemonic generation) |
| `trezor-1.13.1.bin` | Official Trezor One 1.13.1 firmware (505,092 B — needs a 1 MB RGT6, not the 512 KB socket chip) |
| `reference/` | Ground-truth sources: `legacy/v1.13.1` tag — `config.c`, `otp.c`, `trezor.c`, `storage.c`, `norcow.c`, `norcow_blockwise.h`, `norcow_config.h`, `protect.c`, `bl_check.c` |

## The format (from the 1.13.1 source, verified round-trip)

- Norcow blockwise, 16 B blocks, sector 2 @ `0x08008000` (16 KB)
  - word 0 = `0x3243524E` ('NRC2'), word 1 = `~5` (layout version), items from offset 8
  - item: `KEY(2 LE) | LEN(2 LE) | data`; small (≤12 B) in one block; large
    items put a 12-byte 0xFF pad after the header, then data blocks with the
    0xFF VALID flag after the last partial block; all padding 0xFF
  - 16-bit key = `APP<<8 | key` → (APP=0,KEY=2) flashes as `02 00` (the canary)
- **hardware_salt = SHA256(UID[12] @0x1FFF7A10 || OTP block 3[32] @0x1FFF7860)**
  (`trezor.c:collect_hw_entropy`; blank OTP block = all 0xFF, deterministic)
- v4 PIN chain: `KEK‖KEIV = PBKDF2-HMAC-SHA256(pin_bytes, hw_salt‖random_salt, 10000, 44)`
  — **PIN = raw string bytes** on v4 (Kraken's packed-int form was the ≤1.9
  pre-upgrade encoding); EKEYS = ChaCha20Poly1305(KEK, KEIV, aad=∅) over
  `DEK(32)‖SAK(16)`; PVC = tag[:8]; entry (0,2) = `salt(4)‖EKEYS(48)‖PVC(8)`
- Protected entries: `IV(12)‖ENCR‖TAG(16)`, AAD = the 16-bit key LE
- (0,5) STORAGE_TAG = `HMAC(SAK, XOR of HMAC(SAK, key_u16) per protected key)[:16]`
- Entry set generated: (0,1) pin-log 132 B, (0,2) EDEK/PVC, (0,3) pin-set,
  (0,4) version=4, (0,5) tag, (1,0) UUID, (1,1) cfg-version=11 (encr),
  (1,2) mnemonic (encr), (1,7) needs-backup (encr), (1,14) initialized

## Procedure

```sh
PY=/home/tdaly/.cwvenv/bin/python

# 1. generate (defaults: this chip's UID, blank OTP, PIN 4179, random seed)
$PY make_storage.py [--pin N] [--mnemonic "words..."]

# 2. flash to the chip (sector 2)
st-flash --format bin write storage.bin 0x08008000

# 3. dump it back (SWD readback rehearsal)
$PY -c "from swd.stlink import Stlink; st=Stlink(swd_frequency=480000); \
open('readback.bin','wb').write(b''.join(st.get_mem32(0x08008000+i).to_bytes(4,'little') for i in range(0,0x4000,4)))"

# 4. offline decrypt — must recover the known answer
$PY decrypt_storage.py readback.bin --pin 4179 --uid 3e0031001547333032303138
$PY decrypt_storage.py readback.bin --brute 0000-9999 --uid 3e0031001547333032303138
```

Round-trip verified offline 2026-10-22: PIN `4179` → mnemonic recovered,
wrong PIN rejected. Brute-force rate ≈ 85+ PIN/s single-core (matches Kraken).

## For the real locked device

The decryptor is parameterized for exactly this: `--uid`/`--otp3` from the
dump/OTP read, image from the glitch-2 flash dump. Two open format questions
resolve themselves from the dump: norcow layout version (word 1) and the
(0,4) storage version — if version ≥ 5, the PIN chain switches to the
stretched-PIN path (`stretch_pin`, zero nonce) — add that branch if needed.
Kraken's packed-int PIN form only applies to never-upgraded ≤1.9 storages.
