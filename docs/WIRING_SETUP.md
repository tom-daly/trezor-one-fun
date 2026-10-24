# CW Lite ↔ Breadboard ↔ Trezor Wiring Setup

Shunt-resistor measurement rig for side-channel power capture on the Trezor One
(STM32F205), using the ChipWhisperer-Lite (CW1173).

Status: planned topology, not yet wired/verified. Update this file when the
rig is assembled and any drop/behaviour numbers are measured.

## How the CW Lite MEAS port works

- MEAS SMA → low-noise **AC-coupled** amplifier, up to **+55 dB gain**, into a
  10-bit 105 MS/s ADC.
- **Single-ended**: measures a node relative to ground — no differential probe
  needed. The supply side of the shunt is AC-flat, so probing the **target
  side** of the shunt yields `-I(t)·R`.
- AC coupling means it cannot read DC (rail droop etc.) — use a real scope for
  that.

## Pinouts

### CW Lite 20-pin header (J2) — relevant pins

```
Top row (odd):   1   3   5   7   9  11  13  15  17  19
Bottom row:      2   4   6   8  10  12  14  16  18  20

 3  = +3.3V  (200 mA, switchable via scope.io.target_pwr)
 2, 17, 19 = GND
 5  = nRST
 10 = TIO1 (UART RX or TX) — not used right now
 12 = TIO2 (UART) — not used right now
 14 = TIO3 (bidirectional, e.g. smartcard IO)
 16 = TIO4 (usually trigger input)
```

SMAs: **MEAS** (input to LNA + ADC), **GLITCH** (pulse output).

### Trezor One (STM32F205) — pinned-out wires

`VCC`, `GND`, `RST`, `SWCLK`, `SWDIO`, `SWO`

### STM32F205 LQFP64 pin numbers

**See `docs/F205_LQFP64_PINOUT.md`** — the full verified map plus the
clean-QFP64 wire list. Key facts (the v1.1 schematic's F1-family symbol lies
about these):

- **VCAP_1 = pin 31** (glitch point), **VCAP_2 = pin 47 — never ground it**
  (the symbol calls 31/47 "VSS_1/VSS_2"; on real F205 silicon they are the
  1.2 V regulator pins, floating on the stock board)
- **SWCLK/PA14 = pin 49** (not 47), SWDIO/PA13 = pin 46
- VDD = 19, 32, 48, 64 (+ 13 VDDA, 1 VBAT); VSS = 18, 63 (+ 12 VSSA)
- PA9 = 42 (TX), PA10 = 43 (RX), BOOT0 = 60, BOOT1/PB2 = 28, NRST = 7

## Wiring diagram (current rig — shunt omitted)

```
      ChipWhisperer-Lite             Breadboard (rotated 90°,             Trezor One
           (CW1173)                       rails vertical)                 (STM32F205)
  +------------------------+         +-------------------------------+         +-----------------+
  |(micro-USB, SAM3U,      |         |                               |         |                 |
  | FPGA on board)         |         |                               |         |SWO (unused)     |
  |                        |         |                               |         |                 |
  |J2 (2x10) on right      |         |                               |         |pinned-out wires |
  |edge, SMA pads          |         |                               |         |on left edge:    |
  |below it:               |         |                               |         |VCC GND RST      |
  |                        |         |                               |         |SWCLK SWDIO SWO  |
  |J2-10 TIO1, J2-12 TIO2  |         |                               |         |                 |
  |UART — unused right now |         |                               |         |                 |
  |                        |         |                               |         |                 |
  |J2-3   +3.3V            +-------->+(+) rail [A]......[B]          +-------->+VCC (power)      |
  |                        |         |                               |         |                 |
  |J2-2   GND              +-------->+(-) rail [A]......[B]          +-------->+GND              |
  |                        |         |                               |         |                 |
  |J2-16  TIO4             +-------->+col 5   [1]......[2]           +-------->+RST (trigger)    |
  |                        |         |                               |         |                 |
  |J2-14  TIO3             +-------->+col 6   [1]......[2]           +-------->+SWDIO (trig)     |
  |                        |         |                               |         |                 |
  |GLITCH mid pad          +-------->+col 7   [1]......[2]           +-------->+VCAP (glitch)    |
  |MEAS pads (unused)      |         |(unused strips)                |         |                 |
  |                        |         |                               |         |                 |
  +------------------------+         +-------------------------------+         +-----------------+
```

