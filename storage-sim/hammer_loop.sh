#!/bin/bash
# Range-sweep hammer: glitch across the known-good window and log every
# shot, looking for misbehavior (weird/dead/ACK). 16 MHz (62.5ns ext steps,
# ~31ns pulses at width 40-49), band 105-106.5us + margin, multiple
# strengths, looping passes. Auto-dump (JACKPOT_*.bin) on any ACK.
set -u
cd /home/tdaly/trezor-btc/storage-sim
PASS=0
while true; do
    PASS=$((PASS+1))
    echo "=== pass $PASS  $(date +%H:%M:%S) ==="
    T0=$(date +%s)
    G_CLKGEN=16000000 G_OFFSET=-45 G_WIDTH=40,49 G_REPEATS=25,50,100 \
    G_EXT_MIN=1520 G_EXT_MAX=1590 G_STEP=1 G_SAMPLES=3 \
    G_COOLDOWN=0.15 G_REST_EVERY=800 G_REST_S=10 G_OUTPUT=enable_only \
    G_TAG=r1 \
    /home/tdaly/.cwvenv/bin/python -u rdp1_glitch_campaign_full_mem_dump.py \
        >> /tmp/opencode/hammer.log 2>&1
    if ls JACKPOT_*.bin >/dev/null 2>&1; then
        echo "=== JACKPOT ON PASS $PASS ==="
        ls -la JACKPOT_*.bin
        break
    fi
    # between-pass chip health check (known-good command verification)
    echo "--- health check after pass $PASS ---"
    if /home/tdaly/.cwvenv/bin/python -u chip_health.py 2>&1 | grep "HEALTH: GOOD"; then
        :
    else
        echo "=== chip UNHEALTHY after pass $PASS - running total rig reset ==="
        if /home/tdaly/.cwvenv/bin/python -u reset_rig.py 2>&1 | grep RESET; then
            echo "=== rig recovered - continuing ==="
        else
            echo "=== reset ladder FAILED - stopping the loop (physical check needed) ==="
            break
        fi
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
