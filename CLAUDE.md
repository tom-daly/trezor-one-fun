# Project: Trezor One RDP1 glitch campaign (owner's own device — legitimate self-recovery)

## Rig and environment (read first)
- All python runs with `/home/tdaly/.cwvenv/bin/python` (venv with chipwhisperer, python-vxi11, PIL, mss)
- Campaign driver: `storage-sim/rdp1_glitch_campaign_full_mem_dump.py` (env-var config, G_* vars documented in its header)
- Devices: CW-Lite `/dev/ttyACM0`, FTDI `/dev/ttyUSB0`, ST-Link (SWD), LA fx2lafw, Siglent SDS1202X-E scope at `10.11.13.220` via VXI-11 (see skill `siglent-scope` and `scope/scope.py`)
- Boot discipline: chip enters system bootloader ONLY via full power cycle with BOOT0 (CW TIO1) held high; NRST-only reboot does not work out of lockup. CW config discipline: fresh `cw.scope()` open, set `clkgen_freq` FIRST, then glitch params — never reconfigure clkgen mid-session (stale-MMCM artifacts)

## CONTINUAL LEARNING (mandatory)
After EVERY meaningful iteration — campaign pass, single-shot experiment, rig
change, hardware discovery, scope/LA measurement session, or dead-end —
append what was learned to `storage-sim/FINDINGS.md` in the same session.
Log it while it is fresh: the numbers (shots, verdicts, ext/width/repeat,
settings), the interpretation, and what it rules out. Never leave a session
without the FINDINGS entry.

## CAMPAIGN RUNS (mandatory)
- ALWAYS show the live window when a campaign runs: launch a follow-terminal
  on the user's desktop with every campaign/hammer start, e.g.
  `DISPLAY=:1 gnome-terminal --title "<campaign> - live" -- bash -c "tail -n 30 -f <status-log> /tmp/opencode/hammer.log | grep --line-buffered -vE 'WARNING|WARN'"`
  so the user can watch shot verdicts in real time.
- The scope is MEASUREMENT-ONLY. Never leave it connected to the glitch node
  during campaign firing - it damps the injection. Use it for verification
  captures between passes, or the LA on the CW-side leg instead.

## FINDINGS.md = the golden bible
`storage-sim/FINDINGS.md` is the single consolidated master document for the
whole campaign. Treat it as the source of truth:
- New entries append chronologically at the end, with a dated `## HEADING`.
- Whenever a new entry supersedes or contradicts an older one, update the
  older entry with a one-line pointer (`-> SUPERSEDED by <date/heading>`)
  rather than deleting it.
- If the document grows unwieldy, consolidate: merge related entries into a
  summary section at the TOP titled `## CURRENT STATE OF KNOWLEDGE` (keep a
  short list: proven facts, open questions, current best parameters, rig
  quirks), while preserving the full chronological history below.
- Before running any new experiment, READ FINDINGS.md first — it contains
  the accumulated campaign knowledge, proven parameter sets, and the traps
  already fallen into. Do not re-learn what is already written there.
- Key reference material that must stay in sync with FINDINGS: the rig
  comparison table vs mkesenheimer's README_FLASH_DUMP.md and the VoidStar
  Replicant recipe (100 MHz clkgen, enable_only, w40/offset -45/rep20).
