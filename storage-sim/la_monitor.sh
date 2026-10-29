#!/bin/bash
# Periodic LA screen-drops during a running campaign.
# Every ~2 min: grab 0.5 s of the UART lines (4 MS/s), render an annotated
# snapshot (UART bytes labelled, burst at t=0) and show it on the desktop.
# Loop until stopped (pkill -f la_monitor).
OUT=/tmp/opencode/la_live.png
CSV=/tmp/opencode/la_live.csv
while true; do
    cd /home/tdaly/trezor-btc/storage-sim
    sigrok-cli --driver fx2lafw --config samplerate=4000000 \
        --samples 2000000 -O csv > "$CSV" 2>/dev/null
    /home/tdaly/.cwvenv/bin/python la_snapshot.py "$CSV" \
        --sr 4000000 --out "$OUT" --zoom 300 >/dev/null 2>&1
    DISPLAY=:1 xdg-open "$OUT" >/dev/null 2>&1
    sleep 120
done
