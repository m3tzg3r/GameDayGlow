#!/usr/bin/env python3
"""
Govee H6061 streaming animation test.

Pushes a smooth traveling color wave across the 10 hexagon zones over the
local razer/DreamView UDP path, to evaluate how a self-generated "scene"
looks at a given frame rate (the strobe question).

This is a TEST tool -- short default duration, no scheduling, no cron.
Run it on a machine on the SAME LAN as the panel (multicast won't route).

Usage:
    python3 stream_test.py                 # Avalanche, 100ms frames, 30s
    python3 stream_test.py --interval 50   # try 10fps vs 20fps
    python3 stream_test.py --team broncos --speed 0.5 --duration 20
    python3 stream_test.py --interval 200 --team nuggets
"""

import argparse
import base64
import json
import math
import socket
import sys
import time

GROUP_ADDR = "239.255.255.250"
GROUP_PORT = 4001
TTL = 2
NUM_ZONES = 10

# Two-color palettes blended across the panel. (primary, accent)
# High-value/saturated so the wave stays bright; dark base colors render dim.
TEAMS = {
    "avs":     ((230, 20, 60),  (30, 110, 235)),   # bright burgundy-red / blue
    "broncos": ((255, 95, 0),   (20, 70, 235)),    # bright orange / blue
    "nuggets": ((255, 205, 0),  (25, 95, 235)),    # gold / blue
}


def build_color_payload(zones):
    """zones: list of 10 (r,g,b) tuples -> base64 razer 'pt' string.

    Format reverse-engineered from the app's Razer Chroma packets:
        bb 00 <len> b0 00 <segcount> [r g b]*N <xor-checksum>
    """
    assert len(zones) == NUM_ZONES, f"need {NUM_ZONES} zones"
    body = bytearray([0x00, NUM_ZONES])            # 00 0a
    for (r, g, b) in zones:
        body += bytes((r & 0xFF, g & 0xFF, b & 0xFF))
    packet = bytearray([0xBB, 0x00, len(body), 0xB0]) + body
    checksum = 0
    for byte in packet:
        checksum ^= byte
    packet.append(checksum)
    return base64.b64encode(bytes(packet)).decode("ascii")


def send(sock, cmd, data=None):
    msg = json.dumps({"msg": {"cmd": cmd, "data": data or {}}})
    sock.sendto(msg.encode("utf-8"), (GROUP_ADDR, GROUP_PORT))


def lerp(a, b, t):
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def vivid(color):
    """Scale a color so its brightest channel hits 255 -- keeps hue, removes
    the brightness dip that linear RGB blends create at the midpoint."""
    m = max(color)
    if m == 0:
        return color
    s = 255.0 / m
    return tuple(min(255, round(c * s)) for c in color)


def frame_colors(primary, accent, phase, make_vivid=False, mode="team",
                 waves=1.0, fade=0.0):
    """Traveling pattern across the panel, drifting over time via `phase`.

    mode="team": each zone snaps to primary OR accent -- the boundary sweeps,
                 stays on-theme. `fade` (0-1) softens the boundaries by dimming
                 toward black at the edges (fade through black, NOT through
                 purple), so the look fades without going off-brand.
    mode="blend": smooth primary<->accent gradient (passes through mixed
                  colors; pretty but off-brand for red/blue teams).
    """
    colors = []
    for i in range(NUM_ZONES):
        s = math.sin(2 * math.pi * (i / NUM_ZONES * waves) - phase)  # -1..1
        if mode == "team":
            base = accent if s >= 0 else primary
            if fade > 0:
                # brightness ramps 0->1 from boundary to band center
                bright = min(1.0, abs(s) / fade)
                base = tuple(round(c * bright) for c in base)
            colors.append(base)
        else:
            c = lerp(primary, accent, 0.5 + 0.5 * s)
            colors.append(vivid(c) if make_vivid else c)
    return colors


def main():
    p = argparse.ArgumentParser(description="Govee H6061 streaming wave test")
    p.add_argument("--team", choices=TEAMS, default="avs")
    p.add_argument("--interval", type=int, default=100,
                   help="ms between frames (100=10fps, 50=20fps)")
    p.add_argument("--duration", type=int, default=30, help="seconds to run")
    p.add_argument("--speed", type=float, default=0.8,
                   help="wave drift speed (cycles/sec)")
    p.add_argument("--brightness", type=int, default=100,
                   help="panel brightness 1-100 (separate from color)")
    p.add_argument("--vivid", action="store_true",
                   help="(blend mode) normalize every frame to max brightness")
    p.add_argument("--mode", choices=["team", "blend"], default="team",
                   help="team=pure team colors only (default); blend=gradient")
    p.add_argument("--waves", type=float, default=1.0,
                   help="how many color bands span the panel (try 1-3)")
    p.add_argument("--fade", type=float, default=0.0,
                   help="(team mode) soften band edges via black, 0=hard 1=soft")
    args = p.parse_args()

    primary, accent = TEAMS[args.team]
    interval_s = args.interval / 1000.0
    fps = 1000.0 / args.interval
    print(f"team={args.team}  mode={args.mode}  waves={args.waves}  "
          f"interval={args.interval}ms (~{fps:.0f} fps)  duration={args.duration}s  "
          f"speed={args.speed}  brightness={args.brightness}")

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, TTL)
    try:
        send(sock, "turn", {"value": 1})
        time.sleep(0.5)
        send(sock, "brightness", {"value": args.brightness})  # separate from color
        time.sleep(0.2)
        send(sock, "razer", {"pt": "uwABsQEK"})   # enable stream mode
        time.sleep(0.2)

        frames = int(args.duration / interval_s)
        next_time = time.time()
        for n in range(frames):
            phase = 2 * math.pi * args.speed * (n * interval_s)
            payload = build_color_payload(frame_colors(
                primary, accent, phase, args.vivid, args.mode, args.waves, args.fade))
            send(sock, "razer", {"pt": payload})
            next_time += interval_s
            time.sleep(max(0, next_time - time.time()))

        # settle on a clean static frame instead of freezing mid-wave
        send(sock, "razer", {"pt": build_color_payload(frame_colors(
            primary, accent, 0, args.vivid, args.mode, args.waves, args.fade))})
        print("done")
    except KeyboardInterrupt:
        print("\ninterrupted")
    finally:
        sock.close()


if __name__ == "__main__":
    main()
