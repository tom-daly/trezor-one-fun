#!/bin/bash
# shutdown.sh - safe rig shutdown.
# Stops every glitch/campaign script and leaves the rig in a safe idle state:
# crowbar FETs OFF, FET latch released, target chip POWERED DOWN, TIO lines
# high-Z, CW handle freed. Run anytime to be sure nothing is firing.
#   /home/tdaly/.cwvenv/bin/python is NOT needed to invoke - just: bash rig_shutdown.sh
set -u
cd /home/tdaly/trezor-btc/storage-sim
PY=/home/tdaly/.cwvenv/bin/python
ME=$$; PP=$PPID
echo "=== RIG SHUTDOWN  $(date '+%m-%d %H:%M:%S') ==="

kills(){  # kill PIDs matching $1 (excluding this shell), label $2
  for p in $(ps -eo pid,args | grep -E "$1" | grep -v grep | awk -v me=$ME -v pp=$PP '$1!=me && $1!=pp {print $1}'); do
    kill "${2:-}" "$p" 2>/dev/null && echo "  killed $p  ($1)"
  done
}

# 1) loop shells FIRST (so they don't respawn the campaign)
kills 'loop_fulldump\.sh|loop_cycle\.sh|loop_targeted\.sh'
sleep 1
# 2) rig python + heartbeat
kills 'rdp1_glitch_campaign_full_mem_dump\.py|glitch1_boot_rdp\.py|rd_alive\.py|status_heartbeat\.sh'
sleep 1.5
# 3) force any stragglers (incl respawned campaign)
kills 'rdp1_glitch_campaign|loop_fulldump\.sh|loop_cycle\.sh|loop_targeted\.sh|status_heartbeat\.sh' -9
sleep 1

# 4) CW safe teardown (handle must be free, hence after the kills)
"$PY" - <<'EOF'
import gc
try:
    import chipwhisperer as cw
    s = cw.scope()
    s.io.glitch_hp = False           # crowbar FETs OFF
    s.io.glitch_lp = False
    try: s.io.vglitch_reset()        # errata: release any stuck FET latch
    except Exception: pass
    s.io.tio1 = 'high_z'; s.io.tio2 = 'high_z'; s.io.tio4 = 'high_z'
    s.io.target_pwr = False          # power the chip DOWN
    s.dis(); del s; gc.collect()
    print("  CW: crowbar OFF, FETs released, target POWERED DOWN, lines high-Z.")
except Exception as e:
    print(f"  CW teardown SKIPPED ({type(e).__name__}) - CW not reachable; "
          "unplug/replug it to reset the FETs.")
EOF

# 5) verdict
N=$(ps -eo pid,args | grep -E 'rdp1_glitch_campaign|loop_fulldump|loop_cycle|loop_targeted|status_heartbeat|glitch1_boot_rdp|rd_alive' | grep -v grep | awk -v me=$ME -v pp=$PP '$1!=me && $1!=pp' | wc -l)
if [ "$N" -eq 0 ]; then
  echo "=== SHUTDOWN COMPLETE: 0 rig processes, rig idle/safe ==="
else
  echo "=== WARNING: $N rig process(es) still alive: ==="
  ps -eo pid,args | grep -E 'rdp1_glitch_campaign|loop_fulldump|loop_cycle|loop_targeted|status_heartbeat|glitch1_boot_rdp|rd_alive' | grep -v grep | awk -v me=$ME -v pp=$PP '$1!=me && $1!=pp'
fi
