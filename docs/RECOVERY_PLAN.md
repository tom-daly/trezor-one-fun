# Trezor One Seed Recovery Plan

> Legitimate self-recovery of the owner's own locked Trezor One (PIN lost, backup phrase misplaced). Not an attack on a third party's device.

**Target:** own Trezor One (locked out, backup phrase lost) · **MCU:** STM32F205 · **Firmware:** 1.13.1
**Last updated:** 2026-10-11 · **Blocked on:** glitch 2 — offset window + pulse width (see §2); shunt/scope recon still pending

---

## 1. Current state (confirmed live)

| Fact | Value | How we know |
|---|---|---|
| Chip | STM32F2 (DEV_ID 0x411) | DBGMCU_IDCODE = `0x200F6411` |
| Core | Cortex-M3 r2p0 | SCB CPUID = `0x412FC230` |
| Read protection | **RDP level 1** | FLASH_OPTCR = `0x0FFFFFED` (RDP byte `0xFF`); SWD connects, flash reads fault |
| PCROP | **off** | OPTCR bit31 SPRMOD = 0 → rules out PCROP as cause of zeros |
| PIN | **lost** → brute-force | user |
| Passphrase | **UNKNOWN — see risks** | user (unanswered) |
| Trezor bootloader | **fails the firmware's signature check** — "Unknown bootloader detected, unplug, contact support" on firmware boot (user, 2026-10-11) | screen; timing of first appearance unknown (possibly standing/device history) |

The "unknown bootloader" message means the boot chain itself works (Trezor bootloader runs + jumps; firmware runs + renders the error) — only the firmware↔bootloader mutual signature check fails. **Irrelevant to the dump path**: the STM32 system BootROM + UART path is independent of the Trezor bootloader, and the seed lives in storage (`0x08008000`), not the bootloader region. Verify storage integrity first thing once reads work (norcow header canary).

RDP1 is the *recoverable* case (level 2 would permanently kill SWD). Good.

