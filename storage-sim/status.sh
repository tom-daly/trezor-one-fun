#!/bin/bash
# One-shot status digest for the running RDP1 glitch campaign.
# Reads the fulldump log + accum dir; prints a compact snapshot.
# Used by the monitoring subagent and the desktop status window.
cd /home/tdaly/trezor-btc/storage-sim 2>/dev/null || exit 1
L=/tmp/opencode/fulldump_loop.log
ACC=dumps/accum
# stats since the most recent human-initiated start marker (rerun/CAMPAIGN/relaunch)
START=$(grep -nE '^=== .*(rerun|CAMPAIGN|relaunch|REP[0-9])' "$L" 2>/dev/null | tail -1 | cut -d: -f1)
seg=$(tail -n +${START:-1} "$L" 2>/dev/null)
shots=$(echo "$seg" | grep -cE '\] #[0-9]+ ')
succ=$(echo "$seg" | grep -cE '\-> SUCCESS')
lat=$(echo "$seg" | grep -cE 'crossread=CONFIRMED')
uidotp=$(echo "$seg" | grep -cE 'secured under latch')
refused=$(echo "$seg" | grep -cE 'REFUSED')
dead=$(echo "$seg" | grep -cE '\] #[0-9]+ .*-> dead')
partial=$(echo "$seg" | grep -cE 'ACK_NO_DATA')
deadpct=$(awk "BEGIN{printf \"%.1f\",($shots?$dead*100/$shots:0)}")
alive=$(ps -eo args | grep -q '[c]wvenv/bin/python -u rdp1' && echo FIRING || echo "stopped/cooldown")
sc=$(ls "$ACC"/storage_*.bin 2>/dev/null | wc -l)
uidf=$([ -f "$ACC/uid.bin" ] && echo Y || echo n)
otpf=$([ -f "$ACC/otp3.bin" ] && echo Y || echo n)
last=$(echo "$seg" | grep -E '\] #[0-9]+ ' | tail -1 | grep -oE '#[0-9]+ .*(us\))? .*-> [A-Za-z_]+' | head -1)
printf '[%s] %s | shots=%s SUCCESS=%s latch=%s | uid/otp3 secured=%s REFUSED=%s | dead=%s%% partial=%s | accum storage=%s/64 uid=%s otp3=%s\n' \
  "$(date '+%H:%M:%S')" "$alive" "$shots" "$succ" "$lat" "$uidotp" "$refused" "$deadpct" "$partial" "$sc" "$uidf" "$otpf"
[ -n "$last" ] && printf '        last shot: %s\n' "$last"
