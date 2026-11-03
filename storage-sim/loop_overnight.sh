#!/bin/bash
# Overnight two-glitch recovery: restart the chain on any exit (CW dropout,
# crash, bootloader lost) until dumps/overnight/RECOVERED.txt appears. Resets the
# CW USB between restarts to recover from a wedged dropout.
set -u
cd /home/tdaly/trezor-btc/storage-sim
LOG=/tmp/opencode/overnight.log
PY=/home/tdaly/.cwvenv/bin/python
REC=dumps/overnight/RECOVERED.txt

reset_cw() {
  "$PY" -I -c "
import os,glob,fcntl
RST=(ord('U')<<8)|20
for d in glob.glob('/sys/bus/usb/devices/*'):
    try:
        if open(d+'/idVendor').read().strip()=='2b3e':
            b=int(open(d+'/busnum').read()); n=int(open(d+'/devnum').read())
            fd=os.open('/dev/bus/usb/%03d/%03d'%(b,n),os.O_WRONLY); fcntl.ioctl(fd,RST,0); os.close(fd); print('CW USB reset')
    except Exception: pass" 2>/dev/null
}

n=0
while true; do
  if [ -f "$REC" ]; then echo "=== RECOVERED present -> done $(date) ===" | tee -a "$LOG"; break; fi
  n=$((n+1))
  echo "=== [$n] launching chain $(date '+%H:%M:%S') ===" | tee -a "$LOG"
  "$PY" -u glitch_chain_overnight.py >>"$LOG" 2>&1
  rc=$?
  echo "=== [$n] chain exited rc=$rc $(date '+%H:%M:%S') ===" | tee -a "$LOG"
  [ -f "$REC" ] && { echo "=== RECOVERED -> done ===" | tee -a "$LOG"; break; }
  reset_cw | tee -a "$LOG"
  sleep 6
done
echo "=== overnight loop finished $(date) ===" | tee -a "$LOG"
