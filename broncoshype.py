#!/usr/bin/env python3

import json
import logging
import socket
import time
from datetime import datetime

import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

# ----------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------

LOG_FILE_NAME = "broncoshype.log"

TOTAL_DURATION = 8 * 60 * 60  # 8 hours
INTERVAL = 20                 # seconds between status messages

GROUP_ADDR = "239.255.255.250"
GROUP_PORT = 4001
TTL = 2

TEAM_ID = 7  # Denver Broncos on ESPN

# Use the system's local timezone for "today"
LOCAL_TZ = datetime.now().astimezone().tzinfo

# Figure out correct NFL season year based on local date
today_local = datetime.now(LOCAL_TZ)
season_year = today_local.year
if today_local.month < 8:  # Jan–Jul belong to the previous season
    season_year -= 1

API_ENDPOINT = (
    f"https://site.api.espn.com/apis/site/v2/sports/football/nfl/teams/"
    f"{TEAM_ID}/schedule?season={season_year}"
)

# ----------------------------------------------------------------------
# Logging setup
# ----------------------------------------------------------------------

logging.basicConfig(
    filename=LOG_FILE_NAME,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s]: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------

def send_udp_message(cmd, data=None):
    message = {"msg": {"cmd": cmd, "data": data or {}}}
    payload = json.dumps(message)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, TTL)

    logging.info(f"Sending: {payload}")
    sock.sendto(payload.encode("utf-8"), (GROUP_ADDR, GROUP_PORT))
    sock.close()


def get_with_retries(api_url, retries=3):
    session = requests.Session()
    retry = Retry(
        total=retries,
        backoff_factor=0.3,
        status_forcelist=[500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    try:
        response = session.get(api_url, timeout=10)
        response.raise_for_status()
        return response
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to retrieve data after {retries} retries: {e}")
        return None


def debug_dump_schedule(data):
    local_today = datetime.now(LOCAL_TZ).date()
    logging.info(f"Local today: {local_today}")

    for event in data.get("events", []):
        raw = event.get("date", "")
        if not raw:
            continue

        try:
            event_utc = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            event_local = event_utc.astimezone(LOCAL_TZ)
        except Exception as e:
            logging.error(f"Failed to parse event date '{raw}': {e}")
            continue

        logging.info(
            "Event: %s id=%s utc=%s (date=%s) local=%s (date=%s)",
            event.get("name"),
            event.get("id"),
            event_utc,
            event_utc.date(),
            event_local,
            event_local.date(),
        )


def is_team_playing_today(api_url):
    response = get_with_retries(api_url)
    if not response:
        return False

    try:
        data = response.json()
    except json.JSONDecodeError as e:
        logging.error(f"Error parsing JSON response: {e}")
        return False

    events = data.get("events")
    if events is None:
        logging.warning(f"events key missing from API response -- possible API change. Keys present: {list(data.keys())}")
        return False

    debug_dump_schedule(data)

    today_local = datetime.now(LOCAL_TZ).date()
    logging.info(f"Checking events against local date: {today_local}")

    for event in events:
        raw = event.get("date", "")
        if not raw:
            continue

        try:
            event_utc = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            event_local = event_utc.astimezone(LOCAL_TZ)
            event_local_date = event_local.date()
        except Exception as e:
            logging.error(f"Failed to parse event date '{raw}': {e}")
            continue

        if event_local_date == today_local:
            logging.info(
                "Match found: %s on local date %s (utc=%s, local=%s)",
                event.get("name"),
                event_local_date,
                event_utc,
                event_local,
            )
            return True

    logging.info("No events matched today's local date")
    return False

# ----------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------

if is_team_playing_today(API_ENDPOINT):
    logging.info("The Denver Broncos are playing today.")

    send_udp_message("turn", {"value": 1})
    time.sleep(1)

    send_udp_message("razer", {"pt": "uwABsQEK"})
    send_udp_message("razer", {"pt": "uwAgsAAKAAD//30AAAD//30AAAD/AAD//30AAAD//30AAAD/IQ=="})

    num_iterations = TOTAL_DURATION // INTERVAL
    next_time = time.time()

    try:
        for _ in range(num_iterations):
            send_udp_message("status")
            next_time += INTERVAL
            time.sleep(max(0, next_time - time.time()))
    except KeyboardInterrupt:
        logging.info("Interrupted by user")

    logging.info("Script executed successfully.")
else:
    logging.info("The Denver Broncos are not playing today.")