### Rig (confirmed from photos + user)
- Decoupling caps **removed**. Glitch injected on a **separate pad — VCAP** (VoidStar-style), *not* VCC. **All wiring now routes via the breadboard** (no direct CW→Trezor wires): GLITCH comes off the CW SMA-footprint **middle pad** (soldered pin + female jumper) → breadboard column → VCAP; triggers TIO4→col→RST and TIO3→col→SWDIO; power via + rail. Keep glitch jumpers short — breadboard inductance blunts the pulse. Full diagram: ASCII wiring diagram in `docs/WIRING_SETUP.md`.
- VCC (blue) = power only, on the + rail. GND (purple) common.
- **Triggers wired:** TIO4 → RST (reset, glitch 1). TIO3 → SWDIO was the glitch-2-over-SWD attempt — **abandoned** (the RDP check to skip only runs in the UART bootloader's Read Memory handler); TIO3 is now free to become the UART-trigger input.
- SWD via separate **ST-Link** (SWDIO=blue to reader/orange to Trezor; SWCLK=white to reader/brown to Trezor). SWO (yellow) unused.
- Scope MEASURE **not yet wired** → traces flat (`max 0.003`). **This is the blocker.**
- Full wiring plan for the shunt + MEAS rig: **`docs/WIRING_SETUP.md`** (pinouts, ASCII diagram, net list, shunt-drop table, verification procedure). Glitch path stays as-is: **green wire routes via the breadboard (strip 7) and solders directly to the VCAP pad on the STM32 chip**; shunt (10 Ω) goes in the VCC path only.

---

## 2. The recovery chain (two glitches)

### Glitch 1 — re-enable the integrated bootloader ✅ SOLVED
- **Trigger:** TIO4 (reset rising edge). **Params:** width 40, offset −45, repeat 20.
- **Timing:** ext_offset **17000–18900** (170–189 µs after reset) — corrupts the RDP value read from the option bytes during BootROM startup. **Very consistent — first try at 17000** (2026-10-11, `1-trezor_fun.py`: width 39.84375, offset −44.921875, repeat 20, SWD live in 6.5 s; re-verified same day with `1-recon_glitch_trace.py` after the re-canary — SUCCESS first shot at 17000, flash refused = RDP1 as expected). Start sweeps at `G_EXT_MIN=17000`; anything below is wasted crowbar shots. (The earlier "lands only after 17000" read was an artifact of `1-recon_glitch_trace.py`'s old flash canary — see §3.)
- **Effect (Kraken):** re-enables the STM32 **integrated BootROM bootloader** with RDP-level-1 behaviour, exposing its **Read Memory command**. (We also used this glitch to confirm a live session over SWD: DBGMCU `0x200F6411`, SRAM readable-but-empty, flash still faults — but the *dump* is done over UART, not SWD.)

### Glitch 2 — bypass the RDP check during the read ❌ IN PROGRESS (2026-10-11: attempts unsuccessful)
- **Status:** glitch 1 solid — RDP1, SRAM reads blank over SWD, flash NACKs as expected. Glitch 2 so far: "successes" return **all-zeros**, and the glitch **doesn't land at the same moment every attempt**. Both symptoms are documented effects — see below.
- **Interface: UART**, STM32 system-bootloader protocol — sync `0x7F`, Read Memory `0x11`, ACK `0x79` / NACK `0x1F`, **8E1 even parity**, **256 bytes per command**. (Kraken used an FTDI FT232H; our tooling: `6-dump_flash_uart.py` over CW IO1/IO2 @9600, or `usart_read_mem.py` over `/dev/ttyUSB0`.) **Next rig (2026-10-11): wire the FTDI directly to the bootloader USART pins** — host UART on `/dev/ttyUSB0` 115200 8E1, CW for trigger + glitch only (net list: `docs/WIRING_SETUP.md`).
- **Where the RDP check really is (SecGlitcher, Ghidra on the BootROM):** `check_RDP_and_get_addr()` runs **right after the 0x11 + checksum bytes, BEFORE the first ACK** — not at the address stage as `6-dump_flash_uart.py` assumes. Their F429ZI anchor: **ext_offset 9050–9150 cycles (≈90.5–91.5 µs @ 100 MHz) from the 0x11 UART byte, at 115200, width 23–24, repeat 1**. Order-of-magnitude only — find ours via scope recon.
- **Three problems, all sourced:**
  1. **Timing jitter (why it never lands twice in the same place)** — the bootloader UART runs in a slow clock domain; every byte crosses clock domains, so handler timing wanders. SecGlitcher measured the response window: **~104 µs spread at 9600 vs ~11 µs at 115200**. We run **9600** → ~10× sloppier than needed. → **115200 8E1 over the FTDI** (`usart_read_mem.py`, `/dev/ttyUSB0`; the CW Python bit-bang can't reach 115200), sweep an offset *window*, repeat — expect overnight-scale campaigns (SecGlitcher: 622 successes overnight ≈ 155 kB).
  2. **Zeros-despite-ACK, cause A — pulse too fat.** The script still fires glitch-1's shape (width 40, offset −45, **repeat 20**) — a ~20× pulse train. SecGlitcher's bootloader hit needed **width 23–24, repeat 1** ("shortest feasible glitch"); §4 says start widths ~2–12. → **repeat 1, narrow width.**
  3. **Zeros-despite-ACK, cause B — option bytes flipping.** Glitches landing late hit the handlers *after* Read Memory — the option-byte path. Jerin's ACK-but-zeros were **PCROP/SPRMOD getting set**; SecGlitcher saw **RDP→0x55 and SPRMOD→1 mid-sweep**. → **re-read OPTCR via SWD after every zeros-result**, power-cycle to clear shadow state; if SPRMOD sticks, unset it (Jerin's fix).
- Success = a **256-byte block of real data** (≠ all-zeros, ≠ all-ACK `0x79` — SecGlitcher's classifier).

---

## 3. What we ruled out / learned

- **SRAM is not the target.** It reads all-`00` in the bootloader state because nothing is loaded; and per VoidStar, recent firmware **removed the recovery keys from RAM** — so SRAM won't hold the seed on 1.13.1 even if populated. (Confirmed on real firmware-run SRAM, 2026-10-11: only ~1.5 KB non-trivial — `.data`/`.bss` + a small stack, no strings, no secrets.)
- **SRAM signatures, decoded (2026-10-11):** all-zero = a booted image ran and cleared its RAM (firmware or bootloader startup zeroing .bss); **~98% random garbage with a mostly-1s byte histogram** (0xFF/0xDF/0x7F/0xF7… dominant) = **uninitialized power-up RAM — no code ran** on that boot path (observed with a floating BOOT0). Harmless, no data — but a useful state oracle: garbage SRAM ⇒ the last boot went nowhere (check BOOT0 wiring).
- **BOOT pins, decoded from the v1.1 schematic (2026-10-11 evening):** **BOOT0 (pin 60) hardwired to GND, no resistor** (isolate first — lift/cut, then drive from CW TIO1); **BOOT1 (PB2, pin 28) has NO net — it floats** → with BOOT0 high the boot is a coin flip: bootloader or **boot-from-SRAM → hang** (the dead-GPIO/garbage-SRAM signature). **Tie BOOT1 low** for a defined bootloader entry. Also: **PA9 = R8→GND on the board (USB VBUS-sense net)** — PA9 reads LOW when undriven and idles HIGH in the *firmware* (VBUS pull-up) as well as the bootloader (USART1 TX) — **PA9-high is NOT a bootloader discriminator; use the screen** (on = firmware, off = bootloader) or a `0x7F`→ACK.
- **The seed is in encrypted flash** (NORCOW storage, `0x08008000`), recoverable only via the glitch-during-read.
- **All-zeros: two live suspects — don't lock in one.** Our single OPTCR read showed SPRMOD = 0, but that predates the glitch-2 sweeps — both Jerin (zeros = SPRMOD set mid-glitch) and SecGlitcher (SPRMOD→1, RDP→0x55 mid-sweep) show option bytes **can flip during glitch-2 attempts**. Distinguish by re-reading OPTCR right after a zeros-result: SPRMOD flipped → option-byte path (§2.3); SPRMOD clean → pulse too wide, narrow it (§2.2).
- **A boot glitch lands RDP1, never RDP0 — `1-recon_glitch_trace.py`'s old canary couldn't fire by design.** Its "Strategy 2" (glitch once → RDP0 for the whole power cycle → plain SWD flash reads, no per-read glitch) is ruled out by the sources: SecGlitcher — a corrupted RDP read defaults to **RDP1** (0xAA = RDP0, 0xCC = RDP2, everything else = RDP1); Kraken — RDP1→RDP0 "infeasible in practice, due to the hamming distance" (0xFF→0xAA = 4 specific bit flips). Its sweep logs' `AP fault at 0x08000000` lines were **glitch-1 successes** (SWD connected, flash refused = textbook RDP1), miscounted as fails because the canary only accepts valid flash vectors. Glitch-1 verification = SWD-enumerates criterion (`1-recon_glitch_trace.py` primary since 2026-10-11; `1-trezor_fun.py` original in `backup/`); flash extraction = **glitch 2 over the UART bootloader only** (§2).

---

## 4. Plan for next session (with shunt)

1. **Wire the shunt** — 10 Ω in the VCC rail, MEAS SMA center on the **Trezor side** of it (full diagram: `docs/WIRING_SETUP.md`). Keep the **green glitch wire + its ground return short** (breadboard inductance blunts the pulse). Verify target boots with shunt in place before capturing.
2. **Wire the direct UART rig** (net list: `docs/WIRING_SETUP.md`) — FTDI at **3.3 V**, **both bootloader-UART pairs viable** (AN2606 Table 35: F2 bootloader = USART1 PA9/PA10 + USART3 PC10/PC11 + PB10/PB11, **no USART2**): **current rig PA9/PA10** (TX → PA10, RX ← PA9) or **PC10/PC11** (TX → PC11, RX ← PC10 — the VoidStar-proven pair on this exact hardware, the fallback). FTDI TX line teed → TIO3 as the `0x11` trigger input, **BOOT0 driven by CW TIO1 (J2-10) after isolating pin 60 from its hard GND tie** (Trezor v1.1 schematic: BOOT0 wired straight to GND, **no resistor** — a direct +3.3 V tie is a dead short and collapses the rail to ~0.3 V; lift the pin or cut the trace first): `scope.io.tio1 = True/False` = software-controlled boot mode — set the level before each reset (BOOT0 sampled at every reset edge). TIO4 stays on RST, TIO3 stays earmarked for the FTDI-TX trigger tee. Host serial is `/dev/ttyUSB0` **115200 8E1**. (2026-10-11: PA9/PA10 sync silent even with the bootloader provably up — diagnose the physical link with `uart-link-diag.py` before moving pins.)
3. **Scope-recon for glitch-2 timing** — capture a power trace triggered on the **0x11 UART transmission** (tee'd into TIO3; adapt `capture_read_trace.py`). Find the RDP-check feature in the command handler and read off its offset. Warns "trace ~flat → MEASURE not wired" until the shunt is in.
4. **Glitch 2 during the UART read** — bootloader protocol over `/dev/ttyUSB0` (Read Memory `0x11`), CW armed immediately before the `0x11` send, glitch at the found offset, **repeat 1, narrow width** (start widths ~2–12), sweep an offset **window** (~±11 µs jitter @ 115200). Success = a 256-byte block of real data, not NACK/zeros/all-ACK. Narrowing the width is what turns the all-zeros into real data.
5. **Dump the real targets** once a working (width, offset) is locked — all via the UART Read Memory command, 256 B at a time:
   - Storage: `0x08008000`–`0x0800FFFF` (encrypted mnemonic)
   - Unique ID: `0x1FFF7A10` (12 B, hardware salt input)
   - OTP: `0x1FFF7800`–`0x1FFF7A0F` (salt input)
6. **Offline decrypt / PIN brute-force** (see §6).

---

## 5. Scripts

Active set in **`scripts/`** (2026-10-11 cleanup); everything else (SWD
experiments, dated copies, waveshare/FTDI tests, later-stage tools) is
archived in `backup/`. No cross-imports between the two.

| Script (`scripts/`) | What it does |
|---|---|
| `0-trezor-status.py` | **Status check — run this for any "is it alive / what state" question**: POWER (on/off), SWD + IDCODE, RDP level + PCROP from OPTCR, flash-lock probe, firmware-vs-bootloader via SRAM samples. `--power-on` if off (restores off); never touches power if already on |
| `3-dump_sram_direct.py` | Direct SRAM dump over SWD at RDP1-rest — no glitch, no OpenOCD, 128 KB in ~1.2 s. **Halts the core for a clean snapshot** (power-cycle/reset to resume firmware) |
| `uart-link-diag.py` | UART bring-up diagnostic — streams `0x00` while polling every GPIO over SWD: **shows which pin the adapter's TX actually reaches** + PA9 idle (bootloader USART1 alive?) + no-connection/adapter-GND detection |
| `1-recon_glitch_trace.py` | **Primary glitch-1 script** (2026-10-11) — SWD-enumerates = success (flash read informational), thermal cooldowns + rests, CSV per shot in `TRACES/`, optional trace capture (`G_CAP_TRACES=1` once the shunt is wired); defaults = proven window 17000–18900; **on success dumps SRAM over the same SWD connection as validation** (`G_VALIDATE=1` default — clean full dump + all-zero = link proven) |
| `glitch_info_sweep.py` | Glitch 1 then read every region (DBGMCU/CPUID/OPTCR/UID/OTP/SRAM/flash) |
| `2-check_option_bytes.py` | Option-bytes reader incl. SPRMOD/PCROP — **the after-every-zeros-result check (§2.3)** |
| `check_rdp.py` | Quick RDP level check |
| `power_toggle.py` | CW target power off/on — power-cycles (glitch 1 must re-run after) |
| `reset_stlink.py` | ST-Link USB re-enumeration (VoidStar gotcha: SWD check fails after one miss until reset) |
| `usart_force_bootloader.py` | UART bring-up — baud sweep, even parity, ACK test (PA9/PA10) |
| `8-enable-bootloader-mode.py` | Glitch-1 → BOOT0-high → bootloader flow |
| `usart_read_mem.py` | FTDI bootloader reader — **base for the glitch-2 host side** |
| `6-dump_flash_uart.py` | CW glitch campaign — to adapt for the FTDI rig (fix-list below) |
| `capture_read_trace.py` | Scope recon — retarget the trigger to the **0x11 UART byte** |

Attribution (old table): `1-trezor_fun.py` / `6-dump_flash_uart.py` / `usart_read_mem.py` = theirs; my sweeps + capture = mine. In `backup/` but still referenced: `1-trezor_fun.py` (original glitch-1 — params source for §2), `glitch_sram_dump.py` (SRAM confirmed all-zero), `glitch_read_flash.py` (SWD path abandoned), `brutus.py` + `read_hardware_salt.py` (§6 offline stage).

`6-dump_flash_uart.py` fix-list (cross-check 2026-10-11, before the next run): trigger `tio2` times from the **target's TX**, not our `0x11` — trigger on the **0x11 byte** (tee host TX into a spare TIO input, or FTDI UART + CW UART-decode with SecGlitcher's even-parity FPGA fix); glitch shape is still glitch-1's (width 40, offset −45, **repeat 20**) → **repeat 1 + narrow width**; assumes the RDP check at the address stage — it's **before the first ACK** (SecGlitcher); `baud=9600` while printing "115200"; `scope.arm()` commented out and the campaign code unreachable (test-harness mode).

All my scripts: non-interactive, **crowbar torn down on exit/Ctrl+C**, thermal cooldowns, run with `/home/tdaly/.cwvenv/bin/python`.

Useful env knobs: `G2_WIDTHS`, `G2_EXT_MIN/MAX`, `G2_STEP`, `G2_SAMPLES`, `MAX_READS`, `FLASH_CANARY`, `P1_EXT`.

---

## 6. Offline decryption (after flash dump)

Trezor storage = **ChaCha20Poly1305** per entry (`IV | ENCRDATA | TAG`). Key chain:
- `KEK, KEIV = PBKDF2(HMAC-SHA256, password=PIN, salt, iterations=10000, dkLen=352 bits)` (docs note: 352 bits = 2 output blocks → **20000 HMAC iterations total**, ×2 the per-PIN brute-force cost)
- `salt = random_salt (stored) + hardware constants (ProcessorID / serials)`
- PIN unlocks the EDEK (encrypted data-encryption key); PVC verifies a candidate PIN.

**Need to recover the seed:** (a) storage dump, (b) hardware salt = unique ID `0x1FFF7A10` + any serials, (c) the PIN.
**No PIN → brute-force:** PBKDF2 10k iters × PIN space. Short numeric PINs are very feasible on GPU; cost scales with PIN length.

---

## 7. Open risks / blockers (read before sinking days in)

1. **Passphrase (make-or-break).** If this wallet had a BIP39 passphrase and you don't have it, the funds sit in a hidden wallet that **no glitch or PIN-crack can reach** — the passphrase is never stored on the device. **Settle this first.**
2. **Glitch 2 may still be hard** even with the scope; the all-zeros→real-data narrowing isn't guaranteed on the first session.
3. **1.13.1 storage format / brute-force feasibility** — confirm from the dump header; longer PINs slow the brute-force substantially.
4. **Blind sweeps can flip option bytes — an RDP2 flip bricks the device.** SecGlitcher watched RDP→0x55 and SPRMOD→1 when glitches landed on the option-byte path; 0x55 is still RDP1, but **0xCC = RDP2 kills SWD + bootloader permanently** (Kraken: RDP2 irreversible). Bound blind-sweep counts, verify OPTCR via SWD between campaigns, power-cycle between restarts.

---

## 8. Memory map (STM32F205)

| Region | Address | Notes |
|---|---|---|
| Storage (encrypted seed) | `0x08008000`–`0x0800FFFF` | 32 KB, RDP-locked — glitch-2 target |
| Firmware header | `0x08010000` | TRZF magic + version (locked) |
| Unique ID | `0x1FFF7A10`–`0x1FFF7A1B` | 12 B, SEK salt input |
| OTP | `0x1FFF7800`–`0x1FFF7A0F` | salt input |
| Option bytes | `0x1FFFC000` | RDP/PCROP/WRP |
| SRAM | `0x20000000`+ | 128 KB — empty (not the target) |
| DBGMCU_IDCODE | `0xE0042000` | `0x200F6411` (always readable) |
| FLASH_OPTCR | `0x40023C14` | `0x0FFFFFED` (live RDP/PCROP check) |

---

## 9. Tomorrow's checklist

- [ ] Solder/insert 1–10 Ω shunt in VCC rail; MEASURE across it; keep glitch leads short
- [ ] Direct UART rig — **current: PA9/PA10**; PC10/PC11 as the equal fallback (VoidStar-proven). FTDI TX tee → TIO3 trigger. **BOOT0: isolate pin 60 from its hard GND tie first** (schematic: direct short, no resistor) then + rail; verify `0x7F`→ACK at 115200 8E1
- [ ] Capture a trace triggered on the **0x11 UART transmission** → confirm not flat, find glitch-2 offset
- [ ] `6-dump_flash_uart.py` fixes: trigger on the **0x11 byte** (not tio2 = target TX), **repeat 1**, narrow width, `scope.arm()` before send
- [ ] Bootloader UART on FTDI **115200 8E1** (`usart_read_mem.py`) — cuts timing jitter ~104 µs → ~11 µs
- [ ] Glitch 2 at the found offset → 256 B of REAL data (not NACK/zeros/all-ACK)
- [ ] After every zeros-result: **re-read OPTCR via SWD** (SPRMOD/RDP flip?), power-cycle
- [ ] Dump storage `0x08008000` + unique ID `0x1FFF7A10` + OTP over UART
- [ ] **Confirm passphrase status** before committing to the offline brute-force
- [ ] Build offline PBKDF2 PIN brute-forcer + ChaCha20Poly1305 decrypt

---

## References

All sources archived locally in `docs/archive/` (saved 2026-10-11): each has a
markdown text snapshot (`.md`) plus a single-file HTML snapshot with images
embedded (`.html`) — use those if the live links disappear.

- **Kraken** — glitch ~170 µs re-enables debug/bootloader, then read commands extract flash; mitigation = passphrase.
  <https://blog.kraken.com/product/security/kraken-identifies-critical-flaw-in-trezor-hardware-wallets> · archive: `docs/archive/kraken-trezor-flaw.md`/`.html`
- **VoidStar Replicant Pt.1** — VCAP glitch, reset trigger, ext_offset 17000–20000, width ~40%, repeat 20, 24 µs trigger-delay gotcha; recovery keys removed from RAM in newer firmware.
  <https://voidstarsec.com/blog/replicant-part-1> · archive: `docs/archive/voidstar-replicant-part-1.md`/`.html`
- **SecGlitcher** — RDP-check-in-read-handler target; width sits between no-effect and full reset — use the shortest feasible glitch; success = valid block ≠ all-ACK (0x79); their F429ZI numbers: width 23–24, offset 9050–9150 cycles from the 0x11 UART byte; bootloader UART is 8E1 (CW needs the FPGA even-parity fix); **their "Inconsistent Timing" appendix: the UART response jitters ±8 µs run-to-run (slow UART clock domain crossing into the core domain) — fixed-offset glitches are inherently statistical** (we measured our F2: NACK at burst+178.2–184.3 µs, stdev 2.8, random per shot, lag-1 r = −0.11).
  <https://sec-consult.com/blog/detail/secglitcher-part-1-reproducible-voltage-glitching-on-stm32-microcontrollers/> · archive: `docs/archive/secglitcher-part-1.md`/`.html` (re-saved 2026-10-23 as `secglitcher-part1.md`)
- **Jerin Sunny STM32 vglitch** — RDP-check-in-read-handler target; **same injection point as our rig: VCAP_1, decoupling caps replaced for impact, custom MOSFET circuit soldered close** (breadboard/dupont paths are the killer — confirmed on our rig); **full extraction took 621,594 glitch attempts → 1,024 successful reads (≈0.16 %/shot), ~22 h automated** — the statistical reality that justifies the hammer loop; ACK-but-all-zeros = PCROP (SPRMOD) getting set mid-glitch — verify option bytes during sweeps; narrow width; detect valid 256-B blocks.
  <https://jerinsunny.github.io/stm32_vglitch/> · archive: `docs/archive/jerin-sunny-stm32-vglitch.md`/`.html` (re-saved 2026-10-23 as `stm32f4-vcap-glitch-jerinsunny.md`)
- **SySS / M. Kesenheimer — Glitching the STM32F4** (added 2026-10-23) — bootloader-mode RDP1 read bypass, Pico Glitcher + findus library; **the parameter point that worked: (delay 104,000 ns, width 33 ns)** from the UART-byte trigger; window opens ~80 µs after the second checksum byte starts and closes when the ACK goes out 20–40 µs later — 33 ns-class pulses DO corrupt the executing core when the injection path is tight.
  <https://mkesenheimer.github.io/blog/glitching-the-stm32f4.html> · archive: `docs/archive/syss-mkesenheimer-stm32f4-glitch.md`
- **Anvil Secure — Glitching STM32 Read Out Protection** (added 2026-10-23) — independent RDP voltage-glitch work, useful cross-check on methodology and pulse characterization.
  <https://www.anvilsecure.com/blog/glitching-stm32-read-out-protection-with-voltage-fault-injection.html> · archive: `docs/archive/anvil-stm32-rdp-glitch.md`
- **Trezor storage docs** — ChaCha20Poly1305, PBKDF2 10k iters, salt = random + ProcessorID/serials.
  <https://docs.trezor.io/trezor-firmware/storage/index.html> · archive: `docs/archive/trezor-storage-docs.md`/`.html`
- **AN3155 — USART protocol in the STM32 bootloader** (ST, canonical) — the pictures of exactly what we're testing: sync `0x7F` activation sequence, GET ID, Read Memory host/device sequences, ACK/NACK + checksum rules. archive: `docs/archive/AN3155-usart-protocol-stm32-bootloader.pdf` (PDF, mirror copy — st.com blocked from this network)
- **AN2606 — system memory boot mode** (ST, canonical) — BOOT0/BOOT1 sampling + bootloader-selection figures, and the **per-device bootloader pin tables (the F2 USART1 PA9/PA10 source — review the STM32F205xx table)**. archive: `docs/archive/AN2606-system-memory-boot-mode.pdf` (PDF, mirror copy)
- **Trezor One v1.1 schematic + board (official hardware repo)** — Eagle sources; **BOOT0 confirmed hardwired to GND with no resistor** (netlist: U1 pin 60 → GND direct) — hence the isolate-then-tie-high procedure. archive: `docs/archive/trezor_v1.1.sch` + `.brd` · repo: <https://github.com/trezor/trezor-hardware>
- **MKesenheimer/trezor-one-glitching** (GitHub) — full in-situ Trezor One v1.6.0 glitching walkthrough (Pico Glitcher, VCAP SMA, SWD pinheader, photos): RDP2→RDP1, then SWD/RAM — **never uses the STM32 system bootloader or BOOT0**; uses the Trezor's own bootloader mode (both buttons held), where 1.6.0-era firmware kept the recovery key in RAM. archive: `docs/archive/trezor-one-glitching-kesenheimer.md`/`.html`
