#!/usr/bin/env python3
"""
GameDayGlow v2 -- Denver Broncos animated wave.

Same daily schedule check as broncoshype.py (ESPN, timezone-aware), but streams
a slow team-colored wave instead of a static color + keepalives. Multi-team
coordination (last-to-start-wins) is handled by gdg_wave. Drop-in cron
replacement for broncoshype.py.
"""
import logging
import os
import time
from datetime import datetime

import gdg_wave

LOG_FILE_NAME = "broncoshype2.log"
TOTAL_DURATION = 8 * 60 * 60  # 8 hours, matches broncoshype.py
TEAM_ID = 7  # Denver Broncos on ESPN

PRIMARY = (255, 95, 0)     # orange
ACCENT = (20, 70, 235)     # blue

LOCAL_TZ = datetime.now().astimezone().tzinfo
_today = datetime.now(LOCAL_TZ)
SEASON_YEAR = _today.year - 1 if _today.month < 8 else _today.year
API_ENDPOINT = (
    f"https://site.api.espn.com/apis/site/v2/sports/football/nfl/teams/"
    f"{TEAM_ID}/schedule?season={SEASON_YEAR}"
)

logging.basicConfig(
    filename=os.path.join(os.path.dirname(os.path.abspath(__file__)), LOG_FILE_NAME),
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s]: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def is_team_playing_today(api_url):
    response = gdg_wave.get_with_retries(api_url)
    if not response:
        logging.error("Failed to retrieve ESPN schedule")
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

    today_local = datetime.now(LOCAL_TZ).date()
    for event in events:
        raw = event.get("date", "")
        if not raw:
            continue
        try:
            event_local = datetime.fromisoformat(raw.replace("Z", "+00:00")).astimezone(LOCAL_TZ)
        except Exception as e:
            logging.error(f"Failed to parse event date '{raw}': {e}")
            continue
        if event_local.date() == today_local:
            logging.info(f"Match found: {event.get('name')} on {today_local}")
            return True

    logging.info("No events matched today's local date")
    return False


if is_team_playing_today(API_ENDPOINT):
    logging.info("The Denver Broncos are playing today.")
    gdg_wave.run_wave("broncos", PRIMARY, ACCENT, TOTAL_DURATION, logging.info, time.time())
    logging.info("Script executed successfully.")
else:
    logging.info("The Denver Broncos are not playing today.")
