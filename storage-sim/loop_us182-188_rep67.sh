#!/bin/bash
# Overnight grind at the LA-verified window (us 182-188, glitch 191-197us after
# 0x11), strength rolling rep6-7 (36-42ns). Each pass is one sweep (~3000 shots).
# STOP conditions:
#   1. TARGETED FULL DUMP - all 66 chunks assembled (storage_dump.bin). The win.
#   2. PASS_CAP passes completed (data collection done).
# A partial real chunk is REPORTED but does NOT stop the grind (goal is the full
# dump, which a session-latching flip drains in one pass via chain_unglitched).
# New driver: stage-2 removed, cross-read confirm + A/B, lazy dump dir, alert.
set -u
cd /home/tdaly/trezor-btc/storage-sim
LOG=/tmp/opencode/cal182_loop.log
PASS_CAP=10
PASS=0
while [ $PASS -lt $PASS_CAP ]; do
  PASS=$((PASS+1))
  echo "=== PASS $PASS/$PASS_CAP  $(date '+%m-%d %H:%M:%S') ===" | tee -a "$LOG"
  T0=$(date +%s)
  G_CLKGEN=166666667 G_OFFSET=-45 G_WIDTH=5 \
  G_US_MIN=182 G_US_MAX=188 G_RND_LO=33 G_RND_HI=45 \
  G_SAMPLES=3 G_COOLDOWN=0.15 G_RESET_EVERY=1 \
  G_SHOTS=15000 G_TAG=cal182r67p${PASS} \
  /home/tdaly/.cwvenv/bin/python -u rdp1_glitch_campaign_full_mem_dump.py 2>&1 | tee -a "$LOG"
  DT=$(( $(date +%s) - T0 ))
  # 1) TARGETED FULL DUMP -> stop
  if ls dumps/run_*/storage_dump.bin >/dev/null 2>&1; then
    echo "=== *** FULL DUMP COMPLETE on pass $PASS -> $(ls dumps/run_*/storage_dump.bin)  STOPPING ***" | tee -a "$LOG"
    break
  fi
  # 2) partial real chunk -> milestone, but KEEP grinding toward the full dump
  REAL=$(ls dumps/run_*/*.bin 2>/dev/null | grep -v '\.bad\.bin$' | tr '\n' ' ')
  [ -n "$REAL" ] && echo "=== !!! REAL CHUNK banked (partial): $REAL - continuing toward FULL DUMP !!!" | tee -a "$LOG"
  GH=$(ls dumps/run_*/*.bad.bin 2>/dev/null | wc -l)
  echo "=== pass $PASS done (${DT}s). full dump: no. real chunks: ${REAL:-none}. ghosts(all-FF): $GH. ===" | tee -a "$LOG"
  # fast-fail backoff: a pass ending in <60s means the rig is down (CW open fails)
  if [ $DT -lt 60 ]; then
    echo "=== pass $PASS died in ${DT}s - RIG MAY BE DOWN, backing off 120s ===" | tee -a "$LOG"; sleep 120
  else
    sleep 3
  fi
done
echo "=== GRIND ENDED after pass $PASS (cap $PASS_CAP) $(date '+%m-%d %H:%M:%S') ===" | tee -a "$LOG"
