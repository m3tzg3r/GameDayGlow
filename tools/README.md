# tools

Standalone helpers for tuning and protocol exploration. None of these are part
of the cron deployment -- they're for experimenting against a panel on your LAN.

- **stream_test.py** -- live wave/fade tuner. Generates the same animated wave
  as the v2 game-day scripts so you can dial in the look:
  `python3 stream_test.py --team avs --waves 2 --speed 0.03 --fade 1`
  Flags: `--team --mode {team,blend} --waves --speed --fade --vivid
  --brightness --interval --duration`.

- **set_once.py** -- set a static team pattern once and exit (no keepalive).
  Used to measure the razer-mode inactivity timeout (~60s):
  `python3 set_once.py avs 100`  (team, brightness).

- **keepalive_test.py** -- replicates the v1 static behavior (set color, then
  `status` keepalive every N seconds) with no schedule gate, for comparing
  revert behavior: `python3 keepalive_test.py --team avs --interval 30`.

Run these on a machine on the same LAN as the panel (UDP multicast won't route).
