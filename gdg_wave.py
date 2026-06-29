#!/usr/bin/env python3
"""
Shared engine for GameDayGlow v2 animated (wave/fade) scripts.

Streams a slow team-colored wave to a Govee H6061 over the local razer/
DreamView UDP path. The streamed frames double as the keepalive -- the ~60s
razer-mode timeout never fires while we're streaming -- so v2 has NO separate
keepalive loop (unlike v1).

Multi-team coordination: LAST SCRIPT TO START WINS.
Each run writes its start time to a shared claim file. While streaming, every
frame checks the claim; if a newer script has started, this one stops streaming
and exits, leaving the panel to the newer team. This prevents two scripts from
streaming at once (which would flicker the panel at the frame rate) when more
than one team plays the same day.
"""
import base64
import json
import math
import os
import socket
import time

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# --- device / protocol ---
GROUP_ADDR = "239.255.255.250"
GROUP_PORT = 4001
TTL = 2
NUM_ZONES = 10
ENABLE_PT = "uwABsQEK"

# --- look (the settings dialed in during testing) ---
WAVES = 2.0       # 2 bands of each color
SPEED = 0.03      # slow drift, ~one cycle every 33s
FADE = 1.0        # full soft fade (through black, never purple)
INTERVAL = 0.2    # 5 fps -- plenty for this slow drift, half the packets of 10fps

# shared claim file lives next to the scripts
CLAIM_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".gdg_panel_claim")


def get_with_retries(url, retries=3):
    session = requests.Session()
    retry = Retry(total=retries, backoff_factor=0.3, status_forcelist=[500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    try:
        response = session.get(url, timeout=10)
        response.raise_for_status()
        return response
    except requests.exceptions.RequestException as e:
        return None


def _build_payload(zones):
    body = bytearray([0x00, NUM_ZONES])
    for r, g, b in zones:
        body += bytes((r & 0xFF, g & 0xFF, b & 0xFF))
    pkt = bytearray([0xBB, 0x00, len(body), 0xB0]) + body
    chk = 0
    for x in pkt:
        chk ^= x
    pkt.append(chk)
    return base64.b64encode(bytes(pkt)).decode()


def _send(sock, cmd, data=None):
    sock.sendto(json.dumps({"msg": {"cmd": cmd, "data": data or {}}}).encode(),
                (GROUP_ADDR, GROUP_PORT))


def _frame(primary, accent, phase):
    """One wave frame: team-mode bands with fade-through-black at the edges."""
    zones = []
    for i in range(NUM_ZONES):
        s = math.sin(2 * math.pi * (i / NUM_ZONES * WAVES) - phase)  # -1..1
        base = accent if s >= 0 else primary
        bright = min(1.0, abs(s) / FADE) if FADE > 0 else 1.0
        zones.append(tuple(round(c * bright) for c in base))
    return zones


def _read_claim():
    try:
        with open(CLAIM_FILE) as f:
            return float(f.read().strip())
    except (OSError, ValueError):
        return None


def _write_claim(ts):
    tmp = CLAIM_FILE + ".tmp"
    with open(tmp, "w") as f:
        f.write(repr(ts))
    os.replace(tmp, CLAIM_FILE)  # atomic


def run_wave(team, primary, accent, duration, log, now):
    """Claim the panel and stream the wave for `duration` seconds, or until a
    newer script preempts us (last-to-start-wins).

    `now` is the script's start timestamp (time.time()); `log` is a logger fn.
    """
    _write_claim(now)
    log(f"{team}: claimed panel at {now:.3f}; streaming wave for {duration}s (5fps)")

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, TTL)
    try:
        _send(sock, "turn", {"value": 1})
        time.sleep(0.5)
        _send(sock, "brightness", {"value": 100})
        time.sleep(0.2)
        _send(sock, "razer", {"pt": ENABLE_PT})
        time.sleep(0.2)

        frames = int(duration / INTERVAL)
        next_time = time.time()
        for n in range(frames):
            claim = _read_claim()
            if claim is not None and claim > now + 1e-6:
                log(f"{team}: preempted by a newer script (claim={claim:.3f}); bowing out")
                return
            phase = 2 * math.pi * SPEED * (n * INTERVAL)
            _send(sock, "razer", {"pt": _build_payload(_frame(primary, accent, phase))})
            next_time += INTERVAL
            time.sleep(max(0, next_time - time.time()))
        log(f"{team}: finished {duration}s window")
    except KeyboardInterrupt:
        log(f"{team}: interrupted by user")
    finally:
        sock.close()
