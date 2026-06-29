#!/usr/bin/env python3
"""
Replica of the OLD script's light behavior, with NO schedule check.

Reproduces exactly what avshype/broncoshype/nuggetshype do once a game is
detected: turn on -> enable razer -> set static team pattern -> then send
a `status` keepalive every INTERVAL seconds. Lets you test the old behavior
on a no-game day and compare its Ctrl-C revert against stream_test.py.

    python3 keepalive_test.py                      # avs, 30s keepalive
    python3 keepalive_test.py --team broncos --interval 20
    python3 keepalive_test.py --interval 30 --duration 600

Experiment: let it set the color, then Ctrl-C and time how long until the
panel reverts. Compare to stream_test.py (continuous frames) and set_once.py
(no keepalive at all). Same hardware, three packet patterns.
"""
import argparse, json, socket, time

GROUP_ADDR, GROUP_PORT, TTL = "239.255.255.250", 4001, 2

ENABLE = "uwABsQEK"
COLOR = {  # the exact base64 payloads the old scripts ship
    "avs":     "uwAgsAAKAAD//wAAAAD//wAAAAD/AAD//wAAAAD//wAAAAD/IQ==",
    "broncos": "uwAgsAAKAAD//30AAAD//30AAAD/AAD//30AAAD//30AAAD/IQ==",
    "nuggets": "uwAgsAAKAAD///8AAAD///8AAAD/AAD///8AAAD///8AAAD/IQ==",
}

def send(sock, cmd, data=None):
    sock.sendto(json.dumps({"msg": {"cmd": cmd, "data": data or {}}}).encode(),
                (GROUP_ADDR, GROUP_PORT))

p = argparse.ArgumentParser()
p.add_argument("--team", choices=COLOR, default="avs")
p.add_argument("--interval", type=int, default=30, help="keepalive seconds")
p.add_argument("--duration", type=int, default=600, help="seconds before auto-stop")
args = p.parse_args()

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
s.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, TTL)
try:
    send(s, "turn", {"value": 1})
    time.sleep(1)
    send(s, "razer", {"pt": ENABLE})
    send(s, "razer", {"pt": COLOR[args.team]})
    print(f"{args.team} set. sending `status` every {args.interval}s. "
          f"Ctrl-C and watch when it reverts.")

    iters = args.duration // args.interval
    next_time = time.time()
    for _ in range(iters):
        send(s, "status")
        next_time += args.interval
        time.sleep(max(0, next_time - time.time()))
except KeyboardInterrupt:
    print("\nstopped keepalives -- watch the panel now")
finally:
    s.close()
