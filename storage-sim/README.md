# Storage simulation — Trezor v4 on the F205 socket rig

Synthetic Trezor-legacy storage with a **known seed and PIN**, flashed to the
clean F205 at `0x08008000` — a fully verifiable rehearsal target for the
dump → offline-decrypt pipeline before the locked device's real dump.

## Glitch attack — RDP1 bypass, PROVEN end-to-end (2026-10-30)

Voltage-glitch the STM32F2 system-bootloader Read Memory RDP check, dump the
storage, decrypt offline. Verified on the planted rehearsal board:
**PIN `9434` + the full mnemonic were recovered from glitch-dumped memory**
(brute-force 9,435 candidates, 56 s; matches `known-answer.json`).
Chain: glitch RDP1 → Read Memory → NORCOW head → offline PIN brute-force →
decrypt → PIN + seed.

**You only need ~5 targets, not the full 16 KB.** All secrets (EDEK/PVC at
(0,2) + the encrypted mnemonic at (1,2)) live in the NORCOW head = storage
chunks 0–2; chunks 3–63 are blank (0xFF) free space. The campaign therefore
**defaults to targeted**: `storage_0000..0004 + uid + otp3` (7 reads).
`G_FULL=1` dumps the whole 16 KB (mostly blank, for a complete image);
`G_TARGETED_N` sets how many head chunks.

### Rig / attack parameters (verified this chip)
- Chip **STM32F2xx** (DEV_ID `0x411` via `DBGMCU_IDCODE`) — RDP + WRP only,
  **no PCROP/SPRMOD** (so a glitched read never returns a masked pattern; FF =
  genuinely erased flash).
- CW-Lite crowbar (`glitch_hp`+`glitch_lp`) on **VCAP** (1.2 V core rail);
  trigger = TIO3 edge on the `0x11 0xEE` burst; `clkgen 166.67 MHz`.
- **Timing window `us 180–186`** (= `ext/clkgen`), i.e. the pulse landing
  ~189–195 µs after the `0x11` start — straddling the RDP decision (command-end
  ≈ us 173, NACK ≈ us 189). The `us` column sits **+8.68 µs (one bit)** behind
  the actual glitch (CW triggers on the first *rising* edge).
- **Strength `rep6–7` (36–42 ns)** = sweet spot (~2 % dead). `rep8+` is a hard
  dead-cliff (31 % dead, no flips). Sweep step `G_US_STEP=0.1`.
- **The scope MUST be OFF the VCAP node while firing** — a probe there
  (~15–20 pF) damps the glitch (acts like extra decoupling). The LA on the UART
  TX/RX lines is harmless (slow digital, not the glitch node).
- A **latching flip** (unglitched `0x11` keeps ACKing) drains every remaining
  chunk in one burst via `chain_unglitched`. In-band flip rate ≈ 1/400; a flip
  latches ≈ 1/11.
- **Confirmation layer:** oracle (vs `storage.bin`) gates storage chunks;
  cross-read (N consistent latched reads) gates uid/otp3 and is the real-device
  judge. A ghost/erase read can never be banked as real.

### Workflow (prep a known-planted RDP1 board, then glitch)
```sh
PY=/home/tdaly/.cwvenv/bin/python
$PY set_rdp0.py        # RDP1->RDP0 downgrade + mass-erase (needs a power-cycle re-read mid-way)
$PY plant_storage.py   # SWD-program storage.bin @ 0x08008000
$PY uart_rdp0_test.py  # verify: Read Memory ACKs @ RDP0, NRC2 canary intact
$PY set_rdp1.py        # re-arm RDP1 (0x55) -> Read Memory NACKs again
# glitch-dump (TARGETED by default: storage head + uid + otp3):
G_CLKGEN=166666667 G_OFFSET=-45 G_WIDTH=5 G_US_MIN=180 G_US_MAX=186 \
  G_US_STEP=0.1 G_RND_LO=33 G_RND_HI=45 \
  $PY -u rdp1_glitch_campaign_full_mem_dump.py       # + G_FULL=1 for the whole 16 KB
# offline recovery from the glitch-dumped chunks:
$PY decrypt_storage.py storage_from_glitch.bin --brute 0000-9999 --uid <12B-uid-hex>
```
Real locked device: same chain; the UID is glitched out too (SWD blocked at
RDP1), and `otp3` comes from the OTP read. See `FINDINGS.md` for the full
campaign history and calibration data.

## Files

| File | Purpose |
|---|---|
| `rdp1_glitch_campaign_full_mem_dump.py` | **The glitch campaign**: voltage-glitch RDP1 Read Memory → dump storage head (+uid/otp3). Targeted by default; `G_FULL=1` for all 16 KB. Env-var config in its header |
| `set_rdp0.py` / `set_rdp1.py` | Downgrade RDP1→RDP0 (+mass-erase) / re-arm RDP1 (0x55) over SWD — prep the rehearsal board |
| `plant_storage.py` | SWD-program `storage.bin` into flash @ `0x08008000` (region must be erased) |
| `uart_rdp0_test.py` | Verify a planted board at RDP0: Read Memory ACKs, NRC2 canary intact |
| `full_recover.py` | End-to-end: dump storage+uid+otp3 → brute PIN → decrypt → PIN+mnemonic (self-checks `known-answer.json`) |
| `loop_fulldump.sh` | Full-dump runner: multi-pass + crash-safe `dumps/accum/` resume, assembles `storage_dump.bin` at 64/64 |
| `la/` | LA toolset (fx2lafw UART tap): `capture.sh` / `decode.sh` / `timing.py` — sanity-check comms and measure `0x11`→NACK latency without touching the glitch node (safe during firing). D0=TX, D1=RX, 115200 8E1 |
| `FINDINGS.md` | Golden-bible campaign log: every calibration, confound, and result (read before new experiments) |
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
