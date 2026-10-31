#!/bin/bash
# Deterministic status heartbeat: append a campaign digest every INTERVAL
# seconds to the status log (a desktop window tails it). Cannot stall.
# Stops itself when uid AND otp3 are both banked, or the campaign dies for
# several checks in a row. Launch with run_in_background.
INTERVAL="${1:-1800}"      # 30 min default
LOG=/tmp/opencode/campaign_status.log
ACC=/home/tdaly/trezor-btc/storage-sim/dumps/accum
dead=0
while true; do
  bash /home/tdaly/trezor-btc/storage-sim/status.sh >> "$LOG" 2>&1
  # stop if the win is in
  if [ -f "$ACC/uid.bin" ] && [ -f "$ACC/otp3.bin" ]; then
    echo "[heartbeat] uid+otp3 both banked - stopping heartbeat" >> "$LOG"; break
  fi
  # stop if the campaign has clearly died (no python) for 3 checks running
  if ! ps -eo args | grep -q '[c]wvenv/bin/python -u rdp1'; then
    dead=$((dead+1)); [ "$dead" -ge 3 ] && { echo "[heartbeat] campaign not running for 3 checks - stopping" >> "$LOG"; break; }
  else
    dead=0
  fi
  sleep "$INTERVAL"
done
