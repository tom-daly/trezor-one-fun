# FINDINGS — running log of the Trezor seed-recovery campaign

Everything learned, decided, and ruled out — appended chronologically as it
happens. Treat as history; verify current state against the rig before acting.

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
  `4179`, seed `<redacted>` — test fixture, regenerate locally with
  `make_storage.py`) flashed at `0x08008000`; SWD readback byte-identical.
- **End-to-end rehearsal PROVEN: dump → PBKDF2 brute → ChaCha20 decrypt →
  mnemonic. Brute 0000–9999 found PIN 4179 in 24.9 s (~170 PIN/s).**

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
  the UART dump finds PIN 4179 in 23.9 s. The whole glitch-2 back half is
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
  instead of NACK. Known answer = PIN 4179→ no wait, run2: PIN 9434 / seed in
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
