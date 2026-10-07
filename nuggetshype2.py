#!/usr/bin/env python3
"""
GameDayGlow v2 -- Denver Nuggets animated wave.

Daily schedule check via the ESPN NBA scoreboard (timezone-aware, includes
preseason/playoffs), then streams a slow team-colored wave instead of a static
color + keepalives. Multi-team coordination (last-to-start-wins) is handled by
gdg_wave. Drop-in cron replacement for nuggetshype.py.

The NBA CDN scoreboard (cdn.nba.com todaysScoreboard_00.json) started returning
Akamai 403s for non-browser clients, so it is no longer used.

Usage: nuggetshype2.py [--check YYYY-MM-DD]
  --check  only report whether DEN plays on that local date; no lights.
"""
import logging
import os
import sys
import time
from datetime import datetime

import gdg_wave

LOG_FILE_NAME = "NuggetsHype2.log"
TOTAL_DURATION = 4 * 60 * 60  # 4 hours, matches nuggetshype.py
TEAM_ABBR = "DEN"
API_ENDPOINT = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={}"

PRIMARY = (255, 205, 0)    # gold
ACCENT = (25, 95, 235)     # blue

LOCAL_TZ = datetime.now().astimezone().tzinfo

logging.basicConfig(
    filename=os.path.join(os.path.dirname(os.path.abspath(__file__)), LOG_FILE_NAME),
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s]: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def is_denver_nuggets_playing(day):
    response = gdg_wave.get_with_retries(API_ENDPOINT.format(day.strftime("%Y%m%d")))
    if not response:
        logging.error("Failed to retrieve ESPN NBA scoreboard")
        return False

    try:
        data = response.json()
    except ValueError as e:
        logging.error(f"Error parsing JSON response: {e}")
        return False

    events = data.get("events")
    if events is None:
        logging.warning(f"events key missing -- possible API change. Keys: {list(data.keys())}")
        return False

    for event in events:
        teams = {
            c.get("team", {}).get("abbreviation")
            for comp in event.get("competitions", [])
            for c in comp.get("competitors", [])
        }
        if TEAM_ABBR not in teams:
            continue
        raw = event.get("date", "")
        try:
            event_local = datetime.fromisoformat(raw.replace("Z", "+00:00")).astimezone(LOCAL_TZ)
        except Exception as e:
            logging.error(f"Failed to parse event date '{raw}': {e}")
            continue
        if event_local.date() == day:
            logging.info(f"Match found: {event.get('name')} at {event_local:%Y-%m-%d %H:%M %Z}")
            return True

    logging.info(f"No {TEAM_ABBR} game found on {day} ({len(events)} game(s) on the scoreboard)")
    return False


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--check":
        day = datetime.strptime(sys.argv[2], "%Y-%m-%d").date()
        logging.getLogger().addHandler(logging.StreamHandler())
        print("PLAYING" if is_denver_nuggets_playing(day) else "NOT PLAYING")
        sys.exit(0)

    if is_denver_nuggets_playing(datetime.now(LOCAL_TZ).date()):
        logging.info("The Denver Nuggets are playing today.")
        gdg_wave.run_wave("nuggets", PRIMARY, ACCENT, TOTAL_DURATION, logging.info, time.time())
        logging.info("Script executed successfully.")
    else:
        logging.info("Denver Nuggets are not playing today.")
