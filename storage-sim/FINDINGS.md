# FINDINGS — running log of the Trezor seed-recovery campaign

Everything learned, decided, and ruled out — appended chronologically as it
happens. Treat as history; verify current state against the rig before acting.

---

## CURRENT STATE OF KNOWLEDGE (consolidated 2026-10-31)

This section is the living summary; it supersedes the older top matter
(`## Next move`, `## Glitch-2 status`, and the early `## Work state` dates)
for *current* state. The full chronological history is preserved below.

### Proven facts
- **RDP1 readout-protection bypass is SOLVED and reproducible.** A single
  UART-triggered crowbar glitch on VCAP flips the Read Memory command
  NACK→ACK and completes a 256 B flash read. Proven end-to-end on the planted
  practice board (STM32F2, DEV_ID 0x411): `storage_0000` recovered =
  `4e524332 faffffff 02003c00…` = the exact planted NRC2 data (2026-10-30).
  F2 has **no PCROP**, so the all-FF "ghosts" were never a PCROP latch.
- **The hardware_salt needs NO glitch.** At RDP1, SRAM (0x20000000) is fully
  SWD-readable; flash and the 0x1FFF UID/OTP region are blocked. `hardware_salt`
  = SHA256(UID‖OTP3) lives in firmware `.bss` (file-scope static in storage.c),
  persists the whole runtime, and SURVIVES an NRST→system-bootloader entry
  (NRST from *clean* firmware preserves SRAM). Validated end-to-end with a stub
  fw at RDP1 (2026-10-31). So salt = one SWD read; the entire uid/otp3 glitch
  grind is MOOT for the salt.
- **uid/OTP region (0x1FFF7A10 / 0x1FFF7860) is refused at the Read Memory
  ADDRESS stage** even with the RDP command-gate glitched — flash completes
  readily, the OTP region does not (settled 2026-10-30: 15k shots/0 on uid vs
  244 shots/1 on flash, identical params). On the real device (SWD blocked),
  bootloader Read Memory of UID/OTP under RDP1 is NOT demonstrated → the SRAM
  `.bss` salt path is the route.
- **Offline decrypt chain proven:** dump storage → PBKDF2 v4 (10000, 44B) →
  ChaCha20-Poly1305 → mnemonic. Brute 0000–9999 ≈ 25 s. v4 uses raw PIN-string
  bytes (not Kraken's packed int). Practice known-answer.json: PIN <redacted>.
- Practice chip's UID = `3e0031001547333032303138`, OTP3 = `ff`×32 (blank) —
  already in hand via SWD for its decrypt.

### Current best parameters (glitch-2, RDP1 → flash read)
- clkgen **166.666667 MHz**, output **enable_only**, crowbar **glitch_hp+lp**,
  offset −45, width 5 (width/offset are INERT in enable_only — `repeat` is the
  only strength knob).
- Strength: **rep6 (36 ns) dominates clean flips (14/18 historical)**, rep7
  (42 ns) the rest. rep5 (30 ns) too weak, rep8 (48 ns) = dead-cliff (~31%).
  Run random rep6/7 (`G_RND_LO=33 G_RND_HI=45`).
- Window: **driver us 180.3–181.8** (clean peak us 181.0; clean→dirty boundary
  ~181.2–181.5). Frame: driver-us + 8.68 = µs after 0x11 start; physical glitch
  ≈ driver-us + ~9.3. NACK onset ≈ 196.5 µs after 0x11 start.
- reset-per-shot (NRST pulse, BOOT0 high), **scope OFF VCAP during firing**.
- Clean-flip rate ≈ **1/730** inside the sweet spot. Most flips don't latch; a
  latching flip drains all remaining chunks (+ uid/otp3) in one go.
- **Launch:** `loop_fulldump.sh` (resumes from `dumps/accum`, assembles
  `storage_dump.bin` at 64 chunks). Logs to `/tmp/opencode/fulldump_loop.log`
  (the script tees internally — do NOT also redirect stdout to that file).

### Open questions / next moves
- **Clean-flip capability drifts/collapses after ~1 h of continuous firing**
  (2026-10-31 14:00: ~22k shots, 0 clean after the first ~7). Glitch still
  lands (dead ~3.4%, dirty ACK_NO_DATA) but can't reach a clean bypass. LA
  ruled out comms/chip/timing → GLITCH DELIVERY (pulse amplitude). Suspects:
  CW crowbar FET thermal, cracked CW SMA jack (~1000:1 atten suspected),
  loose connection. Remedy ladder: cold-cycle the whole CW, then reflow the
  SMA jack. Periodic fresh rig cycle counters the drift.
- **Real device:** confirm it runs 1.13.1 (version in the (0,4) storage entry);
  get `hardware_salt`'s exact `.bss` address from the 1.13.1 `.map/.elf`
  (reproducible build) — or dump full 128 KB SRAM at RDP1 via SWD and brute
  `.bss`-region 32-B windows against the PVC (self-validating).
- **Glitch-1 (RDP2→RDP1)** not needed for this already-RDP1 device; new script
  `glitch1_rdp2_to_rdp1.py` written (single TIO4 drives NRST and self-triggers
  on its own release edge; 100 MHz, enable_only hp+lp, ext 17000–18900),
  UNTESTED — confirm the POR/release edge triggers cleanly before trusting.

### Rig quirks (the traps already paid for)
- **Boot:** system bootloader only via full power cycle with BOOT0 (TIO1) high;
  NRST-only does NOT recover from a glitch-lockup. BUT NRST from *clean*
  firmware DOES enter the bootloader and preserves SRAM. Pins: TIO1=BOOT0,
  TIO4=NRST, TIO2=high_z, io.target_pwr = supply MOSFET.
- **CW config discipline:** fresh `cw.scope()` open, set clkgen FIRST, then
  glitch params; never reconfigure clkgen mid-session (stale-MMCM artifacts,
  rail-slamming misfire). FPGA bitstream reload (`/tmp/opencode/cwlite_interface.bit`)
  is built into `setup()`. kill-9 → SAM3U USBErrorIO wedge, self-recovers
  ~1 min; `USBDEVFS_RESET` unsticks a wedged CW (the `usb_reset` tool only
  resets the ST-Link).
- **enable_only** = ONE continuous `repeat`-cycle pulse (width/offset inert).
  The GLITCH SMA is an **open-drain crowbar** (MOSFETs to GND) — `glitch_hp` /
  `glitch_lp` must be armed or every shot is a no-op (≈6000 early shots were).
  SMA injection ≫ dupont strength; enable_only+SMA is lethal at high energy.
- **Scope (Siglent, VXI-11 @ 10.11.13.220) is MEASUREMENT-ONLY** — never on the
  glitch node during firing (~15-20 pF load damps the pull → ghosts). SCDP
  returns BMP not PNG; WF? DAT2 unreliable (decode from BMP pixels); arm scope
  only AFTER the CW session connects.
- **Verdicts:** nack (1f1f, correct RDP1) · dead (brownout crash, recoverable,
  NOT damage) · weird (wire-shred junk bytes) · ACK_NO_DATA (dirty
  command-flip, address stage refused) · zombie (all-00) · ghost (all-FF where
  data is expected) · spam (async 1f flood) · SUCCESS (clean flip + data).
- **USB churn:** FTDI re-enumerates ttyUSB0↔1 (`serialfind.py`, VID 0403:6001);
  USB bus resets bounce FTDI+CW together → pyserial read deadlocks; watchdog
  hard-exits on a 60 s stall, loop relaunches. Keep CW and FTDI on different
  USB controllers / a powered hub.
- **Practice vs real:** practice chip = 512 KB F205, real Trezor = 1 MB; the
  66-chunk TARGETS list is practice-sized (16 KB storage + uid + otp3). Real
  device = resize STORAGE_BASE/LEN. `G_PRACTICE_BOARD=YES` guards destructive
  scripts.

---

## Objective
- Recover the seed from the owner's own locked Trezor One (PIN lost, backup lost):
  attack the STM32F205 (RDP1, firmware 1.13.1), dump encrypted storage at
  `0x08008000` + hardware salt, then brute-force the PIN offline.
- Secondary track: build a verifiable practice clone on a clean socketed chip
  (Waveshare STM32-QFP64 board) using Trezor's real encryption with a generated seed.

## Requirements
- Owner's own device — legitimate self-recovery.
- **Keep responses short.**
- Standing convention: any "is it alive / what state" question → run
  `scripts/0-trezor-status.py`.
- Run all scripts with `/home/tdaly/.cwvenv/bin/python`.

## Decisions
- Locked-chip path: glitch 1 (RDP1 enable, SOLVED) + glitch 2 over STM32
  system-bootloader UART; SWD glitch-2 abandoned; SRAM ruled out (1.13.1 keeps
  recovery keys out of RAM).
- **Waveshare board powered from CW J2-3/J2-2** (not the 5 V LDO) to keep
  `target_pwr` automation; ST-Link connects via full uncut 20-pin ribbon to the
  board's port (direct jumper wires to 46/49 failed — headers aren't labeled
  PIN1–64).
- Boot wires: **TIO1→BOOT0, TIO2→BOOT1, TIO4→RET (pad 7)**; glitch wire on
  PIN31 label.
- Practice chip firmware: Trezor 1.13.1 (`trezor-t1b1-1.13.1.bin`) — but clean
  chip is 512 KB (RET6-class), won't fit at `0x08010000` (~493 KB needed).
- User buying STM32F205RGT6 (1 MB) 2–3 pcs from a real distributor; pulled
  Trezor chip from earlier was likely just rotated and may be good.
- Current task: simulate Trezor encryption — generated seed in flash via real
  norcow + PBKDF2/ChaCha20 with this chip's hardware salt, for a verifiable
  dump/decrypt target.

## Work state — completed
- Pinout saved: `docs/F205_LQFP64_PINOUT.md` (VCAP_1=31, VCAP_2=47 never ground,
  SWCLK=49 not 47, SWDIO=46, BOOT0=60, BOOT1=28, NRST=7, PA9=42, PA10=43).
- Waveshare schematic saved: `docs/archive/waveshare-stm32-qfp64-schematic.pdf`
  + `.txt`; findings in `WIRING_SETUP.md` (all VDD one rail; 2.2 µF cap on pad 31
  via COMP.H1 jumper — **open it for glitching**; BOOT jumpers OFF; UART headers
  have 3.3 V pin — never connect FTDI VCC).
- Clean chip alive in socket: IDCODE `0x200F6411`, OPTCR `0x0FFFAAED` (RDP0),
  flash[0]=`0xFFFFFFFF`, `st-info --probe` → STM32F2xx, 512 KB flash, 128 KB SRAM.
- SRAM write+readback proven (`0xDEADBEEF` persists across reconnect).
- Power control proven real (SWD dies during `target_pwr` cut); VCC backfeed
  eliminated (ribbon wiring saga resolved — port + no VCC on ST-Link pin 1).
- Official firmware 1.13.1 downloaded: `trezor-1.13.1.bin` (505092 B, TRZF,
  `https://data.trezor.io/firmware/t1b1/trezor-t1b1-1.13.1.bin`).
- Kraken salt/decrypt recipe extracted: `hardware_salt = sha256(unhexlify(otp))`,
  `salt_assembled = hardware_salt + random_salt`, PIN bytes
  `pack("<I", int("1"+pin))`, `pbkdf2_hmac('sha256', pin_bytes, salt, 10000, dklen=44)`,
  KEK=dk[:32], KEIV=dk[32:44], ChaCha20_Poly1305 per entry.
- Full chain key facts: storage `0x08008000`, firmware `0x08010000`, bootloader
  `0x08000000`, UID `0x1FFF7A10`, canary `02 00 3C 00`.

## Work state — storage-sim (this folder; see README.md)
- 1.13.1 ground-truth sources fetched to `reference/` (tag `legacy/v1.13.1`).
- Full format confirmed from source:
  - norcow blockwise, 16 B blocks, sector 2 @ `0x08008000`, word0=`0x3243524E`
    ('NRC2'), word1=`~5`, items from offset 8; key = `APP<<8|key` (LE).
  - **hardware_salt = SHA256(UID[12] @0x1FFF7A10 || OTP block 3[32] @0x1FFF7860)**
    (`trezor.c:collect_hw_entropy`; blank OTP = all-FF).
  - **Kraken's packed-int PIN = pre-1.10 only; 1.10+ v4 uses raw PIN string bytes.**
  - v4: `KEK‖KEIV = PBKDF2(pin_bytes, hw_salt‖random_salt, 10000, 44)`;
    EKEYS = ChaCha20Poly1305(KEK, KEIV, aad=∅)(DEK‖SAK); PVC = tag[:8].
  - v5 (stretch_pin, zero nonce) branch may be needed if the locked device's
    (0,4) version ≥ 5.
  - Protected entries: `IV(12)‖ENCR‖TAG(16)`, AAD = u16 key LE.
- This chip read: UID `3e0031001547333032303138`, OTP block 3 blank.
- `make_storage.py` + `decrypt_storage.py` + README written; `storage.bin` (PIN
  `<redacted — old 4-digit run>`, seed `<redacted>` — test fixture, regenerate locally with
  `make_storage.py`) flashed at `0x08008000`; SWD readback byte-identical.
- **End-to-end rehearsal PROVEN: dump → PBKDF2 brute → ChaCha20 decrypt →
  mnemonic. Brute 0000–9999 found PIN (old run) in 24.9 s (~170 PIN/s).**

## Work state — active
- **UART bootloader dry run COMPLETE (2026-10-23).** Root cause of the old
  "bootloader never syncs": **BOOT1 (PB2) floated high** (jumper caps were in
  the wrong spot / TIO2 wire never landed) → with BOOT0=1 that's SRAM boot
  (signature: PC=0 SP=0 executing, MODER at reset defaults). Fix: BOOT1 jumper
  cap firmly on the `0` position; BOOT0 still driven by TIO1 (works).
- Bootloader fingerprint on this chip: USB (PA11/PA12 AF10) + CAN2 (PB5/PB13
  AF9) configured, USART1/3+I2C clocks on; USART1 never AF-observed but syncs
  immediately on 0x7F anyway.
- `storage-sim/uart_dump.py`: sync → GET-ID (0x0411) → Read Memory. Full 16 KB
  storage dump over UART, **byte-identical** to planted storage; decryptor on
  the UART dump finds PIN (old run) in 23.9 s. The whole glitch-2 back half is
  proven — only RDP1 stands between this and the locked device.
- PC/SP register reads over DCRDR read 0 on this core even when halted —
  unreliable; use peripheral-register signatures instead.
- TIO2→BOOT1 wire does not reach pad 28 (PB2 stuck high regardless of TIO2) —
  leave BOOT1 on the board jumper, don't rely on that wire.

## Next move
- **RDP1 REHEARSAL TARGET IS LIVE (2026-10-23).** RDP set via `storage-sim/set_rdp1.py`
  (OPTKEYR unlock, OPTCR RDP byte 0x55 + OPTSTRT). Verified: SWD flash read = DP
  fault; UART bootloader syncs (0x7F→79); Read Memory → **NACK 0x1F**. Planted
  storage survived the 0→1 transition. **Do not attach SWD during UART sessions —
  ST-Link attach kills the bootloader UART session** (confirmed twice).
- Board prep done: COMP.H2 jumper (the pad-31 selector; silkscreen "F2xx 31")
  pulled — 2.2 µF off VCAP_1, pad floating = real-Trezor-equivalent glitch node.
  COMP.H1 = cap/GND companion side. DMM die-paths fooled earlier tie readings.
- **Next: wire CW glitch output (GLITCH mid pad → short lead) to the PIN31
  breakout pad, then glitch campaign: trigger on the Read Memory command
  exchange, voltage-glitch VCAP, sweep width/offset, success = data bytes
  instead of NACK. Known answer = PIN (old run)→ no wait, run2: PIN <redacted> / seed in
  known-answer.json.**

## Glitch-2 status (2026-10-23, evening)
- Glitch path on socket rig PROVEN (`glitch2_dryfire.py`): width 40, repeat 20
  kills the core instantly; repeat 1/5 = no effect (clean NACKs).
- **Logic analyzer (Saleae clone, fx2lafw/sigrok) measured the decision
  window** (`la_measure.py` + `la_decode.py`, D0=FTDI TX, D1=chip TX):
  - TIO3 trigger = first rising edge of 0x11, +8.5 us into burst
  - 0x11 0xEE pair ends +182.0 us past trigger; **NACK starts +183.0 us**
  - **RDP decision window ≈ 1 us** — immediate register-check reply, NOT a
    long processing window; first sweep (170-260 us, step 0.5, rep 1/5) was
    mostly too late + too weak.
- Campaign 2 running: ext 170-192 us, step 0.1 us, repeats 8/10/12/15,
  width 40 / offset -45 (proven shape).
- **Campaign 2+3 results: ALL NACK (1208 shots through the exact measured
  window). Root cause found via LA pulse characterization (`pulse_char.py`,
  D2 on the CW GLITCH pad, fat-pulse trick @ 10 MHz clkgen):**
  - **Pulse width is HARDWARE-STUCK at ~60 ns** — no response to width
    20/40/49, offset 0/-45, output enable_only/glitch_only, clkgen 10/100 MHz,
    even after scope.clock.reset_dcms(). The DCM partial-reconfig that
    scales width never takes (CW warns "Partial reconfiguration ... may not
    work"). REPEAT is the only live energy knob (~60 ns tap per unit).
  - LA-verified: pulse lands exactly at requested ext_offset (asked 178.4us,
    observed 178.56us past TIO3 trigger) — sweep timing machinery is correct.
  - Energy scale: repeat 19 in-window = clean NACK (nothing); repeat 20 idle
    = instant kill. The corrupted-but-alive band, if any, sits at ~20+
    repeats fired INTO the decision window.
- **BREAKTHROUGH SESSION (2026-10-23 late): three stacked measurement
  artifacts unraveled:**
  1. **CW-Lite width = % of clkgen cycle** (docs: 0-49.8%, 100% enable-only),
     NOT absolute ns — at clkgen=100MHz width 40 = ~4ns pulses. All earlier
     "energy" sweeps were sparks.
  2. **The SAM3U was serving a stale builtin bitstream** (release_mode
     builtin; the software's cwlite_firmware.zip path was never checked out)
     — bitstream/PR-data mismatch. Fixed per-session by extracting
     cwlite_interface.bit from the package zip and
     `scope.scopetype.reload_fpga(path)`. (Permanent fix = SAM3U fw update.)
  3. **The LA probe on the GLITCH pad was DAMPING the glitch** (~15pF +
     input clamps on the VCAP node, which idles at 1.2-1.8V = right at the
     LA input threshold, so the D2 traces were garbage AND the pulses were
     cushioned). LA stays OFF the glitch pad during campaigns. (LA does
     support 24MHz — verified — use it for UART-side captures.)
- Post-fix reality (`width_sweep.py`): clkgen 4MHz, offset -45, repeat 1 —
  **every width 5-49 kills the idle core**. Width knob alive; energy real.
  Idle-sleep kills still != execution kills (campaign-4 lesson), so fat
  pulses at the decision window may hit corrupted-but-alive.
- **Campaign 5 (running): clkgen 4MHz** (G_CLKGEN env in campaign script),
  ext 700-750 cycles (250ns grid = 175-187.5us), widths 10/25/40/49,
  repeat 1, offset -45.
- **PLAN: width-stretcher** (~$8): CW GLITCH pad (verified 60 ns tick,
  perfect ext_offset timing) -> 74LVC1G123 monostable (R_pot+C sets
  100 ns-2 us) -> logic-level N-FET -> VCAP pad. CW repeat=1, all scripts
  unchanged. Re-run pulse_char.py to verify, then re-enter the 182us window.
  Fallbacks: DIY secglitcher-class FPGA rig (~$50-100), MCU glitcher, or a
  purchased CW Husky.
- Gotchas: FTDI re-enumerates between ttyUSB0/1 → use `serialfind.py`
  (list_ports by VID 0403:6001); plugging USB devices re-enumerates the bus
  and KILLS an open CW handle (LIBUSB_ERROR_NO_DEVICE) — restart cw.scope();
  fx2lafw glitches the first capture samples (decoder must tolerate).

## Relevant files
- `storage-sim/README.md`, `make_storage.py`, `decrypt_storage.py`,
  `storage.bin`, `readback.bin`, `known-answer.json`, `bip39-english.txt`,
  `trezor-1.13.1.bin`, `reference/` (1.13.1 sources)
- `/home/tdaly/trezor-btc/docs/RECOVERY_PLAN.md` — source of truth
- `/home/tdaly/trezor-btc/docs/F205_LQFP64_PINOUT.md` — verified pin map
- `/home/tdaly/trezor-btc/docs/WIRING_SETUP.md` — rig nets
- `/home/tdaly/trezor-btc/docs/archive/trezor-storage-docs.md` — norcow format
- `/home/tdaly/trezor-btc/docs/archive/kraken-trezor-flaw.md` — decrypt ground truth
- `/home/tdaly/trezor-btc/scripts/0-trezor-status.py` — status check
- `/home/tdaly/.cwvenv/bin/python`, `/home/tdaly/.cwvenv/usb_reset`

## Important context
- Not a git repo — all changes live on disk only.
- Header label trap: wire by label (RET, OSIN/OSOUT, BOOT1, BOOT0, U1 TX/RX,
  JTMS/JTCK), not pad number.
- CW supplies target power (J2-3, 200 mA limit); target_pwr toggling works.
- SWD at 480000 Hz (1800000 causes `DP wait`); `DP wait` clears only with a
  target power cycle; `set_reg` trips it — bypass via DCRDR/DCRSR writes.
- Clean chip = 512 KB; locked Trezor = 1 MB — storage `0x08008000` is 16 KB
  sector either way.
- DMM can read steady 3.3 on a working SWD line — use continuous-clocking
  hammer windows (2.6–2.98 V readings prove path).

## Glitch-2 campaign ladder (2026-10-23 night, all logs glitch2_*.csv)
- 5 (4MHz, off-45, w40, rep 10-49): first corruptions - 9f1f @ ext718/rep25,
  ff replies at rep 40/49 (reply-byte corruption), dead zone. Energy bracketed.
- 6 (rep 15-33, ext 714-726): transition band = rep 23-27 @ ext 718-721.
- 7 (hammer, 12 samples/pt): stochastic confirmed; outcomes only
  nack/dead/ff - no ACK. Blunt 212ns pulses (offset -45 @ 4MHz) span ~25
  instructions - can't skip a single branch.
- 8 (16MHz, offset 0, w40=25ns, rep 4): ALL nack - too soft. Surgical
  without energy.
- GO command at RDP1: NACK (all of Read/Write/GO/Erase/Unprotect refused;
  only Get/GetID ACK). No shortcut - glitch is the only path.
- **9 (running): the middle regime - 16MHz, offset -45, width 49 => ~59ns
  pulses on 62.5ns grid, rep 2, ext 2900-2945 (181.25-184us), 6 samples/pt.**
- Unexplored if 9 fails: second-NACK window (~283us = ext 4528 @ 16MHz);
  boot-time OB-shadow read (needs 0x55->0xAA exactly = hamming problem).
- 9 (16MHz off-45 w49=59ns): all nack. 10 (8MHz 118ns): all nack.
  **PHYSICS CONCLUSION: through this wiring the F205's VCAP needs ~5us of
  sustained crowbar to collapse (LDO current limit vs MOSFET, die caps).
  Sub-us pulses never dip the rail. All corruption happens on the COLLAPSE
  EDGE (rail sagging through margin over ~1us). 9f1f math fits: fire
  179.5us + ~4.5us collapse = edge grazes the decision/NACK at ~183us.**
- Campaign 11 (running): edge hammer - 4MHz, w40 off-45, reps 24-26,
  ext 715-721 (178.75-180.25us), 100 samples/pt, 2100 shots. Per-shot
  branch-flip odds likely percent-scale; need the samples.
- IF 11 fails, next moves: (a) improve injection physics - short/heavy
  wire MOSFET->PIN31 direct (current path runs through breadboard + duponts;
  WIRING_SETUP warned to keep it short), sharper collapse = sharper edge;
  (b) second-NACK window at ~283us (ext 1132 @4MHz) - another decision point;
  (c) 0x55->0xAA hamming problem rules out value corruption (Kraken).
- Sanity check caught campaign 11 stalled 11.5 min: CW FPGA partial-reconfig
  HANG (known NewAE failure mode) - our attempt() re-wrote g.width every
  shot, each write triggering PR + DCM reset. **FIX in campaign script:
  width/offset only written on change (LAST_W/LAST_O cache).** Campaign 11b
  relaunched with same params. New tool: storage-sim/sanity.py (campaign-safe
  non-intrusive rig check - USB enumeration, CSV freshness, artifacts).

## Literature + throughput fixes (2026-10-23 night 2)
- Saved: docs/archive/{secglitcher-part1, stm32f4-vcap-glitch-jerinsunny,
  anvil-stm32-rdp-glitch, syss-mkesenheimer-stm32f4-glitch}.md
- **SECGlitcher (SEC Consult 2024)**: exact target = check_RDP_and_get_addr()
  is_rdp_enabled branch (compares RDP reg to 0xAA) right after cmd pair,
  before ACK. **UART-domain crossing jitters response +/-8us** (observed
  ourselves: NACK at +183.0 then +186.1us on two LA runs) - fixed-ext shots
  hit a ~10-40ns instruction inside a ~16us jitter zone => per-shot odds
  ~0.2%. Their CW workaround: 100MHz clkgen for precision.
- **SySS/mkesenheimer F4**: SUCCESS at (104us delay, **33ns width**) via
  VCAP_1 with TIGHT soldered injection (Pico Glitcher). Our 59ns pulses did
  nothing => **our breadboard+dupont injection path is the weak link** (also
  explains the 5us collapse time). Jerin Sunny F4: 621,594 attempts ->
  1,024 reads (0.16%/shot), 22hrs; warns ACK-but-zeros = PCROP/SPRMOD bit
  getting set by glitches (check OPTCR if that happens).
- **NRST fast recovery PROVEN**: TIO4 pulse (20ms low) -> resync in 350ms,
  repeatable. Campaign patched: boot_and_sync(fast=True) NRST path with
  power-cycle fallback; initial boot uses power cycle. ~13x throughput.
- Next hardware task: **rewire glitch injection short/direct** (remove
  breadboard; shortest lead CW GLITCH pad -> PIN31), then 16MHz/offset-0/
  width-49 (31ns pulses, 62.5ns grid) across the full +/-8us jitter zone
  (ext 2800-3056), samples ~20/pt.
- **DIRECT WIRE FIX VALIDATED**: single ~31ns pulse (16MHz, offset 0, w49,
  rep 1) now KILLS the idle core - the old breadboard path delivered nothing
  at 59ns x2. Injection now literature-grade. (A/B via inline sweep after
  rewiring; old results: campaigns 8/10 all-nack.)
- **Campaign 12 (running): 32MHz clkgen, offset -45, width 49 => ~30ns
  pulses on 31.25ns grid** - full coverage of every instruction across the
  whole +/-8us UART-jitter zone (ext 5600-6112 = 175-191us), 8 samples/pt,
  ~4100 shots, NRST fast recovery ~3/s.
- Campaign 12 wedged at shot 600 (FTDI+CW both re-enumerated mid-run; python
  stuck in serial poll). Killed, relaunched as 12b from ext 5680.
- **FPGA-reload ritual now BUILT INTO glitch2_campaign.py setup** (every
  fresh scope() gets the matched 6.0.0 bitstream automatically).
- Operational pattern: USB bus resets bounce FTDI (ttyUSB0<->1) + CW;
  sanity.py catches stalls (<- run it periodically); serialfind handles the
  port churn.
- 12/12b results: 2600 shots @ 32MHz/30ns/rep1 across 175-185.3us - ALL
  nack. Executing core tolerates single 30ns pulses (idle core does not).
  185.3-191us tail unswept at rep1. NOTE: env var is G_SHOTS (not
  G_SHOTS_MAX - 12b hit the 2000 default by typo).
- **Campaign 13 (running): same 30ns/31ns grid, repeat 2,3,4 trains (60-120ns
  near-continuous), ext 5680-6050 (177.5-189us), 5 samples/pt, ~5500 shots,
  G_SHOTS=9000.**
- Campaign 13: 5565 shots @ 32MHz rep 2-4 - all nack. Calibration: rep 8-128
  (up to ~4us of 30ns-pulse spray) at hot center - ALL nack. **Per-pulse
  width ~200ns is required to collapse this rail** (30ns x any count cannot;
  4MHz 212ns pulses could). The CW 'repeat' spacing also appears sparse
  (pulse_char far-strays), so 'trains' are sprays not continuous.
- **HAMMER LOOP (running, overnight): hammer_loop.sh** - reruns the PROVEN
  gray-zone config (4MHz, off-45, w40, reps 24-27, ext 714-724, 40 samples/
  pt = 1760 shots/pass) at ~3/s with NRST recovery + direct wire until a
  JACKPOT_*.bin appears (auto-stop). Log: /tmp/opencode/hammer.log,
  pass counter: /tmp/opencode/hammer-loop-status.log. Popup tails hammer.log.
  F4 literature odds ~0.16%/shot at good params => expect ~1k-10k+ shots.
- **Recovery + check mechanism built into glitch2_campaign.py:**
  1. reconnect() - full session rebuild on USB dropout (scope + FPGA reload
     ritual + glitch/trigger config + serial + boot/sync), 5 tries.
  2. Per-shot try/except: rig-drop -> reconnect -> RESUME same grid point
     (sweeps no longer restart from scratch when the CW bounces).
  3. Resync path also exception-guarded with reconnect fallback.
  4. Heartbeat every 200 shots (rate/ext/verdict) - stalls visible in log.
  Hammer loop v2 relaunched on this (hammer_loop.sh unchanged - passes are
  now just a backstop). CW drops ~every 12 min on this rig; handled.
- **UART jitter measured on the live stream (uart_jitter.py, LA passive on
  D0/D1): NACK at burst+178.2-184.3us, mean 181.4, stdev 2.8, lag-1
  correlation r1=-0.11 => RANDOM per shot (no NACK-trigger self-aiming
  benefit - the user's idea was tested and answered).** Volume hammering
  confirmed as the path.
- KEY correction: the old hammer window (ext 714-724 = 178.5-181us) missed
  the 181-184.3us half of the decision distribution! **Hammer v3: ext
  712-738 (178-184.5us), reps 24-27, 40 samples/pt = 4320 shots/pass**,
  recovery+heartbeat built in. (uart_jitter capture yield was 5/30 - LA
  trigger vs 3/s cadence; window now 8000 samples.)
- **Watchdog added to campaign**: thread checks progress every 10s; 60s
  stall => os._exit(3) so the hammer loop relaunches. Root cause of the
  recurring wedges: FTDI (and CW) re-enumerate mid-run - a pending pyserial
  read then blocks in poll() FOREVER (classic USB-serial disconnect
  deadlock). Both devices bounce together => likely laptop USB bus-level
  resets, not cables. PHYSICAL SUGGESTION for user: move CW and FTDI to
  DIFFERENT USB ports/controllers (lsusb buses 001-004) or a powered hub.
- Hammer v3 live: ext 712-738 (178-184.5us full measured NACK window),
  reps 24-27, 40 samples/pt, reconnect/resume + backoff + watchdog.

## Overnight post-mortem + gray zone v2 (2026-10-24)
- Overnight: 5 passes, 10,800 shots at reps 24-27 - ALL nack, loop stopped
  ~22:40 (session recycle). NOT a rig failure: idle-kill + TIO3-trigger kill
  + clkgen/ADC verification all pass (clkgen honest at 4-100MHz; triggers
  100% fired per ADC capture check).
- **Root cause of all-nack: the direct wire moved the energy scale UP.**
  Escalation at the decision window: reps 24-80 = NOTHING on the executing
  core; **reps 100-800 = the real gray zone (dead + fc/fe corrupted NACKs)**.
  Yesterday's reps-24-27 "gray zone" (9f1f/ff) was an artifact of the lossy
  breadboard path's slow collapse edges.
- **HAMMER v4 (running): reps 100/125/150/200/250/300, ext 712-738,
  30 samples/pt** (~4900 shots/pass) in the verified live gray zone.
- Targeting cross-checked vs articles (user): glitch window = after the
  Read-Memory command pair lands, before the NACK - matches SECGlitcher's
  check_RDP_and_get_addr() and Jerin Sunny. Our fc/fe corrupted NACKs prove
  we're hitting it. BUT the two LA measurements disagree by up to ~14us
  (first: NACK trigger+183us; jitter run: burst+178-184 = trigger+170-176)
  => true window wider than assumed. **Hammer window widened to ext
  700-750 (175-187.5us trigger-relative), applies from the next pass.**
- Single-212ns-pulse sweep (rep 1, ext 700-750, 78 shots): ALL nack - the
  executing core needs sustained conduction, not single taps. Complete
  energy picture: singles/nothing; reps<100/nothing; reps 100-300/mostly
  dead + occasional fc/fe; the jackpot lives in the narrow mixed band
  (reps ~100-200) with the CW's coarse repeat knob.
- **Recommendation: order width-stretcher parts** (width-stretcher-parts.md,
  ~$10: 74HC123/LVC1G123 + logic FET + pot + caps) - clean single 100ns-2us
  pulses, no repeat ambiguity. That is the precise knob this F205 demands.
- HAMMER v5 (running): reps 100/125/150 (the mixed band), ext 700-750
  (widened), 30 samples/pt. Passes ~1h (dead-heavy cadence).

## PUBLISHED PARAMETERS FOUND (2026-10-24) - mkesenheimer Trezor One article
- docs/archive/mkesenheimer-trezor-one-new-firmware.md (Oct 2025): our EXACT
  chip + EXACT attack (RDP1->RDP0 via system bootloader readmem, VCAP node).
  **Stage 2 success: delay 105.45-105.8us after the 0x11ee command start,
  glitch length 10-30ns ("shorter is better, less invasive")**. In our
  trigger reference (TIO3 = +8.5us into 0x11): ~97us from trigger = ext
  1540-1580 @16MHz - a window NEVER swept before (all campaigns targeted
  pair-end 175-190us). Their stage-1 (RDP2->RDP1 at boot) = ~180us after
  VCAP rise - matches our glitch-1 numbers exactly (validates the family).
- Campaign 14 (running): 16MHz, offset 0 (clean pulse), widths 30/40/49
  (19/25/31ns - their class), ext 1540-1580, 40 samples/pt.
- Campaign script now sweeps WIDTH lists (G_WIDTH=30,40,49).
- Pico plan (user has one): findus/PicoGlitcher toolchain - MicroPython UF2
  + pip findus + update-fw; needs a MOSFET (asked user for drawer check).
  Pico Glitcher firmware pinout per findus/firmware/PicoGlitcher.py.

## Pico Glitcher toolchain ALIVE (2026-10-24)
- User's Raspberry Pi Pico: BOOTSEL-flashed MicroPython v1.29.0, then
  findus 1.14.1 (own venv /home/tdaly/.findusenv) + update-fw --version v1.
- **Upstream findus bug found+patched**: firmware/Globals.py defines
  PADS_BANK0_BASE/ADC_BASE only for hw v2/v3 - v1 (bare Pico) firmware
  crashes at init (FastADC.configure_adc). Patch: v1 gets the RP2040
  constants (same silicon as v2). Patched in site-packages; consider
  upstreaming.
- **Pico v1 pin map (firmware/Globals.py): TRIGGER=GP15, RESET=GP0,
  GLITCH_EN=GP1, HP_GLITCH=GP16, LP_GLITCH=GP17, EXT_GLITCH=GP19,
  VTARGET_EN=GP20, VTARGET_OC=GP21.
- His UART setup uses 4.7k pull-ups on BOTH lines (TX,RX) - OWNER COPIED IT
  2026-10-24 with **10k pull-ups on both UART lines -> 3.3V (board rail)**.
  (a) host-TX line (drives target RX; = Pico GP15 trigger source) -> 3.3V,
  (b) target-TX line -> 3.3V. Purpose: defined idle state - the PIO UART
  pattern trigger must not false-fire on a floating line while the target
  is dead/transitioning (we see this as 'weird' verdicts / spurious reads
  on the FTDI RX), and GP15 must never float. Kit has 4.7k/10k. NOT a
  glitch-path component.
- Plan: Blue Pill (user has) = dress-rehearsal target for the Pico rig
  before porting to the F205 socket board. STILL NEED: a MOSFET for the
  crowbar stage (no answer yet on drawer check).
- Campaign 14 (CW, published mkesenheimer window ext 1540-1580 @16MHz,
  19-31ns pulses) running in parallel.

## Pico Glitcher attack script READY (2026-10-24)
- Found mkesenheimer's REAL Trezor One repo: MKesenheimer/trezor-one-glitching
  (archived: kesenheimer-stm32f2-bootloader-memread-{crowbar,mux}.py +
  boot-debugger + README_FLASH_DUMP). His stage-2: uart_trigger(pattern=0x11)
  -> arm(delay, length in ns, ~5ns PIO resolution) -> setup_memread sends the
  command -> PIO fires -> dump. HIS dump= 8KB @0x08000000; ours needs
  0x08008000 16KB (our complete_read does exactly that).
- storage-sim/pico_campaign.py written (adapted): Pico GP15 trigger on
  FTDI TX seeing 0x11, GP16 -> PN2222 crowbar -> pin31; CW kept for power only;
  watchdog + reconnect + JACKPOT auto-save + CSV logging.
- PN2222 x5 identified (kit): parallel crowbar stage x3 + spares.
- Campaign 15 still running on CW (published sub-band, all nack so far).

## OWNER'S INTEL on the kesenheimer repo (2026-10-24)
- MKesenheimer/trezor-one-glitching is based on the OLD Trezor firmware
  (v1.6.0 era). The glitch/uprog procedure itself still works as described
  on current firmware (incl. our v1.13.1 rehearsal twin) - BUT the PIN is
  NOT in SRAM on new firmware. The stage-2 bootloader bypass gives us the
  ENCRYPTED storage block + hardware salt; recovery = offline brute-force
  (decrypt_storage.py, PBKDF2 v4 chain), NOT a RAM extraction.
- Do NOT use his storage/encseed.py / pin-extract.py on our dumps - old
  storage format only. Our v1.13.1 decryptor is the authority.
- Noted in RECOVERY_PLAN.md references.

## CONFIRMED by owner (2026-10-24): this IS the target attack
- The stage-2 bootloader RDP1->RDP0 attack (mkesenheimer
  trezor-one-glitching repo) is the EXACT thing we are doing; we simply run
  it on the CW instead of his Pico Glitcher. Translation table:
  trigger 0x11-byte (TIO3) | delay2 105.45-105.8us (~= ext 1546-1562 @16MHz,
  campaign 15) | length2 10-30ns (~= widths 30/40/49 @16MHz offset 0) |
  crowbar GPIO->FET->VCAP (= CW GLITCH pads -> pin31, floating VCAP).
- Remaining rig deltas vs his: PIO ns-resolution timing + cleaner pulse
  edge => the Pico + PN2222 track exists to close exactly those gaps.

## SECOND VCORE CAP STILL ON BOARD (2026-10-24) - likely our #1 handicap
- Owner read the mkesenheimer article photos: he removed jumpers on pads 31
  AND 47 of the Waveshare STM32-QFP64. Confirmed against F205 LQFP64 pinout
  (DS6329): pad 31 = VCAP_2, other VCAP pin's cap = the pad-47 jumper
  (COMP.C3 in the waveshare schematic). We only pulled COMP.H2 (pad 31).
- F2 fact: VCAP_1 (pin 58) and VCAP_2 (pin 31) are the same internal core
  rail -> a still-connected 2.2uF on the second pin loads the "floating"
  node and damps every crowbar pulse. Best candidate cause for all-NACK at
  the published parameters.
- ACTION: cut COMP.C3 (same way as COMP.H2), then re-measure node idle +
  pulse_char kill threshold, then re-attack. Also archived exact published
  parameter sets from the article text: stage2 optimized 105_450-105_800 ns
  /10-30ns; combined-run success: delay2 104_900-105_300/length2 20-40;
  read stage delay 195_000-198_000/length 100-150 (--address 0x08008190
  --size 0x1fe, two 256B reads cover mnemonic+PIN on v1.6.1 layout).

## COMP.C3 PULLED - NODE UNLOADED (2026-10-24) - MASSIVE THRESHOLD SHIFT
- Owner pulled the pad-47 jumper (COMP.C3): BOTH VCAP pins now float, no
  external cap anywhere on the core rail (real-Trezor parity).
- pulse_char (4MHz clkgen, CW direct pad-31 lead) VERDICT LADDER vs old:
  single ~213ns: nothing -> **DEAD**; single ~163ns: nothing -> 1F;
  single ~100ns: nothing -> **1F 1F (corrupted NACK pair)**; two ~213ns -> 1F 1F.
  Singles previously did NOTHING on the executing core. The unloaded node
  made every pulse ~decisively stronger. Confirms the second 2.2uF was the
  dominant damping mechanism -- and the prime suspect for 3000+ all-NACK
  shots at the published parameters.
- Rig flow at re-verify: user unplugged USB hub during surgery; all
  devices returned (FTDI ttyUSB0, CW, LA, ST-Link). SWD currently silent
  (wedged chip state, irrelevant for bootloader path).
- Next: relaunch campaign 16 at published stage-2 band with unsapped node.

## RDP0 GOOD-READ CAPTURED ON THE SCOPE - READMEM TIMELINE + WORKING SETTINGS (2026-10-26)
- Chip at RDP0 (owner reflashed/replanted, NRC2 canary verified in the dump
  head: 4e524332 fa ffffff 02 003c 00). Full readmem transaction repeated
  cleanly for scope captures (uart_rdp0_test.py flow).
- MEASURED GOOD-READ TIMELINE (scope, trigger = 0x11 start bit falling edge):
  t=0        : 0x11 start bit (command pair begins)
  0-191 us   : the 11 EE readmem command pair
  191-285 us : QUIET GAP = chip ACKs 0x79 on the OTHER line (host TX silent)
  +288 us    : address phase starts (08 00 80 00 88) - visible on host TX
  after that: FF 00 length pair, then ~22 ms of 255 data bytes streaming.
  => THE GLITCH TARGET (+105.45-105.8 us published band) lands INSIDE the
  command-pair window, BEFORE the ACK gap - i.e. corrupt the RDP check
  while the pair is still on the wire / just decoded. Campaign ext mapping
  (8.7us + ext*62.5ns + 2.7us pipeline; ext 1546-1688 @ 16MHz = 105.0-106.5
  us) sits exactly there. At RDP1 the same point ends in the 1F 1F NACK.
- SCOPE SETTINGS THAT WORK (Siglent SDS1202X-E, fw 1.3.27, vxi11 @
  10.11.13.220, driver: scope/scope.py + scope/glitch_shot.py):
  - ch1 = SMA T at QFP VCAP node: 500mV/div, D1M, glitch trigger C1 NEG
    0.9V, TRDL 0 (event centered). ch2 = UART tap (breadboard row with
    TIO3 + LA D0 + QFP RX): HEAVILY ATTENUATED tap - swing only ~126mV
    riding at ~-0.3V (idle -0.24V / low -0.37V) -> needs C2:VDIV 13-20mV,
    C2:OFST ~-0.31V, CPL D1M, trigger C2 NEG at -0.25V (-0.30 flaky;
    scope quantizes trigger levels, sweep-verify before arming).
  - QUIRKS: SCDP returns BMP (800x480) not PNG; WF? DAT2 IS UNRELIABLE
    (disagrees with the screen - decode from BMP pixels instead);
    TRSL/TRSE slope readback is cosmetic (TRSL governs, TRSE shows HT);
    ch2 trace renders MAGENTA on this theme (not cyan!); cursor SCPI
    unsupported (queries hang) - cursors are front-panel only; scope must
    be armed AFTER CW session connects (target-power blip false-triggers);
    user pan/zoom after STOP moves the trigger point off screen-center -
    re-find the falling edge before decoding from pixels.
  - Pixel UART decode recipe (from BMP): 50px/div; at 20us/div 1 bit =
    21.7px; threshold between -0.24 (idle) and -0.37 (low); verified by
    decoding the 11 EE pair + the 08-00-80-00-88 address phase on screen.
- Reference frames archived: campaigns/scope-frames/{now4.bmp (50us/div
  anatomy view), rdp0_readmem.bmp, rdp0_readmem2.bmp}.
- Also this session: enable_only CW output mode is LETHAL with the SMA
  (rail-to-rail thrash, chip hangs; ~2us disturbance, ~9us settle, no POR -
  core lockup). glitch_only (onboard MOSFET crowbar) is SURVIVABLE at all
  tested energies (up to width 49 rep 49 - clean NACKs). Campaign renamed:
  rdp1_glitch_campaign_full_mem_dump.py (G_OUTPUT=glitch_only default,
  header documents mode params + bootloader pin recipe: TIO1=BOOT0 True +
  full power cycle -> sync; NRST-only reboot does NOT work out of lockup).
  ~2900 shots in glitch_only SMA mode so far: all clean NACK, zero weirds
  (band 1546-1562 + full-range 20-190us discovery pass) - energy or window
  still unresolved; SMA-era sweep data in campaigns/*smago* and *disc*.

## MKESENHEIMER RIG COMPARISON - ONE STRUCTURAL DIFFERENCE LEFT (2026-10-26)
- Re-read his README_FLASH_DUMP.md (stage-2 flash-dump attack) and checked
  our rig element-by-element:
  | element | his rig | ours | status |
  | UART pull-ups | 4.7k on TX/RX | 10k pull-ups on TX/RX (owner-installed) | MATCH |
  | VCAP caps | removed, pads 31+47 | COMP.H2 + COMP.C3 pulled | MATCH |
  | trigger discipline | Schmitt set once, never touched | TIO3 edge, frozen | MATCH |
  | stage-2 window | delay2 105_450-105_800 ns, length2 10-30 ns | ext 1546-1688 @ 16MHz = 105.0-106.5 us from 0x11 start | MATCH |
  | VCAP power topology | external <=1.2V fed THROUGH the Pico mux (deliberately weak source) | internal 1.2V LDO actively recharges the node | THE ONE REMAINING DIFFERENCE |
- HIS KEY FACT: target core rail is powered from an external supply via
  VIN1 ("be sure to not exceed 1.2V") through the Pico Glitcher mux - the
  crowbar discharges a WEAKLY-fed node, so even 10-30ns pulses collapse
  the rail. OURS discharges a node the on-chip regulator recharges within
  ns - consistent with all measured evidence (pulses land on time, dips
  are shallow, ~3100 shots incl. max-energy trains = clean NACK, zero
  corrupted bytes).
- Also noted from his README: Pico has no clkgen concept - delay/length
  in direct ns. Our 16MHz+ext translation is fine; no more ad-hoc clkgen
  changes (4MHz excursions produced stale-MMCM artifacts - config
  discipline: fresh scope() open, clkgen FIRST, then glitch params, never
  reconfigure mid-session).
- Bring-up verification ritual if we re-feed VCAP externally: his startup
  trace shows VCAP rises ~150ms AFTER supply power-on (verify on scope).
- OPTIONS from here: (1) rewire VCAP feed: external current-limited 1.2V
  through our SMA path, board's own 3.3V-to-core feed interrupted, CW
  crowbar on top; (2) Pico Glitcher bring-up (pico_campaign.py + crowbar
  stage) - closest to his actual hardware; (3) keep CW hammering - but
  the ~3100-shot ceiling says the topology, not the timing, is the
  blocker.

## VOIDSTAR RECIPE TRANSLATED - SURVIVABLE INLINE BUT ALL-DEAD IN CAMPAIGN (2026-10-26)
- VoidStar Replicant (voidstarsec.com/blog/replicant-part-1) = the proven
  CW-Lite recipe on the SAME chip (Trezor One, stage-1 bootrom): clk_src
  'clkgen' at 100 MHz (10ns/ext-step), output 'enable_only', Glitch Out SMA
  DIRECT to VCAP1, width 40, offset -45, repeat 20, win at ext_offset 19752
  (~173us after true reset assertion; they found their trigger fired 24us
  early - same pipeline-latency discipline as our TIO3 calibration).
  KEY CORRECTIONS TO OUR ASSUMPTIONS: (1) enable_only is NOT wrong per se -
  our 16MHz enable_only was the same recipe at ~8x pulse energy (31ns vs
  ~4ns pulses) = lethal; (2) campaign default offset -45 matches their
  winner; (3) their stage-1 was reset-triggered, ours is stage-2
  (0x11/0xEE readmem at ~105us) - injection recipe transfers.
- INLINE survivability test (fresh CW open, clkgen 100MHz first, enable_only
  w40/off-45/rep20, ext 9700): 3 shots, ALL resp=1f1f probe=1f1f - chip
  alive and locked. RECIPE SURVIVABLE in isolation.
- CAMPAIGN pass vs1 (same params, ext 9660-9760 step 1, 2 samples, G_OUTPUT
  enable_only, no G_LATCH): 202 shots, **verdict dead on EVERY shot**,
  ~1.1/s with resync cycling. CSV: campaigns/glitch2_20261026_210046_vs1.csv.
- OPEN QUESTION (top priority next session): why does the identical config
  kill the chip inside the campaign but not inline? Differences to check:
  campaign per-shot arm/fire loop, its attempt() read timing, its resync
  path, whether width/offset/ext get re-applied per shot (partial-reconfig
  warnings), and whether the campaign's clkgen set path differs. The
  inline-vs-campaign delta is the experiment to bisect.
- Legacy hp/lp static writes now gated behind G_LATCH=1 (off by default) -
  the inline recipe omits them.

## ALL-DEAD BUG FOUND + FIXED: boot_and_sync RE-LATCH (2026-10-26)
- BISECTION: campaign attempt() verbatim inline = dead even in the bare-
  burst form that survived standalone. Cause: boot_and_sync(fast=False)'s
  pre-SMA "re-latch crowbar drivers" ritual (glitch_hp/lp False->True after
  power-up) - static-latched MOSFET gates make every 100MHz enable_only
  fire LETHAL. My earlier G_LATCH gating covered main()/reconnect() but
  NOT boot_and_sync (three copies of the latch existed).
- FIX: all latch sites now gated on G_LATCH=1 (off by default). With the
  latch removed, campaign attempt() x3 = nack 1f1f cleanly.
- PASS vs2 (post-fix): 100MHz enable_only w40/off-45/rep20, ext 9660-9760
  step 1, 2 samples = 202 shots @ 2.1/s, ALL nack, chip alive throughout,
  no weirds, no jackpot. CSV: campaigns/glitch2_20261026_212653_vs2.csv.
  The campaign loop is now healthy at 100MHz - pure hunting from here.

## SESSION CLOSE - RANGE SWEEP STopped, RIG RESET (2026-10-26 late)
- User's model confirmed as the operative plan: sweep the known window
  (105-106.5us + margin = ext 1520-1590 @16MHz, 62.5ns steps), log every
  shot, look for misbehavior, auto-dump on ACK - like the old stage-1
  3-dump_sram_direct.py flow but with UART payload and the good window.
- RANGE-SWEEP r1 launched (16MHz enable_only w40/49 r25/50/100, 1278
  shots/pass, looping) then STOPPED BY USER for the night; chip reset to
  healthy RDP1 bootloader state (sync 79, readmem NACK 1f1f verified).
- UNRESOLVED CARRY-INTO-NEXT-SESSION: delivery verification. During the
  RDP0-reflash bench work the glitch line came loose ("i just reconnected
  the glitch") - after which the old gray-zone settings STILL produced
  pure NACK (4MHz rep 5-400 ladders, scope off the node). We never obtained
  a confirmed node dip AFTER the reconnection (scope timed out during the
  verification attempt; user rule: scope never on the node during firing).
  FIRST ACTION next session: one verified-dip measurement (scope or LA on
  the CW-side leg, single shot between passes) - otherwise sweeps can't
  distinguish "injection works but doesn't fault" from "still broken".
- Also tonight: false alarms retracted (ch1 OFST was -1.8V from knob work ->
  pixel level readings garbage; "scope tap off" was wrong - it sat fine).
  Campaign progress line patched to show GLITCH TIME as us-after-0x11
  (the familiar 105.x number) every 50 shots; live window rule + scope-
  measurement-only rule codified in CLAUDE.md.
- Sweeps run tonight (all pure NACK, delivery unverified since reflash):
  vs2 202 | vs3 808 | vs4 404 | vs5 404 | vs6 510 | vs7 408 | vs8 510 |
  carpet 8x rep800 | 4MHz ladder 2x8 | r1 partial. ~3400 shots.

## OVERNIGHT R1 SWEEP + HEALTH-CHECK BUGS FOUND+FIXED (2026-10-27)
- Overnight r1 loop ran 5+ full passes (1278 shots each, all nack, CSVs in
  campaigns/*_r1.csv) - every pass ended UNHEALTHY -> reset_rig L1 (identical
  power-cycle boot!) reported OK each time. Chip was healthy all along;
  chip_health.py was broken: (1) UnboundLocalError - local 'cw = cw.scope()'
  shadowed the module import so the script CRASHED before printing (grep
  HEALTH found nothing -> loop took the UNHEALTHY branch); (2) Get ID
  checksum was wrong (0x02 needs ^0xFF = 0xFD, not 0x79); (3) it disconnected
  the CW before syncing, which can cut target power (single-owner CW: never
  open a second session while the loop holds it - that throws USBErrorIO).
- All fixed: local renamed to 's', GETID = 02 FD, session stays open through
  the sync then dis with target_pwr True. Verified standalone:
  "HEALTH: GOOD - sync 79, GetID 7901041179, readmem 1f1f [locked(RDP1)]".
- Loop health gate now matches "HEALTH: GOOD" only (DEGRADED/DEAD correctly
  trigger the reset_rig ladder).
- Chip state: alive, RDP1, all r1 passes pure nack, no jackpot. Delivery
  verification (confirmed node dip) STILL pending as first action.

## VERDICT: CW GLITCH OUTPUT STAGE DEAD (2026-10-27, user-confirmed)
- Progression of evidence: LA D3 on CW-side tap SILENT through manual fires
  (24MS/s, full-swing trains - unmissable if present); scope single-triggers
  never fire; user's eyes: flat 0V through manual fires ("i dont even see it
  fire" via scope/one_shot.py). My earlier "alive" claims from AUTO frame-
  diffs and pixel swing analysis were ARTIFACTS (AUTO repaint + UI-marker
  pollution) - both methods officially retired; LA + user eyes + clean
  single-trigger are the trusted instruments.
- Probable cause + time of death: the stale-MMCM violent event 2026-10-26
  ~15:30 (clkgen reconfigured mid-session -> rail-slamming misfire) - last
  confirmed real output behavior. Everything after (~6000 shots: vs2-vs8,
  4MHz ladders, rep-800 carpet, overnight r1 passes) fired into a dead
  output - ALL of that data is void for injection-effectiveness purposes.
- The attack stack is NOT the problem: UART protocol, campaign loop, health
  checks, timing windows, auto-dump - all proven. Only the injection element
  is broken.
- FIX PATHS (pick one):
  1. Inspect/reflow the CW SMA jack (cracked solder from cable strain is
     the classic failure - wiggle test with scope watching, or continuity
     check center pin to PCB).
  2. If the onboard MOSFET totem is blown: board-level repair or NewAE
     replacement.
  3. BYPASS (fastest to glitching again): external crowbar - the planned
     PN2222 3x-parallel stage (bases via 100ohm) driven from a CW TIO pin
     (logic-level enable pulse) or bring up the Pico Glitcher properly
     (pico_campaign.py) - mkesenheimer's actual architecture.
- Tooling note: scope/one_shot.py fires a single manual train (configurable
  args) for output verification; scope/scope.py cwcal saved as the
  cw_scope_calibration function (frame-diff method unreliable - use with
  care).

## BREAKTHROUGH: CW OUTPUT IS ALIVE - MILLIVOLT-SCALE, CRACKED JACK SUSPECTED (2026-10-27)
- THE CONTROL EXPERIMENT (decisive): scope armed at the user's
  max-sensitivity settings (1mV/div, 100ns/div, TRSL NEG @ -1.5mV):
  armed with NO fire = silent 6s, no trigger; armed + ONE manual fire
  = INSTANT FREEZE. VERDICT: REAL GLITCH SIGNAL, present exactly at
  fire moments.
- THE AMPLITUDE IS THE STORY: the output on the SMA is MILLIVOLT-scale
  (not the expected 0-3.3V logic swing). That is why: the LA (fixed
  logic thresholds) never saw it; the scope at normal V/div never saw
  it; the user's max-sensitivity zoom (500uV-1mV/div) finally caught
  it; ~6000 campaign shots produced pure NACK (mV pulses cannot
  disturb a 1.2V core rail).
- WORKING CATCH SETTINGS (saved to skill + scope tooling):
  A: C1 500UV/div, TDIV 50NS, TRSL NEG, TRLV -1.3MV, TRDL 12NS, SINGLE
  B: C1 1MV/div, TDIV 100NS, TRSL NEG, TRLV -1.5MV, SINGLE
  (user's knob-derived; both verified to freeze only on fire)
- ROOT CAUSE HYPOTHESIS: driver/FPGA alive but the output path
  attenuates ~1000:1 - consistent with a CRACKED SMA JACK SOLDER JOINT
  (capacitive coupling of the 3.3V pulse leaves mV residual; the user's
  finger pressure on the jack bridges it -> "touch catches a wave").
  FIX: reflow the CW SMA jack pads. Alternative paths if reflow fails:
  external PN2222 crowbar or NewAE.
- RETRACTION of the earlier "output stage dead" verdict - the stage is
  ALIVE, the SIGNAL is starved. Pixel forensics retired (again); the
  control-experiment method (fire vs no-fire) is the trusted way to
  verify signal presence from now on.

## ONE_SHOT --hard (2026-10-27): max-energy firing mode
- User's doubt accepted: cracked-jack hypothesis UNVERIFIED (they inspected
  it). Signal is millivolt-scale; no mechanism proven yet.
- one_shot.py enhanced: --hard = 1 MHz clkgen (4x longer pulses) + rep 4096
  (~4.1 ms train vs 25 us default = ~160x energy); --loop N = N back-to-back
  trains; --loop combines with --hard; positional args still override.
- Verified: --hard --no-scope fired cleanly. If even this shows zero chip
  effect on the UART side, the attenuation is >1000:1 and the CW output
  stage itself (driver transistor) is the suspect - NOT the jack.

## MECHANISM FOUND (2026-10-27, research): THE GLITCH SMA IS A CROWBAR
- rtfm.newae.com CW1173 "Using Glitch Port": the GLITCH SMA is wired to
  two MOSFETs (glitch_hp 20A pulse / glitch_lp) that PULL THE TARGET RAIL
  TO GND. The FPGA glitch signal only drives them when
  scope.io.glitch_hp=True / scope.io.glitch_lp=True is set in software.
- IMPLICATION: the 2.3mV catches at the SMA are EXPECTED behavior for a
  crowbar seen disconnected - NOT proof of a dying output stage. The
  dead-output verdict crumbles: the fire signal was routed to nowhere
  because OUR CODE NEVER ENABLES glitch_hp/glitch_lp. ~6000 campaign
  shots fired into disabled transistors -> pure NACK, healthy chip.
- Errata workarounds adopted in one_shot.py: vglitch_reset() after each
  fire (transistors can stick ON). New flags --glitch-hp / --glitch-lp.
- FIRST REAL CROWBAR TEST: short train + hp enabled, then chip_health.
  WARNING: do NOT long-short the rail with --hard first (transistor
  stress) - gentle <100us train for the first crowbar shots.

## FORUM INTEL (2026-10-27, research): newae thread 2668 - crowbar mode semantics + expected glitch depth
- Source: forum.newae.com/t/cw-lite-crowbar-circuit-question/2668
  (Aug 2021; answered by jpthibault, NewAE staff; answer accepted).
  Pulled full thread via Discourse JSON API.
- CONFIRMS the crowbar-mechanism entry above: glitch_hp / glitch_lp
  select which of two MOSFETs pull target Vcc to GND; can be used
  individually OR BOTH TOGETHER (max pull strength - an option for our
  first crowbar test if hp alone shows a weak dip).
- OFFICIAL MODE SEMANTICS (accepted answer, post 4):
  * glitch_only: `repeat` SEPARATE pulses, each shaped by width/offset.
  * enable_only: ONE CONTINUOUS pulse lasting `repeat` clock cycles;
    width/offset are IGNORED (no effect on pulse shape).
  -> Consequence for the VoidStar recipe (100 MHz, enable_only, rep20):
    that is a single 200ns continuous crowbar; its w40/off-45 values are
    inert no-ops in enable_only. Sweeping width/offset while in
    enable_only is a wasted axis - only repeat (pulse length) and
    ext_offset (timing) matter in that mode.
- REFERENCE DATAPOINT (thread poster, STM32G0 via 10R shunt + coax,
  glitch_hp only, enable_only repeat=100 @ 100 MHz = 1us crowbar):
  rail only pulled to ~2.2V initially, then decayed until FET release,
  ringback undershoot below 0V after release; net effect = MCU RESET.
  Lessons: (a) us-scale crowbar = POR reset, NOT a useful glitch - our
  200ns-scale trains are the right ballpark; (b) a rail that never
  reaches 0V is NORMAL (die internal caps + coax capacitance fight the
  FET), not evidence of a broken CW output.
- NewAE staff: "Just changing the cable can have a noticeable effect on
  the glitch" - once crowbar shots work, FREEZE the SMA leg/ coax setup;
  any cable change invalidates parameter sweeps.
- Linked thread 2007 (same answer): non-square GLITCHOUT waveform and
  MOSFET not fully driven = expected parasitics at ns scale (FPGA pin,
  trace, FET gate C/L). Do NOT chase a clean square edge on the SMA.
- Schematic ref for the MOSFET stage: newaetech/chipwhisperer hardware/
  capture/chipwhisperer-lite-32bit/cw-lite-arm-main.pdf

## PASS crowb1 - FIRST REAL-CROWBAR CAMPAIGN (2026-10-27, user-stopped at 400/1215)
- Driver patched (rdp1_glitch_campaign_full_mem_dump.py): G_CROWBAR=1 now
  DEFAULT - glitch_hp armed at startup + in reconnect() + re-latched after
  target power events; per-shot vglitch_reset() errata release (verified on
  live scope: vglitch_reset EXISTS in CW 6.0.0 runtime, and does NOT clear
  the glitch_hp latch - safe per-shot). Run-by-name defaults set: 16MHz,
  ext 2848-2928 (LA RDP window 178-183us after TIO3), w10,20,30,40,49,
  rep1,3,5, offset 0, glitch_only.
- SANITY SEQUENCE (per plan above): chip_health GOOD (sync 79, GetID
  7901041179, readmem 1f1f RDP1) -> one_shot --glitch-hp --no-scope (4MHz
  w49 off-45 rep100 = ~25us enable_only train, hp armed) FIRED + vglitch_
  reset RELEASED cleanly (first real execution of that call) -> chip_health
  GOOD again. VERDICT: chip survives a real crowbar pull, FET does not
  stick. Injection arm/release ritual is sound.
- CAMPAIGN: crowb1, ~400 shots at 1.6-1.8/s, ext 2848-2874 (~178.0-179.8us
  after TIO3), all widths/reps: **ALL nack, zero dead/weird/SUCCESS**.
  User stopped the pass. CSV: campaigns/glitch2_20261027_151759_crowb1.csv.
- INTERPRETATION: crowbar is armed and survives, but ~1/3 of the tight LA
  window at gentle settings (5-31ns pulses x1/3/5) produced NO observable
  disturbance on the F205. Either the pull is too shallow at this energy
  (STM32G0 forum datapoint: rail only sagged to ~2.2V under a 1us crowbar;
  F205 decoupling likely similar or better) or the window is still missed.
  NEXT-PASS OPTIONS: (a) finish ext 2874-2928; (b) escalate energy - rep
  10/25 or width sweep upward; (c) SCOPE VERIFY the pull depth between
  passes (measurement-only rule) - if the rail barely moves, skip to
  higher-energy modes (longer enable_only continuous pulses with latch
  discipline); (d) hp+lp BOTH armed (newae 2668: MOSFETs can combine).
- RIG QUIRKS: (1) SIGTERM/SIGINT handlers only tear down the CW session -
  the sweep LOOP KEEPS RUNNING (needs kill -9; fix = os._exit in teardown).
  (2) rig-drop AttributeError hit at only ~5 min this pass (reconnect
  ladder engaged as designed). (3) stdout to file is block-buffered -
  banners only visible after first flush; PR "offset=0 may not work"
  warnings are noise.

## FIRE_30S.PY - periodic fire loop for manual scope catching (2026-10-27)
- New tool `scope/fire_30s.py`: fires the crowbar train every N s (default 30,
  positional arg 1) until Ctrl-C. Crowbar hp ARMED BY DEFAULT (--lp adds lp,
  --no-hp for dry-run; --hard + positional overrides same as one_shot.py).
  Announces "firing in 3/2/1" + timestamped shots; SIGINT/SIGTERM always
  vglitch_reset + un-latch (os._exit hard-exit per rig quirk); waits out the
  train before FET release. Purpose: user catches the pull-down MANUALLY on
  the Siglent (wired on the glitch node) - no scope automation wanted.
- Rig status verified before handoff: CW re-enumerated on /dev/ttyACM0
  (had dropped - replug fixed), scope link up, smoke test (interval 1000,
  zero fires) opened/armed/released cleanly.
- CATCH-GUIDE correction for the manual hunt: the saved catch-A/B settings
  (500uV-1mV/div, NEG @ -1.3/-1.5 mV) were for DISABLED-crowbar feedthrough.
  With glitch_hp armed the real event is a DROP FROM THE ~1.2V VCAP IDLE ->
  use falling edge ~0.9-1.0 V, 100-200 mV/div; TDIV wide enough for the whole
  train (~25 us default / ~4 ms --hard). Partial sag that never reaches 0 V
  is normal (forum 2668 datapoint).

## UNLOADED CROWBAR PROBE READS FLAT 0V - EXPECTED, NOT A FAULT (2026-10-27)
- User probed a wire hooked DIRECT to the glitch output: flat 0 V, no drop on
  any fire. This is PHYSICS, not a dead output: the glitch SMA is an
  open-drain crowbar (MOSFET to GND) - it never sources voltage, it only
  sinks. A node with no pull-up sits at 0 V and every fire is invisible.
  The mV catches earlier were feedthrough at the same unloaded node - the
  only thing an unloaded probe can ever see there.
- CORRECT TESTS:
  A (output stage isolated): lift glitch node off VCAP, pull up 1-10k to
     3V3 (+ rail), probe node -> idle ~3.3V; fire -> slam to 0V = stage OK;
     flat 3.3V = output path broken (cracked SMA jack suspect -> reflow).
  B (real question): rig wired normally, probe the TREZOR-SIDE/strip-7 end,
     Trezor powered -> idle ~1.2V (proves you're on the powered VCAP rail);
     fire -> any dip toward 0 (partial sag OK per forum 2668) = crowbar pulls.
- Sanity traps when hand-driving the scope: CPL GND reads flat 0 regardless;
  trigger level below a 0V idle can never fire; 0V idle on a node that should
  be 1.2-3.3V = wiring break, chase continuity before blaming the CW.

## PIN 31 READS FLAT 0V WHILE CAMPAIGN RUNS AND CHIP WORKS - PROBE ARTIFACT OR OPEN INJECTION PATH (2026-10-27)
- User report: campaign running (sync + NACK loop alive), pin 31 probed flat
  ~0 V. IMPOSSIBLE as a real reading: VCAP_1 IS the 1.2V core regulator
  output - at 0 V the core has no supply and could not execute/NACK. The
  chip working PROVES real VCAP ~= 1.2V.
- Two explanations: (a) probe artifact - bad contact / wrong pad (Waveshare
  headers are NOT pin-number labeled, count from the dot; pin 31 sits right
  before VDD pin 32) / wrong board of the two on the bench; (b) THE DANGEROUS
  ONE: probe is on the CW-side leg of an OPEN injection jumper - leg floats
  0 V, chip fine, and EVERY campaign shot fires into a dangling wire = no-op.
  (b) would cleanly explain crowb1's ~400 silent shots in a tight window.
- CHECK ORDER: VDD pin (32/48/19/64) = 3.3V validates probe+board -> pin 31
  physically counted = ~1.2V -> scope on 31 during live shots: dips = path
  alive; flat 1.2V while firing = open path, ohm out SMA->strip7->pad with
  power off.

## ESCALATION LADDER - "GLITCH TOO SOFT" (2026-10-27)
- User verdict: campaign pulses are too soft. Agreed BY DESIGN: 16MHz
  glitch_only, width<=49 (~31ns max), reps 1/3/5, hp only = gentlest end
  (post-Oct-26-kill sanction). Patched the driver: new G_LP=1 env flag arms
  glitch_lp alongside hp (main + boot_and_sync re-latch + reconnect re-arm;
  teardown already cleared both). Syntax-checked.
- LADDER (safest first), each rung verified before the next:
  1. G_REPEATS=1,3,5,10,20 (no window math changes)
  2. G_LP=1 (both FETs, timing untouched - forum 2668 max pull)
  3. G_CLKGEN=8000000 G_EXT_MIN=1424 G_EXT_MAX=1464  (61ns pulses)
     G_CLKGEN=4000000 G_EXT_MIN=712  G_EXT_MAX=732   (123ns pulses)
     TRAP: ext units are clkgen cycles - rescale EXT or you sweep a wrong
     (100x-off) window. 178-183us window precomputed above.
  4. G_OUTPUT=enable_only + small G_REPEATS (62.5-250ns continuous @16MHz)
     - LAST: us-scale continuous = POR reset (forum datapoint); latched
     enable_only killed a chip 2026-10-26.
- SIGNAL TO WATCH: all-nack = not biting; first rise in dead/weird verdicts
  = pull is real -> stop climbing, sweep timing.
- PRECONDITIONS before trusting any rung: (a) SEE a dip on pin 31 synced to
  shots (else path open - see previous entry); (b) if on the Waveshare
  socket board COMP.H1 must be OPEN - 2.2uF on pad 31 eats 31ns pulses.

## ESCALATION OVERRIDE: START AT VOIDSTAR 200ns (2026-10-27)
-> SUPERSEDED by 2026-10-27 "STRENGTH CORRECTION: SWD-PROVEN 50-100ns FIRST"
  (repeat=20 was never proven anywhere; SWD winners are repeat 5-10)
- User decision: skip the gentle ladder, start at the VoidStar Replicant
  recipe found in scripts/6-dump_flash_uart.py: clkgen 100MHz, enable_only,
  repeat 20 = ONE 200ns continuous crowbar, hp+lp BOTH latched, w40/off-45
  (inert in enable_only). ~6x longer + 2x pull vs the crowb1 ceiling.
- NOTE: 6-dump_flash_uart.py never ran that campaign (sys.exit before the
  loop) - recipe-derived, not rig-proven. This IS the 2026-10-26 kill class
  (enable_only + latched gates @100MHz); repeat stays 20, do not climb.
- RUN (driver env knobs, G_LP patch):
  G_OUTPUT=enable_only G_CLKGEN=100000000 G_WIDTH=40 G_OFFSET=-45
  G_REPEATS=20 G_EXT_MIN=17800 G_EXT_MAX=18300 G_LP=1 G_TAG=voidstar200ns
  TRAP honored: ext units = clkgen cycles -> window rescaled 2848-2928
  (16MHz) to 17800-18300 (100MHz). Default EXT at 100MHz would have swept
  28-29us = 150us too early.
- Expectation: dead/weird verdicts SHOULD appear (chip reacting, driver
  auto-resyncs). All-nack at 200ns hp+lp => injection path itself broken
  -> pin-31 continuity check before any more sweeping.
- Safety variant if chip is precious: same run minus G_LP=1 (hp-only 200ns).

## STRENGTH CORRECTION: SWD-PROVEN 50-100ns FIRST (2026-10-27)
- User correction: the 6-dump_flash_uart.py strength class WORKED - but over
  SWD, in the backup dumpers, not the (dead-code) UART plan. Rig-proven set:
  backup/glitch_memory_read_swd_recovery.py = 100MHz enable_only hp+lp
  repeat 5 (50ns); backup/4-dump_flash.py = same but repeat 10 (100ns,
  "2 works" margin note). These produced the actual flash dumps.
  repeat 20 (200ns) was NEVER proven - demoted to reserve rung.
- RUN (UART campaign at SWD-proven strength, RDP window rescaled @100MHz):
  G_OUTPUT=enable_only G_CLKGEN=100000000 G_WIDTH=5 G_OFFSET=-45
  G_REPEATS=5,10 G_EXT_MIN=17800 G_EXT_MAX=18300 G_LP=1 G_TAG=swd-strength
  (10ns/step, 500 pts x 2 repeats ~ 1000 shots ~ 10 min at 1.7/s)
- Ladder from here if biting-but-no-ACK: G_REPEATS=20 next, nothing else
  changes. First dead/weird verdicts = pull is real.

## 2-MIN RUN swd-strength + TWO CORRECTIONS (2026-10-27)
- USER CORRECTION 1: JACKPOT_155433/155543 (15:54/15:55, canary NRC2,
  identical 256B) are PRE-RDP1 results - storage was readable when planted,
  so Read Memory ACKed un-glitched (hence shot-1 SUCCESS twice). NOT RDP1
  bypasses. What they DO prove end-to-end: trigger->glitch->verdict->
  complete_read->canary chain works; when the real bypass lands, the dump
  machinery is known-good.
- 2-min subagent run (glm-5.3-flash, G_SHOTS=200): 100MHz enable_only
  hp+lp, reps 5/10, ext 17800-17899 only, 198 nack + 2 DEAD (both rep10:
  #84 ext17841, #178 ext17888), clean exit, no reconnects. First genuine
  chip disturbances on this rig: rep10 (100ns) BITES, rep5 (50ns) 0/100.
  Real RDP1 bypass still unfound; window beyond 17899 unexplored.
- USER CORRECTION 2 + PATCH: driver now prints EVERY shot's verdict live
  (timestamp, #, ext/us, w, r, verdict+note) - previously nacks were silent
  between 50-shot heartbeats. Syntax-checked.
- NEXT: resume sweep G_EXT_MIN=17900 G_EXT_MAX=18300 (rep10 focus or both),
  per-shot lines now visible in the tail window.

## 2-MIN CHECK 2 (rep10-rest, 16:23) - TAIL STILL UNEXPLORED (2026-10-27)
- Subagent launch got interrupted mid-flight but the campaign had already
  started and completed cleanly: 200 shots ext 17900-18099 (179.0-181.0us)
  @ 100MHz enable_only hp+lp r10 = 100ns: ALL nack, zero dead/weird.
  Per-shot output patch verified live in the log.
- CUMULATIVE @ r10: 178.0-181.0us swept, 0 SUCCESS, only disturbances ever
  = 2 dead @ 178.41/178.88us (run 1). UNEXPLORED: 181.0-183.0us - the
  decision-adjacent tail (LA: NACK goes out +183.0us; the RDP refusal is
  decided just before). Next: G_EXT_MIN=18100 G_EXT_MAX=18300, same knobs.

## DRIVER DEFAULTS = SWD-PROVEN STRENGTH (2026-10-27)
- rdp1_glitch_campaign_full_mem_dump.py defaults rewritten: bare
  `python rdp1_glitch_campaign_full_mem_dump.py` now = 100MHz enable_only
  hp+lp (G_LP default ON) repeat 10 (100ns), w5/off-45 (inert), ext
  17800-18300 (full LA window @ 10ns steps). Old gentle crowb1 defaults
  (16MHz glitch_only w10-49 rep1,3,5 ext2848-2928) are env-overridable
  history. Header doc updated incl. the repeat<=10 kill caution. Verified
  by config-parse + py_compile; env overrides still win over defaults.

## SMA vs DUPONT STRENGTH - SMA MUCH STRONGER, REP10 VIA SMA = CHIP KILLER (2026-10-27)
- USER MEASUREMENT (definitive, on the scope): the direct SMA injection and
  the dupont/breadboard pin are VASTLY different strengths - SMA much
  stronger. At rep 10 (100ns) via SMA the chip dies EVERY shot.
- Retroactively explains the quiet dupont era: the breadboard path's series
  impedance was eating the pull (consistent with crowb1 silence + only 2
  deads at rep10 when jumpered).
- DEFAULTS DIALED BACK 20%: G_REPEATS 10 -> 8 (8 cycles @100MHz = 80ns,
  exactly -20%). repeat stays the strength knob, 10ns steps: still all-dead
  at 8 -> try 7 (70ns) / 6 (60ns); all-nack -> 9. Dead=nack=SUCCESS ladder:
  too strong dead, too weak nack, sweet spot between.

## STRENGTH-VISIBLE OUTPUT + R0 TUNING VERDICT = LETHAL BAND, NOT STRENGTH (2026-10-27)
- User: log didn't show strength params. Patched: startup banner prints
  STRENGTH line (mode/clkgen/FETs/repN=XX.Xns); per-shot lines now carry
  r8=80.0ns-style pulse length (enable_only only). CSV config row already
  had clkgen.
- 5%-down tuning loop (subagent, G_REPEATS=8 fixed, clkgen ladder ready):
  R0 = 80.0ns was NOT all-dead (35 dead + 10 nack) -> rule says keep 80ns,
  R1-R5 never needed.
- KEY RE-READ of the tally: deads are a CONTIGUOUS ext band 17800-17834
  (178.00-178.34us); nacks start exactly at ext 17835. Same strength flips
  kill<->no-op at ~178.35us = TIMING boundary, not a strength problem.
  Partial faults (ACK/SUCCESS) cluster at lethal-band edges - and run-1's
  2 deads (178.41/178.88us) are in this neighborhood.
- NEXT: dense boundary sweep 80ns, G_US_MIN=178.30 G_US_MAX=179.20
  G_SAMPLES=2; then the rest of the window.

## KNOWN-BASELINE GATE - STOP GUESSING AFTER KILLS (2026-10-27)
- User challenge (correct): after a dead shot the old flow only proved
  "alive" (0x7F->0x79 sync), NOT known state. NRST resync can leave a
  degraded chip answering sync; own boot discipline says NRST is not
  reliable out of lockup. The 182/182-dead boundary run is therefore
  SUSPECT DATA: either a genuinely widened lethal band, or one real kill +
  181 shots at an unverified chip.
- PATCHED: baseline_probe() = unglitched 0x11 0xEE must NACK (0x1F) before
  EVERY shot = bootloader alive + RDP1 still armed + UART nominal.
  shot_with_baseline(): probe -> attempt(); on 'bad': round 0 NRST resync,
  rounds 1-2 full power cycle, re-probe each time; 3 failures = hard error
  (never guess). Bonus: unglitched ACK ('unlocked') = persistent in-session
  bypass -> completes the read with NO glitch (Kraken: RDP1 downgrade can
  persist across soft resets until power cycle).
- Cost: ~ms per shot when healthy; dead shots now cost NRST-or-powercycle
  + re-probe. 'dead' verdicts from here on = glitch killed a PROVEN-healthy
  chip seconds earlier - much stronger evidence.
- NEXT: re-run the boundary sweep (178.30-179.20us, 80ns) WITH the gate.
  Outcomes decode cleanly: probes pass + all-dead = real widened lethal
  band; probe failures/storms = recovery was the problem all along.

## GATE REFINEMENT: BASELINE PROBE ONLY AFTER UNKNOWN STATE (2026-10-27)
- User refinement: gate only when state is actually unknown - after
  dead/weird/ACK_NO_DATA, at campaign start, after rig-drop reconnect.
  A plain nack IS baseline proof (correct 0x1F answer = alive + RDP1 armed
  + UART ok), so healthy nack streaks run full speed with no extra UART
  exchange. Patched: need_baseline flag in main loop; baseline_then_shot()
  replaces shot_with_baseline everywhere relevant. Compile-checked.

## FULL SWEEP ABORTED BY USER @135 SHOTS: 80ns = 100% LETHAL, GATE-VERIFIED (2026-10-27)
- Full-window sweep (178-183us, 80ns SMA-direct) stopped by user at shot
  #135: 135/135 DEAD across 178.00-179.34us. Baseline gate was active:
  after every kill the probe re-verified known baseline (fast NRST
  recoveries, probes passing) -> these are GENUINE kills of verified
  chips, not recovery artifacts. Crowbar manually released after kill -9.
- CONCLUSION: 80ns direct-SMA is entirely in reset-land - no timing sweet
  spot exists at this strength. R0-tuning's 10-nack tail now reads as an
  early-run state fluke (the rung that "passed" the all-dead rule).
- LADDER LOGIC CORRECTION: never actually descended - R1(76ns)/R2(72ns)/
  R3(68ns) untested. Bracket known: 50ns-equiv = all nack (dupont rep5),
  80ns = all dead. Transition zone ~55-75ns is the hunting ground; find
  the rung where dead/nack MIX, then dense-sweep timing there.

## USER SCOPE MEASUREMENT: TARGET RANGE REASSESSED (2026-10-27)
- Fresh scope measurement: the memory-related activity ("mem issue") runs
  from -189us TO 0 relative to the current glitch injection point (+178us
  after TIO3) = ABSOLUTE 0 -> ~178us after TIO3 (the whole 0x11 0xEE pair
  reception period). The old 178-183us window was NACK-edge-derived - only
  the tail of the story. The -11us beyond TIO3 is unreachable (trigger =
  burst start).
- STRENGTH -10%: 80 -> 72.0ns (G_REPEATS=8, G_CLKGEN=111110000) - below
  the gate-verified 100%-lethal 80ns point; expect deads to thin out.
- NEW SWEEP: G_US_MIN=0 G_US_MAX=178; resolution choice: G_STEP=10 (100ns,
  1780 shots, 20-40 min coarse pass) then refine clusters at step 1.

## STRENGTH -20%: 64.0ns (2026-10-27)
- User scope observation at 72ns: no NACK visible = chip dead mid-pair
  (the dead verdict seen from the UART side). 72ns STILL lethal.
- Dropped to 64.0ns = rep8 @ 125MHz clkgen (clean values), now the driver
  DEFAULT. Bracket: >=72ns lethal (80 gate-verified 135/135, 72 observed),
  ~50ns-equiv all-nack (dupont rep5) -> hunting ground 50-72ns, 64 first.
  Ext step at 125MHz = 8ns.
- Wide pass command: G_US_MIN=0 G_US_MAX=178 G_STEP=10 (=80ns steps,
  2225 shots) @ 64ns; refine clusters later at step 1.

## DESCENT CONTINUES: 50ns STILL LETHAL -> DEFAULT NOW 40.0ns (2026-10-27)
- User at 50ns direct-SMA: "hits too hard" - chip still dies, no NACK.
  Direct-SMA descent all-lethal so far: 100/80/72/64/50 ns. KEY FACT:
  dupont-path ~50ns-equiv was ALL NACK -> direct-vs-dupont attenuation
  puts the real bracket BELOW 50ns direct.
- DEFAULTS: G_REPEATS=4 @ G_CLKGEN=100MHz = 40.0ns (10ns ext steps back).
  Next rungs if still lethal: rep3=30ns, rep2=20ns; walk up on first nacks.
  Docstring ladder updated (G_OFFSET line restored, stale rep8 block gone).

## LA MEASUREMENT @ 40ns: CHIP SURVIVES - BRACKET CLOSED TO 40-50ns (2026-10-27)
- la_glitch_timing.py (D0/D1 = host/chip TX, D2 = glitch tap, 16 MHz):
  3 shots @ 40ns/178us: chip ALIVE every shot - clean 1f1f double-NACK
  read by FTDI AND visible electrically on D1 (8 transitions = 2 frames,
  starting ~200us after burst start, consistent with the 183-191us window).
- D2 (glitch tap) FLAT: 40ns < 62.5ns LA sample period - the LA can NEVER
  resolve these pulses (fx2lafw max 24MHz = 41.7ns). Scope remains the
  only pulse-width instrument; LA silence is NOT no-fire evidence.
- Decoder bug found+fixed: back-to-back 1f1f frames failed strict UART
  decode -> script printed "chip DEAD" wrongly; now falls back to raw
  transition evidence ("response on the wire").
- STRENGTH BRACKET CLOSED: >=50ns direct-SMA kills (100/80/72/64/50),
  40ns = alive clean NACK -> MIX ZONE IS 40-50ns. Next probe 45.0ns
  (rep5 @ 111.11MHz clkgen), then sweep 175-185us there.
- Rig notes: CW SAM3U wedged (USBErrorIO during PR program at connect)
  after kill -9 sessions - self-recovered after ~1 min idle; NOTE the
  usb_reset tool only resets the ST-Link, NOT the CW. Sweep window
  default extended to 175-185us per user.

## NEW TOOL: la_campaign_snoop.py - CAMPAIGN + LA SNOOP IN ONE (2026-10-27)
- User request: a campaign variant the LA can snoop to VERIFY the timing.
- Built storage-sim/la_campaign_snoop.py: imports the driver as g2 (same
  G_* env config, baseline gate, verdicts, JACKPOT handling), fires each
  shot inside a 0.8s/16MHz sigrok fx2lafw window, decodes per shot:
  t0 = 0x11 start bit on D0 (= TIO3 reference), chip response start/edges/
  frames on D1, expected glitch moment ext/clkgen vs measured, D2 edges.
  Per-shot CSV -> campaigns/lasnoop_*.csv. LA_* knobs: LA_SR, LA_WIN,
  LA_SHOTS. Pace ~3-5s/shot = verification instrument, not a hammer.
- Caveat encoded in output: sub-62.5ns pulses invisible on D2 at 16MHz -
  D1 response presence/timing/garble is the verifiable signal.

## CLEAN UART SNAPSHOT (LA, no glitch) - THE REFERENCE FRAME (2026-10-27)
- la_snapshot.png (D0/D1 only, 2 MHz): sync exchange host 0x7F -> chip ACK
  0x79 @ +170us; read-mem exchange host 0x11 0xEE (182us burst) -> chip
  NACK 0x1F x2 starting +200us after first TX edge (= the TIO3 reference).
  Both per RDP1 spec. This is the no-glitch baseline waveform to diff any
  disturbed capture against.
- Traps hit while snapshotting (now encoded in tooling memory): mid-session
  0x7F is IGNORED (first sync must be inside the capture); LA window must
  exceed arm delay (0.6s window missed the 0.7s-delayed exchange - use
  1.5s @ 2 MHz like la_measure.py).

## SWEET SPOT CONFIRMED: THE 0xEE-END -> NACK-START GAP (2026-10-27)
- User notes: sweet spot is right after the 0xEE and before the NACK.
  Today's clean LA snapshot quantifies it vs TIO3: 0xEE stop ends ~+173us,
  NACK starts ~+187us -> ~14us decision gap. Driver default 175-185us is
  CENTERED in it. Window choice validated; keep it.
- Reference reconciliation: the 2026-10-23 note ("0xEE ends +182us, NACK
  +183us past TIO3") was almost certainly measured from the 0x11 START-BIT
  FALL, not the TIO3 rising edge (+8.7us offset) - today's independent
  numbers are the authority (gap ~14us, not ~1us).
- Hunt plan unchanged: 45ns (mix zone, 40-50ns bracket) across 175-185us,
  diff disturbed captures vs the la_snapshot.png reference frame.

## WINDOW SET TO THE FULL GAP: 173-187us (2026-10-27)
- Driver defaults updated to EXT 17300-18700 @100MHz = the complete
  0xEE-end->NACK-start decision gap per user notes + LA measurement.
  Full pass at 40ns defaults (~1400 grid points, bare run) next; user
  runs it manually to see what happens.

## 40ns FULL-GAP PASS RESULT + STEP TO 45ns DEFAULTS (2026-10-27)
- glitch2_20261027_185903.csv: 1401 shots 173-187us @ 40ns = 1351 nack
  (96.4%), 48 dead (3.4%, scattered whole window), 2 WEIRD both note 'ff'
  at ext 18539/18682 (185.4/186.8us) - right at NACK-onset. No success.
  Reading: 40ns is at the disturbance floor (occasional kill + rare
  frame-corrupt), everything still alive -> step up.
- Defaults now: CLKGEN=111110000, REPEATS=5 (45.0ns pulse, ext step 9ns),
  window 173-187us. WINDOW IS NOW PRIMARY IN MICROSECONDS (G_US_MIN/MAX,
  auto-converted per clkgen) - the 100MHz-bound cycle literals are gone;
  G_EXT_* raw cycles only as explicit override. Bare run = 45ns full-gap.

## 45ns FULL-GAP: FIRST PARTIAL BYPASS (ACK_NO_DATA) -> STEP TO 48ns (2026-10-27)
- glitch2_20261027_191936.csv: 1556 shots @45ns = 1312 nack (84.3%),
  222 dead (14.3%), 20 weird (junk bytes ff/f0/e0/00../fc000000/fe000000/
  f8000000 = corrupted 0x1f frames, spread whole window), and 2x
  ACK_NO_DATA - NEW VERDICT CLASS, FIRST PARTIAL BYPASS:
    #664 178.97us  cmd stage ACKed (0x79 in response!), addr stage 1f1f
    #989 181.89us  cmd stage ACKed, addr stage silent
  Driver confirmed: response contained 0x79 -> complete_read() ran -> addr
  stage refused. The RDP command-stage NACK WAS FLIPPED at 45ns.
- Dead by segment: 173-177.5 = 21.6%, 177.5-182 = 16.4%, 182-187 = 5.8%
  (early gap = most kill-prone). Both ACK_NO_DATA in the middle segment.
- KEY REASONING for stronger: the addr stage happens AFTER the glitch is
  over -> only a PERSISTENT (latched register/flag) fault can pass it; a
  transient execution fault never can. Each width step deepened the fault
  (40: ff-weirds only; 45: cmd-stage flip) -> 48ns = rep6 @125MHz (ext
  step 8ns, ext 21625..23375) is the next and last rung below the 50ns
  all-dead wall. Defaults updated; bare run = 48ns full-gap.
- Fallback if 48 goes mostly-dead (>60%): retreat to 45ns with
  G_REPEATS=5 G_CLKGEN=111110000 G_SAMPLES=3 (ACK_NO_DATA lottery), or
  hammer the 177.5-182us segment only.

## 48ns FULL-GAP: ZERO FLIPS -> 45ns IS THE FLIP ZONE (2026-10-27)
- glitch2_20261027_194713.csv: 1751 shots @48ns = 48.1% nack, 46.5% dead,
  5.3% weird, ZERO ACK_NO_DATA. Ladder now: 40ns 3.4% dead/0 flips;
  45ns 14.3% dead/2 flips (178.97/181.89us); 48ns 46.5% dead/0 flips;
  50ns wall. The FLIP window sits BELOW the KILL window - at 48ns any
  fault deep enough to reach the decision logic takes the core down.
  More width is the wrong knob from here.
- 48ns weirds are WIRE SHREDDING not decision effects: 93 junk bytes
  (fe00/fc00/f800/e000/c000... = corrupted 0x1f 0x00 frames), 74/93 in
  182-187us = glitch landing on the outgoing NACK frame itself. 0x79 (the
  ACK_NO_DATA byte) cannot arise from bus corruption - decision-level only.
- Dead by segment @48ns: 56.9/56.5/28.3% - kill floor flat and high across
  the early+mid gap (was front-loaded at 45ns).
- DECISION: back to 45ns (rep5 @111.11MHz) + G_SAMPLES=3 full-gap
  (~4668 shots, expect ~6 ACK_NO_DATA if the 2/1556 rate holds; each =
  lottery ticket for a latched/persistent fault = SUCCESS, since the addr
  stage only passes if the flip persists past the glitch). SHOTS_MAX
  default raised 2000 -> 6000 so the run is not truncated. Est 1.5-2.5h
  with recoveries (14% dead @45ns).

## OVERNIGHT RUN CONFIG: 46.0ns x 3 SAMPLES (user decision, 2026-10-27)
- User call after 48ns review: pull back strength to ~46ns AND raise
  samples to 3x per ext point; overnight duration is fine.
- Defaults set: CLKGEN=108695652 (rep5 = 46.0ns exactly, ext step 9.2ns),
  G_SAMPLES=3, window 173-187us -> ext 18804..20326 = 1523 pts x 3
  = 4569 shots. Est 3-4h+ at ~20-28% dead (recovery overhead).
- Hypothesis under test: flip-rate peak sits between 45 (2 flips/1556)
  and 48 (0/1751). If 46nm yields flips >= 45-rate -> farming near the
  peak; if zero -> peak at/below 45, drop back next run.

## 46nm ABORTED (39% DEAD IN 92 SHOTS) -> NO-DEAD FARM AT 42nm (2026-10-27)
- Live 46nm run: 36/92 dead (39%) in first 10 min = kill-floor territory,
  nowhere near the hoped flip/kill split. User call: NO DEADS. Killed at
  ~20:38, CW released, run scrapped at shot ~93 (CSV glitch2_20261027_203515).
- Kill-floor curve is STEEP: 45nm=14.3% -> 46nm~39% -> 48nm=46.5%. The
  survivable band is <=45nm; the flip zone overlaps it near 45.
- NEW PLAN (user): dead-free farm at 42.0nm (rep5 @119.047619MHz, ext step
  8.4ns), G_SAMPLES=4 over 173-187us -> 6668 shots, SHOTS_MAX 8000.
  Logic: 40nm survived 96.6% but showed only wire junk; 42nm is just above
  the survivable floor - if the flip distribution has a deep tail, this
  farms it without paying recovery time. Expected dead <5%.

## 42nm OVERNIGHT FARM: 3 MORE FLIPS, BAND LOCALIZED (2026-10-28 overnight)
- glitch2_20261027_203825.csv: 6668 shots @42nm x4 samples = 92.1% nack,
  7.5% dead, 23 wire-junk weirds, 3 ACK_NO_DATA:
    #3688 180.73us (addr 1f1f), #3879 181.14us (addr 1f1f),
    #4350 182.13us (addr nothing)
- ALL 5 FLIPS EVER (2@45nm + 3@42nm) LAND IN 179-182us - the flip band
  is LOCALIZED to a ~3us strip mid-gap. Early window (173-177.5): 3000+
  shots across all passes, ZERO flips, kills only -> dead weight.
- Ladder update: 40nm 3.4%dead/0 flips; 42nm 7.5%/0.45-per-k; 45nm
  14.3%/1.28-per-k; 46nm 39%+/0; 48nm 46.5%/0. Flip distribution extends
  below 45 - no-dead farming works, user instinct validated.
- All 5 flips TRANSIENT (addr stage refused). Latched-fault lottery: 0/5.
  Next: band-concentrated farm 179-183us @43.5nm x15 samples (~6900
  shots, all in-band) or @42nm x30 (~14k) - pending user choice.

## BAND FARM RUNNING: 42nm x30 IN THE FLIP BAND (2026-10-28, user pick)
- User chose minimal-deads: 42.0nm (rep5 @119.047619MHz), band 179-183us
  ONLY (the localized flip band - all 5 flips ever landed 179-182us),
  G_SAMPLES=30 -> ext 21309..21785 = 477 pts x 30 = 14310 shots.
  Log /tmp/opencode/bandfarm42.log, watch window DISPLAY=:1. PID 300153.
- First 115 shots: 4.3% dead - minimal-dead profile confirmed.
- In-band flip rate @42nm ~1.6/1000 (3 flips / ~1900 in-band shots from
  the overnight run) -> expect ~20+ ACK_NO_DATA draws at the latched-fault
  lottery (currently 0/5). Est 4.5-5.5h with recoveries.
- Ops note: a kill-loop `for P in $(pgrep -f 'rdp1_glitch_campaign')`
  SIGKILLs its own shell (pattern matches own cmdline) - use
  pgrep -af '[r]dp1_glitch' bracket trick. Cost one failed launch attempt,
  no harm done.

## *** 8 SUCCESS SHOTS - ALL PAYLOADS LOST TO INDENT BUG *** (2026-10-28)
- Band farm 42nm produced EIGHT full bypasses (verdict SUCCESS = 0x79 ACK
  + 256B payload read from 0x08008000), first at 22:26 (#2684), user
  spotted #11325 at 23:37. Winning offsets (ext @119.047619MHz, 42.0nm):
    21398 (179.7us)  21424 (180.0us)  21453 (180.2us)  21511 (180.7us)
    21528 (180.8us)  21542 (181.0us)  21679 (182.1us)  21686 (182.2us)
  Two clusters: 179.7-181.0 and 182.1-182.2. ~1 success per 1400 shots
  overall; per winning point ~1/30 samples.
- BUG: the `if verdict == 'SUCCESS'` block sat OUTSIDE the SAMPLES loop -
  checked only the LAST sample's verdict; mid-loop SUCCESS payloads were
  overwritten by subsequent nack shots and never written. No JACKPOT_*.bin
  exists. Campaign kept running (should have torn down) - how it went
  unnoticed for 8 hits.
- FIXED: SUCCESS check moved INSIDE the sample loop (writes payload,
  prints, tears down, returns immediately). Also added G_EXTS env
  (comma list of exact ext values) to hammer known winners instead of a
  range sweep.
- NEXT: hammer the 8 winning exts x50 samples (~400 shots, ~20 min) with
  the fixed code - expect several real JACKPOT dumps.

## HAMMER RESULT: 0/400 - UNDERPOWERED, SURVIVORSHIP BIAS (2026-10-28)
- Hammer of the 8 winning exts x50 = 400 shots, 0 SUCCESS. Root cause of
  the miss: my 1/30-per-winning-point estimate was survivorship bias.
  Honest rate = 8 successes / 11325 in-band shots ~= 1/1416. 400 shots
  expected 0.28 -> zero is the statistically likely outcome, rig fine.
- The apparent time-drift of winning offsets was the SWEEP FRONT moving
  (~4 ext/min), not a physical drift - band is static at 179.7-182.2us.
- RELAUNCH: corrected farm with FIXED capture code, band 179.5-182.5us
  x30 samples = ~357 pts x 30 = ~10710 shots (~3.5-4h) -> expect ~7
  real JACKPOT dumps at the proven 1/1416 rate. G_SAMPLES=30 default,
  G_TAG=band2.

## DRIVER IS NOW A FULL-DUMP COLLECTOR (2026-10-28, user requirement)
- User: real chip has no canary - we need the FULL storage, organized in
  a subfolder. Rewrote the SUCCESS path: each flip reads the NEXT MISSING
  chunk (66 targets: 64x256B storage @0x08008000-0x0800BFFF, uid 12B
  @0x1FFF7A10, otp3 32B @0x1FFF7860, priority storage head -> uid ->
  otp3 -> rest). complete_read() parametrized on CUR target.
- After each secured chunk: chain_unglitched() probes an unglitched 0x11
  - if the bypass latched for the session it drains ALL remaining chunks
  in one go ([LATCHED+] lines); else farm continues for the next chunk
  (one flip = one transaction, verified: shot after SUCCESS nacked).
- Outputs: dumps/run_YYYYmmdd_HHMMSS/<chunk>.bin + manifest.txt per
  chunk (shot/ext/time/first16); storage_dump.bin + uid.hex + otp3.hex
  assembled when complete. G_RESUME=<dumpdir> preloads collected chunks
  for multi-night collection. Heartbeat shows chunks x/66.
- Canary demoted to informational print (practice chip only).
- Cost estimate for full collection: ~66 flips x 1416 shots/flip ~ 90k
  shots (~20h+ farming) unless a latch appears, then it all drains free.
USBDEVFS_RESET unsticks wedged CW

## GHOST NIGHT POST-MORTEM + FLATLINE DETECTOR (2026-10-28)
- collect1 (00:02, 10740 shots @42nm band): 10740/10740 CLEAN NACKS -
  zero dead/weird/flips. Statistically impossible for a firing crowbar
  (expect ~5% dead). Cause: silent pulse failure after the 23:55 kill-9 +
  USBDEVFS_RESET recovery - the session's pulses never landed; healed on
  any fresh scope open. 4h lost, no info gained, chip unharmed.
- Probes this morning: (1) hp/lp arm state survives vglitch_reset;
  (2) lethal 58.8ns in-band shot -> chip DEAD + trigger fired = pulse
  path works; (3) live 120-shot campaign segment @42nm -> 6 dead (5%),
  disturbances normal. Rig exonerated; ghost was session-specific.
- NEW: flatline detector in the shot loop - 400 clean nacks = warning,
  800 = re-arm FETs, 1600 = teardown + hard exit (os._exit(4)) so a
  relaunch gets a fresh CW session. This failure mode can no longer
  burn hours silently.
- Relaunching collector as collect2 (fresh - nothing to resume).

## ZOMBIE FILTER + 41nm + PCROP SOURCE ANALYSIS (2026-10-28)
- Source https://jerinsunny.github.io/stm32_vglitch/ (STM32F401, same
  attack: VCAP glitch, 0x11 under RDP1, 256B per glitch): they hit OUR
  exact zombie - full ACK handshake, data = all zeros. Their diagnosis:
  the GLITCH ITSELF was setting PCROP/SPRMOD (option-byte latch) ->
  under PCROP, flash DATA reads return 0x00. Fix: fine-tune (weaken) the
  glitch. Endgame numbers validate our collector: 1024 chunks / 621594
  glitches / 22h / ~1-per-607 rate, one 256B read per flip, no session
  latch (matches our post-SUCCESS nack observation).
- ZOMBIE FILTER added (asymmetric, deadlock-proof): exact-length required;
  all-0x00 -> verdict 'zombie' (retry chunk, gates baseline resync like
  dead/ACK_NO_DATA - reloads clean OB latches each reset); all-0xFF ALWAYS
  accepted (61/66 chunks are legit FF padding - rejecting = deadlock).
  Self-tested against real module: 00-reject, FF-accept, short-reject,
  data-accept. Practice oracle: banked storage chunks compare vs
  storage.bin, informational MATCH/MISMATCH print + manifest note.
- Strength 42 -> 41.0nm (rep5 @121.951220MHz, ext step 8.2ns); window
  179.0-182.5us (user: start at 179, no early success yet). 428 pts x 30
  = 12840 shots. Rationale: weaker glitch = flip the branch WITHOUT
  corrupting OB latches / killing core mid-22ms-data-phase.
- Phase-2 note (RDP2->RDP1): PCROP risk is REAL there - OB writes are the
  attack surface; post-regression checklist: read back OB (RDP, SPRMOD,
  WRP) via SWD BEFORE trusting dumps; SPRMOD set -> clear via OB write;
  all-zero post-regression reads = suspect PCROP, not zombie.

## CHIP-SPECIFIC TARGET LIST DOCUMENTED (2026-10-28, user)
- The 66-chunk TARGETS list is for the PRACTICE chip ONLY - a different,
  SMALLER-memory part than the Trezor One (16 KB planted region + uid +
  otp3). Documented in-script at the TARGETS definition: on the real
  Trezor chip the dump must cover the FULL memory - resize
  STORAGE_BASE/STORAGE_LEN to the Trezor layout, TARGETS regenerates,
  cost ~1 flip (~1/1400 shots) per extra 256 B chunk.

## DIAL TO 40nm + REST 20s -> 10s (2026-10-28, user)
- collect3 @41nm: 5.7% dead in ~200 shots - user: "not supposed to go
  dead". Back to 40.0nm (rep5 @125MHz, ext step 8ns, ext 22375..22812,
  438pts x 30 = 13140 shots). Tradeoff logged: every flip-capable
  strength (42+) also kills; 40nm = lowest characterized flip-plausible
  point (3.4% dead, its 1401-shot zero-flip sample was underpowered at
  the 1/1416 rate); zero-dead (~38nm) has never flipped.
- G_REST_S default 20 -> 10 (user; the every-300-shots pause).
- collect3 killed at ~#200, nothing banked; collect4 launched fresh.

## DIALED 40 -> 39nm (2026-10-28, user)
- collect5 @40nm killed at ~#160 (3.8% dead - normal for 40). User: one
  more notch down. Defaults now 39.0nm (rep5 @128.205128MHz, ext step
  7.8ns). WARNING logged in-script: 39 is below every strength that has
  ever flipped (all known flips at 42; 40's zero-flip was underpowered).
  If a full 39nm pass yields zero flips -> floor is 40-42, stop descending.

## 39nm FULL PASS: ZERO FLIPS - FLIP FLOOR IS 40-42nm (2026-10-28)
- collect6 (13,500 shots, 179-182.5us, 30 samples/pt @39nm): 13,259 nack
  (98.2%), 226 dead (1.7%), 0 flips / zombies / chunks. Expected ~9 flips
  at the 42nm rate (1/1416). CONCLUSION: 39nm is BELOW the flip floor;
  the 40-42 band is where flipping happens. Do not descend further.
- Single-1f stats confirmed (user observation): P(next=dead) 18.0% after
  single-1f vs 1.37% after clean 1f1f; 100% of deads+flips in the 42nm
  run were within 0.5us of a single-1f; ghost night had ZERO single-1f
  (single-count = definitive 'glitch biting' health metric; candidate
  flatline-detector upgrade, not yet wired in).
- NEXT: user scout - 39nm, 175-189us, 1 shot per 0.1us (G_US_STEP=0.1 ->
  13 cycles = 101ns), 139 pts. New G_US_STEP knob converts us->cycles.
173-192us @ 0.1us step, 5 samples -> ~190 pts x 5 = ~950 shots

## WIDE SCOUT 173-192us @39nm: 39nm DOES FLIP (2026-10-28)
- scout173 (940 shots, 1-per-0.1us x5): 1 ACK_NO_DATA flip @ ext 179.7us
  (+4 single-1f at the same point - 5/5 disturbed), 13 dead, 3 wire-junk.
  Combined with collect6: 39nm flip rate ~1/14,000 vs 42nm 1/1,416
  (10x rarer, NOT zero - collect6's 0/13,500 was bad luck).
- DISTURBANCE MAP @39nm: singles-dense micro-zones 177.2-177.4 and
  179.7-180.0 (4-5/5 disturbed per point); everything else inert except
  scattered deads + NACK-wire junk (183.9, 190.5, 191.1).
- User's single-1f marker theory CONFIRMED at max strength: the flip
  landed exactly at the highest singles-density point. Hammering
  singles-dense points >> blind sweeping.

## HAMMER39 LAUNCHED: 6 hot points x 100 (2026-10-28, user plan A)
- G_EXTS=22712,22725,22738 (zone A 177.2-177.4us) + 23037,23050,23076
  (zone B 179.7-180.0us incl. the flip point), 100 samples each = 600
  shots @39nm. Goal: prove CHUNK SECURED at 39nm with zombie filter live.
  After: full farm back at stronger (42nm) per user plan.

## BACK TO 42nm FULL FARM (2026-10-28, user decision)
- hammer39: 0/600 flips at the 6 hot points; LA capture (Desktop/
  digital.csv, 489s) confirms wire-level: every 79 follows a 7f (resync
  acks), zero 79-after-burst; ff-episodes = kills on the wire (parity-
  dropped by tty -> logged as dead); ch2 shows crowbar firing every shot.
  Hypothesis logged: flips may be reset-conditioned (boot-to-boot HSI
  alignment), not purely ext-timed - future lever: 1-shot-per-boot
  cycling through hot exts.
- User: back to 42nm full farm. Defaults: rep5 @119.047619MHz, band
  179-182.5us, x30 samples = ~10740 shots. The collection strength.

## GHOST-FF READ + 1F-FLOOD STATE + FIXES (2026-10-28)
- farm42 (12.4k shots): 1 zombie (filtered, worked), 1 "CHUNK SECURED"
  storage_0000 = ALL-FF = GHOST READ (flash returned erase-pattern for
  planted data; oracle MISMATCH caught it) - THIRD fault class after
  zombie-00 and wire-shred. Bad chunk purged; storage_0000 re-farms.
  REAL-CHIP IMPLICATION: no oracle there - ghost-FF = silent corruption;
  require cross-read consistency (2 independent flips agreeing) for
  non-blank chunks.
- Then chip entered 1F-FLOOD: async NACK spam (31x1f reads, 1600 in a
  row; user's LA: 1fs flowing BEFORE our 0x11 - stale/async replies
  pair wrongly). Driver scored them 'nack' -> flatline 'clean' counter
  hit 1600 -> hard exit at ext 21721/21726 (sweep 99% done, little lost).
- FIXES: new 'spam' verdict (>=4 x 1f in one read) gates baseline resync
  + resets flatline; ghost reads (oracle MISMATCH) save .bad.bin, NOT
  banked, chunk retried. farm42b launched with G_RESUME (0 chunks ->
  restarts at storage_0000).

## EXTERNAL REF: MKesenheimer/trezor-one-glitching (2026-10-28)
- Same attack, Pico Glitcher (RP2040 crowbar, 1.2V-limited supply, QFP64
  adapter) vs our CW-Lite on VCAP pin 31.
- Stage 2 (RDP1 readmem): delay 105.45-105.8us, length 10-30ns (shorter
  = less invasive). Timing ref = pot-tuned Schmitt trigger -> NOT
  comparable to our TIO3-based 179.7-182.2us; invariant = glitch between
  readmem and NACK. Strength ns not comparable across crowbar hardware.
- STAGE 1 (RDP2->RDP1 downgrade) CONFIRMED WORKING by them: delay
  188.9-189.5us after VCAP rise (broad scout), per-chip hits 191.75-197.16us,
  length 110-150ns. CHIP-TO-CHIP SPREAD ~5.4us -> real-Trezor phase 2 needs
  fresh scout, do not copy practice-chip band.
- They grab only 2 chunks: mnemonic @0x08008190, PIN @0x08008290 -> our
  fallback if real-chip flip rate too slow for full 66.

## TARGETED MODE: 5-CHUNK NORCOW GRAB (2026-10-28)
- User firmware copy = v1.13.1 -> storage v2 / NORCOW, NOT the flat v1
  struct. Article's +0x190/+0x290 offsets are fw-1.6.x only - DEAD for us.
- Norcow dict head @0x08008000 holds ALL secrets, entries sequential:
  PIN_LOGS(0x0001), EDEK_PVC(0x0002) = salt(32)+enc DEK/SAK(64)+poly1305
  tag = COMPLETE offline-PIN-crack material; then VERSION + app entries
  (encrypted mnemonic under DEK). Practice image agrees: 61/64 chunks
  all-FF -> all data in first 3 chunks (768 B).
- G_TARGETED=1 (G_TARGETED_N=5): TARGETS -> storage_0000..0004 + uid +
  otp3 = 7 chunks. 66 -> 7 = ~13x faster (~75 min vs multi-night at
  1/1416/chunk). Offline norcow parser flags truncated entries -> extend
  N if ever needed.
- farm42b (full dump) stopped at 0 chunks, 1 ghost purged earlier; grab1
  launched (PID 406575).

## DRIVER-vs-PHYSICAL TIME UNITS: +9.45us CONSTANT (2026-10-28)
- LA (claude-reviewed, n=65): D2 glitch pulse fires at 189.75us on the LA
  timeline when driver logs 180.3us. Offset +9.45us = ~1.09 UART bit
  times, sigma 0.64us (rock-steady) -> deterministic edge-reference
  mismatch: CW TIO3 (tee on FTDI TX) locks one bit boundary away from
  the LA's t0 anchor (stop-bit edge vs bit-start).
- CRITICAL: driver units are SELF-CONSISTENT - the entire flip band
  (179-182.5), hot exts, single-1f stats are driver units and the pulse
  physically lands where every successful flip has landed. DO NOT apply
  a -9.45us correction - it would move farming off the proven window.
- Translation table: driver 179-182.5us = physical ~188.5-192us.
  Physical numbers are the ones comparable to other rigs' writeups.

## BAND EXTENSION +3.5us: NACK-DEADLINE MAPPING (2026-10-28)
- LA decode of scan182 (n=32 well-paired): glitch offset 191.0-191.5us
  physical (= driver 182.0-182.5, constant +9.45 confirmed again);
  chip NACK reply starts median 195.5us physical (191.5-203.5 spread).
  => 4.0us PHYSICAL GAP between our band top and the NACK = back half
  of the RDP-check window, NEVER farmed. User called it ("another
  3-4us").
- Driver-units translation: NACK median ~186us. New band: 179-186.
- Also flagged: grab1 full sweep (12,540) + farm42b (~5.7k) = ~18k
  shots at 42nm tonight, ZERO flips vs ~13 expected. Something changed
  (reset-conditioning? post-flood chip drift? single-1f collapse?).
  Extended band is also the diagnostic: new territory + if still 0,
  run single-1f density + cold power-cycle.

## TIMING FRAME CORRECTED: TAIL-REFERENCED WINDOW (2026-10-28)
- Proper per-channel LA decode fixes the earlier interpretation: TIO3
  locks on the FIRST edge of the 0x11ee command. Driver us = us after
  COMMAND START. claude's "+9.45us mismatch" = his t0 anchor, not a
  trigger bug. Geometry (driver units): command tail (0xEE stop bit)
  ~174us; NACK leaves ~195.5us; RDP-check window = tail->NACK = ~21.5us
  WIDE. We have only ever farmed 179.7-182.5 = first 8us after tail!
- scan5p (5 passes x 179-189 @0.1us): stopped mid pass 3; 299 shots,
  4 dead + 1 weird in pass 1 - chip biting again at 42nm (vs 18k clean
  shots earlier tonight - fresh boots between passes correlate).
- NEXT: full-window scan, 174-196 @0.1us x5 passes, SAMPLES=1.

## WIN5P DENSITY MAP: HOT ZONE FOUND AT 174-180 (2026-10-28)
- Full-window scan 174-196 x5 passes (1095 shots): 54 dead, 215 single-1f,
  4 weird (00ecfc@187.1, ff@193.4, ff@195.8, ff@178.0). ZERO flips.
- Per-us map: 174-179 HOT (8-18% dead, up to 68% single-1f/50!);
  180-182 moderate (= old band, historical flip zone 179.7-182.2);
  183-192 COLD (0 dead 0 singles across 250 shots - check done, NACK not
  yet queued); 193-196 faint (NACK generation; ff-weirds land here).
- EXPLAINS THE DROUGHT: tonight's zero-flip runs farmed 182.5-186 = COLD
  zone. The old band 179.7+ only ever caught the hot zone's EDGE.
  Virgin high-density territory: 174-179.7 (pre-tail, never farmed).
- NEXT: hammer 174-180 x30 samples (1800 shots).

## MISC (2026-10-28 late)
- hot7 (42nm hot zone 174-180 x30): stopped by user early (~600 shots),
  no flip. hot39 (39nm same zone): stopped at #521, 2.7% dead, no flip.
- hot30 (30nm, rep5 @166.67MHz, 174-180 x30): running for scope
  observation (user watching VCAP droop live). First 161 shots: 0 dead.
- Heartbeat now prints "% of run" (total = grid x SAMPLES x PASSES).

## KESENHEIMER SOURCE REVIEW: RESET-PER-SHOT + TRIGGER MATH (2026-10-29)
- Their stage-2 loop: flush -> arm -> reset(10ms) -> sleep(150ms) ->
  init_bootloader -> ONE memread -> classify. ~2-3 shots/s, and EVERY
  shot = fresh reset + fresh 0x7f sync. One-shot-per-boot is their
  DEFAULT methodology - matches our reset-conditioning hypothesis and
  tonight's data (fresh-boot passes bit hard; 18k-shot same-boot farms
  went cold).
- Trigger: uart_trigger(pattern=0x11) fires at 0x11 byte COMPLETION
  (~87us after burst start). Their delay2 105.45-105.8 + 87 = ~192us
  after burst start = OUR physical flip band 189.7-191.7. WINDOWS
  CROSS-VALIDATED: same spot, different anchor. The "105 vs 174"
  discrepancy was one UART byte of anchor offset.
- NEXT VARIANT: one-shot-per-boot cycling hot exts 174-180(182),
  aggressive resync between shots (~0.5-1 shot/s). All machinery
  already in driver (boot_and_sync + EXTS).

## TIMING VERIFIED + BYTE-BY-BYTE NACK DISCOVERY (2026-10-29 01:10)
- LA verify (52 exchanges, 30nm sweep): D2 at physical 184.25 for driver
  175.0 -> constant physical = driver + 9.25 (3rd consistent measurement).
  Band 175-192 driver = 184-201 physical. Sweep stepping confirmed.
- CLEAN LA DECODE REVEALS PROTOCOL: chip NACKs BYTE-BY-BYTE under RDP1:
  1f #1 starts +99-105us (NACK for 0x11 itself, before 0xEE finishes
  transmitting!), 1f #2 starts ~+189 (NACK for 0xEE). Driver "1f1f" =
  both replies; "1f" single = GLITCH SUPPRESSED THE SECOND NACK BYTE
  (new mechanism for the single-1f marker - it is reply-suppression,
  not check-corruption).
- IMPLICATION: the FIRST RDP check (processing of 0x11) happens at
  physical +87-105 = DRIVER ~78-96 - NEVER FARMED. All our bands sit
  after it. If tonight's 175-192 farm is empty, farm driver 78-100 next
  (the actual first-check window) before touching strength again.
- Defaults now baked: 30nm (166.67MHz), RESET_EVERY=1, 175-192 x3,
  [rst] marker + (% of run) per line.

## RANDOMIZED STRENGTH (2D SEARCH) BUILT IN (2026-10-29 01:15)
- G_RND_REP=1 (DEFAULT ON), G_RND_LO=20 G_RND_HI=45nm: pulse width
  re-rolled EVERY shot (uniform), alongside the ext grid - the
  Kesenheimer 2D search (their crowbar script randomizes length2 10-100nm
  + delay 105-106us per shot; ours: ext grid x 18-48nm effective at
  166.67MHz quantum 6nm; superset of 20-45 by rounding).
- G_RND_REP=0 returns to fixed G_REPEATS ladder.
- Per-shot line shows the rolled strength (r4=24.0ns etc); CSV logs it.
- Nightly config now: 175-192 driver @0.1us x3, 30nm-class random
  strength, reset-per-shot, all guards. VERIFIED: 15-shot test spread
  r3-r8.

## FIRST COMMAND-STAGE ACKs EVER (night farm glitch2_20261029_012753)
- 9504 shots, 173-192us x10, random 24-42nm, reset-per-shot, 01:27-05:05.
  0 success. BUT: 11 ACK_NO_DATA events = chip sent 0x79 for the 0x11
  Read-Memory command (first-stage RDP check BYPASSED), then refused the
  address stage (1f1f x7, silence x4).
- CLUSTER: 10/11 in 179.4-183.7us driver (physical ~188.6-193 = NACK#2
  window per byte-by-byte model). Strengths: 36nm x7, 30nm x3, 42nm x1,
  24nm x0. In-cluster rate 1/215 shots (vs 1/1416 historical flips).
- Dead ladder: 24=0%, 30=0.46%, 36=2.25%, 42=1.69%. 20 weird ff/00
  strays, 1 zombie, 0 ghosts, 0 banked.
- NEW BOTTLENECK: address stage. NEXT: (a) re-farm 178-185us only,
  25-30 samples/pt, strength 30-42; (b) driver mod: on ACK_NO_DATA,
  immediately RETRY addr+count stage several times before resync (the
  corrupted check state may persist briefly - spend the ACK).

## STRATEGY RECONCILIATION + NIGHT5 (2026-10-29 10:30)
- Cross-review (Claude): ACK_NO_DATA = "right place wrong depth" near-miss,
  ONE refusal instant (no second gate), narrow the band, go LESS invasive
  (Kesenheimer 10-30ns). AGREED: one-gate model (real 42nm flips completed
  addr+count UNGLITCHED - data streamed); band narrowed to 179-184.
- DISAGREED on strength direction, with our own data: 24nm nothing ever,
  40nm 0/13500, 36nm near-misses only, 42nm = ALL 8 real flips (~1/1416).
  Kesenheimer's 10-30ns was Pico Glitcher FETs - not comparable to CW
  crowbar coupling. Our gradient: more depth -> state actually flips;
  user's 45nm cap = exactly rep7 42nm quantum.
- DISAMBIGUATOR ARMED: every ACK now logs pre=<hex> (r before addr stage).
  Spurious-ACK/corrupted-NACK#2 model predicts '1f79'; genuine accept
  predicts '7979'. Tonight's ACKs settle it.
- NIGHT5 config: FIXED r7=42nm, 179.0-184.0us @0.1 x30 samples,
  reset-per-shot, ACK-spend armed (5 raw addr retries + stage-2 re-glitch
  random 280-500us into addr phase, G_STAGE2=1 default). Expect ~15k
  shots -> if 42nm flip rate holds (~1/1416), ~10 full flips. Any flip:
  oracle-checked, banked, chain-drain probed.

## 2026-10-29 — collector bug: ghost read tore campaign down at 1/66 ("stuck")

Symptom: run_20261029_102921 flipped on shot #13015 (ext=30266 / 181.6us,
w5 r7=42nm -> SUCCESS), oracle flagged it a GHOST READ (storage_0000 came
back all-FF erase pattern), logged "NOT banked, retrying chunk" — then the
run printed CHUNK SECURED, [LATCHED+] drained (1/66), "collected 1/66", and
stopped. Not a hang: main() returned and the process exited.

Root cause — three cooperating defects in the SUCCESS/collector block:
  A. chain_unglitched() drain path had NO oracle check, so it re-banked the
     exact ghost all-FF read the main SUCCESS path had just refused.
  B. chain_unglitched() returned `drained > 0`; caller treats True as FULL
     COLLECTION -> assemble_and_report + teardown + return. Draining one
     (ghost) chunk ended the whole campaign. Docstring claimed "True only on
     FULL collection" — it did not.
  C. GHOST READ branch had no skip: control fell through to the unconditional
     CHUNK SECURED print and into chain_unglitched() on every ghost.

Fix (this file, same session):
  - chain_unglitched(): added the same practice-oracle guard as the main path
    (reject + save .bad.bin + abandon latch on MISMATCH); returns True ONLY
    when next_target() is None (genuine full collection), else False.
  - GHOST READ now skips SECURED/chain/advance entirely; the chunk stays
    outstanding and farming retries it. Periodic RESET_EVERY resync still runs.
  - CHUNK SECURED print moved inside the non-ghost else (no more false SECURED).

Rules this reinforces: every bank site (main AND latch-drain) must oracle-gate
in practice; "drained > 0" != "collection complete". On a real chip with no
ORACLE the guard is skipped as before — cross-read consistency is the
real-device ghost filter (still TODO).

## 2026-10-29 — all-FF is NOT a ghost, except for the header chunks

Checked the planted practice image storage.bin (plant_storage.py target,
0x08008000, 16384 B): it is 98.2% 0xFF. Only chunks 0,1,2 (first 768 B)
hold real data (NRC2 magic + keys, 303 non-FF bytes total); chunks 3-63 are
legitimately erased flash = all-FF by design.

Implications for the ghost-read filter:
  - "all-FF read == failed/ghost" is ONLY valid for a chunk that is supposed
    to contain data (here: storage_0000/0001/0002). For 61 of 64 chunks all-FF
    is the CORRECT content; the oracle returns MATCH and banks it rightly.
  - The oracle correctly flagged shot #13015 because storage_0000 must start
    4e524332 faffffff (NRC2..), not ffffffff. That check is header-specific,
    not a blanket all-FF rule.
  - Real-device filter (no oracle) must therefore NOT treat all-FF as ghost in
    general. Distinguish a ghost only where data is expected (a magic/header
    chunk). Cross-read consistency still holds: two latched reads agreeing is
    trustworthy, and all-FF agreeing with all-FF is legitimately empty flash.

Collector optimization: the entire payload of interest is ~768 B in chunks
0-2 (+ uid/otp3). If the real storage mirrors this shape, prioritize chunks
0-2 first and let the latch-drain mop up the erased remainder, instead of
farming all 66 targets uniformly.

## 2026-10-29 — night5 review + cross-read confirmation layer, alert, lazy dumps

NIGHT5 (glitch2_20261029_102921_night5.csv): 13,015 shots, FIXED rep7=42ns
(G_RND_REP off - every row repeat=7), us band 179.0-181.6, offset -45, w5.
Verdicts: nack 12596, dead 373 (2.9%), weird 28, ACK_NO_DATA 15, SUCCESS 1,
zombie 1, spam 1.
  - ZERO real flips. The single SUCCESS (#13015, us 181.6) was the all-FF
    GHOST the oracle caught, not data. Real-flip rate here = 0/13015, well
    below the historic ~1/1416 at rep7.
  - WINDOW CLIPPED LOW. Only 179.0-181.6us swept; NACK onset ~187us. The lone
    SUCCESS and 7/16 "got-ACK" events (ACK_NO_DATA+SUCCESS) sit at us>=181.0 =
    the top 0.6us edge. dead% climbs with us (2.0%@179 -> 4.4%@181.6); weird
    00/ff truncations cluster LOW (179.1-179.7). All three point to the
    sensitive zone being ABOVE 181.6. ACTION: shift window up, e.g.
    G_US_MIN=181 G_US_MAX=187, keep rep7.
  - Interesting glitch artifact shot#11797: pre=790b31000102112131446373829279
    = the STM32 Get(0x00) reply (ACK, N=0x0b, V=3.1, cmd list 00 01 02 11 21
    31 44 63 73 82 92, ACK). The glitch made the ROM mis-decode 0x11 as Get.
    Command-decode corruption, not a data leak.

STRENGTH LOGGING (user concern): per-shot `repeat` IS logged faithfully (set
last before arm in attempt(); RND_REP rolls then logs the same var). But the
CSV wasn't self-describing: `width` is a no-op in enable_only (strength =
repeat there), there was no ns column, and stage-2 fires a separately-rolled
s2_rep that only appeared in the note. FIX: CSV now has `rep_ns` (repeat/clkgen
in ns) + `s2_rep` columns; us column trimmed to 1 decimal (XXX.X).

CROSS-READ CONFIRMATION LAYER (new, the oracle-free judge for the real device):
  - confirm_chunk() runs two judges on every recovered chunk. A=oracle (byte
    compare vs storage.bin, practice-only, GATES in practice). B=cross-read:
    read the same chunk CROSSREAD_N times (default 3) from the latched
    session, CONFIRMED only if >=CROSSREAD_MIN (default 2) reads agree. GHOST
    if reads disagree, UNCONFIRMED if the latch dropped before enough reads.
  - all-FF is NOT special: an erased chunk reproduces all-FF and is CONFIRMED
    correctly. The old header-specific oracle rule stays for practice.
  - Gate: ORACLE present -> oracle gates (cross-read observed only). ORACLE
    None (real device) -> cross-read gates. Both judges run on the latch-drain
    path too (chain_unglitched now routes through confirm_chunk).
  - A/B logger: per-event ab_log.csv + end-of-run ab_matrix.txt confusion
    matrix (oracle truth x cross-read verdict). The gating number is FALSE
    ACCEPTS = (oracle MISMATCH, cross-read CONFIRMED); must be 0 before
    trusting cross-read on the real device. Tune CROSSREAD_N/_MIN against it.
  - Tunables: G_CROSSREAD_N, G_CROSSREAD_MIN.

SUCCESS ALERT: a flip now fires a non-blocking desktop alert (terminal bell +
canberra 'complete' chime + spd-say spoken line), plus one on full collection.
Disable with G_ALERT=0.

LAZY DUMP DIR: dumps/run_.../ is no longer created at startup - ensure_dump_dir()
makes it on the FIRST find (first flip candidate). An empty run leaves no
folder; assemble_and_report prints "0/N - no dump dir (nothing found)".

## 2026-10-29 — STAGE-2 OFF by default: one clean glitch dumps the whole read

Decision (user): there should be no stage-2 glitch needed. G_STAGE2 default
flipped 1 -> 0 in rdp1_glitch_campaign_full_mem_dump.py. Raw NON-glitch
address retries (G_ADDR_RETRIES) stay - they just re-send the address bytes.

Evidence - jerinsunny STM32 vglitch logic capture
(docs/archive/jerinsunny_logic1_single_glitch_full_dump.png, from
https://jerinsunny.github.io/stm32_vglitch/assets/images/logic1.png):
  - D3 Glitch = ONE pulse, fired right after the 0x11 0xEE Read Memory
    command. No second glitch anywhere.
  - D2 Rx: the 0x79 where RDP-1 would answer 0x1F NACK is annotated
    "RDP Bypassed". After that single flip the address phase ACKs, the
    length phase (0xFF 0x00 = 256 B) ACKs, and flash streams back
    ("Extracted Data": 00 00 01 20 25 07 00 08 AD 06 ...).
  - Proves: once a CLEAN stage-1 clears RDP, protection is down for the whole
    command - the address phase does NOT independently refuse.

Re-interpretation of ACK_NO_DATA: command-ACK (0x79) then "addr stage refused:
1f1f" is a DIRTY stage-1 - the pulse corrupted the command decode into
emitting 0x79 without clearing the RDP state, so the address phase still sees
protection and NACKs. A second glitch can't fix that. The fix is a cleaner
stage-1 (timing/strength) so the single pulse clears RDP like jerinsunny's.

TUNING OBJECTIVE going forward: convert ACK_NO_DATA near-misses into FULL
bypasses by moving stage-1 (window up toward the 181-187us edge where the ACK
events trend, strength at the rep where ACKs appear), NOT by adding a shot.
This supersedes any earlier "spend the ACK with a stage-2 glitch" framing.

## 2026-10-29 — stage-2 glitch REMOVED; Kesenheimer Main2 port + trigger-reference reconciliation

STAGE-2 FULLY REMOVED (user directive): deleted STAGE2/S2_US_LO/S2_US_HI config,
the attempt() stage-2 block, _last_s2, and the s2_rep CSV column. CSV schema now:
shot,ext_offset,us,width,repeat,rep_ns,verdict,note. Raw NON-glitch address
retries (G_ADDR_RETRIES) kept. Rationale: jerinsunny single-pulse capture + the
single-glitch RDP-1 model - one clean stage-1 clears RDP for the whole read.

KESENHEIMER REFERENCE (docs/archive/kesenheimer-stm32f2-bootloader-memread-
crowbar.py): his Main=RDP2->RDP1 (power-glitch on Vcap rising, RDP-2 only);
his Main2=RDP1->RDP0 (single UART-0x11-triggered glitch, loop, dump). Our
campaign == a port of Main2; our RDP-1 device needs ONLY Main2. His proven
stage-2 params: delay2 105-106us, length2 10-100ns, trigger uart pattern 0x11,
dump 0x08000000 len 0x2000.

TRIGGER-REFERENCE RECONCILIATION (why our ~181us window underperformed):
  - Kesenheimer delay2 is measured from the UART 0x11 PATTERN MATCH (fires when
    the 0x11 byte is fully received, ~90-95us after its start bit @115200 8E1).
  - OUR ext_offset is from the TIO3 edge = the 0x11 START bit.
  - So his 105us maps to ~90 + 105 = ~195-200us in OUR reference - NOT 105us.
  - Independently, our own LA puts the RDP decision / NACK onset at ~187-195us
    after 0x11 start. Both converge on ~190-200us.
  - We were sweeping 173-192us = just BELOW the decision point. night5 ACK
    events trending to the top edge (181+) corroborate: the sweet spot is
    higher. ACK_NO_DATA = firing a hair early -> cosmetic command-ACK without
    clearing RDP.

ACTION: next run G_US_MIN=188 G_US_MAX=200 (TIO3 reference), rep5-7 (30-42ns,
agrees with his 10-100ns + our depth finding), single glitch, reset per shot.
Assumption to verify on the LA: exact 0x11-byte -> pattern-match offset (~90-95us).

## 2026-10-29 — LIVE LA capture: exact RDP decision point + us calibration

Captured live (fx2lafw @4MHz) while the campaign fired, one clean decoded burst
(storage-sim/campaigns/la_live_20261029_1858.csv):
  TX 0x11 @ T0, 0xEE @ T0+95.2us   (one 8E1 byte later - correct)
  2-byte command ends            @ T0+191.0us
  RX NACK 0x1F onset             @ T0+196.5us  (5.5us after command end)
  D2 glitch-marker edge          @ T0+198.75us
  => RDP decision/refusal lands ~191-196.5us after the 0x11 START.

CALIBRATION (resolves the "us" vs 0x11 offset): the campaign heartbeat already
knows glitch_time = t_us + 8.7us after 0x11. That +8.7 = ONE bit time (8.68us):
the CW ext trigger fires on the FIRST RISING edge of 0x11 (start bit is a
falling edge at T0; d0=1 rises 1 bit later). So:
   glitch_after_0x11 = (0x11_start + 8.68) + ext_offset(=t_us)
   to hit the decision window [191, 196.5]us  ->  t_us = [182.3, 187.8]
   => TARGET CAMPAIGN us = 182-188  (G_US_MIN=182 G_US_MAX=188).

This CORRECTS the earlier "G_US_MIN=188 G_US_MAX=200" note (that was treating
the us column as ~0x11-relative; it is actually 8.68us earlier). Evidence it's
right: night5 topped out at us 181.6 = glitch at ~190.3us = right at command-end,
just BEFORE the decision -> only cosmetic ACK_NO_DATA/ghost. The current live run
reaching us 192 = glitch ~200.7us = just PAST the NACK. The bullseye between them
is us 182-188.

TRIGGERING NOTE: a UART pattern trigger is NOT required - the 0x11 burst-start
edge is deterministically tied to the command (fixed baud => fixed 196.5us to
the decision), and CW trigger jitter (night5 sigma 0.64us) is far smaller than
the 5.5us decision window. The timing was a CALIBRATION problem, not a trigger-
capability problem. Kesenheimer's uart_trigger(0x11) is on an RP2040 Pico (PIO),
which is only needed to run his exact findus stack - a full Raspberry Pi (Linux)
cannot meet the sub-us/ns timing.

## 2026-10-29 — FIRST FLIP at verified timing: ghost (all-FF), safeguards held; grind-loop fix

cal182 rep6-7 grind, pass 1 shot #149 (us 182.3, rep6=36ns) -> SUCCESS = a
NACK->ACK flip + completed Read Memory, but the read returned ALL-FF
(ffffffff..x16) instead of the real storage_0000 (NRC2faffffff..).
  - oracle=MISMATCH, crossread=UNCONFIRMED (n_read=1: the flip did NOT latch
    the session, so no 2nd read to confirm). Correctly REJECTED, saved
    storage_0000.bad.bin, NOT banked, grind continued. ab_log recorded it.
  - The confirmation layer did exactly its job on the first live flip - the
    OLD collector would have banked this all-FF as real and torn down at 1/66.

SIGNIFICANCE:
  - At the LA-verified window (glitch 191-197us after 0x11), the flip-to-ACK
    came on shot #149 - far faster than the old ~1/1400. Strong sign the
    optimal timing dramatically raised the NACK->ACK rate. (n=1, not proven.)
  - rep6 (36ns) was enough to flip at the good timing - NOT rep7. Supports the
    rep6-7 choice; the better timing lowers the energy needed.
  - NEW FRONTIER = ghost->data: flips come back as all-FF (Kesenheimer's "flash
    probably erased" / night5 #13015), not real data. Converting ACK-flips into
    DATA-flips is the problem now, not getting an ACK.
  - The UNCONFIRMED (single read, no latch) means we can't cross-read-confirm a
    non-latching flip. A flip that LATCHES the session (unglitched 0x11 keeps
    ACKing) is what lets chain_unglitched drain + cross-read confirm real data.

GRIND-LOOP BUG FIXED: loop_us182-188_rep67.sh detected a flip by "new dump dir",
but a ghost REJECT also creates the dump dir (ensure_dump_dir writes .bad.bin
there). Fixed: stop only on a REAL banked chunk (a .bin that is NOT .bad.bin);
grind now keeps running through ghost rejects. Ghost .bad.bin dirs are expected
during the grind and are not a stop condition.

OPEN QUESTIONS: why all-FF (glitch disrupting the data fetch vs mis-tuned
read-phase energy)? Does any flip return real data or latch the session?
Let the grind accumulate flips and watch the ghost-vs-real / latch ratio.

## 2026-10-29 — higher-strength round (rep9-20) RULES OUT software-only fix; points at VCAP cap

Context: SEC Consult (secglitcher) RDP1 READ_MEMORY dumps use ~230ns crowbar
width (= rep38 at our clkgen) with decoupling caps STRIPPED. We get all-FF
ghosts at rep6-7 (42ns). Tested the software lever: higher strength.

Round: us 182-188, G_US_STEP=0.1 (17cyc, ~0.1us steps), rep9-20 randomized
(G_RND_LO=48 G_RND_HI=120), 3 shots/step, 177 shots (glitch2_..._histr_step01).
Result:
  weird 67 (37.9%)  dead 58 (32.8%)  nack 52 (29.4%)  SUCCESS=0  real=0  ghost=0
  non-nack rises monotonically with rep: rep9 33% -> rep20 76%
  dead/weird spread EVENLY across all us 182-186 (no clean-flip zone)

Interpretation: on the CAPPED board there is NO strength that yields a clean
real-data flip.
  - rep6-7 (short): clean NACK->ACK flips but all-FF GHOSTS (shallow/incomplete
    dip -> cosmetic ACK + erase read).
  - rep9-20 (long): NO clean flips - just weird (corrupted partial resp, e.g.
    c000) and dead (over-driven, mushy chaotic collapse).
This is the signature of the VCAP (2.2uF core-LDO) decoupling cap fighting the
crowbar: it prevents the sharp-but-controlled rail collapse a real bypass needs.
SEC's long pulse works because they stripped decoupling; on our capped board the
same energy just makes chaos.

CONCLUSION: software-only (strength) path is exhausted. NEXT = HARDWARE: pull /
reduce the VCAP decoupling cap (the one on the ~1.2V node = our SMA injection
node) so even a short pulse collapses the rail cleanly, then re-run rep6-7.
Caveat: F2 LDO needs some VCAP capacitance to boot - if fully removing it stops
0x7F->0x79 sync, use a smaller cap, not zero (SEC kept C23 for overshoot).

Rig safety note (confirmed this session): 'dead' = recoverable software crash
(brownout crash of the bootloader), NOT damage - crowbar pulls VCAP DOWN, never
overvolts. Chip re-syncs every shot. Harm signal would be failure to re-sync
after a full power cycle (not seen).

## 2026-10-29 — TWO confounds found: scope damping the glitch node + window missing the lower half

Via the Siglent (10.11.13.220, VXI-11) reachable directly - captured scope + cursors.

1) SCOPE DAMPING (prime confound for the whole session's ghosts): CH1 was clipped
   on the VCAP glitch node the ENTIRE session (~15-20pF + 1M load = acts like
   extra decoupling right at the injection point). Per the rig rule, scope must
   never be on the glitch node during firing. This likely explains the ghosts:
   damped/shallow dip -> cosmetic ACK + erase-pattern read. ALL tonight's cap/
   strength rounds are partly confounded by this. LA timing is NOT affected (LA is
   on UART, off the glitch node). FIX: pull CH1 off VCAP.

2) WINDOW MISSING THE LOWER HALF: scope cursor measurement (C1:CRVA HREL) at a
   us-185 glitch read ΔX = 12.1us between the glitch and the TX (0x11 0xEE end).
   So at us 185, glitch = command-end + 12.1us. With "4us before NACK",
   NACK = command-end + 16.1us. Mapping (1 us of 'us' = 1us glitch time):
     command-end ~= us 173 ; NACK ~= us 189. Decision window = us 173-189 (~16us).
   Every prior sweep ran us 182-188 = only the UPPER ~6us of the window; the first
   ~9us after command-end (us 173-182) was NEVER swept. The RDP check may live
   there. (This also explains the user's "go back 9.5us further" - command-end is
   ~9us below our old us-182 start.)
   NOTE: this 16us command->NACK span (scope) is much wider than the earlier LA
   estimate (~5.5us) - the scope/cursor direct measurement supersedes it.

ACTION (running now): scope OFF, full window us 172-190, rep6-7 (cap off),
G_US_STEP=0.1, G_SAMPLES=10 (~1800 shots). First time sweeping the whole
decision window with no probe loading. If scope-damping was the ghost cause,
flips here should start returning real NRC2.. data.

## 2026-10-30 — overnight 10-pass full-window scope-off grind COMPLETE: works, but all-FF

Config: us 172-190 (full command-end->NACK window), rep6-7 (36-42ns) pinned,
scope OFF VCAP, VCAP cap off, G_US_STEP=0.1, G_SAMPLES=10. Finished all 10 passes.

RESULT: 17,700 shots | nack 17286 | dead 341 (1.9%) | weird 46 | ACK_NO_DATA 22 |
SUCCESS 4 -> ALL 4 were all-FF GHOSTS. REAL chunks banked: 0.
  Flip locations: us 180.7, 180.8 (r7), 182.7, 185.1 (r6) - ALL in the UPPER
  window (command-end +8..13us), NONE in the newly-covered lower window
  (us 172-180). So the "missed lower window" did NOT yield - flips still cluster
  at the same us~181-185 zone as every prior run, and remain ghosts.

Adaptive strength result (earlier tonight): rep6-7 = 1.9-2.5% dead (sweet spot);
rep7-8 = 31% dead, 0 flips (hard dead-cliff). rep6-7 is the ceiling for minimal
dead. Pinned there for the 10 passes.

CONCLUSION after exhausting every variable tonight (scope on/off, VCAP cap
on/off, rep6-20, full decision window, 0.1us resolution, ~40k total shots):
  - The GLITCH CHAIN WORKS end-to-end: it reliably flips NACK->ACK and COMPLETES
    the Read Memory (ACK + 256 bytes) = the RDP bypass succeeds. The hard part
    (bypassing RDP1 readout protection) is SOLVED and reproducible.
  - Every successful read returns all-FF, in EVERY configuration. A completed
    read through a working bypass returning all-FF is most consistent with the
    FLASH BEING ERASED (board never planted / planting didn't take), OR a
    deeper data-path protection that returns FF.
  - LEADING HYPOTHESIS: this Waveshare board's flash at 0x08008000 is erased -
    the "ghosts" are successful reads of empty flash. The oracle only flags
    MISMATCH because it expects planted NRC2.. data that isn't physically there.

NEXT (needs the user / hardware):
  1. VERIFY the flash is actually planted: was plant_storage.py run successfully
     on THIS board? If erased, the attack already works - need a planted board
     or the real target to see real data.
  2. If planted and still all-FF -> investigate data-path protection (the FF-on-
     protected-read failure mode) vs the command-gate bypass.
  3. Board note: target is a Waveshare multi-family STM32 board; F2 jumper set
     for pin 31 (VCAP_1); scope must stay OFF VCAP during firing (it damps).

## 2026-10-30 — CHAIN PROVEN on planted board + full-dump collector fixes

MILESTONE: after set_rdp0 -> plant_storage -> uart_rdp0_test (board re-planted,
NRC2 verified), re-armed RDP1 (set_rdp1, 0x55, Read Memory NACKs), and glitched:
  shot #385, us 180.8, rep7 -> CHUNK SECURED storage_0000, oracle=MATCH,
  bytes = 4e524332 faffffff 02003c00.. = the exact planted NRC2 data.
=> RDP1 readout-protection bypass + real Read Memory recovery PROVEN end-to-end
   on STM32F2 (DEV_ID 0x411, confirmed via DBGMCU_IDCODE; F2 has NO PCROP, so
   the all-FF was never a PCROP/SPRMOD flip). The overnight all-FF was an
   UNPLANTED (erased) board - the glitch chain was always working (even latched:
   the 03:34 flip was cross-read CONFIRMED all-FF = reliable read of empty flash).

FULL-DUMP COLLECTOR FIXES (needed to assemble all 66 chunks):
  1. TARGETS reordered: storage_0000..0063 FIRST (all oracle-gated -> bankable by
     a single flip), uid/otp3 LAST. Old order had uid 2nd -> collector stalled on
     uid (oracle NA -> never banked). G_TARGETED slice updated to match.
  2. confirm_chunk: for a chunk the oracle can't judge (uid/otp3 outside
     storage.bin -> orv='NA'), fall back to CROSS-READ gating instead of the
     oracle MATCH gate (which could never bank them). Storage chunks still
     oracle-gated; uid/otp3 bank on a latched cross-read-CONFIRMED read.
Full dump now: non-latching flips accumulate storage chunks; a latching flip
drains all remaining incl uid/otp3 -> storage_dump.bin + uid.hex + otp3.hex.

## 2026-10-30 ~11:40 — Targeted uid/otp3 grind: FLIP DROUGHT (partial-ACKs, no completions)

Targeted run (resumed 5 storage head chunks from `dumps/accum`, hunting uid
@0x1FFF7A10 + otp3 @0x1FFF7860) over sweep us 180–186, w5, rep6–7 (G_RND 33–45),
reset-per-shot. ~1 h / **3081 shots**:
- **0 full flips / SUCCESS** (expected ~3–8 at the historical ~1/400 in-band rate)
- **92 dead (3.0%)** — healthy rep6–7 signature; crowbar firing + coupling, NOT
  damped and NOT over-hot (rep8+ dead-cliff would be ~31%). Scope is OFF VCAP.
- **12 ACK_NO_DATA partial-flips** (~1/257): command-stage NACK→ACK flipped
  (`pre=79…`) but address/read stage re-refuses (`addr stage refused: 1f1f`).
  Localized `us` of partials: **181.0, 181.1, 181.3×2, 181.7, 183.4** — i.e. the
  live zone is **us ~181.0–181.8**. Dead shots heaviest at 181.4–181.8 too.

**Interpretation:** the pulse is landing in the right window and perturbing the
bootloader (flips the first response), but is **marginal** — it cannot hold the
RDP bypass through the full Read Memory transaction (command→address→data), so
every near-flip dies as ACK_NO_DATA instead of completing. This is a glitch
*quality/strength* margin issue at the window edge, NOT a timing-placement miss
(placement is correct — the action is squarely at us 181) and NOT damping
(dead rate normal). Contrast: the earlier full-dump run completed flips + a
latch readily with the same nominal params — suggests a small drift in
coupling/strength since then.

**uid/otp3 gating reminder:** both are outside storage.bin → oracle=NA → banked
ONLY via the cross-read gate (CROSSREAD_N=3, MIN=2 agreeing), which needs a
**latching** flip (unglitched 0x11 keeps ACKing so read_target_n gets its
repeats). A one-shot flip → UNCONFIRMED → not banked. One latch drains BOTH
uid+otp3 via chain_unglitched. So: need completions first, then a latch (~1/11
of completions). Zero completions = no path to bank yet.

**Next levers (in order of info/cost):**
1. In-situ: dwell on us 181.0–182.0 and nudge strength up a notch (try rep6–8 /
   widen width) to push the marginal partial-ACKs into completions — cheap, no
   teardown. If still 0 completions in ~1–2 passes, it's not strength.
2. Scope verify (pulse off VCAP only for the check shot): confirm pulse shape
   matches the successful full-dump capture — resolves "is the pulse the same as
   when it worked" (drift hypothesis).
3. We already HAVE uid (SWD 3e00…) + otp3 (ff*32) for the offline decrypt; this
   grind proves the real-device path (SWD blocked) — no urgency, so worth doing
   the scope check properly rather than grinding blind.

## 2026-10-30 ~13:12 — Step-1 fine sweep: one FULL pass, still 0 completions → step largely exonerated

Reverted G_US_STEP 0.1 -> 0.006 (ext step 17 -> **step 1**, 0.006us granularity)
on the targeted uid/otp3 grind — the one config delta from the earlier WORKING
full-dump run. Hypothesis under test (user): step 17 was jumping over a <0.1us-
wide completion sweet-spot.

**Result after one complete fine pass (3600 shots, now into pass 2):**
- **0 full completions / SUCCESS** — same as step-17.
- 100 dead (~3.1%, healthy rep6-7), 30 ACK_NO_DATA partial-flips (~1/120),
  partials still clustered at **us ~181** (180.3–181.8).
- The step-1 pass visited EVERY ext in 30000–31000, i.e. all the sub-0.1us
  points step-17 skipped. Hitting them changed nothing.

**Interpretation:** the step hypothesis is **largely ruled out** — if a thin
completion band existed between the step-17 points, the fine pass would have
landed in it ~3x/ext. It didn't. Combined with the 3.2us spread of completed
flips seen in the ORIGINAL working run (far wider than 0.1us), target jitter
clearly dominates and 0.1us stepping was never the deal-breaker. The drought is
a glitch **strength/quality (drift)** problem: pulse lands correctly at us 181
and flips the command-stage NACK->ACK (partial-ACKs prove placement), but is too
marginal to hold the RDP bypass through the full Read Memory transaction, so
every near-flip dies as ACK_NO_DATA. Caveat: flip rate is stochastic; keeping
the fine run going the rest of the day for confirmation, but the negative result
after a full pass is strong.

**Next (tomorrow / when attended):** scope-verify pulse shape vs the working-run
capture (CH1 on VCAP for the verification shot ONLY, off during firing); if drift
confirmed, nudge strength (rep/width) or reflow the CW SMA jack (suspected
cracked — see siglent-scope skill note re ~1000:1 attenuation). uid+otp3 already
in hand (SWD 3e00…, otp3 ff*32) for the offline decrypt — grind is real-device-
path proof only, no urgency.

## 2026-10-30 ~15:07 — LA session: comms healthy, NO timing drift, address-refusal seen on the wire

New reusable LA toolset in `storage-sim/la/` (capture.sh / decode.sh / timing.py
+ README). fx2lafw Saleae Logic, passive UART tap, safe during firing.
Channel map verified: **D0 = TX (host->chip), D1 = RX (chip->host)**, 115200 8E1.

Captured while the step-1 targeted run fired (first target = uid @0x1FFF7A10):
- **Comms healthy / command well-formed.** TX: `7F 11 EE`; RX: `79` (ACK to the
  7F sync) then `1F 1F` (NACK to Read Memory — normal un-glitched RDP1). Rules
  out any UART/wiring fault.
- **Address-stage refusal caught ON THE WIRE.** TX showed `1F FF 7A 10 8A`
  (= uid address 0x1FFF7A10 big-endian + XOR csum 0x8A) sent 4–5× with RX `1F`
  each time — i.e. `complete_read()` + the ADDR_RETRIES loop sending the uid
  address and the chip NACKing it. This is the ACK_NO_DATA failure made visible:
  the command got past (an address is being sent at all) but the **address stage
  for the uid/OTP region is refused**.
- **NO timing drift.** 0x11-command -> NACK latency measured 196.5–198.5 µs on
  the clean 2-byte command bursts (175–180 µs on the shorter sync exchanges),
  dead on the ~196.5 µs calibration. So the RDP decision window has NOT moved;
  our glitch us-window is still correctly placed. The drought is not a stale
  window.

**Where this leaves the diagnosis:** timing drift is OUT (NACK onset unchanged).
The glitch yields command-stage "ACK" events but the address stage refuses —
consistent with EITHER (a) dirty/false command-ACKs (glitch too marginal, bypass
never truly held, so RDP still refuses the address) OR (b) the uid/OTP system-
memory region being refused specifically. The LA cannot separate (a) from (b)
(both read as address-NACK). The storage-flash test (point the collector at a
flash chunk and see if completions resume) remains the decisive separator.
Note we have NEVER glitch-read the uid/OTP region (morning latch only ever
drained storage flash, stopped at chunk 0020), so (b) is a live possibility.

## 2026-10-30 ~17:45 — Switch to loop_fulldump (step 1) to test the storage-flash vs OTP-region hypothesis

Stopped the targeted step-1 run after ~15k shots / 0 completions (uid/otp3 first
target, all ACK_NO_DATA address-refusals). Relaunching loop_fulldump.sh instead,
with G_US_STEP set 0.1 -> 0.006 (ext step 1) so the ONLY changed variable vs the
targeted run is the collector: full-dump resumes storage 0-20 from accum, so the
**first target is storage_0021 (flash @0x08009500)**, not the uid/OTP region.

This is the decisive (a)-vs-(b) separator from the 15:07 LA finding:
- completions/latch RESUME on the flash read -> the drought was the uid/OTP
  system-memory region being refused at the address stage (fundamental, reframes
  uid/otp3 plan).
- flash ALSO droughts -> not the address; hardware strength/drift (scope check).
Config otherwise identical to the morning latch run (loop_fulldump, G_FULL=1,
offset -45, width 5, rep6-7, clkgen 166.667, us 180-186, step 1).

## 2026-10-30 ~17:47 — RESOLVED: the drought was the OTP/UID region, NOT hardware. Flash completes.

The storage-flash test paid off immediately. loop_fulldump (step 1, first target
storage_0022 @0x08009600 flash) produced a **SUCCESS at shot #244** (ext 30081 /
us 180.5, rep6, oracle=MATCH) -> CHUNK SECURED storage_0022. Single non-latching
flip (crossread=UNCONFIRMED, banked by oracle).

Contrast that settles the day's question:
- targeted run (first target = uid 0x1FFF7A10, OTP region): ~15,000 shots, 0 SUCCESS
- full-dump run (first target = storage_0022, flash):        244 shots, 1 SUCCESS

Identical binary, glitch params, step, rig. The ONLY difference is the target
address. Therefore:
- **Hardware is fine** — the rig bypasses RDP and completes a Read Memory on a
  FLASH address readily. The earlier "drift/strength" hypothesis is WRONG (or at
  most minor); the big effect was the address.
- **The drought was the uid/OTP system-memory region (0x1FFF7A10 / 0x1FFF7860)**
  being refused at the ADDRESS stage of Read Memory, even with the RDP command
  gate glitched. The command `0x11 0xEE` is identical; the region is the problem.
  (User's instinct re "a fundamental difference" / "it's not 0x11 0xEE" for OTP
  was correct — not a different command, but that region is not served by Read
  Memory the way flash is.)

Implications:
- For THIS decrypt: no blocker — uid came from SWD (3e00…), otp3 = ff*32.
- For the REAL locked device (SWD blocked): reading uid/OTP via bootloader
  Read Memory under RDP1 is NOT demonstrated and may not be possible via the
  plain address stage. Open item: confirm whether 0x11 reads 0x1FFF7A10 at all
  with RDP down (no-glitch Read Memory at RDP0, during a board re-prep), and
  research the correct bootloader path for the OTP/UID region on STM32F2.
- n=1 so far; watching for more flash completions to rule out a fluke.

## 2026-10-30 ~18:05 — Campaign rewired: LATCH -> uid/otp3 PRIORITY grab (new default behavior)

Implemented the user's strategy in rdp1_glitch_campaign_full_mem_dump.py:
- Farming (single-shot glitching) now targets FLASH only (next_farm_target /
  next_storage_target); uid/otp3 are LATCH-ONLY and never farmed with single
  glitches (that was the drought). Once all flash is banked but uid/otp3 still
  pending, it fishes on any flash range (re-reads one, no re-announce) purely to
  provoke latches.
- On ANY latch, chain_unglitched() now calls grab_extras_latched() FIRST:
  probes uid then otp3 with latch_probe() (liveness-aware - sends unglitched
  0x11 0xEE, checks the 0x79 command-ACK) so an OTP address-refusal is NOT
  mistaken for a dropped latch. Three outcomes logged per extra:
    * CONFIRMED -> banked ("secured under latch"), spoken alert;
    * latched-but-address-REFUSED -> the decisive negative (region not served by
      Read Memory under genuine bypass) - printed, not fatal;
    * latch dropped (command NACK) -> stop.
  THEN it drains remaining flash while the latch holds.
- Completion requires the FULL set incl uid/otp3 (next_target() is None), so the
  campaign is not "done" until a latch delivers uid/otp3.
Compiles clean. Relaunched loop_fulldump (step 1) resumed 42/64 flash chunks,
farming storage_0042, uid/otp3 pending. Prior run proved the rig latches
frequently on flash at step 1 - so we should get a latch (and the uid/otp3
verdict) soon.

## 2026-10-30 ~18:40 — Strength bump: random rep 6/7/8 (G_RND_HI 45->48) to fight the clean-flip drought

New campaign hit the drift zone: 1317 shots, 0 clean completions (P~1% at the
old 1/293 rate), 12 dirty ACK_NO_DATA - pulse landing (~3% disturbance) but
consistently dirty, not clean. Per the plan, nudging strength UP.
- enable_only crowbar: WIDTH is INERT (rep is the only strength knob), so left
  G_WIDTH=5. (User asked for width 5/6; declined - no glitch effect in
  enable_only + width changes trigger risky FPGA partial-reconfig.)
- G_RND_HI 45 -> 48 => random pull now rep 6,7,8 (was 6,7). rep8 = 48ns.
  Reintroduces rep8 which an earlier finding called a dead-cliff (~31% dead) -
  but that was at different coupling; now the glitch is too WEAK (dirty flips),
  so the hope is rep8 pushes marginal dirties over to clean. Random mix keeps
  the proven 6/7 so it's a hedge. Watch the dead rate: if it spikes toward 30%
  with still 0 clean, back rep8 out.

## 2026-10-30 ~18:48 — rep8 backed out; random pull now rep 5/6/7 (G_RND_LO=28 G_RND_HI=45)

rep8 (48ns) too hot (dead-cliff, user call). Reset random pull to rep 5,6,7:
G_RND_LO 33->28 (28ns ceils to rep5; note 30ns rounds up to rep6 at 166.67MHz
so 28 is needed to actually include rep5), G_RND_HI 48->45 (rep7 ceiling).
rep5=30ns is historically the weak end (earlier: <=30ns gave no flips) so this
leans weaker than the 6/7 sweet spot - watching whether clean flips return.

## 2026-10-30 ~21:30 — ANALYSIS: where clean glitches land (all today's ~51.8k shots)

Aggregated every SUCCESS/ACK_NO_DATA across all campaigns/*.csv from 2026-10-30.
Totals: 50140 nack, 1416 dead (2.7%), 128 ACK_NO_DATA (dirty), 18 SUCCESS (clean).

CLEAN-FLIP DISTRIBUTION (the actionable result):
- by us (0.5us bins): peak at us 181.0 (8 of 18); 12 of 18 clean flips fall in
  **us 180.5-181.2**. Sparse singles out to 185.
- by rep: **rep6 (36ns) = 14/18 (78%)**, rep7 = 4/18. rep6 dominates clean flips.
- DIRTY (ACK_NO_DATA) peaks at us 181.5 - i.e. JUST PAST the clean peak. Above
  ~us 181.3 flips increasingly go dirty (command ACK, read refused) instead of
  clean. The clean->dirty boundary is ~us 181.2-181.5.
- clean-flip rate: ~1/730 shots INSIDE us 180.5-181.2, vs ~1/2900 across the
  full 180-186 sweep (~4x dilution). We waste ~80% of shots above the sweet spot.
- the 2 latches ever (storage_0003 @184.0, storage_0024 @181.7) were both rep6.

DRIFT PATTERN (separate, from the proven rerun): clean flips cluster in the
first ~1h after a fresh start then dry up (8 flips 19:00-20:23, then 0 in the
next ~2700 shots/1h). Same marginal-glitch/thermal drift seen all day.

ACTIONABLE for next run: narrow sweep to us ~180.4-181.4 and FIX rep=6 (drop
randomization) to concentrate fire in the clean zone -> several-fold more clean
flips/hour -> more latch chances. Consider periodic fresh rig cycle to counter
the ~1h drift. Hardware: suspected cracked CW SMA jack reflow is the root-cause
candidate for the marginal/ drifting pulse.

## 2026-10-30 ~23:10 — STRATEGY: read hardware_salt from SRAM (.bss) instead of the refusing OTP region (user idea, source-verified)

Instead of glitch-reading uid(0x1FFF7A10)+otp3(0x1FFF7860) - the region whose
ADDRESS STAGE keeps refusing - read the firmware's precomputed hardware_salt
straight out of SRAM. Verified against reference/storage_storage.c:
- line 153: `CONFIDENTIAL static uint8_t hardware_salt[HARDWARE_SALT_SIZE]={0};`
  -> file-scope static => lives in .bss (SRAM), persists whole firmware runtime.
- HARDWARE_SALT_SIZE = SHA256_DIGEST_LENGTH = 32 (line 100).
- storage_init line 804: `sha256_Raw(salt, salt_len, hardware_salt)` => the
  static holds the FINAL SHA256(UID||OTP3) salt, ready-made.
- reused (lines 542,599), never scrubbed.
=> ONE 32-byte SRAM read replaces reading UID+OTP3 AND the offline SHA256, and
   targets SRAM (0x20000000) which the bootloader reads normally (NOT the
   refusing OTP/system block). Once latched, SRAM should COMPLETE where OTP
   REFUSES - makes the latch productive.

Attack: boot real firmware to PIN screen (storage_init has run -> salt in SRAM),
then NRST (NOT power-cycle) with BOOT0 high -> system bootloader with SRAM
preserved (NRST doesn't clear SRAM on F2), glitch-latch, read the known .bss
address of hardware_salt.

OPEN / TO VERIFY before trusting (priority):
1. Does the ROM bootloader overwrite that .bss address before we read? Needs an
   empirical SRAM-SURVIVAL TEST (write known pattern across SRAM from a test fw,
   NRST->bootloader, glitch-read back, see which addresses survive). BIGGEST risk.
2. Still need a latch (RDP gates at command stage regardless of address) - but it
   becomes PRODUCTIVE (SRAM completes vs OTP refuses).
3. NRST-to-bootloader from clean firmware (SRAM-preserving) must work on this rig
   - we've only ever used power-cycle+BOOT0 (which CLEARS SRAM). Test it.
4. Need hardware_salt's exact .bss address from the 1.13.1 .map/.elf (deterministic
   per build).
5. Cannot rehearse on the current 512KB F205 practice board (real 1.13.1 needs
   ~1MB). Validate the MECHANISM with a stand-in fw that stashes a known 32-byte
   marker in .bss; real-device for the real salt.

## 2026-10-30 ~23:30 — *** BREAKTHROUGH: SRAM is readable via SWD at RDP1 (no glitch needed for the salt) ***

PROVEN on this chip. Clean SWD attach at RDP1 (power-cycle BOOT0-high into
bootloader so core runs ROM not protected flash; free CW handle; then Stlink):
  RDP byte = 0x55 (L1), DEV_ID 0x411 (F2) confirmed.
  SRAM 0x20000000 = 0x7FFEEF3D   READ OK
  SRAM 0x20000100 = 0xAFFED63E   READ OK
  SRAM 0x20010000 = 0x00000000   READ OK
  FLASH 0x08000000 : BLOCKED/FAULT
  FLASH 0x08008000 : BLOCKED/FAULT
  UID   0x1FFF7A10 : BLOCKED/FAULT
=> RDP1 protects FLASH and the 0x1FFF system/UID region, but SRAM is wide open
   over plain SWD. (Explains why the glitched-bootloader uid/otp3 read refused at
   the address stage - that region is genuinely protected both ways; SRAM isn't.)

IMPACT: the hardware_salt (SRAM .bss static, = SHA256(UID||OTP3), see 23:10 entry)
is extractable with NO glitch, NO latch, NO grind. The entire uid/otp3 glitch
problem is MOOT - we were glitching to reach a hard-protected region when the
derived salt we actually need sits in unprotected SRAM.

SIMPLIFIED REAL-DEVICE ATTACK:
  1. firmware boots to PIN screen -> storage_init -> salt in SRAM .bss
  2. NRST + BOOT0-high into bootloader (NRST preserves SRAM; core off protected
     flash so SWD attaches at RDP1)
  3. SWD-read 32 bytes at hardware_salt's .bss address -> the salt
  4. encrypted storage (flash chunks 0-2) still via the PROVEN flash glitch-read.
Attach recipe that works at RDP1: fresh cw.scope(), tio1=True (BOOT0 high),
target_pwr off 1.5s / on 2.5s, s.dis()+del+gc, THEN Stlink(swd_frequency=480000).

STILL TO PROVE (test chip enables it): does the firmware .bss salt SURVIVE the
NRST-into-bootloader (ROM bootloader SRAM usage), and at what address? Validate:
RDP0 -> flash stand-in fw writing a known 32B marker to a .bss static -> RDP1 ->
boot -> NRST+BOOT0 bootloader -> SWD-read marker. Low SRAM already shows non-zero
leftovers in bootloader mode (0x7FFEEF3D) so wholesale-zeroing is NOT happening -
promising, but test the specific .bss region.

## 2026-10-31 ~00:00 — *** VALIDATED END-TO-END: no-glitch salt extraction via SRAM at RDP1 ***

Built a 68-byte stand-in firmware (storage-sim/sram_test/: stub.c, link.ld) whose
Reset_Handler writes a recognizable 32B sentinel (0xA0..0xBF) into a .bss static
`fake_salt` @ 0x20000000 - mimicking storage.c hardware_salt[32]. Flashed at RDP0
(st-flash, verified). Then:

STEP A (firmware plants it): boot BOOT0-low -> SWD read 0x20000000 = a0a1..bebf. OK.
STEP B (survival, confound-proof): one CW session - boot fw (BOOT0 low, power
  cycle) then NRST (tio4 low->high_z) with BOOT0 high, POWER CONTINUOUS. UART
  0x7F->0x79 = TRUE (confirms we're in the system bootloader, not a firmware
  re-run). SWD read 0x20000000 = a0a1..bebf INTACT. => sentinel SURVIVED
  firmware->NRST->bootloader at low SRAM. (tested RDP0; survival is RDP-indep.)
STEP C (capstone @ RDP1): set_rdp1 (byte 0x55), repeat B. Result:
  RDP=0x55, in bootloader=True, FLASH 0x08000000 BLOCKED, SRAM 0x20000000 =
  a0a1..bebf. *** FULL CHAIN VALIDATED ***.

PROVEN FACTS (this rig/chip):
- NRST (tio4 pulse) + BOOT0 high (tio1) from CLEAN running firmware ENTERS the
  system bootloader (contrary to the old "NRST doesn't work out of lockup" note -
  that was from a glitch-lockup; from clean fw it works), and PRESERVES SRAM (no
  power cycle).
- RDP1 blocks flash via SWD but SRAM is fully SWD read/writable.
- A firmware .bss value at 0x20000000 (low SRAM) is NOT clobbered by the ROM
  bootloader on NRST entry -> survives to be read.

REAL-DEVICE RECIPE (salt, no glitch):
  1. device runs firmware to PIN screen -> storage_init -> hardware_salt in .bss
  2. NRST + BOOT0-high -> system bootloader (SRAM preserved)
  3. SWD attach (RDP1 ok; flash blocked, SRAM open), read 32B at hardware_salt's
     .bss address -> the salt
  + encrypted storage (flash) still via the PROVEN flash glitch-read.
TODO real device: get hardware_salt's exact .bss address for the real fw build
(1.13.1 .map/.elf); layout is deterministic per build. Our stub's was 0x20000000
only because it's a trivial image - real fw address differs, must be looked up.

=> The entire uid/otp3 glitch grind (all of 2026-10-30) is MOOT for the salt.

## 2026-10-31 ~00:15 — Finding hardware_salt's .bss address: starting points (NEXT SESSION)

Goal: the exact SRAM address of storage.c hardware_salt[32] for the real fw build,
to read the salt from an SRAM dump. NOT a blocker - self-validating fallback:
dump all 128KB SRAM at RDP1 via SWD, run .bss-region 32B windows through
decrypt_storage.py brute-force; the salt that verifies the PVC is the right one.

trezor-1.13.1.bin structure (we have this file):
- legacy TRZF header @ offset 0; codelen ~0x0007B104 (504580B); 512B header, then
  code. Image stripped. Firmware (Trezor One) loads at 0x08010000.
- SHA-256 K-const 0x428a2f98 (LE 98 2f 8a 42) at file offsets 15736, 371694,
  450812, 451480 -> the sha256 transform / K-table is near offset 15736.
- 812 distinct SRAM-range literals (0x2000xxxx) across the image, 3056 refs.
  hardware_salt is ONE of them.
RE path to pin it:
  1. find sha256_Raw (near the K-table @~15736) and its callers.
  2. find storage_init's call sha256_Raw(salt, salt_len, hardware_salt) - the
     3rd arg literal (LDR Rn,=0x2000XXXX) is hardware_salt's address.
  3. cross-check vs the get_salt sites: memcpy(salt+salt_len, hardware_salt, 32).
Cleaner alt: reproducible-build legacy/v1.13.1 (full trezor-firmware repo +
pinned Docker toolchain) -> nm/.map gives the address directly. Confirm the
locked device actually runs 1.13.1 first (version reportable; storage version
in the (0,4) entry of the flash dump).

## 2026-10-31 ~01:xx — Glitch-2 characterization hammer resumed (practice chip, freshly re-planted)

Back on the stand-in (real device deferred - not ready). Re-planted storage:
set_rdp0 (3 passes to clear the erase-drops-DP quirk this time) -> plant_storage
(readback==storage.bin PASS) -> set_rdp1 (0x55). All via the now practice-guarded
scripts (G_PRACTICE_BOARD=YES). Board: RDP1, storage.bin @0x08008000, head blank.

Hammer = loop_fulldump.sh, FULL window to re-confirm ranges/strength:
  us 180-186 (ext 30000-31000), step 1 (0.006us), random rep 5/6/7, offset -45,
  G_FULL=1, reset-per-shot, fresh accum (storage_0000 first).
Goal: run continuously, accumulate the SUCCESS/ACK_NO_DATA/dead distribution by
us+rep to re-confirm the clean-flip sweet spot (expected ~us 180.5-181.2, rep6
from the 2026-10-30 analysis of ~52k shots). Live window + heartbeat + monitor up.

## 2026-10-31 ~14:00 — Clean-flip CAPABILITY COLLAPSED (hardware); LA rules out comms/chip/timing

After the overnight run's first ~6900 shots (7 flips), clean flips stopped and did
NOT recover across ANY approach: burst+cooldown (5310 shots, 0 clean), continuous
NRST (1883 shots, 0 clean) = ~22k shots, 0 clean flips. Glitch still LANDS the whole
time (dead ~3.4%, dirty ACK_NO_DATA ~1/190) - it perturbs but can't reach a clean
bypass. Power-cycle-damping hypothesis DISPROVEN: continuous NRST (no power cycle)
is equally dry.

LA check (storage-sim/la, passive on UART, during firing) isolates it:
- TX: 11 EE 7F ... command sent correctly.
- RX: 1F 1F / 79 - chip ALIVE, NACKs the read (correct RDP1), ACKs the sync.
- command->NACK latency median 194us vs 196.5us calibration = NO timing drift,
  window still correctly placed.
=> comms, chip responsiveness, and timing all VERIFIED GOOD. The only unverified
element is the VCAP pulse itself (LA can't see the ~36ns pulse). So the fault is
isolated to GLITCH DELIVERY: pulse amplitude dropped below the clean-bypass
threshold - a HARDWARE degradation, not software/config.
Suspects: (1) CW crowbar FET thermal (CW fired continuously >1 day, target
power-cycled but CW itself NEVER rested), (2) cracked CW SMA jack worsening,
(3) a loosened connection.

ACTION: cold-cycle the whole CW (unplug/cool/replug - the one reset never done),
then a quick glitch test - clean flip returns => FET-thermal; still dry => inspect/
reflow the SMA jack. Scripts stopped; CW stopped re-opening via software (consistent
with needing the cold-cycle). Practice chip RDP1 + storage planted (accum 10/64);
real device untouched.

## 2026-10-31 — Chip orientation test for an UNMARKED QFP64 (no dimple), power-OFF

Pinout refs (STM32F205 LQFP64): VDD = pins 1,19,32,48,64 (pin 1 = VBAT);
VSS = pins 12,18,63. (See docs/F205_LQFP64_PINOUT.md.) Reversed = instant kill
on power-up, so ALWAYS verify before energizing (rd_alive.py / any power).

Physical markers to check first: chamfered 45deg corner = pin-1 corner; faint
laser dot under angled light/loupe; text orientation (weak hint).

METHOD 2 - DMM diode mode, find the ground group (CHIP OUT OF SOCKET):
  - VSS pins 12/18/63 are internally bonded -> read continuity (~0 ohm) to each
    other, and every I/O pin shows ~0.5-0.7 V to them (RED on I/O, BLACK on VSS).
  - VDD pins 1/19/32/48/64 also mutually connected; diode conducts the OTHER way
    (BLACK on I/O, RED on VDD group). 5 VDD vs 3 VSS pins distinguishes them.
  - Map the VSS trio + one VDD pin to the pinout -> pin 1 (VBAT) is the first pin
    of the VDD side next to the corner -> orientation fixed. Seat to match socket.
  *** This test only works OUT OF SOCKET. *** In-socket it is CONFOUNDED: the
  board's GND net already ties socket positions 12/18/63 together regardless of
  the chip, so mutual continuity there proves nothing about orientation.

IN-SOCKET test (power OFF) - rail short check:
  - Measure 3V3 rail <-> GND rail. Correct orientation = normal chip impedance
    (kOhm-ish / decoupling caps charging). Reversed = a VDD pin on the GND net
    (or vice versa) => abnormal near-short or a diode drop between the rails.
    Any near-short/diode between 3V3 and GND => STOP, do not power.
Only after orientation is confirmed: rd_alive.py (powers chip, reads VCAP~1.2V /
VDD~3.3V on the scope = ALIVE; at RDP2 SWD/bootloader are dead = expected).

## 2026-10-31  New glitch-1 script: glitch1_rdp2_to_rdp1.py (reset-edge trigger wiring reconciled)  -> SUPERSEDED by "glitch-1 CORRECTED" (single TIO4 drive+self-trigger)

Wrote `storage-sim/glitch1_rdp2_to_rdp1.py`, a new boot-glitch (RDP2->RDP1)
script based on `scripts/1-recon_glitch_trace.py`, adapted to the storage-sim
rig and the current wiring. Compiles clean.

KEY WIRING CONSTRAINT documented in the script header: the glitch triggers on
the reset RISING edge, so reset must be DRIVEN by one CW pin and SENSED by a
DIFFERENT one, both on the chip reset net. A single TIO cannot both drive and
sense. Our recent SRAM/RDP work drove reset via TIO4 -> for glitch-1 we need a
second reset connection. Defaults: RESET_DRIVE=nrst (scope.io.nrst drives),
TRIGGER=tio4 (senses the release edge) -- the proven 1-recon scheme. Both are
env-configurable (G1_RESET_DRIVE / G1_TRIGGER) and the script hard-refuses if
they are the same line.

Config: clkgen 100MHz (ext window 17000-18900 = 170-189us defined at 100MHz;
rescale if clkgen changes), enable_only hp+lp crowbar on VCAP, repeat 20,
offset -45, width inert. BOOT0=tio1 LOW (boot firmware; glitch-1 acts in the
BootROM before the firmware jump). Success = SWD enumerates; on success reads
IDCODE/OPTCR/RDP byte/SRAM0 as validation. Read-only + crowbar, no option-byte
writes, no erase. CSV to campaigns/glitch1_<ts>.csv.

OPEN: confirm the physical reset/trigger wiring on the current bench before
running -- if only TIO4 is on the reset net, add the nrst->reset wire (or set
the env knobs to match).

## 2026-10-31  glitch-1 wiring reconciled to SINGLE reset wire (power-cycle trigger)  -> SUPERSEDED by "glitch-1 CORRECTED" (no power-cycle; TIO4 self-triggers on release)

Confirmed with user: this bench has only ONE wire on the reset net - TIO4 on
chip pin 7 (NRST). So the 2-wire drive/sense scheme (nrst drives, tio4 senses)
is impossible here. Reworked glitch1_rdp2_to_rdp1.py accordingly:

DEFAULT is now RESET_DRIVE='power' -- do NOT drive reset as a GPIO. TIO4 is a
pure INPUT (trigger). reboot_flush() power-cycles (target_pwr off 50ms -> on);
the chip's own POR holds NRST low then releases it, and that NRST rising edge
on TIO4 fires the glitch. ext_offset is measured from the NRST release = the
BootROM start, so the 170-189us option-byte window stays valid. The 2-wire
active-drive path (RESET_DRIVE=nrst|tioN) is kept for a future bench but needs a
second reset wire we don't have. setup_scope() forces the trigger line high_z
(pure input). Compiles clean.

Next: run it (needs the live follow-terminal). Watch for whether the POR NRST
edge is clean enough for a stable trigger; if it jitters, the fallback is to
add a 2nd reset wire and switch to active nrst drive.

## 2026-10-31  glitch-1 CORRECTED: single TIO4 drives NRST AND self-triggers on release

User correction (supersedes the 2026-10-31 "power-cycle trigger" entry above):
we never sensed anything externally - the ~180us is a pure delay from the reset
WE generate. One wire (TIO4 on pin 7/NRST) does both: tio4='gpio_low' holds the
chip in reset; tio4='high_z' releases it and the CW trigger block senses that
rising edge ON THE SAME PIN (reads the pin input the instant we stop driving).
So t=0 = reset release, glitch fires at ext_offset (~180us @100MHz = ext 18000).

glitch1_rdp2_to_rdp1.py now: trigger.triggers=NRST(tio4), reboot_flush() =
assert tio4 low -> arm -> release tio4 high_z. target_pwr left ON (no power
cycle; NRST pulse re-runs the BootROM option-byte read each shot). Removed the
RESET_DRIVE/power-cycle machinery and the bogus "can't drive+sense on one pin"
refuse check - that was my misconception; a single CW TIO drives low then
triggers on its own release edge. Env knob simplified to G1_NRST. Compiles.
-> SUPERSEDES the two earlier 2026-10-31 glitch-1 wiring entries.

## 2026-10-31 ~15:23 — Session resume: loop_fulldump relaunched + FINDINGS consolidated

Resumed the full-dump collector (loop_fulldump.sh) on the practice chip after the
afternoon stop. Rig verified ready: CW-Lite (2b3e:ace2) + FTDI (0403:6001 →
/dev/ttyUSB0) both on the bus. Params unchanged (the proven set): 166.667 MHz,
enable_only hp+lp, offset -45, w5, us 180.3-181.8, random rep6/7, reset-per-shot,
scope OFF VCAP, resume from dumps/accum (10/64 storage chunks already banked).
Clean 1f1f NACKs, [rst ok] per shot, chip syncing — crowbar released cleanly on
the fresh scope open (no manual vglitch_reset needed; relaunch setup() handles it).

Ops fix: first launch doubled every log line — loop_fulldump.sh already pipes
through `tee -a /tmp/opencode/fulldump_loop.log`, and the launch ALSO redirected
stdout to that same file (tee's copy + the redirect's copy). Correct launch:
`nohup ./loop_fulldump.sh >/dev/null 2>&1 &` and let the internal tee write the
single copy. Noted for every tee-logging wrapper here.

Consolidated FINDINGS per the golden-bible rule: added a `## CURRENT STATE OF
KNOWLEDGE` section at the TOP (proven facts, current best params, open questions,
rig quirks) that supersedes the stale early top matter; full chronological
history preserved below. Still watching for the ~1h clean-flip drift (2026-10-31
14:00 collapse) — if clean flips don't appear this run, cold-cycle the CW.

## 2026-10-31 ~22:05 — Cold-cycle did NOT restore clean flips: degradation is hardware/injection-path, not thermal

Two back-to-back full-dump runs today, practice chip, 10/64 chunks resumed:
- RUN A (narrowed + no-rest, my launch error): G_US_MIN/MAX 180.3-181.8,
  G_REST_S=0 (flat-out). 8711 shots: 8359 nack, 229 dead (2.6%), 24 ACK_NO_DATA,
  11 zombie, 3 weird. **0 clean SUCCESS.**
- Diagnosed the config drift: the version that WORKED (loop_fulldump.morning_proven.sh,
  2026-10-30, banked chunks + got a latch) used the WIDER window 180-186 AND the
  driver-default rests (G_REST_S=10 every 300 shots). Today's loop_fulldump.sh had
  been narrowed to 180.3-181.8 with G_REST_S=0 (no rests). Restored the proven file
  (today's saved as loop_fulldump.narrow_norest.bak.sh).
- RUN B (after USER COLD-CYCLED the CW + proven config restored): wider 180-186,
  rests back. 5398 shots over ~2h: 5192 nack, 121 dead (2.2%), 14 ACK_NO_DATA,
  5 zombie, 12 weird, 2 spam. **0 clean SUCCESS, 0 chunks banked.**

CONCLUSION (statistically decisive): at the proven ~1/730 clean-flip rate, 5398
shots should yield ~7 clean completions; 0 is P~0.06%. The cold-cycle + rests +
proven wider window did NOT restore clean flips. This RULES OUT FET-thermal as the
cause (unplug/cool/replug would have recovered it). The glitch still BITES (2.2%
dead, 14 dirty ACK_NO_DATA, full window swept) but the pull is too shallow/soft to
land a single clean flip. => degradation is in the INJECTION PATH (cracked CW SMA
jack / connector / lead), temperature-independent. ~14k shots across today confirm
it cannot flip clean in this state.

NEXT (decisive, not more grinding): scope the PULL DEPTH directly - CH1 on VCAP
pin 31, trigger on the drop (NEG ~0.9V), single armed shots, campaign stopped. If
the dip is shallow vs the deeper pulls it made when banking chunks -> injection
path degraded, confirmed on screen. Then reflow the CW SMA jack and re-measure.
This is the delivery-verification that has been deferred for days - do it before
any more campaign time. Chip RDP1 + storage planted; 10/64 chunks in accum.

## 2026-11-01 — RIG-GAP ANALYSIS vs literature + PLAN: external VCAP feed (parts ordered)

Re-read the primary sources (kesenheimer README_FLASH_DUMP + crowbar script,
VoidStar Replicant, cross-checked FINDINGS). Reframed "why isn't ours working"
into two separate problems:

-> SUPERSEDED by 2026-11-01 "VCAP repeat ladder scope captures": direct
   measurement shows full collapse to GND/below — path is HEALTHY, not degraded.
1. ACUTE (today's blocker): injection path DEGRADED. 14k shots across 2 runs,
   0 clean flips; cold-cycle + proven wider window + rests did NOT restore it →
   rules out FET-thermal. Glitch still bites (deads + dirty ACK_NO_DATA) but pull
   too shallow to land clean. Suspect: cracked CW SMA jack / loose lead.
   FIX (free, FIRST): scope the dip (CH1 VCAP pin31, trigger on drop NEG ~0.9V,
   campaign stopped) + reflow the CW SMA jack. We already banked real data with
   the bare crowbar (2026-10-30), so if reflow restores it we may not need the
   feed at all.

2. CHRONIC (the ceiling): we crowbar the LIVE internal LDO; the LDO recharges
   VCAP in ns and fights the pull → marginal 1/730, dirty flips, ~1h drift.
   THE one structural difference from kesenheimer's RELIABLE rig: he feeds VCAP
   from an external <=1.2V current-limited supply (through the Pico mux/crowbar),
   which IDLES the internal LDO → clean deep collapse even at 10-30ns.
   NOTE: VoidStar succeeded on this exact chip with a BARE CW-Lite crowbar direct
   to VCAP1 (no external feed) — so the feed is an OPTIMIZATION, not a
   prerequisite. It addresses the marginality, not today's broken wire.

PLAN (external VCAP feed = kesenheimer crowbar-variant topology, on our CW):
- External ~1.2V current-limited bench supply -> [4.7-10 ohm series R] -> VCAP
  (pin 31, same node as SMA/crowbar). Supply GND common with CW GND. CW crowbar
  stays on top. The weak feed idles the internal LDO; crowbar collapses it clean.
- Mechanism: feeding VCAP at ~1.2V turns the chip's internal LDO pass device off
  (sees target met) → no fast recharge fighting the crowbar.
- SAFETY: NEVER exceed ~1.2V on VCAP (core overvoltage = dead chip). Set supply
  output OFF, dial 1.2V + current limit ~40mA, verify on DMM, THEN connect.
  Practice chip first. Power VDD first (internal LDO brings VCAP to 1.2V), match
  the external supply to ~1.2V, then connect (no inrush). Verify chip still syncs
  (0x7F->0x79); scope that VCAP holds ~1.2V idle and the dip now goes much deeper.
- Series R is the tuning knob (fixed-V supply): too big -> VCAP sags, chip won't
  run -> smaller; dip too shallow -> bigger. Dial on the scope.

PARTS ORDERED (user, 2026-11-01): a ~30V/5A CC/CV bench supply (305D-class;
key specs: 0-30V, true adjustable CC/CV, >=0.01A current resolution) + a resistor
assortment (covers 4.7-47 ohm). No soldering needed with the bench supply —
binding posts + clip leads / one joint.

ORDER OF OPERATIONS when parts arrive: (1) SMA reflow + scope the bare crowbar
dip FIRST (today's blocker, keeps each change diagnosable); (2) if healthy but
still marginal, add the external VCAP feed and re-scope/re-farm. Rig parked idle
until then; 10/64 chunks in accum, chip RDP1 + planted.

## 2026-11-01 — VCAP repeat ladder scope captures (REFUTES the "degraded injection path" parking hypothesis)

Scope ON the glitch node (CH1, 500mV/div, DC1M, 100ns & 50ns/div, trig EDGE
C1 falling ~247mV). Diagnostic captures only — scope damps injection, so this
is characterization, not a campaign. User fired, I captured/opened/sent.
Captures saved: storage-sim/scope_captures/2026-11-01_repeat_ladder/

MEASUREMENT FRAME (confirmed real core rail): at 500mV/div the flat idle sits
~2.4 div above the 0V cursor = ~1.2V = VCAP nominal. So these ARE genuine
core-rail traces, NOT the SMA switching-residual.

REPEAT LADDER (enable_only hp+lp, 166.666667MHz clkgen), trough vs 1.2V idle:
  r4 (held/stale, prob. earlier shot): 120 mV   (~1.08V dip)   100ns/div
  r5:                                   60 mV   (~1.14V dip)    50ns/div
  r6:                                    0 mV   (full ~1.2V to GND) 100ns/div
  r7:                                 -120 mV   (through GND, neg undershoot) 50ns/div
  => monotonic ~60 mV deeper per repeat cycle. Clean, predictable depth knob.

HEADLINE: the 2026-11-01 parking hypothesis ("injection path degraded / pull
too shallow / cracked SMA -> reflow before resuming") is REFUTED by direct
measurement. Crowbar pulls VCAP cleanly to 0V (r6) and BELOW ground (r7) —
full 1.2V brownout, ~1.85-2.0V pk-pk with ringdown. A cracked/attenuating SMA
(feared ~1000:1) would show millivolts, not a swing to ground. INJECTION PATH
IS HEALTHY — no SMA reflow needed on depth grounds. The earlier "mV-scale
output / cracked SMA" catch (skill note) was almost certainly the UNPOWERED-
chip control: no LDO -> no 1.2V rail to collapse -> only FET switching residue.
  -> This supersedes the 2026-11-01 "injection path degraded, suspect cracked
     SMA jack / loose lead" conclusion. That entry: pull depth was never the
     problem.

REFRAME OF THE 0-CLEAN-FLIP DROUGHT: if the rail already slams to ground and
we still got 0 clean flips over thousands of shots, pull STRENGTH is not the
limiter. Two live candidates:
  1. OVER-GLITCHING: r6/r7 crash fully to/below GND -> more likely to
     reset/kill the core (dead, dirty ACK_NO_DATA) than to brown out one RDP
     comparison cleanly. Clean skip likely wants a PARTIAL dip, not a ground
     slam -> sweet spot may sit SHALLOWER than r6 (r4-r5 band, or a short
     width-shaped glitch_only pulse), not deeper. (Note tension w/ older
     "rep5 too weak" entries — revisit: those judged by flip outcome, not by
     measured depth. Now we have measured depth.)
  2. TIMING: if depth is fine, the decision-window offset (G_US_MIN/MAX) is
     the remaining knob.

BEARING ON EXTERNAL-VCAP-FEED PLAN: feed was justified as "deeper/cleaner
collapse by idling the LDO." But we ALREADY get full collapse to ground. So
the feed's value is NOT more depth — at most shot-to-shot SHAPE repeatability
(kill LDO fightback) + taming the long underdamped ringdown (~500-600ns,
overshoot to ~2V; both VCAP caps pulled, node rings on parasitics).
Reconsider whether the feed is on the critical path vs. a shallower/narrower
pulse + timing sweep.

NEXT (when resuming on practice chip, scope OFF the node):
  - depth-vs-flip sweep: walk rep DOWN from 6 (try 4, 5, and width-shaped
    glitch_only partial dips) while holding the proven window; watch for the
    clean-flip band instead of assuming "deeper = better".
  - if depth band found but still no flips, sweep timing (G_US_MIN/MAX).

## 2026-11-01 — NEW TOOL: rdp1_uart_test.py (read-only RDP1 baseline) + healthy result

New reusable diagnostic storage-sim/rdp1_uart_test.py. READ-ONLY: BOOT0-HIGH
power cycle (CW TIO1), crowbar OFF, no glitch, no writes, no RDP touch. Safe
any time. Env G_LEAVE_POWERED=0 cuts power on exit (default leaves powered).
Sequence: 0x7F autobaud -> Get(0x00) -> Get ID(0x02) -> Read Memory(0x11).

RESULT (practice chip, 2026-11-01):
  SYNC    0x7F -> 0x79              bootloader ALIVE
  Get     0x00: v3.1  cmds=[00 01 02 11 21 31 44 63 73 82 92]
  Get ID  0x02: PID=0x411          STM32F2xx (correct part)
  ReadMem 0x11 -> NACK 0x1F        RDP1 ENGAGED (protected)
  VERDICT: UART HEALTHY + RDP1 ENGAGED (ready to glitch).

WHY THIS CAME UP: user reported "not seeing UART". Root cause = a campaign
(rdp1_glitch_campaign_full_mem_dump.py, PID 1113671, ~18min) was still RUNNING
and OWNED /dev/ttyUSB0, so ad-hoc serial reads returned empty. Killed it
(needed SIGKILL - campaign ignores SIGINT/SIGTERM, consistent w/ prior
sessions). LA passive capture: all 8 lines idle HIGH (correct UART idle),
D0=host->chip TX, D1=chip TX, D2=glitch tap; stimulated decode showed
0x7F(host) -> 0x79(chip ACK). UART path confirmed healthy; "no UART" was just
no active traffic + port contention, NOT a fault.

ASIDE: SWD SRAM read attempt (read-only, BOOT0 low) via swd.stlink.Stlink
read_mem32(0x20000000,512) FAILED with StlinkUsbException Errno 5 (USB I/O).
ST-Link present in lsusb (0483:3748 ST-LINK/V2) but errored - needs a
reconnect/replug/reset before the SWD SRAM path (hardware_salt) will work.
Separate issue from the UART path (which is healthy).

## 2026-11-01 — NEW TOOL: rdp1_sram_dump.py (full 128KB SRAM via SWD) + ST-Link USB-reset recovery

We did NOT previously have a full SRAM dumper - only single-word alive checks
(glitch1_boot_rdp.py:98, glitch1_rdp2_to_rdp1.py:116 do st.get_mem32(0x20000000),
one word). Now: storage-sim/rdp1_sram_dump.py reads the WHOLE SRAM.

rdp1_sram_dump.py: READ-ONLY, no glitch. Powers chip (BOOT0 low=firmware, or
G_BOOT0_HIGH=1=bootloader), crowbar OFF; connects swd.stlink.Stlink @ 1.8MHz;
reports IDCODE/Vtarget/RDP(OPTCR 0x40023C14 bits15:8); sanity-checks flash is
BLOCKED; block-reads 0x20000000 in chunks of st.maximum_32bit_data (6144 B on
this ST-Link, aligned to 4) to dumps/sram/sram_<UTC>.bin + hexdump summary.
Knobs: G_SRAM_BYTES (def 131072), G_SWD_HZ (def 1.8M), G_LEAVE_POWERED=0.

RESULT (practice chip, 2026-11-01):
  IDCODE=0x2ba01477 (Cortex-M3)  Vtarget=3.26V
  OPTCR=0x0fff55ed  RDP byte=0x55 -> RDP1 (any non-AA/non-CC = level 1)
  flash @ 0x08000000 over SWD: BLOCKED (confirms RDP1, not RDP0)
  SRAM: 131072 bytes read in 1.2s (106 KiB/s), 99.2% non-zero. SAVED.
  => confirms the proven fact: at RDP1 SWD reads SRAM fine, flash blocked.
  This is the no-glitch FRONT HALF of the hardware_salt path (next: search
  the SRAM image for the salt bytes).

ST-LINK RECOVERY (important rig trick): after a StlinkUsbException Errno 5
(USB I/O), the ST-Link enumerates on the bus (lsusb shows 0483:3748) but
st-info reports "Found 0 stlink programmers" and pyusb can't claim it - the
endpoint is stuck. FIX WITHOUT REPLUG: issue USBDEVFS_RESET ioctl on its
/dev/bus/usb/<bus>/<dev> node:
  import fcntl,os; USBDEVFS_RESET=(ord('U')<<8)|20
  fd=os.open('/dev/bus/usb/003/071',os.O_WRONLY); fcntl.ioctl(fd,USBDEVFS_RESET,0)
(node is crw-rw-rw- plugdev, no sudo needed here). After reset st-info found
it immediately (V2J29S7, chipid 0x411, sram 131072). This likely explains the
earlier ad-hoc SWD SRAM read failure.

## 2026-11-01 — chip IDs consolidated (practice chip)

  DAP IDCODE        0x2ba01477   ARM Cortex-M3 DP (generic, confirms core)
  DBGMCU_IDCODE     0x200f6411   @0xE0042000 (SWD-readable at RDP1)
    DEV_ID          0x411        STM32F2xx
    REV_ID          0x200f       silicon rev (raw; letter unmapped - not the
                                 common 0x1000/1001/2000/2001 codes)
  Bootloader PID    0x411        UART Get ID (0x02) - matches DEV_ID
  st-info chipid    0x411        sram 131072, flash pagesize 131072
  ST-Link serial    37FF6D063143433928181443  (programmer, not chip)

96-bit UID @0x1FFF7A10: BLOCKED at RDP1 over SWD (StlinkException) AND refused
at bootloader address stage. The per-chip unique serial is NOT obtainable at
RDP1 -> hardware_salt must use the firmware's precomputed copy in SRAM .bss
(rdp1_sram_dump.py path), never re-derived from UID. (Re-confirms prior fact.)

## 2026-11-01 — SRAM salt search: ABSENT (no firmware running on practice chip)

Searched the full 128KB SWD SRAM dump (sram_20261101T181125Z.bin, BOOT0-low)
for hardware_salt + UID + keys. ALL MISSING:
  hardware_salt 99ed0b39..eeb5 : not found   UID 3e003100..3138 : not found
  kdf_salt / DEK / KEK / salt[:16] : not found   stub sentinel A0..BF : not found
(Verified the expected salt first: SHA256(uid||otp3) == known-answer hardware_salt,
 TRUE. uid=3e0031001547333032303138, otp3=ff*32.)

WHY ABSENT (confirmed, not ambiguous): the dump is power-on SRAM RETENTION
NOISE, not an initialized firmware image:
  word[0] (init SP)   = 0x3ff6ffad  (invalid; real = 0x2001xxxx)
  word[1] (reset vec) = 0x3d32524a  (invalid; real = 0x080xxxxx)
  Shannon entropy     = 7.844 b/byte (~pure random; real fw SRAM ~4-6)
  longest zero run    = 2 bytes     (a C runtime zeroes .bss -> long zero
                                     regions; none => crt0 never ran)
Cause: practice chip flash HEAD IS BLANK (only storage.bin @0x08008000, nothing
bootable @0x08000000 - see 2026-10-31 ~01:xx re-plant). BOOT0-low boot fetches
an invalid vector table -> immediate fault -> .bss never populated -> no salt.

CONSEQUENCE:
- On the PRACTICE chip the salt is a KNOWN build constant (99ed0b39..eeb5);
  nothing to recover from SRAM. The SRAM search only makes sense against
  salt-COMPUTING firmware that has actually run.
- To rehearse the real-device SRAM salt-extraction here, must flash fw that
  computes+stores the salt (10-31 sentinel stub, or real Trezor 1.13.1) at
  RDP0, boot BOOT0-low, then re-dump. That WIPES + re-plants current storage.
- rdp1_sram_dump.py itself works perfectly (128KB in 1.2s) - the tool is fine;
  there's just no salt in SRAM to find on a chip with no running firmware.

## 2026-11-01 (16:45) - scope-OFF fulldump pass: glitch lands, address stage is the wall  [counts SUPERSEDED by 16:50 - ACK_NO_DATA undercounted 2 vs real 28]

Relaunched loop_fulldump.sh with window opened to 179-186us (G_US_MIN 180->179),
scope OFF the injection node (on UART line only). ~14k shots banked this log.

Verdict tally (loop log, several relaunches): 13634 nack, 346 dead, 21 weird,
17 zombie, 4 spam, **2 ACK_NO_DATA**, 0 SUCCESS, 0 new banks (still 10/64).

PROVEN this pass:
- Glitch lands reliably: 346 dead + 17 zombie + 2 ACK_NO_DATA ~= 2.7% disturbance,
  vs 0.7% on the earlier scope-ON-node run. Scope on the VCAP node WAS damping;
  moving it to the UART line ~4x'd the bite. (Confirms the measurement-only rule.)
- Disturbance is NOT weak-pull / dead-air: it is concentrated and repeatable.
- HOT ZONE = 180.2-181.9us, rep 6/7. The 182-186us top of the window produces
  only climbing nacks (dead air). ~70% of each 179-186 sweep is wasted.
- THE WALL: command flips, address refuses. Both ACK_NO_DATA (180.4us r6,
  181.0us r7) show pre=79...79 -> the single glitch flips the Read-Memory COMMAND
  NACK->ACK (0x79), then every address-stage read refuses (1f1f). We get half the
  protection on best shots; no clean latch landed in this 14k-shot log.

Interpretation: at these params the glitch perturbs the command-stage RDP check
but the address-stage re-check still holds. Next moves to try (in order):
  1. NARROW the window to the hot zone (e.g. 180.0-182.0us) so every shot is
     productive -> ~3-4x effective near-miss rate without changing anything else.
  2. If still only ACK_NO_DATA: the proven morning-latch config DID latch here
     before, so this is a rate problem, not an impossibility - more dwell in the
     hot zone should eventually carry the address stage.

## 2026-11-01 (16:50) - CORRECTION to the 16:45 entry + real flip distribution

The 16:45 tally was WRONG: the grep regex was lowercase-only (`-> [a-z_]+`) so it
missed every ACK_NO_DATA (uppercase). Re-parsed the full loop log (14,163 shots):

CORRECT tally: 13744 nack, 349 dead, **28 ACK_NO_DATA**, 21 weird, 17 zombie,
4 spam, 0 SUCCESS, 0 new banks (still 10/64).

So there were 28 command-flips, not 2. And the hot zone claim was wrong too:
- ACK_NO_DATA (command flips) span 180.1-184.2us and **PEAK at 182.0-182.4us**
  (11 of 28), with a secondary lobe at 180.0-180.2us. NOT 181.
- dead spans the whole 179-186 (brute reset, uninformative for timing).
- => A narrow to 180.0-182.0 would have CUT OFF the main flip cluster. Correct
  narrow window is ~181.8-182.6us (dominant), or 180.0-182.6 to keep both lobes.

The flips, decoded from the pre= bytes (what the glitched Read-Mem returned):
- `790b31000102112131446373829279` (x6): Read Memory returned the FULL Get
  response (79 0b 31 00 01 02 11 21 31 44 63 73 82 92 79) -> command-dispatch
  DESYNC, the richest flip class. Clusters at 180.4-182.5us.
- `7931000079` (x3): ACK + leaked bytes (79 31 00 00 79). ~181-183us.
- `79` bare (x8): command ACK, address stage silent/refused.
- `1f1f111179` (x7): NACKs then 11 11 79 (late/partial ACK).
- `1f79` / `7901041179`: NACK-then-ACK and misc.

Barrier unchanged: command stage flips, address stage never yields data. But the
flip rate is ~4x what I thought (28 not 2), and r7 (42ns) flips dominate the
182us region while r6 (36ns) dominates 180-181us.
Figure: scope_captures/2026-11-01_range_hit/range_and_hits.png
-> 16:45 entry's "2 ACK_NO_DATA" and "hot zone 180.2-181.9" are SUPERSEDED here.

## 2026-11-01 (18:21) - narrowed window 180.0-182.8us: flip density doubled, wall holds

Ran loop_fulldump.sh narrowed to 180.0-182.8us for ~1.5h. This-run tally:
3702 nack, 119 dead, 16 ACK_NO_DATA, 9 zombie, 0 SUCCESS, banks still 10/64.

Narrowing worked as a RATE fix:
- ACK_NO_DATA flip rate = 16/3846 = 1 per 240 shots
  vs old 179-186 window = 28/14163 = 1 per 506 shots  -> ~2x denser.
- disturbance rate 3.7% (vs 2.7% broad).
Flips land where the 16:50 analysis predicted (181.8-182.1us r6/r7), same
signatures: 790b3100...9279 (Read-Mem -> full Get response desync) and 1f1f111179.

WALL UNMOVED: single glitch flips the command-stage RDP check (command NACK->ACK)
but never carries into the address-stage re-check -> addr stage refuses 1f1f every
time. 0 clean latches in ~18k shots across both windows today. This is now a
depth/mechanism problem at the address stage, not a rate problem.
Candidate next moves: (1) keep farming (config latched this morning); (2) sweep
G_WIDTH at the 181.8-182.4 flip peak (currently fixed w5); (3) double-glitch a
second pulse at the address-stage check (needs campaign code change).

## 2026-11-01 (19:45) - RESEARCH on ACK_NO_DATA / zombie: it's a 2-gate structure + UART jitter

Searched published research on the command-ACK-but-address-refused pattern. Key
findings, each mapped to our logs:

1. AN3155 (USART bootloader protocol) defines Read Memory as TWO gated stages:
   - command stage: ACK the command byte, check command-ID + conditions (RDP) -> NACK if bad
   - address stage: check addr valid + checksum AND "read memory only possible when
     NO protection is set" -> ACK else NACK+abort.
   => Our ACK_NO_DATA = glitch beats gate 1 (command ACK 0x79), gate 2 (address-stage
   RDP check) still holds -> 1f1f. STRUCTURAL, not a rig fault.

2. Anvil Secure writeup (anvilsecure.com) ~= our exact rig (STM32F4 RDP1, CW-Lite,
   VCAP glitch, trigger on UART TX, separate USB-UART for parity):
   - Their Read-Mem request landed at ~182.3us == OUR FLIP PEAK 182.0-182.4us.
     Independent confirmation we fire at the right instant.
   - RDP check reads 0x40023C14 (FLASH_OPTCR) - same reg our rdp1_sram_dump reads.
   - Working window a thin ~50-cycle band (ext 18313-18365), and they got CLEAN
     256-byte reads with a SINGLE glitch - no ACK-no-data plateau.
   => our wall is TUNING (pulse depth/shape/phase), NOT a missing 2nd glitch.

3. SECGlitcher (sec-consult.com) "obstacles no one mentioned" - both in our logs:
   - UART clock-domain jitter: response wanders up to 8us shot-to-shot (slow->fast
     clock domain). We glitch at FIXED offset -> true distance to the internal check
     wanders -> explains our 180-184us flip SMEAR.
   - Glitching onto a DIFFERENT bootloader path (RDP->0x55, SPRMOD->0x01). == our
     richest flip pre=790b3100...9279 (Read-Mem returns the full Get response =
     command-dispatch DESYNC), and pre=7900...00 (ACK + 32 zero bytes = address
     stage executes but reads nothing). Distinct landing points, not clean skips.

4. Joe Grand + L. Wouters (github joegrand/stm32-fault-injection): full flash in
   "two glitches" = RDP2->RDP1 downgrade + FPB attack, NOT two glitches inside the
   read. We're already RDP1 so their downgrade glitch is moot.
5. "Shaping the Glitch" (TCHES): glitch waveform/width shaping materially improves
   VFI yield -> supports a width sweep.

CONCLUSION: a single well-tuned glitch clears BOTH gates on hardware like ours
(Anvil proved it). We beat gate 1 reliably, never gate 2 -> attack pulse
depth/shape/exact phase (width sweep at 182.0-182.7us), not double-glitching.
Sources: AN3155; anvilsecure.com glitching-stm32-read-out-protection; sec-consult
secglitcher-part-1; github joegrand/stm32-fault-injection; TCHES "Shaping the Glitch".

## 2026-11-01 (20:10) - CW docs: offset is NOT inert in enable_only (our code comment is wrong)

Read the authoritative GlitchSettings docstrings from the installed CW
(ChipWhispererGlitch.py). The 5 output modes:
  clock_only / glitch_only / clock_or / clock_xor / enable_only.
  Voltage glitching uses glitch_only or enable_only; CW's vglitch_setup()
  DEFAULT is glitch_only (our enable_only is the VoidStar/backup-dumper lineage).

repeat: glitch_only/clock_* = that many DISTINCT pulses; enable_only = a SINGLE
pulse `repeat` cycles wide. (Confirms our shape model.)

CORRECTIONS to our assumptions (our code comment at rdp1_glitch_campaign line
62-63 and FINDINGS 41-42 say "width/offset INERT in enable_only"):
- width: TRUE - "Has no effect when output is enable_only."
- offset: FALSE - docs explicitly say enable_only "width and width_fine have no
  effect, but OFFSET and offset_fine DO." So our OFFSET=-45 is a LIVE shape knob
  we have been treating as dead. Sweepable WITHOUT leaving enable_only.
- offset WARNING: "very large negative offset <-45 may result in DOUBLE glitches
  (CW-lite/pro only)." We run offset=-45 == exactly the double-glitch threshold.
  Our "single" 36ns short may already be edging into a double-pull regime via
  fine-offset -> relevant to the 2-gate wall (a double disturbance could hit both
  the command and address checks). Sweeping offset around -45 is a real stage-1
  shape experiment inside the proven mode.

glitch_only = repeat separate width/offset-shaped spikes (scalpel); the genuine
alternate geometry if offset-in-enable_only doesn't carry gate 2.

## 2026-11-01 (20:30) - *** PRACTICE-CHIP PIPELINE COMPLETE: PIN + MNEMONIC RECOVERED ***

While debating the "we got lucky / did we regress" latch-rate question, checked
what is ALREADY banked in dumps/accum: 10 chunks, including storage_0000/0001/0002.

- Banked chunks 0..2 are BYTE-PERFECT vs planted storage.bin first 768B (==True).
  The glitch extraction of the NORCOW secret region ALREADY SUCCEEDED (10-30 latch
  banked exactly the chunks that matter). storage_0000 magic NRC2, random_salt
  17773784 at +0x18, EDEK_PVC key/tag in 0002 - all real, all verified.
- Ran decrypt_storage.py --brute 0000-9999 --uid 3e00310015473330323031 38
  --otp3 ff*32 on the reassembled banked image (PIN NOT given):
    *** PIN FOUND: <redacted> (9435 candidates, 52.0s)
    entry 0102 mnemonic: "<12-word mnemonic redacted, in known-answer.json>"
    -> both match known-answer.json EXACTLY.

=> FULL CHAIN PROVEN end-to-end: glitch past RDP1 -> extract 3 NORCOW chunks over
   UART -> offline PBKDF2 (v4: PBKDF2-HMAC-SHA256(pin, hw_salt||random_salt,10000,44))
   brute 0000-9999 in <1min -> PIN + seed. Practice rehearsal is DONE.

STRATEGIC REFRAME (the real lesson of the all-FF history):
- 61 of 64 chunks are erased-FF BY DESIGN. All secrets live in chunks 0/1/2 (768B).
- G_FULL=1 full-64 farming has been chasing 61 WORTHLESS erased chunks -> that is
  why today's 18k-shots-0-latches felt like a regression: we were grinding for
  blank data we don't need. The data that matters was banked 2 days ago.
- The "latch rate" anxiety is moot for the practice chip: extraction succeeded.
- REAL-DEVICE plan = TARGETED extraction of 5 objects only: storage 0,1,2 + uid
  (0x1FFF7A10) + otp3 (0x1FFF7860), then the same offline brute. ~5 targets, not
  64. The practice chip has now taught us the shape/timing/pipeline AND proven the
  offline crack. (hw_salt=SHA256(uid||otp3) so real-device needs the real uid+otp3,
  which are the campaign's extra TARGETS - glitch them like any chunk.)

## 2026-11-01 (20:45) - practice chip RESET: set_rdp0 -> plant -> uart test, all PASS

After proving the full pipeline (PIN+mnemonic recovered from banked chunks),
user asked to reset the practice chip for a fresh rehearsal cycle. Sequence:
1. set_rdp0.py (G_PRACTICE_BOARD=YES): RDP 0xBB->0xAA, mass erase on option
   reload, verified flash head all-FF. PASS.
2. plant_storage.py (SWD word program - bootloader Write Mem 0x31 NACKs on this
   chip): storage.bin @0x08008000, readback == storage.bin. PASS.
3. uart_rdp0_test.py: sync 0x79 OK; readmem 0x11ee ACKed (RDP0 unprotected);
   dumped 4096B, head 4e524332 = NRC2 canary = planted storage intact. PASS.
Chip now: RDP0, fresh plant, UART bootloader healthy, Read Memory OPEN.
Next for a glitch rehearsal: set_rdp1.py to re-lock, then the targeted campaign.
(Banked chunks from the prior cycle preserved in dumps/accum - not touched.)

## 2026-11-01 (20:47) - NEW CYCLE: re-locked RDP1, archived cycle-1, targeted campaign on CLEAN ZONE

- set_rdp1.py (G_PRACTICE_BOARD=YES): OPTCR RDP 0xAA->0x55 = RDP1 SET (flash
  survives on 0->1). rdp1_uart_test.py: sync 0x79, Get v3.1, PID 0x411,
  Read Memory NACK 0x1F -> RDP1 ENGAGED + UART healthy. Confirmed re-lock took.
- Archived cycle-1 data -> archive/2026-11-01_cycle1/ (10 accum chunks incl the
  cracked 0/1/2, 3 run dirs, loop log). dumps/accum reset empty for a cold start.
- Launched loop_targeted.sh (pid 1157870): DEFAULT targeted mode = 7 targets
  (storage_0000..0004 + uid@0x1FFF7A10 + otp3@0x1FFF7860) - the real-device
  ~5-object attack shape. Window NARROWED to the proven CLEAN LATCH ZONE:
  G_US_MIN=180.3 G_US_MAX=181.4 (ext 30050-30233), NOT the dirty 182 tail.
  Shape unchanged/proven: 166.67MHz enable_only, hp+lp, rep6/7 (G_RND_LO=33
  G_RND_HI=45), offset -45, width 5, reset-every-shot. Stops when uid+otp3
  banked. First shots: rep6/7, nack 1f1f (RDP1 live). Log: targeted_loop.log.
- This tests the "best chance" thesis: concentrate fire on the clean zone
  (180.3-181.2, peak 181.0) instead of spreading across 180-186. Watch for the
  first latch; if ~5k clean-zone shots yield 0 -> diagnose (timing/depth drift).

## 2026-11-01 (20:48) - CLEAN-ZONE THESIS CONFIRMED: SUCCESS on shot #46

New targeted campaign, clean zone 180.3-181.4us: first SUCCESS at shot #46,
ext=30065 (180.4us) rep6=36ns -> CHUNK SECURED storage_0000 (oracle=MATCH,
byte-correct). 1 latch in 46 shots vs ~18k-shots-0-latches earlier today on the
spread 180-186 window (most of which hit the dirty 182 tail). Concentrating on
180.3-181.4 (clean peak 181.0) was decisive. Latch landed at 180.4us rep6 -
squarely in the predicted clean zone. NOT a regression after all; we were just
firing in the wrong part of the window. Farming continues for 0001-0004+uid+otp3.

## 2026-11-01 (21:10) - D1-B (Obermaier exception/vector-fetch readout) BLOCKED on F2

Tested Obermaier WOOT'20 "D1-B: Extraction via Exceptions" on our F205 @ RDP1 via
SWD (new tool d1b_exception_read.py). Mechanism: at RDP1 with debugger, F1 leaks
flash on the INSTRUCTION bus via interrupt vector fetches (data bus blocked). Point
VTOR at flash, pend NMI, step, read PC = fetched handler addr = a flash word.

Result:
- direct data-bus flash read @0x08008000: BLOCKED (StlinkException) - correct RDP1.
- CONTROL (VTOR->SRAM 0x20002000, planted NMI vector[0x08]=0x20004567): PC read back
  0x20004566 = planted value. => the NMI-pend-step-read-PC MECHANISM WORKS (harness
  correct). Also confirms get_reg('PC')/CortexM(swd) path is good.
- FLASH (VTOR->0x08008000): PC = 0xFFFFFFFE (run 1) / loop addr (run 2); real
  flash[0x08008008]=0x003c0002 NOT leaked. Vector fetch returns erase-pattern FF,
  not flash contents.
=> VERDICT: D1-B is BLOCKED on STM32F2. ST closed the data-bus/instruction-bus
   split that Obermaier exploited on F1. Consistent with ALL public Trezor-One (F2)
   attacks (Kraken, Joe Grand) using GLITCHING, never the exception trick.
   The non-glitch SWD readout path is a DEAD END on F2. Glitch remains the way.
   (Obermaier H3 = glitch+FPB shellcode is still genuine-ST-proven and is the
   coarse-power-cycle fallback if the precise UART glitch stays slow - not tested.)
Tool kept: d1b_exception_read.py (read-only; documents the dead end).

## 2026-11-01 (21:30) - D1-B variants EXHAUSTED: debug-attach locks ALL NV memory on F2

Ran d1b_variants_probe.py (3 angles). Mechanism-level result, not one data point:

P1 readability map @RDP1 over SWD:
  SRAM 0x20000000           -> READABLE (0x7ffeeb1d)
  system bootloader 0x1FFF0000 -> BLOCKED
  OTP 0x1FFF7800 / UID 0x1FFF7A10 -> BLOCKED
  user flash head 0x08000000 -> BLOCKED
  storage 0x08008000        -> BLOCKED
  => ONLY SRAM is debug-readable. Even the ROM bootloader is blocked. This is a
     GLOBAL non-volatile lock on debugger attach = Obermaier H3's premise holds on F2.
P2 access size: 8/16/32-bit all BLOCKED (no size bypass).
P3 running-CPU NMI vector-catch (core never pre-halted): NMI taken (SP dropped a
   full 0x20 exception frame) but flash vector fetch returned 0xFFFFFFFF -> PC
   0xFFFFFFFE. Same FF whether HALTED or RUNNING => the lock is tied to C_DEBUGEN
   (debugger attached at all), not to C_HALT.

CONCLUSION (strong, mechanism-level): every debugger-based flash read is dead on
F2@RDP1, because reading the result requires the debugger whose presence locks all
NV memory. D1-A/D1-B/D1-C/direct-read are ALL closed here. This is exactly WHY
Obermaier H3 exists and is the only genuine-ST method.

THE REAL ALTERNATIVE = H3 (glitch + FPB), and its "glitch" is a COARSE POWER CYCLE
(not a precise instruction-skip): load shellcode to SRAM via SWD (SRAM is writable),
detach, QUICK power-cycle to clear the debug flash-lock while SRAM remanence holds,
boot from SRAM, stage1 sets FPB to patch reset vector 0x00000004 -> stage2 SRAM,
RESET into "flash" -> FPB redirects -> stage2 dumps now-unlocked flash over UART.
The CW target_pwr MOSFET can do the fast power-cycle precisely. Non-destructive,
RDP1-safe. Substantial build (SRAM shellcode + FPB + boot sequencing) but the glitch
is far less timing-sensitive than our UART Read-Memory skip. = the path to evaluate
if the UART glitch stays slow. Tools: d1b_exception_read.py, d1b_variants_probe.py.

## 2026-11-01 (22:00) - H3 primitives: SRAM staging WORKS, remanence DEAD on this board

Ran h3_primitives.py + a floor/NRST follow-up to test an Obermaier-H3 SRAM-shellcode
path (no precise glitch). Results:

- P-WRITE: SRAM write+verify works 9/9 while flash is debug-locked. Shellcode CAN
  be staged in SRAM over SWD.
- P-REMAN: SRAM retention 0.00% at EVERY power-off duration tested (1,2,5,10,20,50,
  100,200,500 ms) AND at a near-instant back-to-back toggle (~tens of us). The core
  rail collapses instantly -> ZERO SRAM remanence. Cause: the glitch mods stripped
  the VCAP decoupling caps (the crowbar node), so the 1.2V core rail (which powers
  SRAM) has nothing to hold it. The mod that enables our glitch kills remanence.
- NRST pulse (reset, NO power loss): SRAM retention 100.00%. A pure reset preserves
  SRAM (and FPB config survives reset too).

THE H3 CONFLICT on this board (mutually exclusive):
  - preserve staged SRAM: only NRST does (100%); power-cycle wipes it (0%).
  - clear the debug flash-lock: Obermaier F1 says needs a POWER CYCLE; NRST does not.
  => can't have both here. H3-classic (power-cycle + remanence) is BLOCKED by the
     zero remanence; H3-via-NRST needs the lock to clear on reset (untested on F2,
     Obermaier says no on F1). Also BOOT1 is not wired to the CW (only BOOT0=TIO1),
     so SRAM-boot selection isn't controllable -> FPB-reset-vector-patch would be
     the only boot path, and the practice flash HEAD is blank (extra complication).

VERDICT: the non-glitch / coarse-glitch SWD avenues are effectively EXHAUSTED on
THIS practice board. Debug-read is globally locked; H3 needs remanence this board
cannot provide. Revisiting H3 would require restoring VCAP capacitance (losing
glitch capability) and wiring BOOT1 - i.e., a different board config. On the REAL
device the known path is still glitch-based (Kraken: glitch RDP then read SRAM that
already holds the running firmware's secrets; or our UART Read-Memory glitch).
Tools kept: d1b_exception_read.py, d1b_variants_probe.py, h3_primitives.py.

## 2026-11-01 (22:15) - CAPS ON: SRAM remanence UNBLOCKED (100% up to ~50ms)

User re-fitted the VCAP decoupling cap (as a jumper - toggleable). Re-ran
h3_primitives.py:
  1,2,5,10,20,50 ms power-off -> 100.00% SRAM retention (512/512)
  100,200,500 ms -> 0.00%
=> remanence window ~<=50ms (threshold 50-100ms). SRAM survives a power cut cleanly.
This is the make-or-break H3 primitive, now WORKING. (Caps-ON helps remanence but
damps the crowbar glitch - jumper lets us toggle: caps ON for H3, OFF for glitching.)

Remaining H3 architecture note: a DEBUGGER can never read flash at RDP1 (RDP1 blocks
it by design, power-cycle or not). H3 works by running CODE (not debugger) that reads
flash - at RDP1 the device's OWN code can read flash. To run SRAM code with no
debugger attached after the lock-clearing power-cycle requires SRAM-BOOT
(BOOT0=1,BOOT1=1) -> BOOT1 (PB2) must be controllable (currently only BOOT0=TIO1 is
wired). Obermaier flow: stage 2-stage shellcode in SRAM + set BOOT=SRAM; quick
power-cycle (<=50ms, clears debug flash-lock, SRAM survives); SRAM-boot runs stage1;
stage1 sets FPB to patch reset-vector 0x00000004 -> stage2, sets BOOT=flash, core
RESET (FPB+SRAM survive reset); boots "from flash" -> FPB redirects -> stage2 runs
with flash accessible -> dumps flash over UART. Next hardware need: wire BOOT1.

## 2026-11-01 (22:40) - SRAM-BOOT WORKS on F2; flash blocked from SRAM-boot (FPB needed)

Built h3_sramboot_test.py (arm-none-eabi toolchain available). BOOT pins confirmed:
TIO1=BOOT0, TIO2=BOOT1, TIO3=trigger, TIO4=NRST. Minimal SRAM-boot dumper test:
- Staged a 64B Thumb dumper at 0x20000000 (vector SP+reset, copy flash->SRAM scratch,
  markers), set BOOT0=1(TIO1)+BOOT1=1(TIO2), power-cycle 30ms, SRAM-boot, readback.
- ALIVE marker 0x1AA1AA1A SET -> SRAM-BOOT ENGAGED, code RAN. The whole chain works:
  power-cycle clears debug lock, SRAM survives (caps), BOOT0+1 high -> SRAM boot.
- Flash read (ldr [0x08008000]) FAULTED before any copy (done-marker unset, scratch
  100% sentinel). => code booted FROM SRAM cannot read flash at RDP1 on F2 (Obermaier
  F1 finding holds). Need the FPB boot-from-flash trick.

PRIMITIVES NOW ALL PROVEN: SRAM write (stage), remanence (caps, <=50ms), SRAM-boot
runs code, NRST preserves SRAM 100% (+ FPB survives NRST). Remaining: FPB.

FPB ATTACK PLAN (every step uses proven primitives + CW boot/NRST/power + SWD):
1. SWD: stage stage1(FPB cfg)+stage2(flash dumper)+remap table in SRAM.
2. BOOT0=1,BOOT1=1 (SRAM boot); detach SWD.
3. power-cycle ~30ms -> clear debug lock, SRAM survives.
4. SRAM-boot stage1: program FPB remap of reset-vector fetch 0x00000004 -> stage2
   addr; enable FPB; spin.
5. CW: BOOT0=0 (flash boot); pulse NRST (SRAM+FPB survive reset, NOT power-off).
6. boots "from flash" -> FPB redirects -> stage2 runs with flash ACCESSIBLE (flash-
   boot at RDP1 = normal op) -> copy flash storage -> SRAM scratch -> spin.
7. SWD reconnect (re-locks flash, but copy already done) -> read scratch.
Unknowns to validate: FPB remap correctness for the vector fetch; stage2 flash access
after flash-boot+NRST with no debugger. Tools: h3_sramboot_test.py (+ d1b_* earlier).

## 2026-11-01 (22:55) - FPB capability confirmed: remap supported, 6 code comparators

Read FPB on the F2: FP_CTRL=0x260 -> NUM_CODE=6, NUM_LIT=2. FP_REMAP RMPSPT(bit29)=1
-> REMAP SUPPORTED. CPUID=0x412fc230 (Cortex-M3 r2p0). So the Obermaier FPB reset-
vector redirect is feasible. FP_REMAP base encoding: write bits[28:5] = offset within
SRAM; hw implies 0x20000000 region (write 0x100 -> table at 0x20000100).
Plan: stage1 (SRAM-booted) sets FP_REMAP + FP_COMP0(addr0x0,remap)=0x1 +
FP_COMP1(addr0x4,remap)=0x5 + FP_CTRL=0x3; remap[0]=SP, remap[1]=stage2|1. Then NRST
with BOOT0=0 -> flash boot -> FPB redirects reset vector -> stage2 (flash-boot mode =
flash accessible) dumps 768B (chunks 0-2) -> scratch -> SWD readback.

## 2026-11-01 (23:05) - *** H3 FPB: DETERMINISTIC NON-GLITCH FLASH EXTRACTION WORKS ***

h3_fpb_attack.py ran FIRST TRY and fully succeeded:
  stage1-done OK, stage2-done OK, scratch head 4e524332faffffff02003c00... ,
  still-sentinel 0/192, FPB dump 768B == storage.bin[:768] BYTE-EXACT.
Then decrypt_storage.py --brute 0000-9999 on the FPB dump:
  *** PIN FOUND: <redacted> (49.9s) *** mnemonic "<12-word mnemonic redacted,
  in known-answer.json>" - both match known-answer.json.

=> The Obermaier-H3 FPB technique extracts flash on the STM32F2 at RDP1
   DETERMINISTICALLY, NO GLITCH, in ~2 seconds (+50s offline crack). Far superior
   to the probabilistic UART Read-Memory glitch for a chip already at RDP1.

Working recipe (all via CW + ST-Link, non-destructive):
  - caps ON (VCAP jumper) for SRAM remanence; BOOT0=TIO1, BOOT1=TIO2, NRST=TIO4.
  - stage stage1(FPB cfg @0x20000000)+stage2(dumper @0x20001000) in SRAM via SWD.
  - BOOT0=1,BOOT1=1; power-cycle 30ms (clears debug lock, SRAM survives).
  - SRAM-boot stage1: FP_REMAP=0x100 (table@0x20000100), remap[0]=SP remap[1]=stage2|1,
    FP_COMP0=0x1 (addr0 remap en), FP_COMP1=0x5 (addr4 remap en), FP_CTRL=0x3.
  - BOOT0=0; pulse NRST (SRAM+FPB survive) -> flash-boot -> FPB redirects reset
    vector -> stage2 reads flash (accessible in flash-boot mode) -> scratch.
  - SWD reconnect -> read 768B scratch. Tool: h3_fpb_attack.py.

REAL-DEVICE CAVEAT: this needs SWD to stage SRAM, so it requires the chip at RDP1.
If the real device is RDP2, SWD is fused off -> must first glitch RDP2->RDP1
(Joe Grand/Kraken style), THEN FPB replaces the per-chunk UART glitch grind.
At RDP1, FPB is the clean deterministic path. Two proven extraction methods now:
(1) UART Read-Memory glitch ~1/46 clean-zone; (2) H3 FPB deterministic no-glitch.

## 2026-11-01 (23:25) - Real device = RDP2, TRANSIENT RDP1 (per power-up) -> two-glitch path

User confirmed: real device is RDP2; the RDP2->RDP1 downgrade is TRANSIENT (must be
re-glitched every power-up; option byte stays 0xCC). Implications:
- FPB/H3 is RULED OUT for the real device: it needs a power-cycle (clears debug lock)
  which drops the transient RDP1 back to RDP2; plus caps conflict (FPB needs caps ON,
  crowbar glitch1 needs caps OFF). FPB stays our deterministic RDP1 technique/fallback.
- REAL-DEVICE ATTACK = TWO glitches per power-up (the rig's original design):
  glitch1 (VCAP crowbar during BootROM RDP read, ~180us after reset release) -> chip
  enters as RDP1, opens system bootloader/SWD that RDP2 denies; THEN glitch2 (UART
  Read-Memory glitch, our rehearsed campaign) -> reads flash storage -> offline crack.
- GATING UNKNOWN: glitch1 (glitch1_rdp2_to_rdp1.py) is WRITTEN but NEVER TESTED - the
  practice chip has been RDP1 all session so glitch1 was never needed. Next: rehearse
  glitch1 on the practice chip (set RDP2, caps OFF, success=SWD enumerates).
- Possible shortcut (not yet rehearsable here): glitch1 + SWD SRAM dump (SRAM readable
  at transient RDP1, no power-cycle) could grab hardware_salt (.bss) + any cached
  encrypted storage from the RUNNING firmware's SRAM = Kraken-style, single glitch.
  Needs real Trezor fw on the practice chip to validate (practice SRAM has no fw now).

## 2026-11-01 (23:45) - practice chip COMMITTED TO RDP2 (irreversible) - now a real-device target

User authorized committing the practice chip to RDP2 (ordering STM32F205RET6 spares
from Mouser for future RDP1-flexible work). set_rdp2.py (G_PRACTICE_BOARD=YES
G_CONFIRM_RDP2=IRREVERSIBLE):
- pre: OPTCR 0x0FFF55ED (RDP 0x55 = RDP1), SWD healthy, storage byte-exact (FPB read
  earlier this session, no flash writes since).
- wrote RDP 0xCC; DP dropped during OPTSTRT (expected); post power-cycle SWD attach
  FAILED == RDP2 CONFIRMED. Debug port + system bootloader now permanently off.
- Planted storage survives (RDP1->RDP2 is a protection INCREASE, no mass-erase).
The chip now mimics the real production Trezor (RDP2, SWD fused off). ONLY entry
path = glitch-1 (transient RDP2->RDP1 per power-up).

NEXT: rehearse glitch-1 (glitch1_rdp2_to_rdp1.py). Requires caps OFF (crowbar needs
fast VCAP collapse; caps are currently ON from the FPB remanence work). Defaults:
clkgen 100MHz, ext 17000-18900 (170-189us after reset release), rep20, offset -45,
BOOT0 low, success = SWD enumerates. First real test of the RDP2->RDP1 downgrade on
this bench (glitch-1 was written but never needed while the chip was RDP1).

## 2026-11-02 (01:15) - *** GLITCH-1 (RDP2->RDP1) WORKING + REPRODUCIBLE ***

New script glitch1_bootloader.py: POWER-ON trigger + BOOT0-HIGH + UART-ACK detect.
Cracked glitch-1 after the inherited NRST / 170-189us approach gave 0 hits across
many passes. Three corrections (all user-driven):
1. POWER-ON trigger (not NRST): cold power-cycle each shot; the chip's internal POR
   drives NRST low then releases -> CW triggers on that POR-release edge = t=0 (the
   mkesenheimer VCAP-rise / cold-boot frame). The RDP option-byte latch happens at
   POWER-ON, which NRST-reset-with-power-held-on never exercised.
2. "Start at 0": the downgrade window is VERY EARLY - ext ~2.6-4.6us after POR-
   release (260-460 cycles @100MHz), NOT ~170us. Every prior sweep started at
   170us and missed it entirely.
3. BOOT0-HIGH + UART-ACK: aim at the system bootloader (RDP2 FORBIDS it). Success =
   bootloader autobaud 0x7F -> 0x79 ACK. Faster/cleaner than SWD and it's the real
   glitch-1 -> glitch-2 configuration.

VERIFIED REAL (not a false positive):
- CONTROL (crowbar disarmed, BOOT0 high, no glitch): 0/6 ACK, bootloader SILENT ->
  RDP2 confirmed (bootloader genuinely blocked without a glitch).
- GLITCH sweep (ext 0-600 / 0-6us, step 10, 4 samples, 207 shots): 6 ACKs at ext
  260/290/400/410/430/460 (2.6-4.6us) -> glitch-induced, reproducible. Concentrated
  in the ~2.6-4.6us window.

Params: clkgen 100MHz, enable_only hp+lp, offset -45, repeat 20, power-off 60ms,
settle 60ms, BOOT0=TIO1 high, BOOT1=TIO2 low, NRST=TIO4 (POR-release trigger), UART
/dev/ttyUSB0 115200 8E1. Success leaves the chip in the RDP1-behaving bootloader
(power held), ready for glitch-2 (Read Memory). Caps OFF (crowbar).
Next: camp the hot window ~2.6-4.6us for a higher hit rate, then chain glitch-2.

## 2026-11-02 (01:40) - glitch-1 RDP1 HOLDS THROUGH NRST -> FPB-after-glitch-1 viable

test_rdp1_holds_nrst.py: glitch-1 (power-on, BOOT0 low, ext camped 240-480) opened
SWD on shot #2 (ext=460): IDCODE=0x2ba01477, OPTCR=0x0fffffed, RDP=0xff. The glitch
corrupts the option-byte LOAD to all-1s (0xff -> not 0xAA/0xCC -> RDP1 behaviour).
Then pulsed NRST (power held, NO power-cycle) and re-checked SWD:
  *** SWD STILL UP, OPTCR still 0x0fffffed (RDP=0xff) ***
=> the glitched RDP1 state HOLDS through an NRST. Option bytes are NOT re-loaded on
   a pin reset (only on power-on) - consistent with why glitch-1 needs a power-on
   trigger. Only a full power-cycle re-asserts RDP2.

IMPLICATION: FPB-after-glitch-1 is VIABLE without the power-cycle (and so without
the caps conflict): glitch-1 -> RDP1+SWD -> stage SRAM dumper + FPB via SWD -> NRST
(RDP1 + SRAM + FPB all survive) -> flash-boot -> FPB redirect -> stage2 reads flash
as own-code (allowed at RDP1) -> UART/scratch dump. ONE glitch-1 then DETERMINISTIC.
Remaining unknown: does the SWD-attach debug-lock clear on detach+NRST (vs needing
a power-cycle, as on F1) so stage2's flash read succeeds - the full FPB-after-glitch1
run will answer it. Also: glitch-1 SWD-open is fast here (#2 shot in the camped window).

## 2026-11-02 (02:00) - FPB-after-glitch-1 CONFIRMED NOT VIABLE (debug-lock needs power-cycle)

glitch1_fpb_chain.py (full run x2): glitch-1 -> SWD open (RDP1) -> stage stage2 +
FPB over SWD -> clear C_DEBUGEN, detach -> NRST (power held) -> flash-boot -> FPB
redirect. Results both runs:
- glitch-1 opened SWD (#21, then #81 - probabilistic but lands).
- SWD direct read of 0x1FFF0000: BLOCKED (debug-locked) - baseline confirmed.
- FPB redirect WORKED: stage2 ALIVE marker 0x1AA1AA1A set -> the reset-vector remap
  (0x4->stage2) fired after NRST at glitched-RDP1. (FPB config via SWD survives NRST.)
- stage2 then FAULTED on the first flash read (ldr 0x1FFF0000): DONE marker unset,
  scratch still sentinel (nothing read).
=> the debugger-induced flash-lock (from SWD staging) does NOT clear on detach+NRST;
   it needs a full POWER-CYCLE (Obermaier F1 behaviour holds on F2). A power-cycle
   re-asserts RDP2 (glitch-1 is transient) AND loses SRAM without caps. So FPB-after-
   glitch-1 is MUTUALLY EXCLUSIVE and NOT VIABLE for the real RDP2 device.

(Self-correction: the script's first verdict printed a false "WORKS" due to a mismatched-
length byte comparison; corrected - the data always showed the faulted read.)

VALIDATED ALONG THE WAY (reusable facts): glitch-1 opens SWD in the ~2.4-4.8us window;
glitched RDP1 + SRAM + FPB config all SURVIVE an NRST (only power-off re-latches options /
clears FPB / clears the debug-lock); FPB reset-vector remap set via SWD works.

CONCLUSION: real RDP2 device -> GLITCH-2 CHAIN is the path (glitch-1 opens the bootloader,
glitch-2 Read Memory). FPB stays the deterministic STABLE-RDP1 technique only.
Tools: glitch1_fpb_chain.py, test_rdp1_holds_nrst.py, glitch1_bootloader.py.

## 2026-11-02 (02:15) - FPB-after-glitch-1 negative CONFIRMED, confound removed

Re-ran glitch1_fpb_chain.py with stage2 reading USER FLASH 0x08000000 FIRST (prior
test read the system ROM first and faulted there - a confound). Result (#71 SWD open):
stage2 ALIVE set, but FAULTED on the ldr 0x08000000 (MARK_A never written, user-flash
AND rom scratch both still sentinel). => the debug-lock blocks own-code reads of USER
FLASH too, not just the system ROM - the negative is unconfounded. Lock needs a
power-cycle (F1 behaviour on F2); power-cycle re-asserts RDP2. FPB-after-glitch-1 is
definitively OUT for the real RDP2 device.
Only untried FPB angle left: fully power down the debug access port (DP CTRL/STAT
CDBGPWRUPREQ/CSYSPWRUPREQ) before detach, in case clearing C_DEBUGEN alone isn't
"detached" enough to drop the lock - long shot. Otherwise: glitch-2 chain.

## 2026-11-02 (02:30) - FPB-after-glitch-1 EXHAUSTED: even proper exit_debug() doesn't clear the lock

Last untried lever: swd.stlink.Stlink has NO __del__/close, so `del st` never issued
exit_debug - the DP stayed powered and the chip still saw a debugger. Added an
explicit st._com.exit_debug() (real detach, DP de-asserted) before NRST. Result
(#234 SWD open): exit_debug issued OK, stage2 RAN (ALIVE set, FPB redirect worked),
but STILL FAULTED on the user-flash read (MARK_A unset, scratch sentinel).
=> the debugger flash-lock does NOT clear on a proper debug-exit + NRST either. It
   genuinely needs a full POWER-CYCLE (Obermaier F1 behaviour, fully confirmed on F2).
FPB-after-glitch-1 is EXHAUSTIVELY ruled out: every lever tried (C_DEBUGEN clear,
exit_debug, user-flash-first, multiple runs). Power-cycle clears the lock but
re-asserts RDP2 (glitch-1 is transient) -> mutually exclusive. DONE with FPB for RDP2.
(glitch-1 hit rate is variable: SWD opened at shots #2/#21/#71/#81/#234 across runs.)
REAL-DEVICE PATH = glitch-2 chain (glitch-1 opens bootloader; glitch-2 Read Memory).

## 2026-11-02 (02:12) - OVERNIGHT two-glitch recovery launched (self-healing)

glitch_chain_overnight.py running unattended for full recovery by morning. Flow:
glitch-1 (power-on, BOOT0 high, ext 2.4-4.8us) -> bootloader; then glitch-2
(trigger 0x11 burst, ext 179-184us hot zone, rep 3-4 = 30-40ns @100MHz) Read-Memory
flip. Collects PER CHIP: storage chunks 0/1/2 (memory ranges) + uid (0x1FFF7A10) +
otp3 (0x1FFF7860) + SRAM dump (0x20000000, 64 chunks/16KB) - all via glitch-2
Read-Memory, latch-draining remaining targets on each flip. uid/otp3 READ FROM CHIP
(not hardcoded) and used for the offline PIN brute (decrypt_storage.py). Writes
dumps/overnight/RECOVERED.txt on PIN found. Self-healing: catches CW/FTDI dropouts,
USB-resets the CW (2b3e) + reconnects; __main__ self-restarts on fatal errors;
resumes collected chunks from dumps/overnight/ across restarts.
Same chip as the campaign/FPB dumps (now RDP2), so glitch-2 hot zone is known-good.
Open risk: 100MHz clkgen vs original 166.67MHz (us window + 40ns pulse transfer, but
glitch may behave slightly differently); if no ACK flips by morning, re-home both
phases at 166.67MHz. Launched via managed background (persists with the session).

## 2026-11-02 07:17 — OVERNIGHT two-glitch chain: 0 bootloader opens in ~9000 shots (glitch-1 REGRESSION)

`glitch_chain_overnight.py` ran clean 02:11 -> 07:17 (self-healing, no crashes,
no errors, re-homed get_bootloader at the 6000-shot cap ~07:07). Params were
BYTE-IDENTICAL to the proven glitch-1 set: 100 MHz clkgen, enable_only hp+lp,
width40, offset -45, repeat 20, ext 240-480 (2.4-4.8us), power-off 60ms,
BOOT0=TIO1 high, BOOT1=TIO2 low, POR trigger on TIO4. Caps OFF.

RESULT: **0 bootloader ACKs across ~9000 power-on shots.** Zero 0x7F->0x79.
Never reached glitch-2. dumps/overnight/ empty, no RECOVERED.txt.

Interpretation: earlier this campaign glitch-1 opened the bootloader at ~1/35
(207 shots -> 6 ACKs) with these exact params. 0/9000 at the same params is not
a tuning miss — p(chance) ~ 0. This is a **physical/environmental regression**
between the proven run and overnight. Ranked suspects:
  1. CRACKED CW SMA jack (already flagged in siglent-scope skill: glitch output
     path attenuates ~1000:1 when the jack is cracked -> crowbar barely pulls
     VCAP -> chip boots normally into RDP2 every shot, bootloader stays dead).
     This is the single most likely cause and matches the symptom exactly.
  2. A crowbar / BOOT0 / NRST dupont lead worked loose overnight.
  3. POR-release edge on TIO4 not being caught -> scope never fires the pulse.
DECISIVE DIAGNOSTIC (next): scope on the glitch node (Ch1, catch-B: 1MV/div,
TDIV 100NS, TRSL NEG, TRLV -1.5MV, SINGLE), fire a few glitch-1 shots, confirm
the crowbar pulse is actually present on VCAP. If flat -> cracked SMA / loose
crowbar lead. If present -> re-home the window at 166.67MHz.
Chain left RUNNING pending the user's call on pausing for the scope check.

## 2026-11-02 07:30 — ROOT CAUSE: socketed chip is at STABLE RDP1, not RDP2. glitch-1 regression explained.

After the proven glitch1_bootloader.py ALSO returned 0 ACKs (rig-state, not
script), measured the chip directly over SWD with NO glitch:
  ST-Link ATTACHES. IDCODE=0x2ba01477. OPTCR=0x0fffffed (read 3x identical)
  -> RDP byte 0xFF = **RDP LEVEL 1**.
  flash 0x08000000/0x08008000 BLOCKED, UID 0x1FFF7A10 BLOCKED,
  SRAM 0x20000000 = 0x6ff6ff3d (reads), RCC 0x40023800=0x00000f83 (reads).
This is textbook RDP1: debug attaches, SRAM+peripherals read, flash+OTP locked.
NOT RDP2 (at RDP2 the SWD-AP is fused off -> no attach, no OPTCR read at all);
NOT RDP0 (flash would read).

CONSEQUENCE / why glitch-1 "stopped working": glitch-1 is an RDP2->RDP1
downgrade. The chip is ALREADY at RDP1, so there is nothing to downgrade and no
bootloader-via-glitch event to catch -> 0 ACKs is the CORRECT behaviour, not a
broken rig. The board was never touched; the TARGET STATE is what differs from
the earlier runs.

IMPLICATION for RDP2 narrative: RDP2 is irreversible (no RDP2->RDP1 path). If
this chip reads RDP1 now, set_rdp2.py never actually committed 0xCC (silent
fail / OBL_LAUNCH not taken). So the earlier "glitch-1 RDP2->RDP1 cracked" was
NOT validated against a genuine RDP2 target -- flag for the real-device plan.

PIVOT: at stable RDP1 the proven no-glitch FPB (Obermaier-H3) flash dump applies
(h3_fpb_attack.py, dumps storage chunks 0-2 @0x08008000). UID+OTP3 for the PIN
brute are ALREADY KNOWN for this chip (uid=3e0031001547333032303138,
otp3=ff*32). So: FPB-dump storage -> offline brute -> PIN+mnemonic, no glitching.
(Caveat: FPB H3 needs VCAP caps ON for SRAM remanence across its ~30ms
power-cycle; crowbar campaign ran caps OFF. If caps are off the tool fails
cleanly at the remanence step -> then caps must go back on.)

## 2026-11-02 07:33 — FPB-at-RDP1 attempted; blocked ONLY by caps-off (remanence 0%). Clear path to finish.

Ran h3_fpb_attack.py against the RDP1 chip: staged OK, but after the 30ms
power-cycle stage1-done NOT SET, scratch = random uninitialised SRAM
(0/192 sentinels) -> SRAM did not survive the POR. Confirmed with a clean
remanence sweep (write 8-word pattern via SWD, power-cycle, read back):
  off  20ms -> 0/8 survived
  off  30ms -> 0/8
  off  50ms -> 0/8
  off 100ms -> 0/8
=> VCAP decoupling cap is currently OFF (crowbar config). SRAM remanence 0% at
all tested off-times. FPB H3 needs SRAM to persist across its ~30ms clear-lock
POR, which requires the cap ON (earlier: 100% <=50ms with caps on).

STATUS: one physical action away from recovery. Re-fit the VCAP cap (the one
lifted for crowbar injection; crowbar no longer needed - chip is RDP1, not
RDP2). Then: h3_fpb_attack.py dumps storage chunks 0-2 -> offline PIN brute with
the already-known uid=3e0031001547333032303138 / otp3=ff*32 -> PIN + mnemonic.
No glitching required. (Caps-on will damp the crowbar, which is fine; the
crowbar/glitch path is not needed for this chip.)

## 2026-11-02 07:36 — Confirmed PERSISTENT RDP1 via deliberate cold boots (caps-on will NOT resurrect RDP2)

User concern: re-fitting VCAP cap + restart would charge caps and revert chip to
RDP2 (i.e. current RDP1 is a transient glitch state). Disproven directly: with
NO glitch output and no boot-pin forcing, cut target_pwr for 600ms then 1000ms
(full discharge cold boots) and re-read over SWD each time:
  before / cold#1(600ms) / cold#2(1000ms): ALL -> SWD ATTACHED, OPTCR=0x0fffffed,
  RDP=0xff = LEVEL 1, flash blocked. Identical every time.
A transient glitch-RDP1 cannot survive a 1s full-discharge cold boot; RDP2 would
show SWD attach FAIL. => stored option byte genuinely 0xFF (persistent RDP1);
set_rdp2 never committed 0xCC. RDP level is latched from flash option bytes at
every POR; the cap affects rail ramp/SRAM-remanence/crowbar damping only, NOT
the latched value. Re-fitting the cap is safe: cannot create a 0xCC that is not
in flash. Waiting on user to re-fit VCAP cap, then FPB dump.

## 2026-11-02 08:05 — SOCKETED PRACTICE CHIP IS A CLONE (RDP2 not implemented). Major.

Chased why set_rdp2 never commits. Found the real cause via halted-core probing
and OpenOCD, then chip ID:

Programming behaviour (both swd-python AND OpenOCD):
 - With core RUNNING (BOOT0 high bootloader), OPTCR[15:8]<-0xCC silently does not
   hold (bootloader stomps option regs). This is why the OLD set_rdp2 (which
   attached in bootloader mode, never halted) no-op'd every time.
 - With core HALTED (swd cm.halt()), register ACCEPTS 0xCC (readback 0x0fffccec),
   but OPTSTRT set SR=0 (no BSY, no program) -> RDP stays 0xff.
 - With OpenOCD `reset halt` (clean halt-at-reset), OPTSTRT DID assert BSY
   (SR=0x00010000) = a real option program cycle ran, DP then dropped (looked
   like RDP2 activating). BUT after a full cold boot: SWD attaches 6/6,
   OPTCR=0x0fffffed, RDP=0xff -> STILL RDP1. 0xCC never persists in option flash.

Chip identity (the tell):
   DBGMCU_IDCODE 0xE0042000 = 0x200f6411  -> REV_ID=0x200F, DEV_ID=0x411
   DAP IDCODE=0x2ba01477, CPUID=0x412fc230 (generic CM3, clones copy these).
   Genuine STM32F205 REV_IDs are ONLY 0x1000/1001/2000/2001/2003/2007.
   0x200F is NOT an ST rev_id.

CONCLUSION: the socketed part is a CLONE STM32F2 (GD32/APM32/CKS-class). Clones
implement RDP Level 1 (SWD flash lockout) but NOT genuine Level 2 - the 0xCC
fuse state is not in silicon, so option program reverts to 0xff (= L1). Hence:
RDP2 cannot be set on this chip by any tool; "glitch-1 RDP2->RDP1" was never
validated (no RDP2 target ever existed); last night's "RDP2 confirmed" was the
old verify's false positive.

CONSEQUENCES:
 - This clone is UNUSABLE as an RDP2 / glitch-1 practice target. It remains fine
   for RDP1 work already proven on it (glitch-2 Read-Memory, FPB H3 dump).
 - The real Trezor is a GENUINE ST STM32F205 at RDP2. Validating the glitch-1
   step REQUIRES a genuine ST chip set to RDP2. Rig notes mention genuine ST
   STM32F205RET6 (LQFP64) on hand (vs the Waveshare QFP64 clone board) - plant
   storage on a GENUINE ST part, set_rdp2 (now halt-core-correct) on THAT.
 - set_rdp2.py has been fixed: correct level decode (0xAA=L0/0xCC=L2/else=L1),
   ST-Link USB reset, and it now needs a clean halt. For genuine parts, drive
   the program via OpenOCD `reset halt` (asserts BSY) rather than cm.halt() on a
   running bootloader.

## 2026-11-02 08:20 — UART bootloader silent at RDP1 after the replug (SWD still solid)

User chose: keep the clone, practice glitch-2/FPB at RDP1. Pre-check the UART
path WITHOUT glitching (plain power-on, BOOT0=TIO1 high, 0x7F autobaud):
 - 8 cold boots @60ms, then 5 @150/300ms, then 1s of 0x7F spam -> ZERO bytes.
Bootloader was reachable earlier this campaign on THIS chip (glitch-2 Read
Memory + FPB both worked at RDP1), so 0 bytes now = physical: BOOT0 (TIO1) and/or
FTDI TX/RX leads disturbed during the full unplug/replug the RDP-state test
needed. SWD, by contrast, is rock-solid (OPTCR read all morning).
=> glitch-2 path is blocked until UART/BOOT0 wiring is restored. FPB over SWD
needs no UART and is proven byte-exact, but needs the VCAP cap re-fitted (caps
currently OFF: remanence 0/8). Recommend FPB (SWD-based, reliable) unless the
user wants to re-verify the UART/BOOT0 leads for glitch-2 practice.

## 2026-11-02  UART-dead triage — fault isolated to chip-side USART jumpers (SWD/host/CW all proven good)

Chip sat untouched overnight; user asked for full sanity checks. Results:

- **Chip ALIVE, RDP1, unchanged overnight.** verify_rdp2.py: SWD attaches 6/6
  clean, IDCODE=0x2ba01477, OPTCR=0x0fffffed (RDP byte 0xFF = L1). SRAM +
  peripheral reads fine; flash/info/ROM/core-register reads BLOCKED (RDP1
  signature). Still the clone (REV_ID 0x200F).
- **CW power + GPIO drive PROVEN.** Drove TIO3 low -> LA D0 went 100% low;
  TIO3 high_z + FTDI idle -> D0 high; FTDI spam -> D0 carries 0x7F. So the CW
  output stage is alive and physically reaches the chip-RX breadboard row
  (the row shared by TIO3 + LA D0 + QFP RX, per 2026-10 scope notes).
- **Host TX PROVEN at the chip-RX row.** uart_spam.py (BOOT0 high, crowbar
  off, full power cycle, spam 0x7F @115200 8E1). LA capture (4 MHz, 8 ch):
  ONLY D0 moves (host 0x7F, idle-high). D1 (chip TX) + D2-D7 FLAT HIGH, zero
  edges. 0 bytes read back by FTDI.
- **Chip TX (LA D1) totally silent** across all tests. Chip is not responding.
- **SWD cannot read boot mode at RDP1 on this clone.** reset_halt + get_reg
  returns SP/PC/LR = 0xFFFFFFFC/FE/FF regardless of BOOT0 level (core-register
  readback is blocked, same as code/flash). So "is it in the bootloader?"
  cannot be answered in software here. (An earlier bare halt once returned
  SP=0x20000FE0 at BOOT0=1 but it is not reproducible -> treat as noise.)

INTERPRETATION / ISOLATION:
  Everything on the host/CW/SWD side is good: power, ground, NRST, SWDIO/SWCLK
  (SWD works => those pins + Vdd + Vss are all connected), CW GPIO drive, and
  the host 0x7F is present at logic levels on the chip-RX row. The ONLY
  unproven links are the last-inch QFP USART jumpers that SWD cannot see:
    (1) chip-RX row  -> actual USART RX pin (PA10), and
    (2) USART TX pin (PA9) -> LA D1 / FTDI RX.
  One or both were disturbed in the big unplug/replug the RDP-state tests
  required. (The 126 mV "attenuated RX" from Oct was a cracked-SMA SCOPE
  artifact, NOT the real line — the LA sees a clean rail-to-rail 0x7F.)
  Secondary hypothesis kept on file: the OpenOCD option-byte program cycle
  (BSY asserted) during the RDP2 attempts *might* have perturbed the clone's
  boot config, but a faithful F2 clone honours BOOT0 as a pure pin and OPTCR
  reads normal, so this is lower-probability than a jumper.

NEXT: glitch-2 is blocked until D1 shows a 0x79. Fastest confirm = scope
directly on the QFP RX and TX pins. Alternative that needs NO UART: the
SWD-only FPB dump (h3_fpb_attack.py), which rides the one rock-solid channel
(needs VCAP caps ON for the remanence step).

## 2026-11-02  60s cold power-down retest — NO change (rules out transient latch)
User asked to shut the rig down 1 min and retry. Target_pwr off + all TIO
high_z for 60s, then re-power into bootloader (BOOT0 high) + spam 0x7F + LA.
Result identical: FTDI reads 0 bytes; LA D0 (host TX) carries 0x7F (52 edges,
idle high), D1 (chip TX) + D2-D7 flat, zero edges. A full cold cycle does NOT
revive the UART => not a transient/latched state; persistent physical cause at
the chip-side USART pins (or boot config). Decision pending: scope QFP TX pin
vs run SWD-only FPB dump.

## 2026-11-02  RDP change IMPOSSIBLE on this clone — confirmed 3 ways; "RDP2 yesterday" was a false positive
User recalled setting RDP2 yesterday. RECONCILED: the OLD committed set_rdp2.py
(git a6f33b0) verify block printed "RDP2 CONFIRMED" on ANY exception during the
SWD re-attach (`except Exception: ... == RDP2 CONFIRMED`) — fired on the routine
errno-5 USB wedge after a CW power cycle, NOT on a burned fuse. It also had
RDP_L1=0x55 hard-coded (wrong; L1 reads 0xFF). Both bugs fixed this morning.
LIVE state (rdp_state.py, cold boot): ST-Link attaches, IDCODE 0x2BA01477,
OPTCR 0x0FFFFFED, RDP byte 0xFF=LEVEL 1, SRAM 0x20000000 readable, FLASH
0x08000000 BLOCKED. Textbook RDP1 — impossible output at true RDP2.
RDP1->RDP0 attempts (all FAIL, chip won't commit any RDP option change):
  - OpenOCD reset-halt + unlock + stage RDP=0xAA (reg accepted 0x0fffaaec) +
    OPTSTRT -> SR=0x00000000 (no BSY, no program), reverts to 0xFF.
  - set_rdp0.py x2 (swd, no halt) -> OPTCR after write still 0x0FFFFFEC (RDP
    byte never even staged 0xAA), RDP still 0xFF after power cycle -> aborts.
CONCLUSION: the clone enforces RDP1 read-lockout but its option-byte PROGRAM
path is dead for RDP (0xCC and 0xAA both silent no-ops). Cannot reach RDP0 or
RDP2 via SWD. The only erase this chip honours (per set_rdp0 notes) is the UART
bootloader Extended-Erase 0x44 -> everything converges on reviving the UART.

## 2026-11-02  UART: NOT wiring — boot mode + all pins proven good over SWD; bootloader mapped but silent
Scope link was down (interface DOWN, needs sudo/power), so diagnosed entirely
over SWD by driving/reading chip GPIO & boot-latch registers. All PROVEN good:
  - TX pin PA9: drove it as GPIO output over SWD (halt, RCC_AHB1ENR|=1, MODER
    PA9=output, toggle BSRR ~10Hz) -> LA D1 followed (18 edges), nothing else.
    => chip TX pin -> D1/FTDI-RX path INTACT.
  - RX pin PA10: drove PA10 as GPIO -> LA D0 (the host-0x7F row) followed (48
    edges). => chip RX pin <- RX row INTACT; host 0x7F does reach PA10.
  - BOOT1 (=PB2): read via GPIOB_IDR while toggling CW TIO2 -> PB2 = 0/1/0
    exactly follows TIO2. BOOT1 correctly 0.
  - BOOT0 (dedicated pin, not GPIO-readable): read SYSCFG_MEMRMP.MEM_MODE
    (reports memory mapped at 0x0 by the boot-pin latch) while toggling CW
    TIO1 -> BOOT0=1 => MEM_MODE=1 (system BOOTLOADER), BOOT0=0 => MEM_MODE=0
    (main flash), repeatable. => TIO1 reaches BOOT0 and correctly selects the
    system bootloader.
Confound noted: with ST-Link attached the core is caught halted at the reset
vector, so RCC clock-enable fingerprint reads all-zero in every mode (incl.
free-running 2s at BOOT0=0) and is NOT a usable running-state signature here.
Also: storage-sim "firmware" may be a storage plant without a bootable vector
table, so RCC=0 at BOOT0=0 does NOT prove flash erased.
NET: UART silence is NOT wiring and NOT boot mode. The ROM bootloader is
correctly mapped on BOOT0 high but does not answer 0x7F autobaud (free-running,
no debugger). Suspect the bootloader itself went non-responsive after today's
RDP2/OpenOCD/set_rdp0 option-program attempts, or a clone quirk. Next: careful
free-running sync retry w/ baud sweep; else pivot to SWD-only FPB dump.

FREE-RUN SYNC SWEEP: 0x7F @ 115200/57600/38400/19200/9600/230400 8E1, fresh
power-cycle each, BOOT0 high -> 0x79 at NONE. Chip TX (LA D1) stays silent =>
bootloader transmits nothing. Confirms ROM bootloader non-responsive despite
correct boot mode + wiring.

## 2026-11-02  SWD-only FPB extraction SUCCESS — storage dumped byte-exact, no UART/glitch
With the UART bootloader internally dead and the clone stuck at RDP1, pivoted
to the SWD-only Obermaier-H3 FPB route. caps ON. h3_fpb_attack.py:
  stage1=84B stage2=52B, IDCODE 0x2ba01477, RDP 0xff.
  SRAM boot (BOOT0=1/BOOT1=1) 30ms power-cycle -> stage1 set FPB (done 0x51A1E001)
  flash boot (BOOT0=0) + NRST pulse -> FPB reset-vector remap -> stage2 ran
  (done 0xD09ED09E), copied 192 words from 0x08008000 -> scratch.
  still-sentinel 0/192; scratch head 4e524332faffffff02003c00ffffffff ==
  flash truth; full 768B == storage.bin byte-exact.
  -> dumps/fpb_storage_0_2.bin.
PROVES: (1) storage is INTACT (not erased by today's option attempts);
(2) the SWD-only FPB dump is the reliable extraction path on this chip while
the UART bootloader is non-responsive; (3) glitch-2 is not needed to get the
secrets off this RDP1 chip. Caps must be ON (SRAM remanence across the 30ms gap).

## 2026-11-02  END-TO-END on FPB dump: PIN + mnemonic recovered, matches known-answer
decrypt_storage.py dumps/fpb_storage_0_2.bin --brute 0000-9999
  --uid 3e0031001547333032303138 --otp3 ff*32
  -> parsed 10 NORCOW entries, version 4; PIN FOUND: <redacted> (58.3s);
     entry 0102 mnemonic "<12-word mnemonic redacted, in known-answer.json>".
     Both match known-answer.json exactly.
COMPLETE: SWD-only FPB extraction -> offline decrypt -> PIN+mnemonic, with NO
UART bootloader and NO glitch. This is the working recovery path on this RDP1
chip given the dead bootloader. (768B chunks 0-2 is sufficient: it carries the
EDEK, salts and the encrypted mnemonic entry.)

## 2026-11-02  New socketed chip: alive, clone RDP1 (NOT RDP2), FPB works, storage BLANK
User swapped in "a trezor-type RDP2" chip. Read-only characterization:
  - ST-Link attaches, Target voltage 3.26V, Cortex-M3 detected, SRAM reads.
    => ALIVE. (At true RDP2 SWD could not attach at all.)
  - DAP IDCODE 0x2BA01477; DBGMCU_IDCODE 0x200F6411 REV_ID 0x200F (same non-ST
    clone fingerprint as the previous chip); OPTCR 0x0FFFFFED RDP 0xFF = LEVEL 1;
    FLASH 0x08000000 blocked (RDP1). => clone at RDP1, NOT RDP2.
  - VCAP: needed caps on BOTH VCAP pins. Flash-boot remanence sweep read 0%
    clean-zero (this chip's firmware clears SRAM on reset - it has running fw,
    unlike the prev empty clone). SRAM-BOOT remanence test = 100% @ 5/10/20ms,
    confirming SRAM retains fine with both caps.
  - h3_fpb_attack.py: stage1-done 0x51A1E001, stage2-done 0xD09ED09E (both ran),
    scratch head = ffffffffffffffffffffffffffffffff => storage sector 0x08008000
    is ERASED/blank on this chip. FPB mechanism WORKS; just no NORCOW data.
  - Confirms it is a DIFFERENT physical chip than the PIN-<redacted> part (that read
    NRC2 data; this reads all-FF). The swap took.
NET: alive new clone at RDP1 with blank storage. Not a provisioned RDP2 target.
For genuine RDP2 / glitch-1 validation still need the real ST STM32F205RET6.

## 2026-11-02  Full READ-ONLY dump of the "chip pulled from a trezor" — firmware present, storage BLANK
fpb_fulldump.py (chunked FPB, 8x64KB, OFF_MS=30, both VCAP caps on). READ-ONLY:
SRAM-stage + power/boot/NRST toggles only, no flash/option writes.
  - IDCODE 0x2ba01477, RDP 0xff (clone REV_ID 0x200F at RDP1, SWD open).
  - FLASH 512KB -> dumps/flash_fulldump.bin (all 8 chunks stage2-done OK).
  - SRAM 128KB -> dumps/sram_fulldump.bin (459 non-zero bytes; fw clears SRAM).
Analysis:
  - Bootloader sectors 0x08000000/0x08004000 populated; TRZR magic @0x806b744;
    strings TREZOR/SatoshiLabs/bootloader/PIN present => genuine Trezor(-type) fw.
  - Firmware 0x08010000..0x0807FFFF ~98% populated.
  - Storage sectors 0x08008000 AND 0x0800C000 = 0/16384 non-FF = FULLY ERASED.
  - NRC2 @0x08049bd8 + NRCW @0x08049c90 are firmware compiled-in constants (mid
    code, not a sector boundary), NOT live NORCOW storage.
VERDICT: no PIN/seed/wallet on this chip - NORCOW storage unprovisioned or
wiped. Nothing to recover here. read_mem32 block reads (<=1024B/4-aligned)
make full dumps fast; read_mem8 caps at 64B.

## 2026-11-02  GENUINE RDP2 target seated (user's test backup, wallet set up last night)
User swapped in a Trezor backup provisioned last night. Characterization:
  - CW powers it: ST-Link VTREF = 3.25V (3.3V rail present at chip).
  - OpenOCD: "init mode failed (unable to connect to the target)" - NO DAP, no
    Cortex-M3 detected. swd.stlink attach FAILED 3/3 (consistent, not transient).
  - No USB enumeration (target USB not cabled to host on this rig).
Same rig/socket attached every RDP1 clone instantly -> wiring good -> a powered
chip with a dead debug port = genuine RDP LEVEL 2. This is the real locked
Trezor target (first true RDP2 part this campaign has had).
IMPLICATIONS:
  - SWD/FPB extraction (the clone path) is IMPOSSIBLE at RDP2 - debug fused off,
    cannot stage shellcode or read flash/SRAM.
  - System bootloader is also disabled at RDP2 -> UART Read-Memory unavailable.
  - ONLY entry = glitch-1 (crowbar voltage glitch at boot -> transient RDP2->RDP1
    behaviour), then read storage. This is the campaign's original unvalidated
    goal; now there IS a genuine RDP2 part to run it against, with a KNOWN test
    wallet (ideal validation).
CAVEAT: cannot independently prove firmware is actively running (no SWD/USB/
scope); powered + worked-last-night => treated as a live RDP2 chip. VCAP~1.2V
on the scope would confirm core-alive if the scope link is brought up.

## 2026-11-02  glitch-1 on genuine RDP2 target: full proven window, 0/15208 — needs retune/verify
Ran glitch1_rdp2_to_rdp1.py against the genuine RDP2 chip with the proven old
recipe (from scripts/1-recon_glitch_trace.py): clkgen 100MHz, ext 17000-18900
(170-189us) step 1, offset -45, repeat 20, width 40 (inert/enable_only),
BOOT0 low, cold power-on trigger (POR-release edge on TIO4/NRST), power-off
60ms, caps OFF (user pulled both VCAP caps). 15208 shots, ~4h, 0 SWD opens.
Log: campaigns/glitch1_20261102_131425.csv ; /tmp/opencode/glitch1.log.
INTERPRETATION: the exact params that opened the ORIGINAL Trezor (landed at
ext 17000 first try) do NOT downgrade THIS backup device in a full-window sweep.
Leading hypotheses (test in order):
  1. INJECTION NOT LANDING - crowbar may not be collapsing VCAP (SMA/contact,
     or the CW ext trigger not firing on this board's POR-release edge).
     VERIFY ON SCOPE before more blind sweeping (scope link currently down).
  2. WRONG WINDOW - different device/firmware => RDP-read moment may sit outside
     170-189us; widen/scan.
  3. INSUFFICIENT ENERGY - bump repeat 20 -> 30/40.
  4. TRIGGER REFERENCE - try warm-NRST trigger vs cold power-on; offset sweep.
Decision: verify injection (scope VCAP collapse + that the trigger fires) FIRST;
do not burn more hours against a possibly-dead crowbar.

## 2026-11-02 (late) — 0/15208 ROOT-CAUSE CANDIDATE: t=0 FRAME MISMATCH (recipe transposed across incompatible trigger frames)
Diffed scripts/1-recon_glitch_trace.py (the proven source of ext 170-189us,
1-trezor_fun ext-17000-first-try 2026-10-11) against glitch1_rdp2_to_rdp1.py:
  OLD frame: pwr off -> NRST DRIVEN LOW while unpowered -> arm -> NRST
  released -> THEN power returns. t=0 = FIRST RISING EDGE AS RAILS COME UP
  (VDD-ramp edge; chip too young to hold NRST low internally).
  NEW 'poweron' frame: NRST floats; chip's POR owns the pin through the ramp;
  t=0 = POR-RELEASE edge (BootROM start).
The two t=0s differ by the rail ramp + POR duration - dozens of us, and it
moves with the VCAP caps (pulled for crowbar). ext 170-189us was ONLY ever
proven in the OLD frame; the 15208-shot afternoon ran it in the poweron frame
where the number is meaningless. 0/15208 is therefore EXPECTED, not evidence
of a dead crowbar. (The clone's real 2.6-4.6us events were poweron-frame =
POR-release +us = option-byte load time - consistent.)
UPGRADES to glitch1_rdp2_to_rdp1.py:
  - G1_TRIGGER=old reproduces the 1-recon sequence EXACTLY (5 lines);
  - in-band trigger-fire check: post-shot scope.capture() returns True on
    timeout -> logs NO-FIRE per shot + summary count (a dead/unseen trigger
    can no longer masquerade as 15k misses). ADC lock + adc.timeout=0.5 added.
NEXT (after CW replug - currently off bus): (1) 50-shot sanity in old frame
w/ trigger check - answers rig-health AND recipe-frame in minutes;
(2) if firing: full old-frame 170-189 step1 sweep (~2h); (3) poweron-frame
EARLY sweep 0-30us step5 + 30-170 step50 (~1k shots) - the never-farmed
option-load window on the genuine part.

## 2026-11-02 (later) — REPLICANT cross-reference (voidstarsec blog) applied
Replicant (wrongbaud 2022, real Trezor One + CW-Lite, reproducing chip.fail):
- reboot_flush IDENTICAL to our G1_TRIGGER=old frame -> frame archaeology
  confirmed. Their params = ours (100MHz, offset -45, repeat 20, width 40).
- THEIR TRAP #1 (ST-Link wedge after first failed attach -> all later shots
  false negatives, fixed via per-shot USB reset): ours calls usb_reset every
  shot; verified working (exit 0, "ST-Link reset successfully"; device num
  unchanged = port reset, but fresh Stlink() per shot covers the lib state).
- THEIR TRAP #2: CW triggers ~24us BEFORE NRST reaches 3.3V (rise time) ->
  their sweet ext was 194-197, NOT the chip.fail 170. Lesson: per-rig offset
  = 170us + (rig NRST-rise gap). USER NOW MEASURING glitch/VCAP + NRST on
  the scope for our gap number.
- SWEEP PLAN: old-frame 17000-20500 step1 x3 (covers chip.fail 170, our
  1-trezor_fun 170-first-try, Replicant 194-197 + margin) once the scope
  gap is known (adjust center if gap measured).
- On SUCCESS: swd_check now AUTO-DUMPS 128KB SRAM while power is held
  (G1_SRAM_DUMP=1 default) - firmware boots BOOT0-low, so hardware_salt
  (SHA256(uid||otp), storage.c .bss) is in RAM at attach time; with EDEK
  from glitch-2 later, that completes offline PIN material. Replicant's
  chip.fail-era "seed in SRAM" is mitigated in modern fw, but hardware_salt
  is exactly what we still need (uid/otp otherwise unreadable at RDP1).

## 2026-11-02 (evening) — rig.md created; VCAP/crowbar diagnostics; fresh chip no-ACK
Session was a hardware-state debug, not a glitch pass.
- NEW DOC: `rig.md` (authoritative TIO map, supersedes CLAUDE.md pin mapping).
  Confirmed mapping (user): TIO1=BOOT0, TIO2=BOOT1, TIO3=trigger tap (a glitch
  script), TIO4=NRST. UART = FTDI /dev/ttyUSB0 115200 8E1 (NOT on CW). BOOT0
  also has a 3V3 jumper. DMM-confirmed pins: 31=VCAP_1 (1.2V core/glitch node),
  32=VDD (3.3V).
- SYMPTOM that started it: VDD(pin32)=3.3V but VCAP_1(pin31)=0V on the original
  (genuine backup) chip -> core rail held low -> no fw/bootloader, SWD silent.
  With the glitch SMA UNPLUGGED, pin31->GND reads OPEN (power off) = no static
  short on the node. => leading suspect: crowbar FET on the SMA leg failed SHORT
  after heavy enable_only+SMA firing (consistent with today's "clean-flip
  capability collapses" note). Chip likely NOT the fault.
- Swapped in a FRESH chip + restored VCAP caps, SMA disconnected. Bootloader
  STILL gives no 0x7F->0x79 ACK over FTDI, across: 1s AND 3s settle, 30 retries,
  BOOT0 high (jumper+TIO1), BOOT1 high_z AND BOOT1 driven LOW (TIO2=False).
  Serial config identical to the working campaign. => the no-ACK is NOT config.
- CLAUDE.md TRAP found: rdp1_uart_test.py and the campaign power_into_bootloader
  set tio2='high_z'. On this rig TIO2=BOOT1, so that leaves BOOT1 undriven ->
  can boot SRAM not bootloader. Driving TIO2=False didn't recover ACK here, but
  the scripts should still be fixed to drive BOOT1 low explicitly.
- OPEN (gating): VCAP_1 voltage on the fresh chip powered was never read back.
  Two live hypotheses: (a) core rail not at 1.2V (chip not running); (b) UART
  wire disturbed by the rework (FTDI TX<->PA10, PA9<->FTDI RX, GND). Next:
  read pin31 live; FTDI TX-RX loopback to prove the comms path end-to-end.

## 2026-11-02 (evening, cont.) — RDP LEVEL CONFIRMED = 1 (via SWD option-byte read)
Read-only SWD read of FLASH_OPTCR (0x40023C14) on the current (fresh) chip:
  OPTCR = 0x0FFFFFED ; RDP byte (bits15:8) = 0xFF => RDP LEVEL 1.
  (0xAA=L0, 0xCC=L2, anything else=L1.)
- SWD ATTACHED and read a register => by itself proves NOT RDP2 (RDP2 =
  permanently dead debug port). Chip is RDP1 with a live SWD port.
- Resolves "was locked rdp2 / supposedly reads rdp1": it is RDP1. Prior RDP2
  belief was wrong or it was already downgraded.
- CONSEQUENCE: the earlier bootloader no-0x7F-ACK is NOT a protection effect
  (RDP1 bootloader should ACK; only Read Memory NACKs). Back to a
  bootloader-ENTRY (BOOT0 high at pin?) or UART-WIRING issue for the FTDI path.
- But SWD-at-RDP1 WORKS => the hardware_salt route (SRAM .bss readable over
  SWD at RDP1; flash/OTP blocked) is open without needing the bootloader UART.
- Tool: scratchpad read_rdp.py (power via CW, Stlink(480k), decode OPTCR>>8).

## 2026-11-02 (evening, cont.2) — investigate_chip.py: RDP1 confirmed + NO-ACK ROOT CAUSE = BOOT0 not high (core LOCKUP)
Built `investigate_chip.py` = the single authoritative READ-ONLY chip report
(SWD triangulation; bootloader ACK demoted to secondary). Full output on the
current fresh chip:
- CHIP ALIVE: VDD=3.23V (ST-Link measured), DEV_ID=0x411 (STM32F2xx) REV=V,
  Cortex-M3, DAP IDCODE 0x2BA01477.
- RDP LEVEL 1, triangulated & self-consistent: OPTCR=0x0FFFFFED RDP byte 0xFF
  (authoritative); SRAM readable; FLASH/STORAGE/SYSROM/OTP/UID/FSIZE all FAULT
  over SWD -> flash blocked AGREES with L1. nWRP=0xFFF (no write-protect).
- ROOT CAUSE of the bootloader no-0x7F-ACK we chased all evening:
  DHCSR=0x03090000 => core in LOCKUP; halted regs PC=0xFFFFFFFE SP=0xFFFFFEE0
  LR=0xFFFFFFF9 = all-FF pattern = booting BLANK/invalid flash -> HardFault ->
  lockup. So the chip is in FLASH boot, NOT the bootloader => nothing answers
  0x7F. ** BOOT0 IS NOT ACTUALLY HIGH AT THE PIN ** (the 3V3 jumper isn't
  reaching BOOT0 / wrong pad / bad contact). The silence was NEVER UART wiring.
- Also note: flash appears blank on this chip (consistent with the lockup
  pattern; cannot read flash at RDP1 to confirm directly).
FIX: get BOOT0 genuinely high (verify 3V3 at BOOT0 = pin 60 on LQFP64, or drive
CW TIO1 high and confirm) -> chip enters ST bootloader -> at RDP1 it should ACK
0x7F and NACK Read Memory. THEN the UART path can be trusted.
TOOL: run `investigate_chip.py` for any "what state is this chip" question
(supersedes judging state from a bootloader ACK). rdp1_uart_test.py's tio2=
'high_z' bug (TIO2=BOOT1 must be LOW) still stands to be fixed.

## 2026-11-02 (evening, cont.3) — BOOT0-high test: both boot pins physically wrong
Ran investigate_chip.py with G_DRIVE_BOOT0=1 (TIO1 drives BOOT0 high) vs the
default (tio1=high_z, trust the 3V3 jumper). Halted-core registers:
  tio1=high_z : SP=0xFFFFFEE0 PC=0xFFFFFFFE  (all-FF = blank-flash boot)
  tio1=True   : SP=0x20000FE0 PC=0x00000000  (valid SRAM SP) -- STILL LOCKUP
Deductions:
  1. The BOOT0 "3V3 jumper" does NOT hold BOOT0 high: with TIO1 released the
     chip boots blank flash (SP all-FF) => BOOT0 is LOW. Jumper not on pin60 /
     tied to GND / no contact.
  2. Driving TIO1 high DOES reach BOOT0 (SP became a valid SRAM addr) but the
     core still LOCKUPs and the bootloader still won't ACK => it lands on SRAM
     boot, not system bootloader. Signature of BOOT1 FLOATING HIGH (BOOT0=1,
     BOOT1=1 -> boot from SRAM -> uninitialized vectors -> lockup).
=> BOTH boot pins wrong at the chip. LQFP64: BOOT0=pin60 must be 3.3V (jumper
isn't doing it); BOOT1=PB2=pin28 must be 0V (likely floating -> add pulldown or
land TIO2 on pin28). Do NOT run a 3V3 jumper AND TIO1 on BOOT0 simultaneously.
Added G_DRIVE_BOOT0 env toggle to investigate_chip.py.

## 2026-11-02 (evening, cont.4) — BOTH boot jumpers on wrong rails (BOOT0 low, BOOT1 high)
Two boot signatures from investigate_chip.py halted-core SP (RDP1, fresh chip):
  TIO1 high_z (jumper only): SP=0xFFFFFEE0 (all-FF) = BLANK FLASH boot => BOOT0=0
  TIO1=True (force BOOT0 hi): SP=0x20000FE0 (SRAM addr) = SRAM boot => BOOT0=1,BOOT1=1
=> BOOT0 jumper gives LOW (want HIGH); BOOT1 gives HIGH (want LOW). Effectively
swapped. tio2=False does NOT override BOOT1 (TIO2 not landing on PB2, or a hard
jumper holds it high). Longer 1.5s power-off did not change outcomes => timing
wasn't the blocker here; BOOT1-high is.
FIX (LQFP64): BOOT0=pin60 -> 3V3 (HIGH); BOOT1=PB2=pin28 -> GND (LOW). Only
BOOT0=1,BOOT1=0 enters the system bootloader; current state boots flash/SRAM
-> lockup -> no 0x7F ACK. investigate_chip.py now auto-names which boot pin is
wrong from the SP pattern (SRAM SP=BOOT1 high; all-FF SP=BOOT0 low).

## 2026-11-02 (evening, cont.5) — TIO2 driven low but BOOT1/PB2 still high = wire fault
With explicit s.io.tio2='gpio_low' (readback CONFIRMS 'gpio_low') and
tio1='gpio_high' (BOOT0 high), the chip STILL boots SRAM (SP=0x20000FE0,
LOCKUP) => BOOT1 is HIGH at the pin despite TIO2 commanded low. So the CW drive
is correct; the TIO2 -> PB2(BOOT1, pin28 LQFP64) CONNECTION is broken (wire not
landing on pin28, lifted in the chip swap) or PB2 has a pull-up overriding it.
FIX: continuity TIO2 header -> pin28; measure pin28 (should be 0V). Simplest:
tie pin28 directly to GND (BOOT1=0 is static). Then re-run investigate_chip
G_DRIVE_BOOT0=1 -> expect core in system bootloader (PC in 0x1FFF0000, no
LOCKUP) + 0x7F->0x79 ACK. (Boolean tio=False does not reliably drive low; use
'gpio_low'/'gpio_high' strings.)

## 2026-11-02 (evening, cont.6) — CORRECTION: chip IS entering the bootloader; remaining fault = UART wiring
Earlier "SRAM boot / BOOT1 high" heuristic was WRONG. Evidence: with BOOT0 high
(TIO1) the halted SP is a STABLE 0x20000FE0 every run, while SRAM[0] read varies
(0x7FFEFF1D / 0x6FFEFF8D / 0x7FBEFB9D...). True SRAM boot would load SP from
SRAM[0] (varying garbage); a stable 0x20000FE0 is the ST SYSTEM BOOTLOADER's own
initial SP. => the chip HAS been entering the bootloader whenever BOOT0=1. The
LOCKUP/PC=0 is the ST-Link halting into RDP1-protected bootloader code (debug
artifact), not a boot failure. Tying pin28->GND changing nothing is consistent:
BOOT1 was already effectively fine / irrelevant to bootloader entry here.
=> BOOT PINS ARE OK. The ONLY remaining blocker to the 0x7F->0x79 ACK is the
UART path (FTDI <-> chip PA9/PA10). NEXT: FTDI TX->RX loopback to prove the
adapter+cable+software; then continuity FTDI TX->PA10(pin43), PA9(pin42)->FTDI
RX, common GND. investigate_chip.py heuristic fixed (stable SP != SRAM[0] =>
bootloader; SP==SRAM[0] => SRAM boot).

## 2026-11-02 (evening, cont.7) — RIG VALIDATED END-TO-END on a blank RDP0 chip
Swapped in a fresh blank chip. investigate_chip.py G_DRIVE_BOOT0=1:
  RDP0 (OPTCR=0x0FFFAAED, byte 0xAA); core RUNNING in bootloader (PC=0x1FFF2B8C,
  SP=0x20000FD0, LR=0x1FFF19C1 -- NO lockup); 0x7F->0x79 ACK (FTDI UART good);
  ALL regions readable (flash blank FF, storage FF, sysrom 0x20001000, OTP FF,
  UID=0031003D 30334715 38313032, FSIZE=512KB F205RE).
=> THE WHOLE RIG IS GOOD: BOOT0=TIO1, BOOT1=TIO2/pin28-GND, FTDI TX->PA10(pin43),
   RX->PA9(pin42), GND common, SWD, power -- all correct. The 0x79 ACK we spent
   the evening chasing was never a rig fault.
=> The PREVIOUS "RDP1" chip was the problem: with identical wiring it sat in
   genuine LOCKUP (PC=0, no bootloader execution) and never answered UART.
   The real in-bootloader signature is PC in 0x1FFF0000 + core RUNNING (this
   blank chip), NOT the earlier PC=0/lockup. That chip is suspect/abnormal.
investigate_chip.py verified correct across RDP0 (all readable, in bootloader,
ACK) and RDP1 (SRAM-only, flash fault). It is the authoritative state tool.

## 2026-11-02 (evening, cont.8) — CHIP_A data archived; UID catalog
All dumps/keys/sram to date = ONE chip (STM32_TEST_CHIP_A). Moved intact to
`chips/CHIP_A_UID/` (+ README) so it's preserved and not confused with the new
blank bench chip. Chip is kept for further testing.
UID catalog (STM32 96-bit UID):
  STM32_TEST_CHIP_A : 3e0031001547333032303138  (RDP1; known-answer PIN <redacted>)
  blank bench chip  : 3d0031001547333032303138  (RDP0, blank 512KB)
  => SIBLING DIES, same wafer: differ ONLY in first byte (3E vs 3D = wafer X/Y).
CHIP_A last status: RDP1, alive, SWD ok, but core LOCKUPs (no bootloader run,
no 0x7F ACK) on a rig that ACKs the blank sibling -> chip-specific anomaly, TBD.

## 2026-11-02 (evening, cont.9) — chip-c practice clone built at RDP0
New practice chip = chip-c (blank sibling of chip-a, UID 3d0031001547333032303138;
chip-a is 3e...). Data in `chips/chip-c/`.
- make_storage.py --uid 3d... --pin <redacted> -> storage.bin + known-answer.json
  (PIN <redacted>; mnemonic "<redacted>"; hardware_salt 60167b7bc5a9163d6df031ff642132f0ceb4c6bcdd6e
  629ab0125262014ea6b2 = SHA256(UID||OTP3 ff*32); storage v4).
- plant_storage.py (G_PRACTICE_BOARD=YES): region all-FF confirmed, programmed
  0x08008000 via SWD, readback PASS.
- Verified via investigate_chip.py G_DRIVE_BOOT0=1: RDP0, STORAGE=3243524E
  (NRC2), bootloader 0x7F->0x79 ACK, all readable. FLASH 0x08000000 still blank
  (storage sector only, no firmware). "Load RDP0 first" DONE.
- NEXT (planned): fake .bss salt in SRAM (sram_test/stub.c mimics storage.c
  hardware_salt[32], or SWD write the 32B salt), then set RDP1 for glitch-2
  practice with a known answer.
- NOTE: uart_rdp0_test.py does NOT drive BOOT0 (predates BOOT0=TIO1 rig) -> use
  investigate_chip.py to verify, or add tio1=True/tio2=gpio_low to it.

## 2026-11-02 (evening, cont.10) — chip-c re-keyed: 6-digit PIN + 24-word mnemonic
Rebuilt chip-c storage with a 6-digit PIN and 24-word (256-bit) BIP39 mnemonic.
- make_storage.py --pin <redacted> --mnemonic "<24 words>" --uid 3d... (gen_mnemonic
  supports 256-bit; used the `mnemonic` lib to make the phrase). PIN <redacted>;
  mnemonic "<redacted>"; hardware_salt unchanged (60167b7b..., UID-derived).
- NEW TOOL erase_storage.py: SWD sector-2 erase (0x08008000, SER|SNB2|PSIZE word
  |STRT) so plant_storage can re-plant; practice-guarded. Worked (sector -> FF).
- Re-planted (readback PASS), investigate_chip: RDP0, STORAGE=NRC2, bootloader
  ACK. decrypt_storage.py storage.bin --pin <redacted> -> PIN FOUND, recovered the
  24-word mnemonic. Full v4 chain works with 6-digit PIN + 24-word seed.
- chips/chip-c/ updated (storage.bin, known-answer.json, README). brute note:
  6-digit space is 1e6 PINs (decrypt_storage --brute 000000-999999) vs 1e4.

## 2026-11-02 (evening, cont.11) — generate_bss.py: fake .bss hardware_salt in SRAM
NEW TOOL generate_bss.py: compiles a thumb stub (arm-none-eabi-gcc) whose .bss
array = the hardware_salt, links it to SRAM, loads via SWD and RUNS it with the
debugger (CortexM: set SP/PC/PSR -> run, brief spin, halt) so the salt lands in
.bss like firmware -- no SRAM-boot needed, so it does NOT fight pin28->GND
(BOOT1). Salt source: --salt | --uid/--otp3 | known-answer.json (default).
chip-c run: salt 60167b7b... planted at .bss 0x20000044 (verified MATCH); full
128KB SRAM dumped to chips/chip-c/sram_bss_dump.bin (salt present). Note the
stub also carries the salt as a .rodata const (0x20000024) since it's baked in,
not computed; real fw computes SHA256(UID||OTP) so only the .bss copy exists.
This completes the practice inputs: storage (flash) + hardware_salt (SRAM .bss),
both with a known answer, still at RDP0. Next: set RDP1 for glitch-2 practice.
Tools copied into chips/chip-c/ (generate_bss.py, erase_storage.py) for the record.

## 2026-11-02 (evening, cont.12) — chip-c locked to RDP1 (glitch-2 target ready)
NEW TOOL set_rdp1.py: RDP0->RDP1 via SWD option-byte write (RDP byte 0xBB; HARD
refuses 0xAA/0xCC so it can't clear protection or brick to RDP2). Same proven
sequence as set_rdp2 (BOOT0-high bootloader + CortexM halt + OPTKEYR unlock +
OPTSTRT + reload). Practice-guarded.
Result on chip-c: OPTCR 0x0FFFAAED -> 0x0FFFBBED, RDP byte 0xBB = L1. Verified
via investigate_chip: RDP1, SRAM readable, FLASH/STORAGE/SYS/OTP/UID all FAULT,
bootloader 0x7F->0x79 ACK (Read Memory NACKs at RDP1 = the protection). Storage
survived (RDP0->RDP1 no erase).
=> PRACTICE CLONE COMPLETE: chip-c mirrors the real device at RDP1 with a known
answer (PIN <redacted>, 24-word mnemonic) + storage at 0x08008000 + hardware_salt
re-plantable in SRAM via generate_bss.py. SRAM clears on power cycle, so re-run
generate_bss.py at RDP1 before the salt-recovery practice.
All chip-c tools copied into chips/chip-c/ (make/plant via working dir; set_rdp1,
generate_bss, erase_storage archived there).

## 2026-11-03 — OpenOCD cross-check at RDP1: gets nothing more than pyswd
Ran openocd 0.12.0 (stlink + stm32f2x.cfg) read-only on chip-c at RDP1:
  OPTCR=0x0fffbbed (RDP1, matches investigate_chip); options_read -> "Device
  Security Bit Set"; "STM32 flash size failed, probe inaccurate" (flash-size reg
  0x1FFF7A22 is in the blocked region). mdw: SRAM OK; FLASH/STORAGE/UID all
  error -4 (blocked). Same access profile as pyswd EXACTLY.
=> RDP1 is a silicon AHB gate; NO debug host (OpenOCD/pyOCD/ST-Link Util)
   bypasses it. Only a glitch opens the window. Also reconciles the 2026-11-02
   OpenOCD misread ("not rdp1") - it now clearly shows the security bit set.

## 2026-11-03 — investigate_chip.py: OpenOCD cross-check added (opt-in)
Added an independent OpenOCD RDP cross-check to investigate_chip.py, opt-in via
G_OPENOCD=1 (runs after the pyswd phases so the ST-Link is free; target still
powered). It shells openocd (stlink+stm32f2x), parses OPTCR + "Device Security
Bit Set", and the VERDICT prints "OpenOCD xck: L<n> -> AGREES/DISAGREES". Two
independent transports now confirm the RDP level - catches a bad single-tool
read like the 2026-11-02 OpenOCD misfire. Verified on chip-c RDP1: both read
OPTCR 0x0FFFBBED -> L1, AGREES. (Default run stays pyswd-only/fast.)
Also documented G_DRIVE_BOOT0 / G_OPENOCD in the script header.

## 2026-11-03 — plant_storage.py rewritten: provisions OTP + keys storage to chip identity
Copied real fw source to trezor-firmware-legacy-v1.13.1/. Confirmed the salt
derivation from source: collect_hw_entropy (trezor.c) = UID(12 @0x1FFF7A10) ||
OTP block 3 (32 @0x1FFF7860); hardware_salt=SHA256(that) kept in storage.c .bss
static. OTP block 3 = FLASH_OTP_BLOCK_RANDOMNESS=3; lock byte @0x1FFF7A00+3=
0x1FFF7A03 (0x00=locked). First boot writes RANDOM to it + locks if unlocked =>
real salt is random+locked+debug-unreadable => recoverable ONLY from .bss/SRAM.
plant_storage.py now mirrors this: reads the chip's real UID over SWD, provisions
OTP block 3 (G_OTP=keep|random|<64hex>, random+lock = real behavior), derives
hardware_salt from the chip's ACTUAL uid+otp, builds+plants v4 storage keyed to
that salt (make_storage.build), writes known-answer.json. storage.bin is now an
OUTPUT, not input. RDP0-only (aborts otherwise, safe), practice-guarded; OTP
writes are one-time/permanent. py_compile OK, make_storage integration verified
(16KB img, salt==SHA256(uid||otp)). UNTESTED on hardware (needs a blank/RDP0
chip; chip-c is RDP1 so would need a rebuild). OTP byte-programmed (PSIZE=byte)
exactly like flash_program_byte; storage word-programmed; inline sector-2 erase.

## 2026-11-03 — chip-c WIPED to RDP0; wipe method + scripts-in-chip-folders fix
- Scripts must live ONLY in storage-sim, not inside chips/<name>/ (data-only).
  Removed the .py copies from chips/chip-c/; chip-a was already clean.
- WIPE: the SWD option-byte downgrade (RDP 0xBB->0xAA via OPTCR+OPTSTRT) did NOT
  commit the L1->L0 regression on this rig (stayed 0xBB after reload). The
  reliable method is the bootloader READOUT UNPROTECT command over FTDI:
  sync 0x7F->0x79, send 0x92 0x6D -> ACK 0x79, chip mass-erases + sets RDP0,
  then RESETS (no 2nd ACK before reset is normal). wipe_chip.py rewritten to use
  it (BOOT0 high via TIO1, BOOT1 low). Verify attach can hit a transient
  "DP wait" right after the reset -> added retry; confirm with investigate_chip.
- Result on chip-c: RDP0, FLASH 0x08000000 = FF, STORAGE 0x08008000 = FF (plant
  erased), UID readable again (3d...). Blank, ready to re-provision via the new
  plant_storage.py (reads UID, provisions OTP, keys storage to the chip).

## 2026-11-03 — chip-c reprovisioned via new plant_storage.py (random+locked OTP) + bugfixes
Wiped chip-c, then re-provisioned with the rewritten plant_storage.py:
- G_OTP=keep validation run: PASS (read UID, salt SHA256(UID||FF)=60167b7b,
  planted storage, decrypt-ready). Validated the whole flow minus OTP burn.
- G_OTP=random: hit 2 bugs in the new OTP code, both fixed:
  (1) write_mem8 needs bytes not list -> bytes([b]); failed pre-transfer so OTP
      was intact. (2) flash_unlock faulted when flash already unlocked (double
      unlock, OTP data-write then lock-write) -> guard flash_unlock on CR.LOCK.
      Also added one-time recovery: if OTP block already written+unlocked, KEEP
      the existing value and just lock it (OTP bits only FF->0; never rewrite).
- Final: OTP block 3 = 0c7afc72...b67236 (LOCKED, permanent); hardware_salt =
  c03bb669...e875794c = SHA256(UID||OTP3). storage planted, decrypt round-trip
  PASS (PIN <redacted> -> 24-word mnemonic). chips/chip-c/ updated (data only).
- KEY POINT (real scenario): assuming blank OTP gives WRONG salt (60167b7b);
  real salt needs the random OTP, which is locked + debug-unreadable at RDP1/2
  -> salt obtainable ONLY from .bss/SRAM. OTP survives mass-erase, so future
  reprovision of chip-c must use G_OTP=keep (plant_storage reads the locked OTP).

## 2026-11-03 — VALIDATED automatic .bss generation (resident salt-firmware)
Clarified: .bss is auto-generated only by RESIDENT FIRMWARE on boot; chip-c had
none (generate_bss.py = manual SWD injection). Built+flashed a salt-firmware at
0x08000000 (sector 0 only; new tool validate_auto_bss.py, embeds a self-contained
SHA256 + reads UID@0x1FFF7A10 and OTP block3@0x1FFF7860 -> SHA256 -> .bss static
hardware_salt[32], sets hw_ready=0xA5, spins). LD syntax needs regions on
separate lines w/ spaces. Validated: flashed, power-cycle BOOT0 LOW (boot from
flash, no debugger/injection), SWD read .bss -> hw_ready=0xA5 AND hardware_salt =
c03bb669...e875794c = known answer, found in SRAM dump. Proves the real-device
mechanism on the clone: fw reads its own UID + LOCKED random OTP (offline-
unknowable) and derives the correct salt into SRAM -> recover from .bss. chip-c
now has resident salt-firmware (storage sector 2 intact). Next: set RDP1/RDP2;
fw still auto-generates .bss on boot at any RDP (CPU reads OTP regardless), then
glitch to open SWD and lift .bss.

## 2026-11-03 — chip-c LOCKED to RDP1 + full real-device scenario validated
set_rdp1.py: OPTCR 0x0FFFAAED -> 0x0FFFBBED (RDP 0xBB=L1), no erase (resident
salt-firmware + storage survived). Validated at RDP1 (BOOT0 LOW boot -> SWD):
hw_ready=0xA5 (fw auto-ran), hardware_salt @ .bss 0x20000000 = c03bb669... read
over SWD (SRAM readable at RDP1, NO glitch for the salt); storage/flash/OTP3/UID
all BLOCKED. => complete faithful RDP1 glitch-2 target w/ known answer (PIN
<redacted>, 24-word). Practice chain: salt from .bss (no glitch), storage from
glitch-2 bootloader bypass, offline brute PIN. salt .bss symbols: hardware_salt
@0x20000000, hw_ready@0x20000020 (fixed by link script).

## 2026-11-03 — glitch-2 pipeline dry-run VALIDATED on chip-c (crowbar disarmed)
Reconnected crowbar SMA to VCAP (pin31); investigate_chip confirms chip-c still
ALIVE (VDD 3.26, RDP1, bootloader ACK) -> the crowbar FET is NOT shorting the
core rail on this chip (unlike CHIP_A). Wired TIO3 trigger tap onto the QFP64 RX
(PA10/pin43 = the FTDI TX / Read-Memory command line). TIO2=BOOT1 stays low
(pin28 GND), NOT a UART.
Dry run: rdp1_glitch_campaign_full_mem_dump.py with G_CROWBAR=0 G_LP=0 G_SHOTS=20
(glitch "commented out" - module arms + triggers on TIO3 but FETs disarmed = no
VCAP pull). Result: bootloader SYNCED, 20 shots all -> nack (1f1f) = correct RDP1
Read-Memory refusal, [rst ok] every shot, clean (no spam/dead/weird). => full
pipeline (BOOT0, FTDI UART, command burst, TIO3 trigger line, NRST reset loop,
logging) works on chip-c. Needed: mkdir campaigns dumps/accum (were moved to
chip-a). Ready for a LIVE pass (G_CROWBAR=1) - the 1f1f NACKs are what a landed
glitch flips to 79 (ACK).

## 2026-11-03 — GLITCH-2 VALIDATED on chip-c (clean flip read real storage)
Live pass: G_CROWBAR=1 G_LP=1 window 180-182us rep6/7 (G_RND_LO=33 HI=45).
Bootloader synced; shot #79 ext=30026 (180.2us) w5 r7=42ns -> SUCCESS = clean
NACK->ACK flip + Read Memory completed. The read (256B) BYTE-MATCHES
chips/chip-c/storage.bin (the chip's real current storage). It was "REJECTED
oracle=MISMATCH" ONLY because the campaign's oracle loaded the stale working-dir
storage.bin (old PIN-<redacted>/blank-OTP build), not chip-c's current random-OTP
build -> false negative in QC, not a glitch failure.
=> glitch-2 bypass WORKS on chip-c. Crowbar healthy (lands clean flips, doesn't
short the rail). Sweet spot ~180.2us = SAME as CHIP_A -> window transfers to the
sibling die. Flip rate ~1/79 in the hot window (lucky/strong).
FIX: added G_ORACLE env to the campaign (default storage.bin) so it can point at
chips/chip-c/storage.bin. For a real dump run on chip-c:
  G_ORACLE=chips/chip-c/storage.bin G_CROWBAR=1 ... rdp1_glitch_campaign_full_mem_dump.py
Stopped the 1000-shot run after the diagnosis (was rejecting good flips vs stale
oracle). Needed mkdir campaigns dumps/accum (were moved to chip-a).

## 2026-11-03 — scope-damping confirmed on chip-c full-dump run; aborted to remove scope
During the chip-c full dump the Siglent was still on the VCAP SMA-T (glitch
node). 165 shots: 2 dead (crowbar landing), 2 resync, 0 SUCCESS, 0 banked -
vs the quick run's clean flip at #79. Consistent with the known ~15-20pF
scope-load damping the crowbar pull (weak pull -> no clean flip / ghosts).
Stopped the campaign + watcher to physically disconnect the scope from VCAP
(measurement-only discipline). Crowbar FET confirmed HEALTHY on chip-c (dead
verdicts = pulse lands). Resume the dump with the scope OFF the node:
  G_ORACLE=chips/chip-c/storage.bin G_CROWBAR=1 G_LP=1 G_US_MIN=180 G_US_MAX=182
  G_RND_REP=1 G_RND_LO=33 G_RND_HI=45 G_TARGETED_N=6 ... full_mem_dump.py

## 2026-11-03 — EXTERNAL-VCAP-FEED RESEARCH: plan externally validated + stage-1 intel
Sources gathered supporting the weak-feed topology (Nov 1 plan):
1. PRIMARY: mkesenheimer.github.io/blog/trezor-wallet-hack-v161.html (Oct 2025,
   F205 v1.6.1+ attack): "An adjustable power supply (for example RD6006)" is a
   PREREQUISITE; photo caption: "external power supply connected to VIN1 (be
   sure to not exceed 1.2V)"; the MUX output IS the V_CAP supply. His working
   RDP2->RDP1->flash attack RUNS ON the external <=1.2V feed.
2. HIS V3 HARDWARE (Jan 2026): Pico Glitcher v3 adds NATIVE 1.2V rail support -
   "glitching is most effective when the glitch amplitude closely matches the
   target's supply rail". He productized the concept.
3. GENERALIZED TECHNIQUE: fault-injection-library multiplexing docs - supply
   switched between voltage LEVELS (not just GND), voltage profiles; mux doubles
   as target power source (weak feed + crowbar).
4. ACADEMIC MIRROR: Vosoughi & Kose, GLSVLSI'19 "Leveraging On-Chip Voltage
   Regulators Against Fault Injection" (saved /tmp/opencode/kose_glsvlsi19.pdf):
   on-chip VR = documented FI COUNTERMEASURE - single-phase cuts fault count
   5.45%, 32-phase 91.82%. Converse: the F2's internal LDO is a (mild)
   countermeasure fighting our crowbar; idling it via external feed removes it.
   Their cap-size analysis also supports our VCAP cap removal.
STAGE-1 TACTICAL INTEL from the same post (new firmware):
   - His t=0 frame = V_CAP RISE, sensed by adjustable Schmitt (EXT1) ON THE
     VCAP LINE ITSELF - self-relative frame, immune to ramp/NRST differences.
     That is WHY his numbers transfer across rigs.
   - Stage-1 sweet: ~180us after VCAP rise (10us later than old-fw 170);
     combined-attack delay 188.9-189.5us, length 110-130ns.
   - TRANSLATION TO OUR NRST FRAME (user scope 11-02: VCAP event ~80us,
     NRST rise ~90us -> NRST lags VCAP by ~10us): sweet = NRST-rise +
     170-179us; length ~110-130ns (rep 11-13 @100MHz) worth trying beside
     rep 20. Prior "170-189 swept" runs were with the DEAD crowbar path -
     the window is effectively unswept.
CONCLUSION: 305D + series-R weak feed = his topology minus the mux (we keep
the CW crowbar). Order stands: fix/verify crowbar path FIRST, then add feed.

## 2026-11-03 — RESEARCH LOCKED: external VCAP feed mechanism (bench-supply/LDO interplay)
Sources: archived kesenheimer-README_FLASH_DUMP.md + stm32f2-bootloader-memread-mux.py
(lines 178-181), mkesenheimer.github.io Pico Glitcher v2 blog, EFTON gotcha g201,
Kose GLSVLSI'19 on-chip-VR-countermeasure paper.

FACTS (verified):
- MUX TOPOLOGY: mkesenheimer's VCAP is wired to the Pico MUX output; idle = VI1
  = 1.2V CONTINUOUS (bench supply VIN1), glitch = connect GND for t1 ns
  (`mul_config={"t1":length,"v1":"GND"}`, initial "VI1"). Not a pulse mode -
  the node is externally paralleled at nominal for the whole session. MUX stage
  = TS3A4751 analog switch: <=1 Ohm, >=100 mA - hard enough to BE the rail.
- LDO ON-DIE CANNOT BE DISABLED on F205 (no SMPS/LDO select, unlike F7/H7).
  External feed can only form a parallel standoff - 3 regimes:
    below setpoint -> LDO pass stays OPEN, wins (no gain);
    at setpoint    -> benign standoff (his rig; EFTON g201 hotwire precedent);
    above setpoint (~1.25-1.30V) -> LDO pass CLOSES = "LDO idled" (Kose framing).
- DIAGNOSTIC/TRICK: raise VIN with 305D in CC (~30-50mA limit) and watch the
  bench current step from ~0 to full core draw (~10-30 mA) -> that step marks
  the die's LDO setpoint and proves LDO is shut. 305D CC readout = free meter.
- CANNOT: disable LDO (impossible), park rail LOW (LDO fights to setpoint),
  deepen collapse (11-01 scope ladder already hits 0V at r6, below-GND at r7).
  REAL VALUE of feed: ringdown damping (~500-600ns underdamped ringback),
  shot-to-shot shape repeatability, and a deterministic shallow-dip knob
  (source impedance via series R) for the over-glitching hypothesis.
- CAUTIONS: >=3.3V into VCAP kills the core (multiple documented cases);
  keep VIN <= ~1.30V - overdriving only makes the core harder to glitch.
ORDER (updated - crowbar path verified healthy 11-01, so feed is next):
  1) 305D + series R (100 then 22/10 Ohm) -> VCAP node, CC 50mA, find setpoint
     via CC readout, settle feed at nominal ~1.20V.
  2) Re-run r4-r7 depth ladder (scope off node during firing) vs 11-01
     captures - compare ringdown shape/repeatability.
  3) Shallow-band flip sweep (r4/r5 + width-shaped partial dips) with feed in.

## 2026-11-03 — FULL END-TO-END RECOVERY on chip-c (glitch storage + .bss salt)
Complete chain proven on the faithful RDP1 clone (random/locked OTP, resident
salt-firmware, planted storage):
- glitch-2 dumped storage chunks 0,1,2 (oracle=MATCH): storage_0000 ext=30259
  (181.6us) rep6, storage_0001 ext=30315 (181.9us) rep7, storage_0002 ext=30119
  (180.7us) rep7. Resume (G_RESUME) worked across runs. Scope OFF the node =
  clean flips at ~1/700-800.
- salt from firmware .bss in SRAM dump (chips/chip-c/sram_*.bin @ 0x20000000) =
  c03bb669...e875794c = SHA256(UID||OTP) (real-device route; OTP random+locked,
  unreadable).
- offline: assembled 3 glitched chunks + salt -> decrypt_storage -> PIN <redacted>,
  24-word mnemonic "<redacted>" = EXACT match to known-answer.json.
Recovery needs chunks 0-2 only (0=EDEK/PVC->PIN; mnemonic 0102 tail straddles
into chunk 2). 2 chunks gave PIN but 0102 TAG MISMATCH (tail in FF-pad); chunk 2
completed it. Script updated: G_EXTRA=0 (skip uncrackable uid/otp3),
G_STORAGE_BASE/LEN/SECTOR_LEN (default both NORCOW sectors 0x08008000+0x0800C000,
head-of-each-sector in targeted mode) for the real 32KB/2-sector storage; chip-c
uses G_STORAGE_LEN=0x4000. 1MB vs 512KB does NOT affect pulls (fixed addresses).

## 2026-11-03 (end of session) — RESUME POINT
Stopped for the night. Rig left SAFE: crowbar disarmed (glitch_hp/lp off), TIOs
high_z, target_pwr OFF.
STATE:
- chip-c = faithful RDP1 clone, FULLY CRACKED end-to-end today: glitch-2 dumped
  storage chunks 0-2, .bss salt from SRAM, decrypt -> PIN <redacted> + 24-word
  mnemonic (matches known-answer). See RDP1_TO_DUMP.md for the full story.
- Banked chunks: dumps/run_20261103_012612 (0,1) + dumps/run_20261103_015300 (2).
- Script upgrades today (all tested): investigate_chip G_OPENOCD, plant_storage
  OTP-provision rewrite, generate_bss, validate_auto_bss, set_rdp1, wipe_chip,
  erase_storage; campaign: G_EXTRA (skip uid/otp3), G_STORAGE_BASE/LEN/SECTOR_LEN
  (both NORCOW sectors default), G_ORACLE.
NEXT (tomorrow):
- The "new lean run" (G_TARGETED_N=3 G_EXTRA=0 G_STORAGE_LEN=0x4000) was launched
  then stopped before completing - re-run to confirm the trimmed campaign banks
  0-2 cleanly with zero wasted shots, then re-verify recovery from fresh chunks.
- Optional: cosmetic - the collector startup print still hardcodes
  "(16 KB storage + uid + otp3)"; update to reflect actual target count.
- Real-device plan unchanged: G_STORAGE_LEN=0x8000 (both sectors), salt from the
  device's own .bss; mechanism identical.

## 2026-11-03  chip-2 (real Trezor part) identified + investigate_chip device-firmware boot
- New part **chip-2**, pulled from a real Trezor. Installed in the rig and ID'd
  read-only with investigate_chip.py.
- **RDP LEVEL 1** (OPTCR 0x0FFFFFED, RDP byte 0xFF). Triple-agreement:
  pyswd + independent OpenOCD cross-check + flash/storage/OTP/UID all blocked.
  Debug port is ALIVE (DAP IDCODE 0x2BA01477, SRAM readable) -> definitively
  NOT RDP2 (L2 would fuse SWD dead; we'd get no IDCODE). User expected L2; the
  part is L1 -- either an RDP2 set never committed or it was only ever L1.
  (L1 is the good outcome: the whole glitch->SWD recovery path needs L1.)
- Boots its **resident Trezor firmware** from main flash: PC=0x08005C4A (in the
  Trezor bootloader region, below norcow storage @0x08008000), SP=0x2001FBA8.
  Core shows LOCKUP = RDP1 debug-halt artifact, not a boot failure.
- **investigate_chip.py upgraded**: now ACTIVELY DRIVES the device-firmware boot
  config (TIO1/BOOT0=gpio_low, TIO2/BOOT1=gpio_low) set before target_pwr so it
  latches at the power-on reset -- no longer trusts a jumper/pulldown. G_DRIVE_BOOT0=1
  still overrides to BOOT0-high for the ST system bootloader. Verdict now keys off
  the driven boot pins + PC region (main flash => DEVICE FIRMWARE; system ROM while
  BOOT0 low => BOOT0 stuck high at pin), replacing the stale SP-pattern heuristic
  that mislabeled a device-firmware boot as "LIKELY IN THE BOOTLOADER".
- POSTURE: chip-2 is a real-device part. Practice-board guard (G_PRACTICE_BOARD=YES)
  and no chip-modifying scripts apply. Open question: is chip-2 seed-bearing (recover)
  or a donor/spare (realistic practice target)?

## 2026-11-03  chip-2 H3/FPB first attempt -> blocked by missing VCAP hold-up
- Ran h3_fpb_attack.py on chip-2 (real seed part, RDP1), real-device mode
  (G_ORACLE unset, G_OUT=chips/chip-2/storage_fpb_0_2.bin). Result: stage1-done
  NOT SET, scratch came back CLEAN-ZERO (0/192 still-sentinel). I.e. staged SRAM
  code did not survive to run; real Trezor firmware then zeroed SRAM on flash boot.
- Diagnosed with h3_primitives.py:
    P-WRITE  = 9/9 OK (SRAM staging over SWD works fine)
    P-REMAN  = 0.00% retention at EVERY off-duration 1..500 ms.
  => the 1.2V core rail collapses instantly: NO VCAP hold-up capacitance present.
     SRAM remanence is the make-or-break primitive for H3; with no VCAP caps it
     is impossible. (chip-c had the caps on -> <=50ms window -> attack worked.)
- FIX (user): install VCAP caps on pin 31 (VCAP_1) + pin 47 (VCAP_2), ~2.2uF each.
- RIG MODE NOTE: H3/FPB wants VCAPs ON (hold rail -> remanence, glitchless).
  The glitch-2 campaign wanted VCAPs OFF (crowbar must pull pin 31). Opposite
  requirements; H3 needs no crowbar so no conflict. Set caps per the attack in use.
- NEXT: with VCAPs on, re-run h3_primitives.py P-REMAN to find chip-2's retention
  window, pick OFF_MS inside it, then re-run h3_fpb_attack.py.
- h3_fpb_attack.py made real-device-safe this session: G_ORACLE optional (unset =>
  judge success by stage2-done + scratch-filled, ALWAYS save), G_OUT sets dump path.

## 2026-11-03  chip-2 remanence: CAPS WORK; h3_primitives P-REMAN is confounded on real firmware
- CORRECTION to the "0% retention" entry above: that reading was a measurement
  artifact, NOT a remanence failure. h3_primitives repowers with BOOT0 LOW ->
  real Trezor firmware boots and memset-zeroes SRAM before readback, so it reads
  0% no matter how well the rail holds. (Tells: 0% even at 1ms, caps-on==caps-off
  identical, and CLEAN ZEROS rather than random bit-rot = software memset.)
  -> the P-REMAN test is INVALID on any chip running real RAM-clearing firmware.
- TRUE remanence (scratchpad reman_bootloader.py: repower into ST SYSTEM
  BOOTLOADER, BOOT0=1/BOOT1=0, ROM that does NOT wipe SRAM, read back over SWD):
      1,2,5,10,20,50 ms off -> 100% retention (8/8)
      100 ms off            -> 0% (random 0xaae967d7 = genuine analog decay)
  => VCAP caps ARE holding the 1.2V core rail. Remanence window ~ up to 50ms,
     gone by 100ms. FPB attack OFF_MS=30 is safely inside it.
- Therefore the chip-2 FPB failure (stage1-done NOT SET, clean-zero scratch) is
  NOT remanence. Clean zeros there = the step-3 flash-boot ran real firmware and
  wiped SRAM, which only happens if stage1 never programmed the FPB. Prime
  suspect: SRAM-boot (BOOT0=1,BOOT1=1) not engaging -> BOOT1/PB2(pin28) not
  reaching HIGH at the pin, so it lands in the bootloader and stage1 never runs.
  NEXT: h3_sramboot_test (does SRAM-booted code execute on chip-2?).

## 2026-11-03  chip-2 FPB chain: fault localized to redirect/vector-catch
- h3_sramboot_test on chip-2: ALIVE marker SET (0x1aa1aa1a) => SRAM-boot ENGAGES
  and runs our code (BOOT0=1/BOOT1=1 works; BOOT1/PB2 reaches the pin fine).
  DONE marker NOT set, scratch 64/64 still-sentinel => SRAM-booted code CANNOT
  read flash at RDP1 (faults), exactly as Obermaier found on F1. This is WHY the
  FPB boot-from-flash trick is needed; not a bug.
- fpb_survives_nrst (scratchpad): programmed FPB over SWD, pulsed NRST (TIO4 low
  50ms, power held), reconnected: FP_CTRL=0x261 ENABLE=1, FP_COMP0=0x1 enabled,
  FP_REMAP=0x20000100, remap table [0]=0x20010000 [1]=0x20001001 ALL INTACT.
  => FPB config SURVIVES NRST on chip-2. FP_CTRL reset value 0x260 => NUM_CODE=6
  comparators present. The "NRST preserves FPB" premise HOLDS.
- So the chip-2 FPB failure is NOT: remanence (caps good to 50ms), NOT SRAM-boot
  (runs our code), NOT FPB-survives-NRST (intact). Remaining unknowns: (a) does
  SRAM-booted stage1 actually ARM the FPB from code (vs debugger), and (b) does
  the remapped reset-vector fetch get caught so stage2 runs in flash-boot context.
  NEXT: instrument - SRAM-boot stage1, reconnect, read S1_DONE + FP_CTRL/COMP to
  confirm code-armed FPB. (Reconnect re-locks flash, so this checks arming only.)

## 2026-11-03 — FW SOURCE CHECK: does 1.13.1 wipe SRAM + where OTP/UID/salt live (real device)
Vendored tree trezor-firmware-legacy-v1.13.1 (no full RAM wipe exists):
- legacy/firmware/setup.c:117 - the ONLY explicit RAM clear is the USB OTG
  peripheral RAM (memset_reg 0x50020000-0x50020500). No full-SRAM scramble
  anywhere; standard C-runtime .bss zero-fill at reset is all.
- RAW entropy slot is deliberately wiped: legacy/firmware/trezor.c:129-147
  collect_hw_entropy(true) fills HW_ENTROPY_DATA[44] with UID(12B) + OTP block3
  (32B); legacy/firmware/config.c:389-390 passes it into storage_init(...) then
  memzero(HW_ENTROPY_DATA) immediately after -> raw OTP3 window in SRAM is
  transient (micro-seconds-tenths of a second after main()).
- BUT the DERIVED salt never dies: storage/lib storage.c:153
  `static uint8_t hardware_salt[32]`; storage.c:804 in storage_init()
  `sha256_Raw(salt, salt_len, hardware_salt)`; grep for memzero(hardware_salt)
  = ZERO hits. hardware_salt therefore persists in SRAM for the WHOLE firmware
  session until power-off. (Upstream leaves it in RAM while zeroing the raw
  entropy - the CONFIDENTIAL annotation is cosmetic.)
- Unprivileged edge: trezor.c:176-178 collect(false) would fill HW_ENTROPY
  with 0x3C junk; normal real-device boot is privileged -> collect(true)=2real.
CONSEQUENCE for the real-device chain:
  Raw OTP/UID direct glue: need NOT. The salt decrypt_storage.py needs is
  hardware_salt = sha256(UID||OTP3) - and its 32B copy sits permanently in
  firmware .bss/SRAM. So: glitch-1 (RDP2->RDP1) -> SWD SRAM readable -> dump
  SRAM -> read hardware_salt at its static .bss address (find offset once by
  disassembling the glitch-dumped firmware binary: sha256_Raw store target).
  Optional value of raw OTP3: it is the cross-check for the SRAM candidate
  (salt == sha256(UID||OTP3)); raw values recoverable by pointing the glitch-2
  readmem farm at 0x1FFF7A10 (UID) / 0x1FFF7860 (OTP3) after landing at RDP1 -
  never yet exercised on chip-a/c, one driver change.
  SECONDARY fallback target: the transient HW_ENTROPY_DATA raw-44B window
  (main() -> first storage_init) could in principle be caught by a boot-time
  SWD attach, but persistence of hardware_salt makes it unnecessary.

## 2026-11-03  chip-2 FPB EXTRACTION WORKS (transient first miss) — but chunks 0-2 are all-FF
- Re-ran h3_fpb_attack.py x2 on chip-2: BOTH succeeded. stage1-done 0x51A1E001,
  stage2-done 0xD09ED09E, 192/192 words filled. The single earlier failure
  (clean-zero scratch) was a TRANSIENT redirect miss - these non-ST clone parts
  (REV_ID 0x200F) are flaky on the vector-catch; a straight retry fires it. All
  primitives had already verified green (remanence/SRAM-boot/stage1-arms-FPB/
  FPB-survives-NRST), so the fix was simply: retry.
- BUT scratch head = ffffffff... => first 768B of sector 0x08008000 is ERASED.
  This does NOT mean seedless: NORCOW is a 2-sector store (0x08008000 + 0x0800C000,
  16KB each). On a used device the ACTIVE sector may be 0x0800C000, and/or live
  entries are appended deeper than the first 768B. 768B sufficed only for FRESH
  chip-c. => MUST dump the FULL 32KB NORCOW (both sectors) to locate NORCOW magic
  (4e524332 "NRC2") + the encrypted PIN/mnemonic entries.
- NOTE: a chip with chip-2's exact fingerprint (IDCODE 0x2ba01477 / DBGMCU
  0x200F6411) was logged 2026-11-02 as a clone at RDP1 with firmware present but
  BOTH storage sectors fully erased. Must confirm chip-2 is not that blank part;
  the full-storage dump settles it.
- chips/chip-2/storage_fpb_0_2.bin written (768B, all-FF) - superseded by the
  full-storage dump next.

## 2026-11-03  chip-2 FULL flash dump — STORAGE ERASED, no seed present
- fpb_fulldump.py (512KB, 8x64KB FPB chunks, caps on, non-destructive) succeeded
  on chip-2. -> chips/chip-2/flash_fulldump.bin (also dumps/flash_fulldump.bin).
- Bootloader (0x08000000/0x08004000) + firmware (0x08010000..0x0807FFFF) ~98%
  populated = genuine Trezor-type firmware.
- STORAGE: sector2 0x08008000 = 0/16384 non-FF; sector3 0x0800C000 = 0/16384
  non-FF. FULL 32KB NORCOW region = 0/32768 non-FF. COMPLETELY ERASED.
- "NRC2" magic hits only at 0x08049bd8/0x08049c8c = inside firmware CODE (the
  norcow magic constant), NOT a storage-sector header. No NORCOW data anywhere.
- CONCLUSION: chip-2 has intact firmware but ERASED storage. The encrypted seed
  lives ONLY in NORCOW storage -> it is NOT recoverable from this chip. Erased
  flash is physically 0xFF; no undelete.
- We did NOT erase it: all chip-2 ops this session were read-only/non-destructive
  (SRAM+power/boot/NRST+FPB reads; no flash/option writes; no RDP downgrade; no
  readout-unprotect). It arrived blank.
- IDENTITY: chip-2 fingerprint (IDCODE 0x2ba01477 / DBGMCU 0x200F6411) == the
  2026-11-02 "chip pulled from a trezor" that was already firmware-present /
  storage-erased. Almost certainly the same physical clone part. For a genuine
  seed recovery we need the actual seed-bearing ST STM32F205, not this blank clone.
- SILVER LINING: the FPB (Obermaier-H3) extraction is now PROVEN on a real-firmware
  chip at RDP1 end-to-end on this rig (caps on, retry past the flaky first redirect).
  When the true seed-bearing chip is in the socket, this is the clean no-glitch path.

## 2026-11-03  CORRECTION + CRITICAL DOCTRINE: chip-2 is firmware 1.13.1 (right chip); DO NOT BOOT TARGET FIRMWARE
- CORRECTION to the "1.12.1 / blank / wrong chip" entries: the 1.12.1 string is
  the BOOTLOADER version. The FIRMWARE version is in the TRZF image header @0x10000:
  bytes "01 0d 01 00" = 1.13.1, model "T1B1" (Trezor One). So chip-2 IS the device
  the user provisioned (upgraded to fw 1.13.1, created a wallet, logged in twice OK).
- Storage is nonetheless fully erased (both NORCOW sectors 0/16384 non-FF). The
  wallet existed (two good logins) -> it was wiped AFTER provisioning, i.e. during/
  after extraction. User h/w note: "some pins got messed up" during the pull.
- CAUSE (most likely, not provable after the fact): pin-damaged storage left NORCOW
  inconsistent; then booting the Trezor FIRMWARE ran storage_init, which WIPES
  storage it cannot validate. We booted device firmware many times on chip-2:
  investigate_chip.py now drives BOOT0 low = device-firmware boot (added this
  session per user request), and h3_primitives' flash-boot remanence sweep cold-
  booted it ~9x. Any boot runs storage_init. No explicit script issued an erase/
  RDP-change; the wipe path is the firmware's own storage_init.
- *** DOCTRINE FOR THE REAL SEED-BEARING DEVICE ***
  NEVER boot the target's own firmware. Booting runs storage_init which can WIPE
  the very storage we need. Use ONLY:
    (1) read-only SWD characterization that does NOT execute flash firmware, and
    (2) the FPB (Obermaier-H3) dump, whose redirect jumps to stage2 so the Trezor
        firmware NEVER executes -> storage_init never runs -> cannot wipe.
  Do the FPB storage dump FIRST, before anything that could boot firmware.
- TODO tooling: add a read-only / no-firmware-boot mode to investigate_chip.py
  (do NOT drive BOOT0 low on the real target); default the real-device path to it.

## 2026-11-03  PRECISE mechanism of chip-2 wipe (source-grounded) — corrects earlier entry
- CORRECTION: earlier I implied "booting firmware -> storage_init -> wipe" as if
  any boot wipes. FALSE. Per storage/norcow.c norcow_init (lines ~250-267): it
  wipes ONLY if NO sector has the valid NRC2 magic (find_start_offset requires
  header == NORCOW_MAGIC 0x3243524E) OR on a version downgrade. A HEALTHY wallet
  has the magic -> found=sectrue -> norcow_wipe() is NOT called. Normal boots of a
  working wallet do not touch storage.
- Physical evidence: both sectors 0/32768 non-FF = a CLEAN erase (erase_sector/
  norcow_wipe), NOT bit-rot. Bit-rot would leave old ciphertext mostly present with
  only a bad header.
- Honest chain: (1) ROOT CAUSE = extraction ("messed-up pins": brownout or a
  partial/interrupted flash write to the storage header during the pull) corrupted
  the sector header so it no longer read as NRC2; (2) TRIGGER = first firmware boot
  in the rig (investigate_chip BOOT0-low, then h3_primitives flash-boot remanence
  sweep ~9x) ran norcow_init, found no valid magic, called norcow_wipe() -> clean
  erase of both sectors.
- KEY CONSEQUENCE for the real device: a corrupted-HEADER sector still contains the
  old encrypted bytes. An FPB raw dump taken BEFORE any firmware boot would capture
  them (potentially reconstructable). Booting the firmware is what converts
  "corrupted header" into "zeroed sectors". => FPB-dump raw storage FIRST, never let
  norcow_init run on the target. Doctrine reaffirmed and now source-justified.

## 2026-11-03  Glitch tools hardened against firmware boot; mixed RDP1/RDP2 fleet workflow
- Lesson applied (chip-2 wipe): the thing that wipes storage is the TREZOR flash
  code (stock bootloader -> firmware -> storage_init/norcow_wipe). Both glitch
  campaigns must boot the ST SYSTEM bootloader (BOOT0 high), never the Trezor flash.
- glitch1_rdp2_to_rdp1.py: default changed to BOOT0 HIGH (was low). A firmware
  boot (G1_BOOT0=low) is now REFUSED unless G1_ALLOW_FW_BOOT=YES. The RDP2->RDP1
  glitch targets the BootROM option-byte RDP read (independent of BOOT0) and
  succeeds when SWD opens, so it works from the system bootloader with NO Trezor
  flash execution. (Added `import sys`.)
- rdp1_glitch_campaign_full_mem_dump.py: verified every power-on is preceded by
  tio1=True (BOOT0 high); reads flash via the bootloader UART Read-Memory. Trezor
  flash code never runs. Safe as-is.
- investigate_chip.py: G_SAFE=1 = firmware-free characterization (enters ST
  bootloader; warns loudly before any BOOT0-low firmware boot).
- MIXED FLEET (user has some RDP1, some RDP2 chips): do NOT hard-jumper BOOT0/BOOT1.
  The RDP1 chips are recovered by FPB, which needs the CW to TOGGLE BOOT0/BOOT1
  (SRAM-boot 1/1 then flash-boot 0/x); a fixed BOOT0=1/BOOT1=0 jumper blocks FPB.
  Let the CW drive the boot pins; rely on the safe software defaults above. One rig
  config then handles both types.
- PER-CHIP WORKFLOW: socket -> CW holds BOOT0 high (safe) -> read-only RDP check.
  SWD attaches => RDP1 => FPB-first dump. SWD dead => RDP2 => glitch-1 (BOOT0 high)
  to transient RDP1 => FPB or glitch-2 UART. Never boot Trezor firmware on any seed
  chip; dump raw storage before anything runs norcow_init.

## 2026-11-03  investigate_chip.py now SAFE BY DEFAULT (no firmware boot)
- Flipped the default: investigate_chip.py now enters the ST system bootloader
  (BOOT0 high) by default and NEVER boots the Trezor firmware unless G_BOOT_FW=1
  is explicitly set (loud wipe warning). G_SAFE / G_DRIVE_BOOT0 kept as safe
  aliases. Reverses the earlier-this-session change that made firmware-boot the
  default (which, with chip-2's already-corrupted storage header, contributed to
  the wipe). Verified flag logic: default/G_SAFE/G_DRIVE_BOOT0 -> BOOT0 high;
  only G_BOOT_FW=1 -> BOOT0 low.
- All three chip tools are now firmware-boot-locked by default: investigate_chip
  (safe default), glitch1_rdp2_to_rdp1 (BOOT0-high default + refuse), glitch-2
  campaign (always BOOT0-high).
