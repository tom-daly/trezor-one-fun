#!/bin/bash
# LA decode — dump the UART byte streams from a capture (sanity view).
# TX (D0) should show: 7F ... 11 EE ...   RX (D1): 79 ... 1F 1F ...
# A glitched SUCCESS shows 79 (ACK) where RX would otherwise be 1F.
#
# Usage: decode.sh [IN.sr] [BAUD]
set -u
IN="${1:-./la_cap.sr}"
BAUD="${2:-115200}"
# 8E1 = even parity; the bootloader UART is 8E1.
echo "==== TX  (D0, host->chip)  baud=$BAUD 8E1 ===="
sigrok-cli -i "$IN" -P uart:rx=D0:baudrate="$BAUD":parity=even -A uart=rx-data \
  2>/dev/null | grep -oE '[0-9A-Fa-f]{2}' | tr '\n' ' '; echo
echo "==== RX  (D1, chip->host)  baud=$BAUD 8E1 ===="
sigrok-cli -i "$IN" -P uart:rx=D1:baudrate="$BAUD":parity=even -A uart=rx-data \
  2>/dev/null | grep -oE '[0-9A-Fa-f]{2}' | tr '\n' ' '; echo
