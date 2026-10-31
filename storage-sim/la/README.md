# LA toolset — fx2lafw UART tap

Passive logic-analyzer scripts for the RDP1 glitch rig. The Saleae Logic
(`0925:3881`, fx2lafw) sits on the **UART lines only** — a slow, wrong-node tap
that **does not damp the glitch**, so it is safe to run *while the campaign
fires* (unlike the scope on VCAP). Use it to sanity-check comms and to measure
command/response timing without touching the glitch node.

## Channel map (verified 2026-10-30)
| ch | line | carries |
|----|------|---------|
| D0 | UART **TX** (host/FTDI → chip) | `7F` sync, `11 EE` Read Memory command |
| D1 | UART **RX** (chip → host/FTDI) | `79` ACK, `1F` NACK |
| D2–D7 | unused / floating | — |

UART is **115200 8E1** (even parity) — the STM32 system bootloader default.

## Scripts
| file | what |
|------|------|
| `capture.sh [OUT.sr] [RATE] [SAMPLES]` | grab a trace (default 3 s @ 2 MHz → `la_cap.sr`) |
| `decode.sh [IN.sr] [BAUD]` | print the TX/RX byte streams (sanity view) |
| `timing.py [IN.sr]` | measure `0x11`→NACK latency vs the ~196.5 µs calibration |

## Typical session
```sh
cd /home/tdaly/trezor-btc/storage-sim/la
bash capture.sh la_cap.sr 2m 6000000      # 3 s @ 2 MHz
bash decode.sh la_cap.sr                   # expect TX: 7F 11 EE … / RX: 79 1F 1F …
/home/tdaly/.cwvenv/bin/python timing.py la_cap.sr
```

## Reference numbers (calibration)
- 2-byte command airtime @115200 8E1 ≈ **191 µs**
- NACK onset ≈ **196.5 µs** after the `0x11` start
- A glitched **SUCCESS** shows `79` (ACK) on RX where an un-glitched RDP1 chip
  answers `1F` (NACK). The LA can confirm *that an ACK happened*, but it cannot
  resolve the ~32 ns crowbar pulse itself — that needs the scope on VCAP
  (measurement-only, never during firing).

See `../FINDINGS.md` for the campaign log.
