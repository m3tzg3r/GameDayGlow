#!/usr/bin/env python3

import requests
import json
import socket
import time
import logging
from datetime import datetime
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

# Constants
LOG_FILE_NAME = 'avshype.log'
TOTAL_DURATION = 4 * 60 * 60  # 4 hours
INTERVAL = 30  # 30 seconds
GROUP_ADDR = "239.255.255.250"
GROUP_PORT = 4001
TTL = 2
AVALANCHE_TEAM_ID = 21

logging.basicConfig(
    filename=LOG_FILE_NAME,
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s]: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)


def send_poweron():
    message = {"msg": {"cmd": "turn", "data": {"value": 1}}}
    group = GROUP_ADDR
    port = GROUP_PORT
    ttl = TTL
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, ttl)
    json_result = json.dumps(message)
    logging.info(f"Sending: {json_result}")
    sock.sendto(bytes(json_result, "utf-8"), (group, port))


def send_razer_command(pt):
    message = {"msg": {"cmd": "razer", "data": {"pt": pt}}}
    group = GROUP_ADDR
    port = GROUP_PORT
    ttl = TTL
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, ttl)
    json_result = json.dumps(message)
    logging.info(f"Sending: {json_result}")
    sock.sendto(bytes(json_result, "utf-8"), (group, port))


def send_message():
    message = {"msg": {"cmd": "status", "data": {}}}
    group = GROUP_ADDR
    port = GROUP_PORT
    ttl = TTL
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, ttl)
    json_result = json.dumps(message)
    logging.info(f"Sending: {json_result}")
    sock.sendto(bytes(json_result, "utf-8"), (group, port))


def get_with_retries(url, retries=3):
    session = requests.Session()
    retry = Retry(total=retries, backoff_factor=0.3, status_forcelist=[500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    try:
        response = session.get(url, timeout=10)
        response.raise_for_status()
        return response
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to retrieve data after {retries} retries: {e}")
        return None


def debug_dump_schedule(data, current_date):
    game_week = data.get("gameWeek", [])
    dates_found = [d.get("date") for d in game_week]
    logging.info(f"Checking schedule for: {current_date}")
    logging.info(f"gameWeek contains {len(game_week)} day(s): {dates_found}")


def is_colorado_avalanche_playing():
    current_date = datetime.now().strftime("%Y-%m-%d")
    endpoint = f"https://api-web.nhle.com/v1/schedule/{current_date}"

    response = get_with_retries(endpoint)
    if not response:
        return False

    schedule_data = response.json()
    game_week = schedule_data.get("gameWeek")

    if not game_week:
        logging.warning(f"gameWeek key missing from API response -- possible API change. Keys present: {list(schedule_data.keys())}")
        return False

    debug_dump_schedule(schedule_data, current_date)

    for game_day in game_week:
        if game_day.get("date") != current_date:
            continue

        games = game_day.get("games", [])
        logging.info(f"Found {len(games)} game(s) scheduled for {current_date}")

        for game in games:
            home_team_id = game.get("homeTeam", {}).get("id")
            away_team_id = game.get("awayTeam", {}).get("id")
            if home_team_id == AVALANCHE_TEAM_ID or away_team_id == AVALANCHE_TEAM_ID:
                return True

        return False

    logging.warning(f"No entry for {current_date} in gameWeek -- API may have changed date format")
    return False


if is_colorado_avalanche_playing():
    logging.info("The Colorado Avalanche are playing today.")

    send_poweron()
    time.sleep(1)

    send_razer_command("uwABsQEK")
    send_razer_command("uwAgsAAKAAD//wAAAAD//wAAAAD/AAD//wAAAAD//wAAAAD/IQ==")

    num_iterations = TOTAL_DURATION // INTERVAL
    next_time = time.time()

    try:
        for _ in range(num_iterations):
            send_message()
            next_time += INTERVAL
            time.sleep(max(0, next_time - time.time()))
    except KeyboardInterrupt:
        logging.info("Interrupted by user")

    logging.info("Script executed successfully.")
else:
    logging.info("The Colorado Avalanche are not playing today.")
