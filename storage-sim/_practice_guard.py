"""Safety fence for device-MODIFYING scripts.

These scripts write option bytes, program flash, or mass-erase. On the real
RDP2 Trezor that would DESTROY the seed (e.g. an RDP1->RDP0 regression erases
all flash). Real-device work is strictly READ-ONLY + the crowbar glitch; a
guarded script must NEVER run against it.

Refuses unless G_PRACTICE_BOARD=YES is explicitly set, so none of these can fire
by accident while a glitch-1 session has SWD open on the real device.
"""
import os
import sys


def require_practice_board(what):
    if os.environ.get('G_PRACTICE_BOARD') != 'YES':
        sys.exit(
            '\n' + '!' * 70 +
            f'\nREFUSED: "{what}" MODIFIES the chip (option bytes / flash / erase).\n'
            'On the real RDP2 Trezor this would DESTROY the seed. It is\n'
            'PRACTICE-BOARD ONLY. If you are certain you are on the practice\n'
            'board, re-run with  G_PRACTICE_BOARD=YES\n' + '!' * 70)
    print('[guard] G_PRACTICE_BOARD=YES acknowledged - practice board only.')