- `[A]......[B]` / `[1]......[2]` = **two different holes of the same
  connected strip/rail** — one jumper in from the CW, a separate jumper out
  to the Trezor. Never jam two jumpers into one hole.
- GLITCH comes off the CW SMA-footprint **middle pad** (soldered pin +
  female jumper) → breadboard column → VCAP. Keep both glitch jumpers short.
- **TIO1/TIO2 (UART) unused** — the CW bit-banged UART is dropped for glitch 2
  (9600-only, ~104 µs timing jitter); the bootloader UART moves to the **FTDI**,
  and TIO3 → SWDIO is likewise abandoned (glitch 2 doesn't work over SWD) — see
  *Planned: direct bootloader-UART wiring* below. TIO3 becomes the
  UART-trigger input.
- ST-Link connects **directly** to the Trezor (not via the breadboard):
  SWCLK → SWCLK, SWDIO → SWDIO, GND → GND — **no 3.3V OUT from the
  ST-Link** (its VCC pin only senses).
- Omitted for clarity: SWO (unused), MEAS SMA (nothing to measure until the
  shunt goes in).

## Net list (current rig)

| From | To | Carries |
|---|---|---|
| CW J2-3 (+3.3V) | breadboard **+ rail, hole A** | target power in |
| breadboard **+ rail, hole B** (same rail, different hole) | Trezor VCC | target power out (no shunt yet) |
| CW J2-2 (GND) | breadboard **− rail, hole A** | common ground in |
| breadboard **− rail, hole B** (same rail, different hole) | Trezor GND | common ground out |
| CW J2-16 (TIO4) | breadboard **strip 5, hole 1** | trigger from CW |
| breadboard **strip 5, hole 2** (same strip) | Trezor RST | reset trigger (glitch 1) |
| CW J2-14 (TIO3) | breadboard **strip 6, hole 1** | trigger from CW |
| breadboard **strip 6, hole 2** (same strip) | Trezor SWDIO | read trigger (glitch 2) |
| GLITCH SMA **middle pad** (soldered pin + female jumper) | breadboard **strip 7, hole 1** | glitch pulses in |
| breadboard **strip 7, hole 2** (same strip) | Trezor **VCAP pad** | glitch pulses out — keep both leads short |

Rule: **every through-signal uses two different holes of the same connected
strip/rail** (hole 1 in from the CW, hole 2 out to the Trezor) — never jam
two jumpers into one hole.
| ST-Link | SWCLK, SWDIO, (GND) | debugging/flashing |

## Planned: adding the shunt (10 Ω on hand, not yet installed)

Insert the 10 Ω **in series in the VCC wire between the + rail and the Trezor**
(see net-list delta below), then connect MEAS SMA center to the Trezor side of
it. Everything else stays exactly as wired — glitch path (VCAP) untouched.

| From | To | Carries |
|---|---|---|
| breadboard (+) rail | 10 Ω shunt leg 1 | power through shunt |
| shunt leg 2 → **sense row** | Trezor VCC | VDD ≈ 3.3V − I·R |
| MEAS SMA center | **sense row** (= Trezor side of shunt) | voltage measurement |
| MEAS SMA shell | breadboard (−) rail | ground return |

## Planned: direct bootloader-UART wiring (glitch-2 rig)

Glitch 2 targets the RDP check inside the **UART bootloader's Read Memory
handler** — there is no SWD equivalent (Kraken, SecGlitcher and Jerin Sunny all
glitch over UART). The CW bit-banged UART is dropped: host serial moves to the
**FTDI on `/dev/ttyUSB0` at 115200 8E1**, and the CW does trigger + glitch only.

| From | To | Carries |
|---|---|---|
| FTDI TX (**3.3 V levels!**) | **MCU RX — PA10** (USART1 RX, **current rig**) or **PC11** (USART3 RX) | host bytes: 0x7F, 0x11, address, length |
| **MCU TX — PA9** (USART1 TX, **current rig**) or **PC10** (USART3 TX) | FTDI RX | ACK/NACK + data out |
| FTDI GND | breadboard − rail | common ground |
| FTDI TX line, **tee** → breadboard **strip 8** | CW J2-14 (**TIO3**) | 0x11-byte trigger input to the CW |
| CW J2-10 (**TIO1**) | **BOOT0 — LQFP64 pin 60, only AFTER isolating it from its hard GND tie** | **software-controlled boot mode**: `scope.io.tio1 = True` → next reset enters the bootloader; `False` → firmware. Set the level *before* each reset (BOOT0 is sampled at every reset edge) |
| − rail **or CW J2-12 (TIO2)** | **BOOT1 — PB2, LQFP64 pin 28 — UNCONNECTED on the stock board!** | **must be tied LOW**: the v1.1 schematic has no net on PB2, so BOOT1 floats — with BOOT0 high the boot is a coin flip: bootloader or boot-from-SRAM (hang, dead-GPIO signature). Tying it low makes BOOT0-high = bootloader every time |

- **Both pairs are viable — AN2606 Table 35:** the **F2 bootloader enables
  USART1 (PA9/PA10), USART3 (PC10/PC11) and USART3-alt (PB10/PB11)
  simultaneously**; there is **no USART2 in the F2 bootloader** (the PA2/PA3
  wiring comment in `6-dump_flash_uart.py` is an F0/F4-ism). **Current rig:
  PA9/PA10** (2026-10-11, user — staying on it for now). **PC10/PC11 is the
  VoidStar-proven pair on this exact hardware** (their rig photo wires
  PC10/PC11 + BOOT0) and **physically easier to get to** (user, 2026-10-11)
  — the preferred pair when rewiring. All pairs: 115200 8E1.
- **PC10/PC11 may be on labeled pads at the board edge** (VoidStar's photo
  wires them alongside SWD/BOOT0 — check the board first). If not on pads,
  direct-to-chip like the VCAP green wire. PA9/PA10 alternative needs LQFP64
  soldering: **PA9 = pin 42, PA10 = pin 43, BOOT0 = pin 60** (cross-checked
  against an F205 breakout pinout + the F105/F107 datasheet table).
- **BOOT0 is HARDWIRED to GND on the stock board — no resistor** (confirmed
  from the official v1.1 schematic netlist, 2026-10-11: the BOOT0 net is just
  U1 pin 60 → a GND symbol, directly wired). Tying pin 60 to the + rail as-is
  is a **dead short** — the rail collapses to ~0.3 V (observed 2026-10-11).
  **Isolate first**, then tie high. Two methods (open `docs/archive/
  trezor_v1.1.brd` to find pad 60's trace):
  1. **Cut the trace (preferred)** — light repeated scalpel passes *across*
     the pad-to-ground-via trace (never toward the chip), meter-checking
     pin 60's pad→GND until it flips from ~0 Ω to **open**; then solder the
     wire to pin 60's pad (pin+pad are one node, now isolated). Lowest risk —
     nothing touches the chip.
  2. **Lift the pin (fallback)** — flux + fresh solder on the joint, melt it,
     lever the pin up ~30° with the scalpel from the outer tip (bend ONCE,
     gently — pins fatigue); wick the pad clean; solder the wire to the
     lifted pin and **strain-relief it with glue immediately**.
  Verify with the meter that BOOT0 → GND reads **open**, wire to the + rail,
  confirm the rail holds 3.3 V. With BOOT0 high, every reset enters the
  system bootloader; remove the wire to boot the wallet normally. Kraken
  cites exactly this BOOT0/BOOT1 soldering as the fiddly part of in-situ
  attacks (they socketed the MCU on a BreakingBitcoin board instead).
- **Soldering:** 30 AWG magnet/wire-wrap wire + flux; after each joint, meter
  continuity to the breadboard column and check no shorts to the neighboring
  pins; strain-relief the wires so the pads don't lift.
- **FTDI must be set to 3.3 V signaling** — 5 V will damage the STM32.
- **TIO3 → SWDIO is freed** (glitch 2 no longer goes over SWD) — TIO3 becomes
  the UART-trigger input; TIO4 stays on RST (glitch 1 + resets).
- **Trigger:** arm immediately before sending `0x11`, trigger on the UART edge
  on TIO3 (the start-bit edge is enough if nothing else transmits after
  arming), or use the CW UART decoder + SecGlitcher's even-parity FPGA fix for
  exact `0x11` matching. Coarse sweep ≈ **2 byte-times ≈ 190 µs after the 0x11
  start bit ± ~11 µs jitter @ 115200**, then narrow.
- **BOOT0 control status (CONFIRMED 2026-10-22):** the lift + TIO1 wiring
  **works** — power-cycle with TIO1 LOW boots the firmware (screen on,
  "unknown bootloader" message = the wallet firmware running), so the die
  sees TIO1's level and the pin-60 bond is fine. The only remaining fault:
  **the BOOT1 tie at pin 28 is not conducting** (BOOT1 floats high → every
  BOOT0-high power-cycle goes boot-from-SRAM → dead hang, GPIOA 0x0000 +
  garbage SRAM). One wire to re-do: pin 28 → − rail, verified under
  magnification against the pad map (27=PB1, **28=PB2**, 29=PB10).
- **Per-attempt loop (no-reset variant — the plan while BOOT0 control is
  broken):** sync ONCE (`0x7F` → ACK), then per attempt: **arm → `0x11` +
  checksum → glitch → read the response** — **no reset between attempts**
  (the bootloader stays synced; only the scope re-arms). The classic
  reset-per-attempt loop (soft reset → re-sync → arm → `0x11` → glitch) is
  for when BOOT0 control is reliable. Per Kraken the RDP1 downgrade
  persists across soft resets until a power-cycle; after any power-cycle,
  re-run glitch 1 first.

## Waveshare STM32-QFP64 socket board (clean-chip rig) — schematic findings

Source: `docs/archive/waveshare-stm32-qfp64-schematic.pdf` (+ `.txt` text
dump), saved 2026-10-22. Key facts extracted from the official schematic:

1. **All MCU VDD pads share the AMS1117 3.3 V rail** (VDD_1/2/3/4, VDDA, VBAT
   all on one net with the LDO output). Power injection can collapse to
   **one 3.3 V wire into any VDD header pin** + one GND — fewer wires, fewer
   failure points. (Bench-verify with a beep test before removing wires.)
2. **⚠ 2.2 µF capacitors on pads 31 and 47** (COMP.C2/COMP.C3, via COMP.H1/
   COMP.H2 jumper headers). These are the VCAP pins on F2/F4 silicon — the
   board fits the datasheet caps, **but pad 31 is our glitch injection point
   and a 2.2 µF cap rounds the glitch off**. For glitch campaigns: **open the
   COMP.H1 jumper** (pad 31 cap out of circuit) — closer to the stock Trezor
   board, which leaves both VCAP pins floating. Keep 47's cap on for
   stability when not glitching.
3. **BOOT0/BOOT1 jumper headers** (3-pin: 3.3 V / signal / GND, with
   BOOT0.R1/BOOT1.R1 resistors) — both jumpers **OFF** in our rig so TIO1
   (BOOT0, pad 60) and TIO3 (BOOT1, pad 28) drive the pads uncontested.
4. **20-pin JTAG/SWD port is ARM-standard**: pin 7 = JTMS/SWDIO → pad 46,
   pin 9 = JTCK/SWCLK → pad 49 (F2 position of the device-selection
   jumpers). Full uncut ribbon works for SWD — proven.
5. **UART headers P2/P3 carry a 3.3 V pin** — never connect the FTDI's VCC
   to it (back-feeds the rail and defeats CW power control; suspected cause
   of the earlier always-lit power LED). Use only TX/RX/GND. U1RX → pad 43
   (PA10), U1TX → pad 42 (PA9).
6. The board's MCU symbol is F1-lineage again (VSS at 31/47, PD0/PD1 at
   5/6) — same trap as the Trezor schematic; trust
   `docs/F205_LQFP64_PINOUT.md` for real F205 pad functions.
7. **ST-Link wiring (final, proven)**: full ribbon into the 20-pin port.
   Direct jumper wires to pads 46/49 failed repeatedly — **root cause: the
   expansion headers are NOT labeled PIN1–PIN64**. Several pads appear only
   under function names: pad 7 = **RET**, pads 5/6 = OSIN/OSOUT, pad 28 =
   **BOOT1**, pad 60 = **BOOT0**, pads 42/43 = U1 TX/RX, pads 46/49 =
   JTMS/JTCK. Counting to "PIN46"/"PIN49"/"PIN7" lands on wrong nets. Wire
   by the printed label, not the pad number. ST-Link pin 15 (nSRST) lands
   on the port's pin 15 which is **not** the JNRST net on this board
   (JNRST is port pins 1–2) — so no reset contention with TIO4.

## Shunt sizing

| Target draw | Drop @ 10 Ω | Verdict |
|---|---|---|
| 10 mA | 0.1 V | Fine |
| 20 mA | 0.2 V | Fine (VDD ≈ 3.1 V) |
| 40 mA | 0.4 V | Marginal (VDD ≈ 2.9 V — near STM32 brownout) |
| 60 mA | 0.6 V | Too much — target may crash/reset |

- Feeding the **whole Trezor board** (display, flash, etc.) through J2-3 (200 mA
  limit) means `I_total × 10 Ω` drop — measure total board current before
  trusting the rig.
- If drop is too much: parallel two 10 Ω (→ 5 Ω) or feed only the STM32 VDD
  pins through the shunt.
- Higher R → better SNR; lean on CW gain (up to 55 dB) to compensate lower R.

## Key topology points

1. **Shunt between + rail and Trezor; MEAS taps the Trezor side** — probing the
   + rail side sees almost nothing.
2. **Everything lands on the breadboard — no direct CW→Trezor wires.**
   Power uses the +/− rails; TIO4, TIO3 and GLITCH each land on their own
   terminal-strip column, then a second jumper runs from that column to the
   Trezor pin. Glitch hits the **VCAP pad**, not VCC — so the planned shunt
   (VCC path) and the glitch path are electrically separate, and adding the
   shunt shouldn't perturb the logged glitch-1 parameters.
3. **Glitch path is the sensitive one** — it now runs CW SMA pads → soldered
   pin → female jumper → breadboard column → jumper → VCAP. Every extra cm
   and every breadboard contact adds inductance/resistance that rounds off
   the pulse: keep both jumpers as short as possible and seated firmly
   (reseat if glitches become unreliable).
4. **ST-Link must not power the target** — no 3.3V OUT from ST-Link; only
   SWCLK/SWDIO/GND (VCC sense pin only senses).
5. **Optional trigger**: reconfigure SWO pin as GPIO toggle in firmware →
   wire SWO → CW J2-16 (TIO4) for exact-window triggering.
6. **Breadboard caveats**: power path OK at these currents, but rails are
   flaky — reseat jumpers if the Trezor boots erratically or glitches become
   inconsistent. Note the CW Lite has **no SMA jacks on this unit** — the
   SMA footprints are 3-pad holes (signal center, grounds outside); the
   middle pad carries the signal (only the GLITCH middle pad is used, via a
   soldered pin + female jumper).

## Verification procedure

1. Current draw first: multimeter in series with 3.3V feed, run heaviest
   target operation, note peak/typical current (see drop table above).
2. Install shunt, power up, confirm Trezor boots normally with shunt in
   place (no random resets — else drop too high or cold joint).
3. Software sanity check:

```python
import chipwhisperer as cw
scope = cw.scope()

scope.gain.gain = 30   # raise toward 45 if small; lower if clipped at ±0.5
scope.adc.samples = 5000
scope.adc.timeout = 2
scope.trigger.triggers = "tio4"  # or existing trigger source

scope.arm()
# ...trigger the target...
scope.capture()
t = scope.get_last_trace()
print(f"min={t.min():.3f} max={t.max():.3f}")
```

- amplitude < ~0.05 → raise gain
- flat-topped at ±0.5 → lower gain
- healthy: clock-rate ripple + activity bursts around crypto ops

## References

- CW Lite / 20-pin connector docs: https://chipwhisperer.readthedocs.io/en/latest/Capture/20-pin-connector.html
- CW303 Arm target (shunt R66 reference design): https://chipwhisperer.readthedocs.io/en/latest/Targets/CW303%20Arm.html
- NewAE forum thread on MEAS port / shunt topology: https://forum.newae.com/t/how-does-cw-lite-measure-port-actually-work/1348
- NAE-CW1173 datasheet: https://media.newae.com/datasheets/NAE-CW1173_datasheet.pdf
