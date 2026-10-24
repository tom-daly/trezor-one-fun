# Width-stretcher glitch rig — parts list

Fixes the one broken knob on our CW-Lite: the GLITCH pad's pulse width is
hardware-stuck at ~60 ns (DCM partial-reconfig never applies). This board
takes the CW's *verified* 60 ns timing tick and stretches it to an
adjustable 100 ns–2 µs crowbar pulse into the VCAP node (pad 31).

```
CW GLITCH pad ──[100R]──► /A or /B  74LVC1G123  Q ──► 1k ──► FET gate
                           monostable                     │
CW GND ──────────► VCC/GND (3.3 V)              SI2302/IRLZ44N
                                                 D ──► VCAP (PIN31 pad, shortest lead)
                          R_pot (1–10k)                 S ──► GND
                          C_sel (100p/1n/10n)
```

## Core BOM (~$8–12)

| # | Part | Example / package | Purpose | Est. |
|---|------|-------------------|---------|------|
| 1 | Monostable, single | **74LVC1G123DBVR** (SOT23-6) or **74HC123** (DIP-16, breadboard-friendly) | turns the 60 ns CW tick into an RC-set pulse | $0.50–1 |
| 2 | Logic-level N-channel MOSFET, low RDS(on) | **SI2302** / **AOI3400** (SOT-23) or **IRLZ44N** (TO-220, works at 3.3 V gate) | the crowbar that shorts VCAP to GND | $0.50–1 |
| 3 | Trim pot 1–10 kΩ | any single-turn trimmer | fine width adjust | $0.50 |
| 4 | Cap set: 100 pF, 1 nF, 10 nF (ceramic) | 2 of each | coarse width range (see table below) | $1 |
| 5 | Resistors: 1×100 Ω, 2×1 kΩ | 1/4 W anything | input series, gate series/pull-down | — |
| 6 | Breadboard + jumper wires | — | assembly | — |
| 7 | (If SOT-23 parts) SOT-23→DIP adapter breakouts | 5-pack | breadboarding SMD | $2 |

Total new from Digi-Key/Mouser: **~$10 + shipping**; from a hobby drawer,
probably **free**.

## Width ranges with tw ≈ 0.45·R·C (74HC123; LVC1G123 K ≈ 0.45 similar)

| C | R = 1 kΩ | R = 5 kΩ | R = 10 kΩ |
|------|----------|----------|-----------|
| 100 pF | ~45 ns | ~225 ns | ~450 ns |
| 1 nF | ~450 ns | ~2.2 µs | ~4.5 µs |
| 10 nF | ~4.5 µs | ~22 µs | ~45 µs |

Start zone per our data: **C = 1 nF, R ≈ 500 Ω–2 kΩ → ~200 ns–1 µs** —
sweep wider once the LA confirms the shape.

## Wiring notes

- Monostable input: **A or B** (use whichever edge the CW tick provides —
  measure with the LA; /A triggers on falling, B on rising per datasheet
  wiring). 100 Ω series from the CW GLITCH pad.
- **REXT/CEXT pins** of the '123 carry the R and C — keep that loop tight.
- FET: gate via 1 kΩ (stops ringing), **10 kΩ gate pull-down to GND** so the
  crowbar can never conduct when idle. Drain → VCAP wire **as short as
  possible** (< 5 cm); source → board GND.
- Power the '123 from the CW's 3.3 V (J2) so grounds share naturally.
- CW-side settings once built: `output='enable_only'`, `repeat=1` — every
  other script/campaign unchanged.

## Bring-up procedure (after assembly)

1. Continuity + shorts check before connecting to the CW or the target.
2. `pulse_char.py` with the LA on the FET gate (or drain): verify the pulse
   width actually tracks R/C and lands at the requested ext_offset.
3. Scope/DMM the VCAP pad idle voltage (~1.2–1.8 V) — must be undisturbed
   until a shot fires.
4. Re-run the campaign: ext 178–186 µs, step 0.1 µs, repeat=1, sweeping R.

## Fallback options (if parts are a hassle)

- **74LVC1G14 Schmitt + diode+RC one-shot** — cruder width control, same
  idea, ~$3.
- **DIY FPGA glitcher** (secglitcher pattern, Lattice iCE40/ECP5 + FET
  module, ~$50–100) — standalone, ns-programmable, more build effort.
- **MCU glitcher** (STM32H7-class, input-capture → delay → compare, ~$20) —
  adequate resolution, firmware work.
- **Purchase: ChipWhisperer Husky** — real money, solves it out of the box.
