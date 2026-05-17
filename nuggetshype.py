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
LOG_FILE_NAME = 'NuggetsHype.log'
TOTAL_DURATION = 4 * 60 * 60  # 4 hours
INTERVAL = 30  # 30 seconds
GROUP_ADDR = "239.255.255.250"
GROUP_PORT = 4001
TTL = 2

API_ENDPOINT = "https://cdn.nba.com/static/json/liveData/scoreboard/todaysScoreboard_00.json"

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


def send_keepalive():
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


def debug_dump_schedule(scoreboard):
    games = scoreboard.get("games", [])
    game_codes = [g.get("gameCode", "N/A") for g in games]
    logging.info(f"Scoreboard contains {len(games)} game(s): {game_codes}")


def is_denver_nuggets_playing():
    current_date = datetime.now().strftime('%Y-%m-%d')

    response = get_with_retries(API_ENDPOINT)
    if not response:
        return False, None

    try:
        data = response.json()
    except json.JSONDecodeError as e:
        logging.error(f"Error parsing JSON response: {e}")
        return False, None

    scoreboard = data.get("scoreboard")
    if scoreboard is None:
        logging.warning(f"scoreboard key missing from API response -- possible API change. Keys present: {list(data.keys())}")
        return False, None

    game_date = scoreboard.get("gameDate")
    if game_date != current_date:
        logging.info(f"API not updated yet. Current date: {current_date}. Game date from API: {game_date}")
        return False, None

    debug_dump_schedule(scoreboard)

    games = scoreboard.get("games")
    if games is None:
        logging.warning(f"games key missing from scoreboard -- possible API change. Keys present: {list(scoreboard.keys())}")
        return False, None

    for game in games:
        game_code = game.get("gameCode", "")
        if "DEN" in game_code:
            return True, game_code

    logging.info("No DEN game found in today's scoreboard")
    return False, None


playing, game_code = is_denver_nuggets_playing()

if playing:
    logging.info(f"The Denver Nuggets are playing today. Game Code: {game_code}")

    send_poweron()
    time.sleep(1)

    send_razer_command("uwABsQEK")
    send_razer_command("uwAgsAAKAAD///8AAAD///8AAAD/AAD///8AAAD///8AAAD/IQ==")

    num_iterations = TOTAL_DURATION // INTERVAL
    next_time = time.time()

    try:
        for _ in range(num_iterations):
            send_keepalive()
            next_time += INTERVAL
            time.sleep(max(0, next_time - time.time()))
    except KeyboardInterrupt:
        logging.info("Interrupted by user")

    logging.info("Script executed successfully.")
else:
    logging.info("Denver Nuggets are not playing today.")
