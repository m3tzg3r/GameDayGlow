#!/usr/bin/env python3
"""
GameDayGlow v2 -- Denver Nuggets animated wave.

Same daily schedule check as nuggetshype.py (NBA CDN scoreboard), but streams a
slow team-colored wave instead of a static color + keepalives. Multi-team
coordination (last-to-start-wins) is handled by gdg_wave. Drop-in cron
replacement for nuggetshype.py.
"""
import logging
import time
from datetime import datetime

import gdg_wave

LOG_FILE_NAME = "NuggetsHype2.log"
TOTAL_DURATION = 4 * 60 * 60  # 4 hours, matches nuggetshype.py
API_ENDPOINT = "https://cdn.nba.com/static/json/liveData/scoreboard/todaysScoreboard_00.json"

PRIMARY = (255, 205, 0)    # gold
ACCENT = (25, 95, 235)     # blue

logging.basicConfig(
    filename=LOG_FILE_NAME,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s]: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def is_denver_nuggets_playing():
    current_date = datetime.now().strftime("%Y-%m-%d")

    response = gdg_wave.get_with_retries(API_ENDPOINT)
    if not response:
        logging.error("Failed to retrieve NBA scoreboard")
        return False

    try:
        data = response.json()
    except ValueError as e:
        logging.error(f"Error parsing JSON response: {e}")
        return False

    scoreboard = data.get("scoreboard")
    if scoreboard is None:
        logging.warning(f"scoreboard key missing -- possible API change. Keys: {list(data.keys())}")
        return False

    game_date = scoreboard.get("gameDate")
    if game_date != current_date:
        logging.info(f"API not updated yet. Current: {current_date}, API: {game_date}")
        return False

    games = scoreboard.get("games")
    if games is None:
        logging.warning(f"games key missing -- possible API change. Keys: {list(scoreboard.keys())}")
        return False

    for game in games:
        if "DEN" in game.get("gameCode", ""):
            return True

    logging.info("No DEN game found in today's scoreboard")
    return False


if is_denver_nuggets_playing():
    logging.info("The Denver Nuggets are playing today.")
    gdg_wave.run_wave("nuggets", PRIMARY, ACCENT, TOTAL_DURATION, logging.info, time.time())
    logging.info("Script executed successfully.")
else:
    logging.info("Denver Nuggets are not playing today.")
