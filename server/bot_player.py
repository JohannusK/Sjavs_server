from __future__ import annotations

import random
import threading
import time
from typing import Callable, List, Optional, Sequence, Tuple

PERMANENT_TRUMPS = {"QC", "QS", "JC", "JS", "JH", "JD"}
SUITS = ("C", "D", "H", "S")


class BotBrain:
    """
    Reusable Sjavs bot that plays random-but-legal cards via a provided command
    transport (callable that sends a raw command string and returns a response).
    """

    def __init__(
        self,
        name: str,
        send_fn: Callable[[str], str],
        poll_interval: float = 0.2,
        verbose: bool = False,
    ) -> None:
        self.name = name
        self._send_fn = send_fn
        self.poll_interval = poll_interval
        self.verbose = verbose

        self.player_id: Optional[int] = None
        self.trump: Optional[str] = None
        self.hand: List[str] = []
        self.current_trick: List[Tuple[int, str]] = []
        self.trick_winners: List[int] = []
        self.last_declared_suits: str = ""
        self.deal_choice_needed = True

        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    # ------------- lifecycle -------------
    def start(self) -> bool:
        if not self._join_table():
            return False
        self._thread.start()
        return True

    def stop(self) -> None:
        self._stop_event.set()

    def join(self, timeout: Optional[float] = None) -> None:
        self._thread.join(timeout)

    def is_alive(self) -> bool:
        return self._thread.is_alive()

    # ------------- transport helpers -------------
    def _log(self, message: str) -> None:
        if self.verbose:
            print(f"[{self.name}] {message}")

    def _send(self, payload: str) -> str:
        return self._send_fn(payload)

    def _join_table(self) -> bool:
        response = self._send(f"Hallo, Eg eri {self.name}").strip()
        if not response.startswith("P"):
            self._log(f"Failed to join table (response={response!r})")
            return False
        try:
            self.player_id = int(response[1:])
        except ValueError:
            self._log(f"Could not parse seat assignment from {response!r}")
            return False
        self._log(f"Took seat P{self.player_id}")
        return True

    def _command(self, body: str) -> str:
        if self.player_id is None:
            raise RuntimeError("Bot has no assigned player id.")
        return self._send(f"P{self.player_id} {body}")

    # ------------- main loop -------------
    def _run(self) -> None:
        while not self._stop_event.is_set():
            try:
                raw = self._command("GU")
            except Exception as exc:  # noqa: BLE001
                self._log(f"Command error: {exc}")
                time.sleep(1.0)
                continue

            text = raw.strip()
            if not text or text == "No new updates.":
                time.sleep(self.poll_interval)
                continue

            self._log(f"<< {text}")
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            for line in lines:
                self._handle_update(line)

            time.sleep(self.poll_interval)

    # ------------- update handlers -------------
    def _handle_update(self, line: str) -> None:
        self._log(f"< {line}")

        if "has played" in line:
            self._record_play(line)
            return

        lower_line = line.lower()
        if " vann" in lower_line:
            self.current_trick.clear()
            try:
                winner_id = int(line.split()[1])
                self.trick_winners.append(winner_id)
            except (ValueError, IndexError):
                pass
            return

        if line.startswith("Round totals"):
            self.hand.clear()
            self.current_trick.clear()
            self.trick_winners.clear()
            self.trump = None
            self.deal_choice_needed = True
            return

        if line.startswith("The current trump is"):
            self.trump = line.split()[-1].strip(".")
            return

        if line.startswith("Deck split") or line.startswith("Deck unchanged"):
            return

        if line.startswith("Received 8 cards"):
            self._refresh_hand()
            return

        if ("choose 'split" in lower_line) and self.deal_choice_needed:
            self._handle_split_choice()
            return

        if (self.name in line) and ("turn to declare" in lower_line or "hvat meldar" in lower_line):
            self._handle_declaration()
            return

        if line == "What suit is your declaration?":
            self._handle_suit_choice()
            return

        if line.startswith("Play a card") or line == "Your turn!":
            self._play_card()
            return

        if line.startswith("Declarations complete"):
            self.current_trick.clear()
            return

    # ------------- split/declaration helpers -------------
    def _handle_split_choice(self) -> None:
        if random.random() < 0.5:
            position = random.randint(10, 22)
            action = f"split {position}"
        else:
            action = "banka"
        response = self._command(action).strip()
        self._log(f"> {action} [{response}]")
        self.deal_choice_needed = False

    def _handle_declaration(self) -> None:
        summary = self._command("maxmeld").strip()
        digits = "".join(ch for ch in summary if ch.isdigit())
        suits = "".join(ch for ch in summary if ch.isalpha()).upper()
        self.last_declared_suits = suits
        length = int(digits) if digits else 0

        if length < 5:
            response = self._command("M 0").strip()
            self._log(f"> M 0 [{response}]")
            return

        response = self._command(f"M {length}").strip()
        self._log(f"> M {length} [{response}]")
        if "Invalid" in response:
            fallback = self._command("M 0").strip()
            self._log(f"> M 0 [{fallback}]")

    def _handle_suit_choice(self) -> None:
        if self.last_declared_suits:
            if "C" in self.last_declared_suits:
                suit = "C"
            else:
                suit = random.choice(list(self.last_declared_suits))
        else:
            suit = random.choice(SUITS)

        response = self._command(f"S {suit}").strip()
        self._log(f"> S {suit} [{response}]")
        if "Invalid" in response:
            suit = random.choice(SUITS)
            retry = self._command(f"S {suit}").strip()
            self._log(f"> S {suit} [{retry}]")
        self.trump = suit

    # ------------- hand management -------------
    def _refresh_hand(self) -> None:
        response = self._command("show")
        if "hand:" not in response:
            return
        cards_section = response.split(": ", 1)[1].strip()
        self.hand = [card.strip() for card in cards_section.split(",") if card.strip()]
        self._log(f"Hand -> {self.hand}")

    def _record_play(self, line: str) -> None:
        try:
            parts = line.split()
            player_id = int(parts[0])
            card = parts[-1]
        except (ValueError, IndexError):
            return
        self.current_trick.append((player_id, card))
        if player_id == self.player_id and card in self.hand:
            self.hand.remove(card)

    # ------------- card utilities -------------
    def _is_trump(self, card: str) -> bool:
        return card in PERMANENT_TRUMPS or (self.trump is not None and card.endswith(self.trump))

    def _matches_lead(self, card: str, lead_card: str) -> bool:
        if self._is_trump(lead_card):
            return self._is_trump(card)
        return card[1] == lead_card[1] and card not in PERMANENT_TRUMPS

    def _legal_cards(self, lead_card: Optional[str]) -> List[str]:
        if not lead_card or self.trump is None:
            return list(self.hand)
        if self._is_trump(lead_card):
            trumps = [card for card in self.hand if self._is_trump(card)]
            return trumps or list(self.hand)
        matching = [card for card in self.hand if self._matches_lead(card, lead_card)]
        return matching or list(self.hand)

    def _play_card(self) -> None:
        if not self.hand:
            self._refresh_hand()
            if not self.hand:
                return

        lead_card = self.current_trick[0][1] if self.current_trick else None
        options = self._legal_cards(lead_card)
        random.shuffle(options)

        for card in options:
            response = self._command(f"P {card}").strip()
            self._log(f"> P {card} [{response}]")
            if response in {"OK", ""}:
                if card in self.hand:
                    self.hand.remove(card)
                self.current_trick.append((self.player_id or 0, card))
                return
            if "Tú hevur ikki" in response:
                self._refresh_hand()
            if "Ikki loyvt" in response:
                continue
        for card in list(self.hand):
            response = self._command(f"P {card}").strip()
            if response in {"OK", ""}:
                if card in self.hand:
                    self.hand.remove(card)
                self.current_trick.append((self.player_id or 0, card))
                return


def unique_names(count: int, pool: Sequence[str]) -> List[str]:
    names = list(pool)
    random.shuffle(names)
    if count <= len(names):
        return names[:count]
    result = names
    for idx in range(len(names), count):
        result.append(f"Bot{idx + 1}")
    return result
