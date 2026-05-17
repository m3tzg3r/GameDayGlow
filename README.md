# GameDayGlow

Automatically sets Govee lights to team colors on game days for the Colorado Avalanche, Denver Broncos, and Denver Nuggets. Runs as a cron job, checks if the team is playing today, and if so turns on the lights and holds the color for a set period of time.

## How it works

Govee has an official API but it requires authentication and a cloud round-trip. These scripts use an undocumented local multicast API that Govee devices listen on over UDP. A debug mode can be unlocked with a key that allows direct color control without cloud authentication. The scripts send a keepalive every 20-30 seconds to prevent the debug session from timing out.

This all happens on your local network. No cloud, no login, no Govee account required once the device is on your network.

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

These scripts run as cron jobs. The run duration is configurable per script via the `TOTAL_DURATION` constant. Scripts are staggered so that if multiple teams are playing on the same day they do not step on each other.

Example:

```
0 6 * * * /usr/bin/python3 /path/to/avshype.py
30 6 * * * /usr/bin/python3 /path/to/broncoshype.py
0 7 * * * /usr/bin/python3 /path/to/nuggetshype.py
```


## Adapting for other teams

To use these scripts for a different team:

- **NHL** -- change `AVALANCHE_TEAM_ID` to your team's numeric ID from the NHL API
- **NFL** -- change the team ID in the ESPN endpoint URL (e.g. `/teams/7/` for the Broncos)
- **NBA** -- change the `"DEN"` abbreviation to your team's three-letter code
- Update the Razer color payload to match your team's colors

## Logs

Each script writes to its own log file in the working directory:

- `avshype.log`
- `broncoshype.log`
- `NuggetsHype.log`

If the lights stop working mid-season, check the log first. The scripts warn when API response structure changes, which has happened between NHL and NBA seasons.

## Disclaimer

This is a personal hobby project provided as-is. It uses an undocumented device API that could change or stop working at any time with a firmware update. Use at your own risk. I am not responsible for any issues that arise from running these scripts, including but not limited to device behavior, network disruptions, or changes to third-party APIs.
