# STM32F205 LQFP64 — verified pinout (project reference)

**Save date:** 2026-10-22. Ground truth for this rig. Do not trust the v1.1
schematic's pin map blindly — see the trap warning below.

## The trap: the official schematic uses an F1-family symbol

`trezor_v1.1.sch` draws U1 with the **`STM32F10XRXT6`** symbol
("STM32F101/103 family") while stuffing `STM32F205RET6`. Its pin map is
F1/F105-lineage and is **wrong for the F205 silicon in three places that
matter**:

| Pad | Symbol says (F1) | Real F205 silicon | Evidence |
|---|---|---|---|
| 31 | VSS_1 | **VCAP_1** | .brd: pad 31 is net `N$4`, a **single-contact floating net** (not GND!); glitch-1 landed here 6× verified |
| 47 | VSS_2 | **VCAP_2** | .brd: pad 47 is net `N$8`, also single-contact/floating; grounding it would short the 1.2 V core regulator |
| 5/6 | PD0/PD1 | PH0/PH1 | F2 port D; both are the HSE crystal pins either way (.brd: XTAL2/XTAL1) |

Also note: **SWCLK/PA14 = pin 49** (not 47 — on this package PA14 sits after
the VCAP_2/VDD_2 pair at 47/48).

Silicon is confirmed F2: DBGMCU IDCODE `0x411` (STM32F2xx) read via SWD on the
locked Trezor.

## Full LQFP64 map

Legend: **[BRD]** = verified in `trezor_v1.1.brd` copper (board was designed
for F205R silicon and works in production); **[BHV]** = verified behaviorally
on the locked Trezor; **[SYM]** = from the v1.1 symbol map (F1-style), not
copper-verified, consistent with all cross-checks, not needed by the rig.

| Pin | Name | Notes |
|---|---|---|
| 1 | VBAT | [BRD] to +3V3 |
| 2 | PC13 | [SYM] |
| 3 | PC14/OSC32_IN | [SYM] |
| 4 | PC15/OSC32_OUT | [SYM] |
| 5 | PH0/OSC_IN | [BRD] crystal net XTAL2 |
| 6 | PH1/OSC_OUT | [BRD] crystal net XTAL1 |
| 7 | NRST | [BRD] reset circuit (N$2) |
| 8–11 | PC0–PC3 | [SYM] (PC2 used on board: N$20) |
| 12 | VSSA | [BRD] GND |
| 13 | VDDA | [BRD] +3V3 |
| 14–17 | PA0–PA3 | [SYM] |
| 18 | VSS | [BRD] GND |
| 19 | VDD | [BRD] +3V3 |
| 20–23 | PA4–PA7 | [SYM] (PA4/PA5/PA7 used on board) |
| 24 | PC4 | [SYM] |
| 25 | PC5 | [SYM] (used: N$19) |
| 26 | PB0 | [SYM] (used: N$3) |
| 27 | PB1 | [SYM] (used: N$7) |
| 28 | **PB2/BOOT1** | [SYM] **no net on stock board** (floats); locked chip's input bond is DEAD — clean chips are fine |
| 29 | PB10 | [SYM] (USART3-alt TX in bootloader) |
| 30 | PB11 | [SYM] (USART3-alt RX in bootloader) |
| 31 | **VCAP_1** | [BRD+BHV] floating on stock board (no cap!); **glitch injection point** |
| 32 | VDD | [BRD] +3V3 |
| 33–36 | PB12–PB15 | [SYM] |
| 37–40 | PC6–PC9 | [SYM] — symbol-sourced placement, never needed by the rig |
| 41 | PA8 | [SYM] |
| 42 | **PA9** | [BHV] USART1_TX → FTDI RX |
| 43 | **PA10** | [BHV] USART1_RX ← FTDI TX |
| 44 | PA11 | [BRD] USB D− (N$18) |
| 45 | PA12 | [BRD] USB D+ |
| 46 | **PA13/SWDIO** | [BRD+BHV] SWD connector net N$15 |
| 47 | **VCAP_2** | [BRD] floating on stock board — **DO NOT GROUND** |
| 48 | VDD | [BRD] +3V3 |
| 49 | **PA14/SWCLK** | [BRD+BHV] SWD connector net N$17 |
| 50 | PA15 | [SYM] |
| 51 | PC10 | [SYM] USART3_TX (VoidStar-proven bootloader pair) |
| 52 | PC11 | [SYM] USART3_RX (VoidStar-proven bootloader pair) |
| 53 | PC12 | [SYM] |
| 54 | PD2 | [SYM] |
| 55 | PB3 | [BRD] used (N$14 — likely SWO) |
| 56–59 | PB4–PB7 | [SYM] |
| 60 | **BOOT0** | [BRD+BHV] hardwired GND on stock board (lifted on our locked unit, driven by CW TIO1 — works) |
| 61 | PB8 | [SYM] |
| 62 | PB9 | [SYM] |
| 63 | VSS | [BRD] GND |
| 64 | VDD | [BRD] +3V3 |

## Clean QFP64 (glitch-practice / technique-validation rig) — wire list

| Net | Pins / connections |
|---|---|
| +3.3 V (CW J2-3) | pins **1, 13, 19, 32, 48, 64** + 100 nF to GND at each VDD + one 4.7 µF bulk |
| GND (CW J2-2) | pins **12, 18, 63** |
| VCAP_1 (31) | **glitch output** (already wired) — no cap, matches stock board & locked rig |
| VCAP_2 (47) | **leave floating** (stock board does; never ground it) |
| BOOT0 (60) | CW **TIO1 (J2-10)** |
| BOOT1 (28) | **− rail (GND)** — alive on clean chips; tied low → BOOT0-high = system bootloader |
| NRST (7) | reset column ← CW **TIO4 (J2-16)** |
| SWDIO (46) | ST-Link SWDIO |
| SWCLK (49) | ST-Link SWCLK |
| UART RX (43, PA10) | FTDI **TX** (3.3 V signaling!) |
| UART TX (42, PA9) | FTDI **RX** |

- **No crystal needed** — bootloader and test code run on the internal HSI.
- Decoupling matters more than on the Trezor PCB (breadboard/adapter is
  noisy): keep the 100 nF caps close to the chip.
- The stock board leaves **both VCAP pins floating** (N$4/N$8 are
  single-contact nets) — that's why the rig also runs capless and why glitches
  are sharp on this target family.

## Evidence trail

1. `trezor_v1.1.sch` device: `STM32F10XRXT6` (F101/103 library), value
   `STM32F205RET6` — F1-lineage symbol map.
2. `trezor_v1.1.brd` copper: pad→net extraction (2026-10-22) — pads 31/47 on
   floating single-contact nets N$4/N$8; 32/48/64/19 on +3V3; 18/63 on GND;
   60 on GND; 46/49 on SWD nets; 45 on USB_D_P.
3. Behavioral on locked Trezor: glitch-1 via pad 31 (6× verified), PA10=43
   reached by FTDI TX, BOOT0=60 responds to TIO1, SWD on 46/49 works,
   IDCODE `0x411` = F2.
4. ST migration doc (F2→L4, device.report): VCAP_1 = 31 on LQFP64 — matches.
