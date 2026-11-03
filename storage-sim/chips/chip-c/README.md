# chip-c — faithful practice clone (random+locked OTP)

STM32F205RET6, sibling die of chip-a (same wafer).
- **UID: `3d0031001547333032303138`** (chip-a is `3e...`).
- 512 KB flash, Cortex-M3, DEV_ID 0x411.

## Provisioned 2026-11-03 (plant_storage.py, G_OTP=random) — models a real first boot
plant_storage read the chip's real UID, **provisioned OTP block 3 with 32 random
bytes + LOCKED it** (exactly like `collect_hw_entropy`), derived the salt from the
chip's ACTUAL UID+OTP, and planted v4 storage keyed to it. Decrypt round-trip PASS.

Known answer (`known-answer.json`, **NOT committed**):
- **PIN `<redacted>`** (6-digit), storage v4.
- **24-word mnemonic**: `<redacted — see known-answer.json>`
- **OTP block 3 (0x1FFF7860): `0c7afc7213bd9c4274086851d771c5d77d785899cbdc41407a42aef7a5b67236`**
  — LOCKED, one-time, permanent. Survives a mass-erase (it's in the system region).
- **hardware_salt = `c03bb669684482a3731aa83c183d13f4f118550c38a7a9daaa2707c5e875794c`**
  = SHA256(UID ‖ OTP3).

## Why this is the real scenario
- The salt is NOT recomputable offline: assuming blank OTP (`FF×32`) gives the
  WRONG salt `60167b7b...`; the true one needs the random OTP.
- At RDP1/2 the OTP is debug-unreadable AND locked → the salt exists only as the
  firmware's computed value in SRAM `.bss`. Recover it there (`generate_bss.py`
  stand-in / real fw), never by reading OTP.

## Status
- **RDP0** (just reprovisioned). OTP readable here; blocked once locked to RDP1.
- Next: `generate_bss.py` to put the salt in `.bss`, then `set_rdp1.py` (glitch-2
  target) — or set RDP2 for the full glitch-1 scenario.

## Files (data only; scripts live in ../../)
- `known-answer.json`, `storage.bin`, `sram_bss_dump.bin`.

## Resident salt-firmware (auto .bss) — validated 2026-11-03
Flashed a tiny salt-firmware at `0x08000000` (sector 0; storage sector 2
untouched) that on boot reads UID + OTP block 3 and computes SHA256 into a `.bss`
static - like real fw. Validated with `validate_auto_bss.py`: BOOT0-low power
cycle -> firmware auto-ran (hw_ready=0xA5), `.bss hardware_salt` = `c03bb669...`
= known answer, with NO SWD injection. So on every boot the salt is auto-present
in SRAM (reading the real, locked, offline-unknowable OTP) - the genuine recovery
mechanism. Firmware is reproducible from validate_auto_bss.py (source embedded).

## RDP1 lock + full validation — 2026-11-03
set_rdp1.py -> RDP byte 0xBB (no erase; firmware + storage survive). Validated
the real-device recovery scenario at RDP1 (BOOT0-low boot, then SWD):
- firmware auto-ran (hw_ready=0xA5); hardware_salt @ .bss 0x20000000 =
  c03bb669... readable via SWD SRAM (NO glitch needed for the salt).
- storage/flash/OTP3/UID all BLOCKED over SWD -> OTP unreadable (can't recompute
  salt), storage needs glitch-2 (bootloader Read Memory bypass).
chip-c is now a COMPLETE faithful RDP1 glitch-2 target with a known answer.
Recovery chain to practice: (1) salt = boot BOOT0-low, SWD-read .bss@0x20000000;
(2) storage = glitch-2 dump @0x08008000; (3) offline brute PIN (<redacted>;
1e6 space) -> mnemonic.
