# RDP1 → DUMP → SEED — the story of cracking chip-c

*How a readout-protected STM32F205 gave up its PIN and 24-word seed, end to end,
on 2026-11-03. A faithful Trezor-One model (chip-c), attacked with only what a
real locked device yields: a voltage-glitched flash dump and a SRAM scrape.*

---

## The target

chip-c is a socketed STM32F205RET6 — a sibling die of our earlier chip-a (same
wafer, UID `3d0031001547333032303138` vs `3e...`). We built it into a faithful
Trezor-One model so a win here means the method works on the real thing:

- **RDP level 1.** SWD can read SRAM but *not* flash, OTP, UID, or system memory;
  the ROM bootloader answers `0x7F→0x79` but **NACKs Read Memory** (`1f`). That
  NACK is the wall.
- **Random, locked OTP.** `plant_storage.py` provisioned OTP block 3
  (`0x1FFF7860`) with 32 random bytes and locked it — exactly like a real Trezor
  first boot (`collect_hw_entropy`). Value: `0c7afc72…b67236`. It is now
  one-time, unreadable over the debug port, and **impossible to guess**.
- **Resident salt-firmware** at `0x08000000` that, on every boot, reads the
  chip's own UID + OTP and computes
  `hardware_salt = SHA256(UID‖OTP) = c03bb669…e875794c`
  into a `.bss` static — mirroring `storage.c`. (Validated auto-generating on a
  BOOT0-low boot with no injection.)
- **Planted v4 storage** at `0x08008000` holding PIN **<redacted>** and a 24-word
  mnemonic, encrypted under that salt.

The secret we're after is encrypted with a key derived from a PIN we don't know
and a salt built from an OTP we can't read. The only openings: SRAM (readable at
RDP1) and a glitch.

---

## Building the test target (how chip-c was loaded)

chip-c started as a blank part. We provisioned it to look like a real
post-first-boot Trezor, then locked it — each step verified with
`investigate_chip.py` (authoritative RDP level from the option bytes, plus what's
readable). The guard `G_PRACTICE_BOARD=YES` is required on every chip-modifying
script so none of this can ever fire at the real device.

```bash
# 0) if the chip was already locked, wipe it back to a blank RDP0 first.
#    RDP1->RDP0 is a mass-erase, done via the bootloader's Readout Unprotect
#    (0x92) command over UART (the SWD option-downgrade didn't commit on this rig).
G_PRACTICE_BOARD=YES python wipe_chip.py

# 1) provision like a real first boot, keyed to the CHIP'S OWN identity:
#    read its UID, write + LOCK a random 32-byte OTP block 3 (== collect_hw_entropy),
#    derive hardware_salt = SHA256(UID||OTP), build a v4 norcow storage image for
#    a generated 6-digit PIN + 24-word seed, program it at 0x08008000, and write
#    known-answer.json.  (plant_storage.py calls make_storage.py internally.)
G_PRACTICE_BOARD=YES G_OTP=random \
  G_OUT=chips/chip-c/known-answer.json G_STORAGE_OUT=chips/chip-c/storage.bin \
  python plant_storage.py
#   -> OTP 0c7afc72…  salt c03bb669…  PIN <redacted>  (+ 24-word mnemonic)

# 2) flash the resident salt-firmware at 0x08000000: on every boot it reads the
#    chip's own UID + OTP and writes SHA256(UID||OTP) into a .bss static (like
#    storage.c). This step builds it, flashes it, and PROVES it auto-generates
#    the salt on a BOOT0-low boot with no debugger injection.
G_PRACTICE_BOARD=YES python validate_auto_bss.py
#   (generate_bss.py is the alternative: SWD-inject a known salt into .bss
#    without firmware — a stand-in before the real salt-firmware existed.)

# 3) lock it. RDP0 -> RDP1 writes option byte RDP=0xBB; it does NOT erase, so
#    the storage and firmware survive. Now flash/OTP/UID are debug-blocked and
#    the bootloader NACKs Read Memory — a genuine RDP1 target.
G_PRACTICE_BOARD=YES python set_rdp1.py
```

At this point chip-c is indistinguishable, for attack purposes, from a locked
production device: a random unreadable OTP, firmware that re-derives the salt
into SRAM every boot, encrypted storage behind the RDP1 wall — and a
`known-answer.json` we keep only so we can *grade* the crack.

## The shape of the attack

`hardware_salt = SHA256(UID‖OTP)` is the crux. You can't recompute it — the OTP
is random and locked. But the **firmware already computed it** and left it in
`.bss`. So the recovery splits in two:

