from __future__ import annotations

import random
import threading
from typing import List, Optional

from .bot_player import BotBrain, DIFFICULTY_STRATEGIES


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

    def ensure_bots(
        self,
        requested: Optional[int] = None,
        difficulty: Optional[str] = None,
    ) -> str:
        with self._lock:
            current_players = len(self.game.players)
            max_players = 4
            if current_players >= max_players:
                return "Table already has four players."

            normalized_difficulty = difficulty.lower() if difficulty else None
            if normalized_difficulty and normalized_difficulty not in DIFFICULTY_STRATEGIES:
                return f"Unknown bot difficulty: {difficulty}."

            target = requested if requested is not None else max_players
            target = max(0, min(target, max_players))
            if target <= current_players:
                return "No bots added."

            needed = target - current_players
            names = self._generate_names(needed, current_players, normalized_difficulty)
            added = 0
            for offset, name in enumerate(names):
                bot_difficulty = normalized_difficulty or self._difficulty_for_name(
                    name, current_players + offset,
                )
                bot = BotBrain(
                    name=name,
                    send_fn=self.game.process_command,
                    poll_interval=0.2,
                    verbose=self.verbose,
                    difficulty=bot_difficulty,
                    strategy_names=DIFFICULTY_STRATEGIES[bot_difficulty],
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

    def _generate_names(
        self,
        count: int,
        current_players: int = 0,
        fixed_difficulty: Optional[str] = None,
    ) -> List[str]:
        used_names = {bot.name for bot in self._bots}
        used_names.update(player.name for player in self.game.players.values())
        available = [name for name in self._name_pool if name not in used_names]
        random.shuffle(available)
        names: List[str] = []
        for offset, name in enumerate(available):
            if len(names) >= count:
                break
            difficulty = fixed_difficulty or self._difficulty_for_name(
                name, current_players + len(names),
            )
            names.append(self._decorate_name(name, difficulty))
        suffix = 1
        while len(names) < count:
            difficulty = fixed_difficulty or self._difficulty_for_name(
                "Bot", current_players + len(names),
            )
            candidate = self._decorate_name(f"Bot{suffix}", difficulty)
            suffix += 1
            if candidate in used_names or candidate in names:
                continue
            names.append(candidate)
        return names

    def _difficulty_for_name(self, _name: str, slot_index: int) -> str:
        levels = ("easy", "medium", "hard")
        return levels[slot_index % len(levels)]

    def _decorate_name(self, base_name: str, difficulty: str) -> str:
        suffix = difficulty.capitalize()
        if base_name.endswith("Bot"):
            return f"{base_name[:-3]}{suffix}Bot"
        return f"{base_name}{suffix}Bot"
