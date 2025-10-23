from __future__ import annotations

import random
import threading
from typing import List, Optional

from .bot_player import BotBrain


class BotManager:
    def __init__(self, game, verbose: bool = False) -> None:
        self.game = game
        self.verbose = verbose
        self._lock = threading.Lock()
        self._bots: List[BotBrain] = []
        self._name_pool = [
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

    def _log(self, message: str) -> None:
        if self.verbose:
            print(f"[BotManager] {message}")

    def ensure_bots(self, requested: Optional[int] = None) -> str:
        with self._lock:
            current_players = len(self.game.players)
            max_players = 4
            if current_players >= max_players:
                return "Table already has four players."

            target = requested if requested is not None else max_players
            target = max(0, min(target, max_players))
            if target <= current_players:
                return "No bots added."

            needed = target - current_players
            names = self._generate_names(needed)
            added = 0
            for name in names:
                bot = BotBrain(
                    name=name,
                    send_fn=self.game.process_command,
                    poll_interval=0.2,
                    verbose=self.verbose,
                )
                if bot.start():
                    self._bots.append(bot)
                    added += 1
                    self.game.broadcast_players(f"{name} has joined the table.")
                else:
                    self._log(f"Failed to start bot {name}")

            if added == 0:
                return "Unable to add bots."
            return f"{added} bot(s) joined the table."

    def stop_all(self) -> None:
        with self._lock:
            for bot in self._bots:
                bot.stop()
            for bot in self._bots:
                bot.join(timeout=1.0)
            self._bots.clear()

    def _generate_names(self, count: int) -> List[str]:
        used_names = {bot.name for bot in self._bots}
        used_names.update(player.name for player in self.game.players.values())
        available = [name for name in self._name_pool if name not in used_names]
        random.shuffle(available)
        names: List[str] = []
        for name in available:
            if len(names) >= count:
                break
            names.append(name)
        suffix = 1
        while len(names) < count:
            candidate = f"Bot{suffix}"
            suffix += 1
            if candidate in used_names or candidate in names:
                continue
            names.append(candidate)
        return names
