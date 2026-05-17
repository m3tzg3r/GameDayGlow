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
LOG_FILE_NAME = 'broncoshype.log'
TOTAL_DURATION = 8 * 60 * 60  # 8 hours
INTERVAL = 20  # 20 seconds
GROUP_ADDR = "239.255.255.250"
GROUP_PORT = 4001
TTL = 2

# Figure out correct NFL season year
today = datetime.now()
season_year = today.year
if today.month < 8:   # Jan–Jul belong to the previous season
    season_year -= 1

API_ENDPOINT = f"https://site.api.espn.com/apis/site/v2/sports/football/nfl/teams/7/schedule?season={season_year}"

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


def send_udp_message(cmd, data=None):
    message = {"msg": {"cmd": cmd, "data": data or {}}}
    group = GROUP_ADDR
    port = GROUP_PORT
    ttl = TTL
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, ttl)
    json_result = json.dumps(message)
    logging.info(f"Sending: {json_result}")
    sock.sendto(bytes(json_result, "utf-8"), (group, port))
    sock.close()


def get_with_retries(api_url, retries=3):
    session = requests.Session()
    retry = Retry(total=retries, backoff_factor=0.3, status_forcelist=[500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)

    try:
        response = session.get(api_url, timeout=10)
        response.raise_for_status()
        return response
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to retrieve data after {retries} retries: {e}")
        return None


def debug_dump_schedule(data):
    local_today = datetime.now().strftime('%Y-%m-%d')
    utc_today = datetime.utcnow().strftime('%Y-%m-%d')
    logging.info(f"Local today: {local_today}")
    logging.info(f"UTC today:   {utc_today}")

    for event in data.get('events', []):
        event_date = event.get("date", "").split("T")[0]
        logging.info(f"Event: {event.get('name')} "
                     f"id={event.get('id')} "
                     f"date={event.get('date')} "
                     f"-> parsed_date={event_date}")


def is_denver_broncos_playing(api_url):
    response = get_with_retries(api_url)
    if not response:
        return False

    try:
        data = response.json()

        events = data.get('events')
        if events is None:
            logging.warning(f"events key missing from API response -- possible API change. Keys present: {list(data.keys())}")
            return False

        debug_dump_schedule(data)

        local_today = datetime.now().strftime('%Y-%m-%d')
        utc_today = datetime.utcnow().strftime('%Y-%m-%d')
        logging.info(f"Checking against dates: {local_today} (local), {utc_today} (UTC)")

        for event in events:
            event_date = event.get('date', '').split('T')[0]
            if event_date in (local_today, utc_today):
                logging.info(f"Match found: {event.get('name')} on {event_date}")
                return True

        logging.info("No events matched today's date")
        return False

    except json.JSONDecodeError as e:
        logging.error(f"Error parsing JSON response: {e}")
        return False


if is_denver_broncos_playing(API_ENDPOINT):
    logging.info("The Denver Broncos are playing today.")

    send_poweron()
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
