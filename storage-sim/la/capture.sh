#!/bin/bash
# LA capture — fx2lafw Saleae Logic on the UART lines (passive tap, does NOT
# damp the glitch; safe to run while the campaign fires).
#
# Channel map (this rig, verified 2026-10-30):
#   D0 = UART TX  (host/FTDI -> chip)   carries 7F sync, 11 EE Read Memory
#   D1 = UART RX  (chip -> host/FTDI)   carries 79 ACK, 1F NACK
#   D2..D7 = unused / floating
#
# Usage: capture.sh [OUT.sr] [RATE] [SAMPLES]
#   OUT.sr   output file            (default: ./la_cap.sr)
#   RATE     samplerate             (default: 2m  -> 0.5us/sample, 8.7 samp/bit @115200)
#   SAMPLES  number of samples      (default: 6000000 -> 3 s @ 2 MHz, spans ~2 shots)
set -u
OUT="${1:-./la_cap.sr}"
RATE="${2:-2m}"
SAMPLES="${3:-6000000}"
echo "[la] capturing $SAMPLES samples @ $RATE -> $OUT  (campaign may keep firing)"
sigrok-cli --driver fx2lafw --config samplerate="$RATE" --samples "$SAMPLES" -o "$OUT"
echo "[la] done: $(ls -la "$OUT" 2>/dev/null)"
