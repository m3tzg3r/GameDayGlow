#!/usr/bin/env python3
"""
Set the panel to a static team pattern ONCE, then exit. No keepalive.

Purpose: test whether razer-mode colors persist on their own. Run this,
note the time, walk away, and check back at 30s / 1m / 3m / 10m to see
*if and when* the panel reverts to its default. That tells us whether the
keepalive loop is needed at all.

    python3 set_once.py             # Avalanche
    python3 set_once.py broncos
    python3 set_once.py nuggets
"""
import base64, json, socket, sys, time

GROUP_ADDR, GROUP_PORT, TTL, NUM_ZONES = "239.255.255.250", 4001, 2, 10

# (accent color, base color) -> zones 2,4,7,9 get accent, rest get base
TEAMS = {
    "avs":     ((255, 0, 0),     (0, 0, 255)),
    "broncos": ((255, 125, 0),   (0, 0, 255)),
    "nuggets": ((255, 255, 0),   (0, 0, 255)),
}

def build_payload(zones):
    body = bytearray([0x00, NUM_ZONES])
    for r, g, b in zones:
        body += bytes((r & 0xFF, g & 0xFF, b & 0xFF))
    pkt = bytearray([0xBB, 0x00, len(body), 0xB0]) + body
    c = 0
    for x in pkt:
        c ^= x
    pkt.append(c)
    return base64.b64encode(bytes(pkt)).decode()

def send(sock, cmd, data=None):
    sock.sendto(json.dumps({"msg": {"cmd": cmd, "data": data or {}}}).encode(),
                (GROUP_ADDR, GROUP_PORT))

team = sys.argv[1] if len(sys.argv) > 1 else "avs"
brightness = int(sys.argv[2]) if len(sys.argv) > 2 else 100  # 1-100
accent, base = TEAMS[team]
zones = [accent if i in (1, 3, 6, 8) else base for i in range(NUM_ZONES)]

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
s.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, TTL)
send(s, "turn", {"value": 1})
time.sleep(0.5)
send(s, "brightness", {"value": brightness})   # separate from color; test if it applies in razer mode
time.sleep(0.2)
send(s, "razer", {"pt": "uwABsQEK"})
time.sleep(0.2)
send(s, "razer", {"pt": build_payload(zones)})
s.close()
print(f"set {team} pattern at brightness {brightness} and exited. "
      f"note the time and watch for a revert.")
