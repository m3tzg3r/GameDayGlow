# GameDayGlow

Automatically sets Govee lights to team colors on game days for the Colorado Avalanche, Denver Broncos, and Denver Nuggets. Runs as a cron job, checks if the team is playing today, and if so lights the panel in team colors for a set period of time.

## Versions

Two flavors of the game-day scripts. They share the same daily schedule checks and run windows; they differ in what they put on the panel.

- **v1 (static):** `avshype.py`, `broncoshype.py`, `nuggetshype.py`. Set a static two-color team pattern once, then send a `status` keepalive every 20-30s to hold it for the run window.
- **v2 (animated):** `avshype2.py`, `broncoshype2.py`, `nuggetshype2.py` plus the shared `gdg_wave.py` engine. Stream a slow team-colored **wave** that drifts across the panel with a soft fade, for motion instead of a flat color. This is the version currently deployed -- see [v2: animated wave](#v2-animated-wave).

Both target the **Govee H6061** (Glide Hexa, 10 addressable zones).

## How it works

Govee has an official API but it requires authentication and a cloud round-trip. These scripts use an undocumented local multicast API that Govee devices listen on over UDP. A debug mode can be unlocked with a key that allows direct color control without cloud authentication.

### Keepalive timing (v1)

The debug/razer streaming session has a measured inactivity timeout of roughly **60 seconds**: with no packets sent and no other controller active (e.g. the Govee desktop app closed), the panel drops out of debug mode and reverts to its default state after about a minute. The 20-30 second keepalive interval sits comfortably under that timeout. The margin is deliberate -- this is UDP multicast, so a keepalive packet can be dropped silently; a sub-timeout interval means losing one keepalive won't push past the 60s deadline and cause a mid-game revert.

Note: if the Govee desktop app is running with Razer Chroma Connect active, the app streams its own color state to the panel continuously, which will both keep the session alive and override these scripts. The scripts assume no app is running (e.g. a headless Raspberry Pi), which is the normal cron deployment.

This all happens on your local network. No cloud, no login, no Govee account required once the device is on your network.

## v2: animated wave

The v2 scripts (`*2.py` + `gdg_wave.py`) stream a slow team-colored wave instead of a static color. Key differences from v1:

- **No separate keepalive.** v2 streams color frames continuously (~5fps), and those frames *are* the keepalive -- the ~60s razer timeout never fires while streaming.
- **The look.** Each of the 10 zones snaps to one of the two team colors (never an in-between), and the boundary between the color bands drifts slowly across the panel. Band edges fade toward black -- never blending red into blue, which would produce off-brand purples. Defaults (in `gdg_wave.py`): `WAVES=2`, `SPEED=0.03`, `FADE=1.0`, `INTERVAL=0.2` (5fps). The `tools/stream_test.py` tuner generates the same wave so you can experiment with these before committing.
- **Multi-team coordination: last-to-start-wins.** Because v2 streams continuously, two scripts running at once would fight and flicker the panel at the frame rate. To prevent that, each run writes its start time to a shared claim file (`.gdg_panel_claim`, next to the scripts). While streaming, every frame it checks the claim; if a newer script has started, the older one stops and bows out, handing the panel over cleanly. With a staggered cron that fires teams at different times, the panel naturally rotates through whichever team most recently started.

## How the API was discovered

The Razer commands were discovered by sniffing local network traffic with Wireshark while the Govee Windows app was running. The app communicates with devices over UDP multicast, and an undocumented debug mode activation key and color command format were identified by analyzing those packets. The color payload is base64-encoded and contains RGB values that map to team colors.

This is a passive discovery method -- no credentials were extracted, no servers were accessed, and no terms of service were circumvented. The device is on a local network and responds to anyone who sends the right UDP packet.

## Is this legal?

Yes. You own the device, it is on your local network, and you are sending UDP packets to hardware you purchased. This is no different from what projects like Home Assistant do when they reverse engineer local device APIs. There is no hacking, credential theft, or unauthorized access involved.

## APIs used

- **NHL** -- `api-web.nhle.com` (Colorado Avalanche, team ID 21)
- **ESPN** -- `site.api.espn.com` (Denver Broncos, team ID 7)
- **NBA CDN** -- `cdn.nba.com` (Denver Nuggets, team abbreviation DEN)

## Requirements

pip install requests



## Cron setup

These scripts run as cron jobs. The run duration is configurable per script via the `TOTAL_DURATION` constant. Stagger the start times across teams; with v2 the most-recently-started team owns the panel (last-to-start-wins), so staggered entries rotate the colors through the day.

Example (v2 -- swap the `2.py` for the plain names to run v1 static instead):

```
0 6 * * * /usr/bin/python3 /path/to/avshype2.py
30 6 * * * /usr/bin/python3 /path/to/broncoshype2.py
0 7 * * * /usr/bin/python3 /path/to/nuggetshype2.py
```

All four files (`gdg_wave.py` plus the three `*2.py` scripts) must live in the same directory so the per-team scripts can `import gdg_wave`.


## Adapting for other teams

To use these scripts for a different team:

- **NHL** -- change `AVALANCHE_TEAM_ID` to your team's numeric ID from the NHL API
- **NFL** -- change the team ID in the ESPN endpoint URL (e.g. `/teams/7/` for the Broncos)
- **NBA** -- change the `"DEN"` abbreviation to your team's three-letter code
- **Colors:** in v1, update the base64 Razer color payload; in v2, just set the `PRIMARY` and `ACCENT` RGB tuples at the top of the `*2.py` script (the `gdg_wave` engine builds the payload and checksum for you).

### Color payload format (for reference)

The v1 payloads and the v2 engine both produce the same packet: `bb 00 <len> b0 00 0a` followed by 10 RGB triples (one per zone) and a trailing XOR checksum of all prior bytes. `bb`=marker, `b0`=set-colors, `0a`=10 zones. The enable packet is `uwABsQEK`.

## Logs

Each script writes to its own log file (v2 writes alongside the scripts; v1 in the working directory):

- v1: `avshype.log`, `broncoshype.log`, `NuggetsHype.log`
- v2: `avshype2.log`, `broncoshype2.log`, `NuggetsHype2.log`

If the lights stop working mid-season, check the log first. The scripts warn when API response structure changes, which has happened between NHL and NBA seasons. v2 logs also record when a script claims the panel or is preempted by a newer one.

## tools/

Standalone helpers (not part of the cron deployment) for tuning and protocol exploration -- `stream_test.py` (live wave tuner), `set_once.py` and `keepalive_test.py` (timeout/keepalive diagnostics). See `tools/README.md`.

## Disclaimer

This is a personal hobby project provided as-is. It uses an undocumented device API that could change or stop working at any time with a firmware update. Use at your own risk. I am not responsible for any issues that arise from running these scripts, including but not limited to device behavior, network disruptions, or changes to third-party APIs.
