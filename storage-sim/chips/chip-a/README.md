# CHIP_A_UID — archived data (chip "STM32_TEST_CHIP_A")

All dumps, keys, and SRAM captures produced up to **2026-11-02** belong to this
one physical chip. Archived here (data preserved; the chip is kept for further
testing) so it is not confused with the fresh bench chip we moved to.

## Chip identity
- **STM32F205RET6**, LQFP64, DEV_ID `0x411`, 512 KB flash.
- **Unique ID (UID): `3e0031001547333032303138`**
- OTP3: blank (`ff`×32).
- NOTE — the current blank bench chip is a **sibling die** from the same wafer:
  UID `3d0031001547333032303138` (differs ONLY in the first byte, `3E` vs `3D`
  = wafer X/Y coord). Tell them apart by that first byte.

## Known answer (planted practice secret) — `known-answer.json` (NOT committed)
- PIN **<redacted — see known-answer.json>**, storage version 4.
- mnemonic: **<redacted — see known-answer.json>** (12 words)
- random_salt `17773784`, hardware_salt
  `99ed0b39e41e65462f833c7f1d4bb454314bc2c218e6d163c2c8b88d610aeeb5`.
- Full KEK/KEIV/DEK/SAK in the JSON.

## Status as of 2026-11-02 (end of session)
- Last seen **RDP1**, chip alive (VDD 3.3 V, SWD attaches, SRAM readable,
  flash/OTP/UID blocked = consistent with RDP1).
- BUT with BOOT0 high the core sits in **LOCKUP** (PC=0, all-FF boot vectors)
  and never runs the system bootloader → **no `0x7F` ACK** — abnormal. The
  identical rig ACKs a blank sibling chip perfectly, so this is **chip-specific,
  not a rig fault**. Open question: why this part won't run its bootloader
  (damage? weird option/flash state?). Worth revisiting.

## Key proven result in the dumps
- `dumps/.../storage_0000.bin` first16 = `4e524332 faffffff 02003c00 ...`
  = the planted NRC2 data, recovered via a single UART-triggered VCAP crowbar
  glitch at RDP1 → the RDP1 readout-protection bypass proof (2026-10-30).

## Contents
- `dumps/` — all glitch output: storage chunks, full flash (`flash_fulldump.bin`
  512 KB), full SRAM (`sram_fulldump.bin` 128 KB), per-run manifests/logs,
  `accum/`, `overnight/`, rehearsal archives.
- `known-answer.json` — the planted secret + derived keys.
- `uid.hex`, `otp3.hex` — chip UID / OTP.
- `storage*.bin`, `readback.bin`, `uart-*.bin` — earlier storage/UART captures.

See `../../FINDINGS.md` for full chronological history and `../../rig.md` for wiring.

## Campaign logs (added 2026-11-02)
- `campaigns/` — 79 campaign CSVs (glitch1 / glitch1bl / glitch2 per-shot
  logs, 2026-10-29 .. 2026-11-02). All CHIP_A.
- `opencode_logs/` — 31 live tee logs copied from /tmp/opencode (fulldump,
  fullwin, cal182, campaign_status, g1_* etc.) — preserved before the blank
  chip's runs overwrite those /tmp paths.

## More CHIP_A archives (added 2026-11-02, batch 2)
- `archive/` — cycle snapshots (2026-11-01_cycle1).
- `scope_captures/` — scope capture sessions (range_hit, repeat_ladder).
- `la_captures/` — logic-analyzer .sr captures (from ../la/; la/ scripts kept as tooling).
- `SRAM_20261011_192819/` — early SRAM dump (was in project root).
