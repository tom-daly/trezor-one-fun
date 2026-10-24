#!/bin/bash
# Overnight glitch-2 hammer: rerun the proven gray-zone config until a
# JACKPOT appears (or the loop is stopped). Each pass adds hundreds more
# stochastic samples at the known-corruptible settings.
#
# Direct-wire gray zone (found 2026-10-24): reps 100-800 produce dead +
# corrupted replies (fc/fe) at the decision window; reps <100 = nothing
# (10,800 overnight shots proved the old reps 24-27 band is sub-threshold
# through the direct wire - the old gray zone was a lossy-path artifact).
# With NRST fast recovery this runs ~2 shots/s incl. resyncs.
set -u
cd /home/tdaly/trezor-btc/storage-sim
PASS=0
while true; do
    PASS=$((PASS+1))
    echo "=== pass $PASS  $(date +%H:%M:%S) ==="
    T0=$(date +%s)
    G_CLKGEN=4e6 G_OFFSET=-45 G_WIDTH=40 G_REPEATS=100,125,150 \
    G_EXT_MIN=700 G_EXT_MAX=750 G_STEP=1 G_SAMPLES=30 \
    G_COOLDOWN=0.02 G_REST_EVERY=800 G_REST_S=10 \
    /home/tdaly/.cwvenv/bin/python -u glitch2_campaign.py \
        >> /tmp/opencode/hammer.log 2>&1
    if ls JACKPOT_*.bin >/dev/null 2>&1; then
        echo "=== JACKPOT ON PASS $PASS ==="
        ls -la JACKPOT_*.bin
        break
    fi
    # rapid-fail backoff: a pass lasting <60s means the rig is unhealthy
    # (wedged FPGA / USB bounce) - wait instead of spin-crashing
    DT=$(( $(date +%s) - T0 ))
    if [ $DT -lt 60 ]; then
        echo "=== pass $PASS died after ${DT}s - backing off 45s (rig unhealthy?) ==="
        sleep 45
    else
        sleep 2
    fi
done
