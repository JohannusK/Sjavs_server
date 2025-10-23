#!/usr/bin/env python3
"""
Launch a small set of robot players that keep Sjavs rounds moving.

Usage:
    python scripts/random_bots.py --host 127.0.0.1 --port 65432 --bots 3

Run this while the server is up, then attach your own client as the
fourth seat to play alongside the bots.
"""

from __future__ import annotations

import argparse
import socket
import time
from typing import Callable, List

from server.bot_player import BotBrain, unique_names


def make_send_fn(host: str, port: int, timeout: float = 3.0) -> Callable[[str], str]:
    def send(message: str) -> str:
        data = message.encode("utf-8")
        with socket.create_connection((host, port), timeout=timeout) as sock:
            sock.sendall(data)
            return sock.recv(4096).decode("utf-8")

    return send


def main() -> None:
    parser = argparse.ArgumentParser(description="Launch random Sjavs bot players.")
    parser.add_argument("--host", default="127.0.0.1", help="Server hostname (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=65432, help="Server port (default: 65432)")
    parser.add_argument("--bots", type=int, default=3, help="Number of bots to launch (default: 3)")
    parser.add_argument("--quiet", action="store_true", help="Reduce logging output.")
    args = parser.parse_args()

    name_pool = [
        "AnnaBot",
        "BergBot",
        "CarlaBot",
        "DaniBot",
        "EirikBot",
        "FreyBot",
        "GunnarBot",
        "HelgaBot",
        "IvarBot",
    ]
    bot_names = unique_names(args.bots, name_pool)

    send_fn = make_send_fn(args.host, args.port)
    bots: List[BotBrain] = []

    for name in bot_names:
        bot = BotBrain(name=name, send_fn=send_fn, verbose=not args.quiet)
        if bot.start():
            bots.append(bot)
        else:
            print(f"[{name}] Failed to join the table.")
        time.sleep(0.1)

    try:
        while any(bot.is_alive() for bot in bots):
            time.sleep(1.0)
    except KeyboardInterrupt:
        print("Stopping bots...")
    finally:
        for bot in bots:
            bot.stop()
        for bot in bots:
            bot.join(timeout=1.0)


if __name__ == "__main__":
    main()