| Half | Where it lives | How we take it |
|------|----------------|----------------|
| **the salt** | firmware `.bss` in SRAM | SWD reads SRAM at RDP1 — **no glitch** |
| **the storage** | flash `0x08008000` | glitch the bootloader's RDP1 NACK → ACK |

Then, offline: storage + salt → PBKDF2 → ChaCha20 → PIN → mnemonic.

### Half one: the salt, for free

Power on BOOT0-low so the salt-firmware runs and fills `.bss`; attach SWD; dump
all 128 KB of SRAM. The salt sits right at the start of `.bss`:

```
rdp1_sram_dump.py  (BOOT0 low)
0x20000000  c0 3b b6 69 …   → chips/chip-c/sram_*.bin
flash BLOCKED (RDP1)  ·  SRAM readable  ·  salt found at 0x20000000
```

No glitch, no drama. On a real device the firmware does the same thing every
boot; you just read it out of SRAM in the RDP1 window.

### Half two: the storage, through the wall

This is the fun part.

---

## The glitch rig

The STM32 bootloader validates the `0x11 0xEE` Read-Memory command, and at RDP1
it refuses — sending `1f 1f`. A sharp collapse of the **VCAP core rail** (1.2 V)
at exactly the right instant corrupts that decision, and the bootloader ACKs
(`79`) and hands over 256 bytes instead.

Wiring (one net is the trick):

```
FTDI TX ──┬── QFP64 RX (PA10 / pin 43)      ← command arrives here
          └── CW TIO3 (high-Z trigger tap)  ← CW triggers on the command edge
QFP64 TX (PA9 / pin 42) → FTDI RX           ← bootloader replies
TIO1 → BOOT0 (pin 60, high)   TIO2 → BOOT1 (pin 28, GND)   TIO4 → NRST
Crowbar SMA → VCAP (pin 31)                 ← the pull
```

The CW watches the outgoing command on TIO3, waits a tuned number of cycles, and
fires a crowbar pulse into VCAP. Window is measured in **µs after the TIO3 edge**.

**Proven parameters (carried from chip-a, transferred to the sibling die):**
166.67 MHz clkgen · `enable_only` · crowbar `hp+lp` · offset −45 ·
**rep6 (36 ns) / rep7 (42 ns)** random · window **180–182 µs** (sweet spot
~180.2–181.9) · reset per shot.

---

## The run

### Dry-fire first (glitch commented out)

Before firing anything real, we ran the whole campaign with `G_CROWBAR=0` — the
trigger and comms alive, the FET disarmed. Result: bootloader synced, 20 shots
all clean `nack (1f1f)`, resets fine. The pipeline — boot, UART, command burst,
TIO3 trigger, reset loop — was proven end to end with zero risk.

### Then, live

First live pass landed a clean flip at shot **#79** and read storage_0000 —
byte-for-byte correct. The "hard part" (bypassing RDP1 and completing a Read
Memory) worked on the first real attempt.

### Two detours worth remembering

1. **The stale oracle.** The campaign byte-compares each read against a reference
   `storage.bin`. Ours was an old build, so correct reads were flagged
   `oracle=MISMATCH` and rejected. Fix: `G_ORACLE=chips/chip-c/storage.bin`. The
   glitch was never wrong — the yardstick was.
2. **The scope was damping the glitch.** The Siglent, still on the VCAP SMA-T,
   added ~15–20 pF that softened the crowbar pull — `dead` brownouts but no clean
   flips (the LDO recharges the node faster than a loaded pulse can collapse it).
   Pulling the scope off the node restored full strength immediately. *Measure
   between passes, never during.*

### Banking the chunks

Scope off, oracle correct, the flips came at the expected ~1/700–800:

```
storage_0000  ext=30259 (181.6 µs)  rep6=36 ns   oracle=MATCH
storage_0001  ext=30315 (181.9 µs)  rep7=42 ns   oracle=MATCH
storage_0002  ext=30119 (180.7 µs)  rep7=42 ns   oracle=MATCH   (resumed 0/1, farmed 2)
```

A detail that mattered: **2 chunks gave the PIN but not the mnemonic.** chunk 0
holds the EDEK/PVC (all the PIN-crack material), so PIN `<redacted>` fell out of two
chunks instantly. But the 24-word mnemonic entry (`0x0102`, 186 B) is the last
entry — its ciphertext tail runs **past byte 512 into chunk 2**, so with only
chunks 0–1 we got `entry 0102: TAG MISMATCH`. One more flip (chunk 2) completed
it.

---

## The payoff

Assemble chunks 0–2 (768 B, FF-padded), feed the `.bss` salt, decrypt:

