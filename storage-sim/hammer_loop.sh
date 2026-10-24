#!/bin/bash
# Overnight glitch-2 hammer: rerun the proven gray-zone config until a
# JACKPOT appears (or the loop is stopped). Each pass adds hundreds more
# stochastic samples at the known-corruptible settings.
#
# Proven gray zone (campaign 5/6/7): 4MHz, offset -45, width 40,
# reps 24-27, ext 714-724 (178.5-181us) - produced 9f1f/ff/dead there.
# With the direct wire + NRST fast recovery this config gets ~3 shots/s.
set -u
cd /home/tdaly/trezor-btc/storage-sim
PASS=0
while true; do
    PASS=$((PASS+1))
    echo "=== pass $PASS  $(date +%H:%M:%S) ==="
    T0=$(date +%s)
    G_CLKGEN=4e6 G_OFFSET=-45 G_WIDTH=40 G_REPEATS=24,25,26,27 \
    G_EXT_MIN=712 G_EXT_MAX=738 G_STEP=1 G_SAMPLES=40 \
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
