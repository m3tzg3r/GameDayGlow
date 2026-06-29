#!/usr/bin/env python3
"""
GameDayGlow v2 -- Colorado Avalanche animated wave.

Same daily schedule check as avshype.py, but instead of a static color + status
keepalives, it streams a slow team-colored wave for the run window. Multi-team
coordination (last-to-start-wins) is handled by gdg_wave. Drop-in cron
replacement for avshype.py.
"""
import logging
import time
from datetime import datetime

import gdg_wave

LOG_FILE_NAME = "avshype2.log"
TOTAL_DURATION = 4 * 60 * 60  # 4 hours, matches avshype.py
AVALANCHE_TEAM_ID = 21

# (primary, accent) -- bright, saturated so the fade stays vivid
PRIMARY = (230, 20, 60)    # burgundy-red
ACCENT = (30, 110, 235)    # blue

logging.basicConfig(
    filename=LOG_FILE_NAME,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s]: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def is_colorado_avalanche_playing():
    current_date = datetime.now().strftime("%Y-%m-%d")
    endpoint = f"https://api-web.nhle.com/v1/schedule/{current_date}"

    response = gdg_wave.get_with_retries(endpoint)
    if not response:
        logging.error("Failed to retrieve NHL schedule")
        return False

    try:
        schedule_data = response.json()
    except ValueError as e:
        logging.error(f"Error parsing JSON response: {e}")
        return False

    game_week = schedule_data.get("gameWeek")
    if not game_week:
        logging.warning(f"gameWeek key missing -- possible API change. Keys: {list(schedule_data.keys())}")
        return False

    for game_day in game_week:
        if game_day.get("date") != current_date:
            continue
        games = game_day.get("games", [])
        logging.info(f"Found {len(games)} game(s) scheduled for {current_date}")
        for game in games:
            home = game.get("homeTeam", {}).get("id")
            away = game.get("awayTeam", {}).get("id")
            if home == AVALANCHE_TEAM_ID or away == AVALANCHE_TEAM_ID:
                return True
        return False

    logging.warning(f"No entry for {current_date} in gameWeek")
    return False


if is_colorado_avalanche_playing():
    logging.info("The Colorado Avalanche are playing today.")
    gdg_wave.run_wave("avs", PRIMARY, ACCENT, TOTAL_DURATION, logging.info, time.time())
    logging.info("Script executed successfully.")
else:
    logging.info("The Colorado Avalanche are not playing today.")