```
*** PIN FOUND: <redacted> ***
entry 0102: <redacted>
```

Exact match to the known answer. **The locked chip gave up its seed** — through a
voltage glitch for the storage and a SRAM read for the salt, nothing else.

---

## What carries to the real device

- **512 KB vs 1 MB doesn't matter.** Storage is at a fixed address; sectors 0–4
  are identical on both parts. Total flash size only differs up in the firmware
  region, which we never touch.
- **Real storage is two norcow sectors** (`0x08008000` + `0x0800C000`, 32 KB) and
  the *active* one can be either. The campaign now defaults to covering **both**
  (`G_STORAGE_LEN=0x8000`), grabbing the head of each sector; chip-c's
  single-sector plant uses `G_STORAGE_LEN=0x4000`.
- **Skip the uncrackable targets.** `G_EXTRA=0` drops uid/otp3 — the `0x1FFF`
  region is refused at the address stage even with the gate glitched (15k shots,
  0 reads). You never need them: the salt comes from `.bss`.
- **Only chunks 0–2 are needed** — chunk 0 → PIN, chunks 1–2 → mnemonic;
  everything past that is blank `FF` tail.

---

## The scripts (what each one does)

All run with `/home/tdaly/.cwvenv/bin/python`. Chip-modifying ones require
`G_PRACTICE_BOARD=YES`.

**Build / provision the target**
| script | role |
|--------|------|
| `wipe_chip.py` | RDP1→RDP0 **mass-erase** via bootloader Readout Unprotect (`0x92`) → blank chip |
| `plant_storage.py` | read UID, provision + **lock a random OTP** (block 3), derive salt, build + program v4 storage at `0x08008000`, write `known-answer.json` |
| `make_storage.py` | build a v4 norcow storage image for a given UID/OTP/PIN/mnemonic (used by `plant_storage`) |
| `erase_storage.py` | SWD erase of the storage sector only (re-plant without a full wipe) |
| `validate_auto_bss.py` | build + flash the salt-firmware at `0x08000000`; prove it auto-fills `.bss` on a BOOT0-low boot |
| `generate_bss.py` | alternative: SWD-inject a known salt into SRAM `.bss` (no firmware) |
| `set_rdp1.py` | lock RDP0→RDP1 (writes `0xBB`; refuses `0xAA`/`0xCC`; no erase) |

**Inspect**
| script | role |
|--------|------|
| `investigate_chip.py` | authoritative read-only state: RDP level from option bytes, cross-checked against flash readability + core state; optional OpenOCD second opinion (`G_OPENOCD=1`) |

**Attack**
| script | role |
|--------|------|
| `rdp1_sram_dump.py` | dump SRAM over SWD (boot firmware BOOT0-low first → the `.bss` salt). `G_OUT_DIR` sets the output folder |
| `rdp1_glitch_campaign_full_mem_dump.py` | **glitch-2**: voltage-glitch the RDP1 Read-Memory NACK→ACK and bank storage chunks (`oracle=MATCH` on practice) |
| `decrypt_storage.py` | offline: assembled storage + salt → PBKDF2 v4 → ChaCha20 → brute PIN → mnemonic |

## Reproduce it

```bash
# 1) salt (no glitch): BOOT0-low boot lets firmware fill .bss, then dump SRAM
G_OUT_DIR=chips/chip-c python rdp1_sram_dump.py          # salt @ 0x20000000

# 2) storage (glitch-2): scope OFF VCAP; TIO3 on PA10; crowbar on pin 31
G_ORACLE=chips/chip-c/storage.bin G_CROWBAR=1 G_LP=1 \
  G_US_MIN=180 G_US_MAX=182 G_RND_REP=1 G_RND_LO=33 G_RND_HI=45 \
  G_TARGETED_N=3 G_EXTRA=0 G_STORAGE_LEN=0x4000 G_PASSES=5 \
  python rdp1_glitch_campaign_full_mem_dump.py
# resume across runs / FTDI churn:  add  G_RESUME=dumps/run_<prev>

# 3) recover: assemble banked chunks 0-2, decrypt with the salt (uid/otp here)
python decrypt_storage.py <assembled.bin> \
  --uid 3d0031001547333032303138 \
  --otp3 0c7afc7213bd9c4274086851d771c5d77d785899cbdc41407a42aef7a5b67236 \
  --pin <redacted>            # or --brute 000000-999999 for the blind case
```

See `FINDINGS.md` for the full log and `rig.md` for the wiring. On the real
device: `G_STORAGE_LEN=0x8000` (both sectors) and the device's own `.bss` salt —
the mechanism is identical.
