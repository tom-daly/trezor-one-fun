#!/bin/bash
# Calibrated run (2026-10-29): fire INTO the measured RDP decision window.
# Live LA capture put the 0x11->NACK decision at 191-196.5us after the 0x11
# START; the campaign "us" column is 8.68us (one bit-time) earlier than that
# (CW triggers on the first RISING edge of 0x11), so the decision maps to
# campaign us = 182-188. See FINDINGS 2026-10-29 "LIVE LA capture".
#
# Uses the NEW driver (stage-2 removed, cross-read confirm + A/B, lazy dump
# dir, success alert, rep_ns column). Strength rolls rep5-7 (30-42ns) - rep4
# is below threshold, dropped via G_RND_LO=25.
set -u
cd /home/tdaly/trezor-btc/storage-sim

G_CLKGEN=166666667 G_OFFSET=-45 G_WIDTH=5 \
G_US_MIN=182 G_US_MAX=188 \
G_RND_LO=25 G_RND_HI=45 \
G_SAMPLES=3 G_COOLDOWN=0.15 G_RESET_EVERY=1 \
G_SHOTS=15000 G_TAG=cal182 \
/home/tdaly/.cwvenv/bin/python -u rdp1_glitch_campaign_full_mem_dump.py \
    2>&1 | tee -a /tmp/opencode/cal182.log
