# RIG — STM32F205 glitch bench: wiring & config (authoritative)

Living hardware reference for the RDP1 glitch campaign. **This file supersedes
the pin mapping in `CLAUDE.md` where they conflict** — correct it in place as
the bench changes, and keep CLAUDE.md's "Rig and environment" section pointing
here. Last updated **2026-11-02**.

---

## CW-Lite TIO map  (AUTHORITATIVE — user, 2026-11-02)

| CW pin | Function | Notes |
|--------|----------|-------|
| **TIO1** | **BOOT0** | high → bootloader select (see Boot). Also has a 3V3 jumper today. |
| **TIO2** | **BOOT1** | **must be LOW for system bootloader.** Floating/high → chip boots SRAM. |
| **TIO3** | **Trigger tap (QFP64)** | CW ext-trigger input for a glitch script (taps the UART line to self-trigger). Not a comms path — comms is the FTDI. |
| **TIO4** | **NRST** | reset. |
| **Glitch SMA** | crowbar (open-drain FET → GND) on **VCAP_1 (pin 31)** | MILLIVOLT-scale pulse; `enable_only` needs `glitch_hp`/`glitch_lp` armed or it's a no-op. |
| **io.target_pwr** | VDD supply MOSFET | `True` = 3V3 on. |

> ⚠️ **Conflict with CLAUDE.md** (which still says `TIO2=high_z`, and treats
> only TIO1=BOOT0 / TIO4=NRST): **TIO2=BOOT1 and TIO3=UART_RX are the correct
> current wiring.** Update CLAUDE.md to match. Several scripts
> (`rdp1_uart_test.py`, the campaign's `power_into_bootloader`) still set
> `tio2 = 'high_z'` — on this rig that leaves **BOOT1 undriven**, which can
> block system-bootloader entry (no `0x7F→0x79` ACK). Drive **TIO2 = False**
> (BOOT1 low) for bootloader work.

---

## Target

- **STM32F205RET6, LQFP64 (QFP64).** Intended RDP level: **RDP1**.
- Pins confirmed by DMM this session (2026-11-02):
  - **pin 31 = VCAP_1** — internal 1.2 V core LDO output + smoothing cap.
    Idle ≈ 1.2 V when the core is up; **also the glitch-injection node** (Ch1 SMA).
  - **pin 32 = VDD** — 3.3 V rail.
- VCAP decoupling cap(s) were pulled for the crowbar campaign and are being
  restored (2026-11-02). STM32F2's LDO needs capacitance on VCAP_1 to start.

## Boot configuration (LQFP64 / STM32F2)

| BOOT0 | BOOT1 | Boots from |
|-------|-------|------------|
| 0 (LOW) | X | Main flash = device firmware |
| 1 (HIGH) | 0 | **System bootloader** (UART/DFU ROM) ← what we want |
| 1 (HIGH) | 1 | Embedded SRAM |

- For bootloader entry: **TIO1 high (BOOT0=1), TIO2 low (BOOT1=0)**.
- BOOT0 also jumpered to 3V3 today. Pick one drive method; TIO1-high + 3V3
  jumper both high is fine. **Never jumper BOOT0 low while TIO1 drives high**
  (push-pull-into-GND contention — can stress the TIO pin).

## UART (bootloader comms)

- **FTDI FT232R, `/dev/ttyUSB0`** (VID `0403:6001`), **115200 8E1**.
- This is the comms path for the ST bootloader: `0x7F`→`0x79` autobaud,
  Get/GetID, Read Memory. **Not on the CW.**
- `serialfind.py` handles ttyUSB0↔1 re-enumeration churn.
- Chip bootloader USART = **USART1: PA9 = TX (pin 42), PA10 = RX (pin 43)**
  on LQFP64. Expected wiring: **FTDI TX → pin 43 (PA10)**, **pin 42 (PA9) →
  FTDI RX**, common GND. *(Verify by continuity if ACK is silent — a lifted
  wire or TX↔RX swap is the usual culprit.)*

## Boot / reset discipline

- System bootloader **only via a full power cycle** with BOOT0 high **and
  BOOT1 low**. NRST-only does **not** recover from a glitch lockup.
- NRST from *clean* firmware does enter the bootloader and preserves SRAM.

## CW config discipline

- Fresh `cw.scope()` open → set `clock.clkgen_freq` **FIRST**, then glitch
  params. Never reconfigure clkgen mid-session (stale-MMCM artifacts).
- `enable_only` = one continuous `repeat`-cycle crowbar pulse (width/offset
  inert; `repeat` is the strength knob). Crowbar is open-drain to GND — arm
  `glitch_hp`/`glitch_lp` or every shot is a no-op.
- FPGA bitstream reload is built into `setup()`.

## Devices on the bench

| Device | Address | Notes |
|--------|---------|-------|
| CW-Lite CW1173 | USB `2b3e:ace2`, CDC `/dev/ttyACM0` | glitch + power + boot pins |
| FTDI FT232R | USB `0403:6001`, `/dev/ttyUSB0` | bootloader UART, 115200 8E1 |
| ST-Link | SWD (USB `0483`) | debug port (blocked at RDP1 for flash) |
| LA fx2lafw | USB | UART TX/RX only; can't resolve the ~32 ns pulses |
| Siglent SDS1202X-E | `10.11.13.220` VXI-11 | **measurement only** — never on the glitch node during firing. `SCDP` returns **BMP**, not PNG. |

- All Python: **`/home/tdaly/.cwvenv/bin/python`** (venv: chipwhisperer,
  python-vxi11, PIL, mss).

## Known crowbar-hardware caveat (2026-11-02)

- The crowbar FET on the glitch SMA can fail **short** after heavy
  `enable_only`+SMA firing, clamping **VCAP_1 to 0 V** even with the gate off
  (VDD still 3.3 V, core dead → no firmware, no bootloader, SWD silent).
  Diagnose by unplugging the SMA at VCAP_1: if pin 31 returns to ~1.2 V, the
  crowbar leg was the short; the chip is fine.

---

## Authoritative chip-state tool

**`investigate_chip.py`** is the single read-only "what state is this chip"
report. It triangulates over SWD (option-byte RDP + flash-readability
cross-check + core state) and demotes the bootloader ACK to a *secondary*
signal. **Judge RDP from this, never from a bootloader ACK.** Run it with
`/home/tdaly/.cwvenv/bin/python investigate_chip.py`.

## RESOLVED 2026-11-02 — no-`0x7F`-ACK root cause = BOOT0 not high

Current fresh chip per `investigate_chip.py`: **alive (VDD 3.23 V, DEV_ID
0x411, Cortex-M3), RDP LEVEL 1** (OPTCR 0x0FFFFFED / RDP byte 0xFF; SRAM
readable, all flash/system/OTP blocked → agrees with L1). The evening's
bootloader silence was **not** UART wiring: **DHCSR = 0x03090000 → core
LOCKUP**, halted regs `PC=0xFFFFFFFE SP=0xFFFFFEE0 LR=0xFFFFFFF9` = all-FF =
**booting blank/invalid flash → HardFault → lockup.** So the chip is in **flash
boot, not the bootloader** → nothing answers `0x7F`. **BOOT0 is not actually
high at the pin** (3V3 jumper not reaching **BOOT0 = pin 60** on LQFP64).
**Fix:** verify 3V3 at pin 60 (or drive TIO1 high and confirm) → chip enters
the ST bootloader → at RDP1 it should ACK `0x7F` and NACK Read Memory.
