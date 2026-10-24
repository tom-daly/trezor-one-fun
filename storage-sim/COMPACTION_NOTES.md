# Compaction notes (2026-10-22)

Session checkpoint from the Trezor seed-recovery project. Source of truth for
state between compactions — treat as history, verify against the repo before
acting.

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
