from __future__ import annotations

import random
import threading
import time
from collections import Counter
from typing import Callable, List, Optional, Sequence, Tuple

PERMANENT_TRUMPS = ("QC", "QS", "JC", "JS", "JH", "JD")
SUITS = ("C", "D", "H", "S")
CARD_POINTS = {"A": 11, "T": 10, "K": 4, "Q": 3, "J": 2}
DIFFICULTY_STRATEGIES = {
    "easy": ["discard_filler_when_losing"],
    "medium": [
        "dont_overtake_partner",
        "partner_points_dump",
        "lead_unseen_ace",
        "safe_last_player_capture",
        "discard_dead_suit",
        "discard_filler_when_losing",
    ],
    "hard": [
        "dont_overtake_partner",
        "partner_points_dump",
        "stinga_low_trump",
        "save_high_trumps",
        "safe_last_player_capture",
        "win_cheap_trick",
        "lead_unseen_ace",
        "follow_with_strength_when_long",
        "protect_ace_leads",
        "preserve_entry",
        "discard_dead_suit",
        "bleed_trump_late",
        "discard_filler_when_losing",
    ],
}


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
        difficulty: str = "medium",
        strategy_names: Optional[Sequence[str]] = None,
    ) -> None:
        self.name = name
        self._send_fn = send_fn
        self.poll_interval = poll_interval
        self.verbose = verbose
        self.difficulty = difficulty
        self.strategy_names = list(
            strategy_names
            if strategy_names is not None
            else DIFFICULTY_STRATEGIES.get(difficulty, DIFFICULTY_STRATEGIES["medium"])
        )

        self.player_id: Optional[int] = None
        self.trump: Optional[str] = None
        self.hand: List[str] = []
        self.current_trick: List[Tuple[int, str]] = []
        self.trick_winners: List[int] = []
        self.seen_suits_played: set[str] = set()
        self.seen_cards_played: List[str] = []
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
            self.seen_suits_played.clear()
            self.seen_cards_played.clear()
            self.trump = None
            self.deal_choice_needed = True
            return

        if "No player declared trump. Redealing." in line:
            self.hand.clear()
            self.current_trick.clear()
            self.seen_suits_played.clear()
            self.seen_cards_played.clear()
            self.trump = None
            self.last_declared_suits = ""
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
        if len(card) >= 2:
            self.seen_suits_played.add(card[1])
            self.seen_cards_played.append(card)
        if player_id == self.player_id and card in self.hand:
            self.hand.remove(card)

    # ------------- card utilities -------------
    def _is_trump(self, card: str) -> bool:
        return card in PERMANENT_TRUMPS or (self.trump is not None and card.endswith(self.trump))

    @staticmethod
    def _same_team(player_a: Optional[int], player_b: Optional[int]) -> bool:
        if player_a is None or player_b is None:
            return False
        return player_a % 2 == player_b % 2

    def _lead_card(self) -> Optional[str]:
        return self.current_trick[0][1] if self.current_trick else None

    def _lead_is_trump(self) -> bool:
        lead = self._lead_card()
        return bool(lead and self._is_trump(lead))

    def _remaining_players_after_me(self) -> int:
        return max(0, 4 - (len(self.current_trick) + 1))

    def _ordinary_trump(self, card: str) -> bool:
        return self._is_trump(card) and card not in PERMANENT_TRUMPS

    def _trick_points(self, trick: Optional[Sequence[Tuple[int, str]]] = None) -> int:
        plays = trick if trick is not None else self.current_trick
        return sum(self._card_points(card) for _, card in plays)

    def _seen_trump_count(self) -> int:
        return sum(1 for card in self.seen_cards_played if self._is_trump(card))

    def _hand_suit_counts(self, cards: Optional[Sequence[str]] = None) -> Counter:
        suits = [
            card[1]
            for card in (cards if cards is not None else self.hand)
            if len(card) >= 2 and not self._is_trump(card)
        ]
        return Counter(suits)

    def _winning_cards_by_type(self, legal_cards: Sequence[str]) -> tuple[List[str], List[str]]:
        winning_cards = self._winning_cards(legal_cards)
        trump_winners = [card for card in winning_cards if self._is_trump(card)]
        in_suit_winners = [card for card in winning_cards if not self._is_trump(card)]
        return in_suit_winners, trump_winners

    def _lowest_winning_card(
        self,
        winning_cards: Sequence[str],
        lead_card: str,
        prefer_non_permanent_trump: bool = False,
    ) -> Optional[str]:
        if not winning_cards:
            return None
        ordered = list(winning_cards)
        if prefer_non_permanent_trump:
            ordinary = [card for card in ordered if self._ordinary_trump(card)]
            permanent = [card for card in ordered if card in PERMANENT_TRUMPS]
            ordered = ordinary + permanent
        return min(
            ordered,
            key=lambda card: (
                0 if (prefer_non_permanent_trump and self._ordinary_trump(card)) else 1,
                self._card_strength(card, lead_card),
                self._card_points(card),
            ),
        )

    def _lowest_value_discard(self, legal_cards: Sequence[str]) -> Optional[str]:
        suit_counts = self._hand_suit_counts()
        return min(
            legal_cards,
            key=lambda card: (
                self._card_points(card),
                0 if not self._is_trump(card) else 1,
                suit_counts.get(card[1], 0),
                self._card_value_rank(card),
            ),
            default=None,
        )

    def _highest_value_feed(self, legal_cards: Sequence[str]) -> Optional[str]:
        return max(
            legal_cards,
            key=lambda card: (self._card_points(card), -self._card_value_rank(card)),
            default=None,
        )

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

    def _partner_id(self) -> Optional[int]:
        if self.player_id is None:
            return None
        return ((self.player_id + 1) % 4) + 1

    def _card_value_rank(self, card: str) -> int:
        value = card[0]
        if value == "A":
            return 14
        return {"K": 13, "Q": 12, "J": 11, "T": 10, "9": 9, "8": 8, "7": 7}.get(value, 0)

    def _card_strength(self, card: str, lead_card: str) -> Tuple[int, int]:
        if card in PERMANENT_TRUMPS:
            return 3, len(PERMANENT_TRUMPS) - PERMANENT_TRUMPS.index(card)
        if self._is_trump(card):
            return 2, self._card_value_rank(card)
        if card[1] == lead_card[1]:
            return 1, self._card_value_rank(card)
        return 0, self._card_value_rank(card)

    def _current_winning_play(
        self, trick: Optional[List[Tuple[int, str]]] = None
    ) -> Optional[Tuple[int, str]]:
        plays = trick if trick is not None else self.current_trick
        if not plays:
            return None
        lead_card = plays[0][1]
        winner = plays[0]
        best_strength = self._card_strength(winner[1], lead_card)
        for player_id, card in plays[1:]:
            strength = self._card_strength(card, lead_card)
            if strength > best_strength:
                winner = (player_id, card)
                best_strength = strength
        return winner

    def _card_points(self, card: str) -> int:
        return CARD_POINTS.get(card[0], 0)

    def _winning_cards(self, legal_cards: Sequence[str]) -> List[str]:
        if not self.current_trick:
            return []
        winning_cards: List[str] = []
        for card in legal_cards:
            candidate = self.current_trick + [(self.player_id or 0, card)]
            winner = self._current_winning_play(candidate)
            if winner and winner[0] == self.player_id:
                winning_cards.append(card)
        return winning_cards

    def _strategy_partner_points_dump(self, legal_cards: Sequence[str]) -> Optional[str]:
        if not self.current_trick or self.player_id is None:
            return None
        winner = self._current_winning_play()
        partner_id = self._partner_id()
        if not winner or winner[0] != partner_id:
            return None

        remaining_players = 4 - (len(self.current_trick) + 1)
        winning_card = winner[1]
        partner_is_secure = remaining_players == 0 or winning_card == "QC"
        if not partner_is_secure:
            return None

        return self._highest_value_feed(legal_cards)

    def _strategy_dont_overtake_partner(self, legal_cards: Sequence[str]) -> Optional[str]:
        if not self.current_trick or self.player_id is None:
            return None
        winner = self._current_winning_play()
        partner_id = self._partner_id()
        if not winner or winner[0] != partner_id:
            return None
        secure = self._remaining_players_after_me() == 0 or winner[1] == "QC"
        if secure:
            return self._highest_value_feed(legal_cards)
        return self._lowest_value_discard(legal_cards)

    def _strategy_stinga_low_trump(self, legal_cards: Sequence[str]) -> Optional[str]:
        if not self.current_trick or self.player_id is None:
            return None
        if self._lead_is_trump():
            return None
        winner = self._current_winning_play()
        partner_id = self._partner_id()
        if winner and winner[0] == partner_id:
            return None

        lead_card = self.current_trick[0][1]
        in_suit_winners, trump_winners = self._winning_cards_by_type(legal_cards)
        if in_suit_winners or not trump_winners:
            return None

        trick_points = self._trick_points()
        non_permanent_trump_winners = [card for card in trump_winners if self._ordinary_trump(card)]
        if non_permanent_trump_winners:
            return self._lowest_winning_card(non_permanent_trump_winners, lead_card, prefer_non_permanent_trump=True)
        if trick_points < 10:
            return None
        return self._lowest_winning_card(trump_winners, lead_card, prefer_non_permanent_trump=True)

    def _strategy_save_high_trumps(self, legal_cards: Sequence[str]) -> Optional[str]:
        if not self.current_trick:
            return None
        lead_card = self.current_trick[0][1]
        _, trump_winners = self._winning_cards_by_type(legal_cards)
        if len(trump_winners) < 2:
            return None
        return self._lowest_winning_card(trump_winners, lead_card, prefer_non_permanent_trump=True)

    def _strategy_safe_last_player_capture(self, legal_cards: Sequence[str]) -> Optional[str]:
        if len(self.current_trick) != 3:
            return None
        winner = self._current_winning_play()
        if winner and winner[0] == self._partner_id():
            return None
        winning_cards = self._winning_cards(legal_cards)
        if not winning_cards:
            return None
        return self._lowest_winning_card(winning_cards, self.current_trick[0][1], prefer_non_permanent_trump=True)

    def _strategy_win_cheap_trick(self, legal_cards: Sequence[str]) -> Optional[str]:
        if not self.current_trick:
            return None
        if self._current_winning_play() and self._current_winning_play()[0] == self._partner_id():
            return None
        winning_cards = self._winning_cards(legal_cards)
        if not winning_cards:
            return None
        return min(
            winning_cards,
            key=lambda card: (self._card_strength(card, self.current_trick[0][1]), self._card_points(card)),
        )

    def _strategy_discard_filler_when_losing(self, legal_cards: Sequence[str]) -> Optional[str]:
        if not self.current_trick or self.player_id is None:
            return None
        winner = self._current_winning_play()
        partner_id = self._partner_id()
        if not winner or winner[0] in {self.player_id, partner_id}:
            return None

        winning_cards = self._winning_cards(legal_cards)
        if winning_cards:
            return None

        return self._lowest_value_discard(legal_cards)

    def _strategy_discard_dead_suit(self, legal_cards: Sequence[str]) -> Optional[str]:
        if not self.current_trick or self.player_id is None:
            return None
        winner = self._current_winning_play()
        partner_id = self._partner_id()
        if not winner or winner[0] in {self.player_id, partner_id}:
            return None
        if self._winning_cards(legal_cards):
            return None
        return self._lowest_value_discard(legal_cards)

    def _strategy_lead_unseen_ace(self, legal_cards: Sequence[str]) -> Optional[str]:
        if self.current_trick:
            return None
        if len(self.trick_winners) > 2:
            return None
        ace_candidates = [
            card for card in legal_cards
            if (
                card.startswith("A")
                and len(card) >= 2
                and card[1] not in self.seen_suits_played
                and not self._is_trump(card)
            )
        ]
        if not ace_candidates:
            return None
        ace_candidates.sort(
            key=lambda card: (
                self._card_points(card),
                -self._card_value_rank(card),
            ),
        )
        return ace_candidates[0]

    def _strategy_follow_with_strength_when_long(self, legal_cards: Sequence[str]) -> Optional[str]:
        if not self.current_trick:
            return None
        lead_card = self.current_trick[0][1]
        follow_cards = [card for card in legal_cards if self._matches_lead(card, lead_card)]
        if len(follow_cards) < 2:
            return None
        if self._winning_cards(follow_cards):
            return None
        suit_counts = self._hand_suit_counts()
        if suit_counts.get(lead_card[1], 0) < 2:
            return None
        return min(
            follow_cards,
            key=lambda card: (self._card_points(card), self._card_value_rank(card)),
        )

    def _strategy_protect_ace_leads(self, legal_cards: Sequence[str]) -> Optional[str]:
        if len(self.current_trick) != 1:
            return None
        partner_id = self._partner_id()
        leader_id, lead_card = self.current_trick[0]
        if leader_id != partner_id:
            return None
        if not lead_card.startswith("A") or self._is_trump(lead_card):
            return None
        return self._highest_value_feed(legal_cards)

    def _strategy_preserve_entry(self, legal_cards: Sequence[str]) -> Optional[str]:
        if self.current_trick:
            return None
        non_trumps = [card for card in legal_cards if not self._is_trump(card)]
        if len(non_trumps) < 2:
            return None
        strong_entries = [card for card in non_trumps if card[0] in {"A", "K"}]
        if not strong_entries:
            return None
        return min(
            non_trumps,
            key=lambda card: (
                1 if card in strong_entries else 0,
                self._card_points(card),
                self._card_value_rank(card),
            ),
        )

    def _strategy_bleed_trump_late(self, legal_cards: Sequence[str]) -> Optional[str]:
        if self.current_trick or self.trump is None:
            return None
        if len(self.trick_winners) < 5:
            return None
        seen_trumps = self._seen_trump_count()
        if seen_trumps >= 8:
            return None
        trump_cards = [card for card in legal_cards if self._ordinary_trump(card)]
        if not trump_cards:
            return None
        return min(
            trump_cards,
            key=lambda card: (self._card_points(card), self._card_value_rank(card)),
        )

    def _choose_card(self, legal_cards: Sequence[str]) -> str:
        strategy_map = {
            "dont_overtake_partner": self._strategy_dont_overtake_partner,
            "partner_points_dump": self._strategy_partner_points_dump,
            "stinga_low_trump": self._strategy_stinga_low_trump,
            "save_high_trumps": self._strategy_save_high_trumps,
            "safe_last_player_capture": self._strategy_safe_last_player_capture,
            "discard_filler_when_losing": self._strategy_discard_filler_when_losing,
            "discard_dead_suit": self._strategy_discard_dead_suit,
            "lead_unseen_ace": self._strategy_lead_unseen_ace,
            "follow_with_strength_when_long": self._strategy_follow_with_strength_when_long,
            "protect_ace_leads": self._strategy_protect_ace_leads,
            "preserve_entry": self._strategy_preserve_entry,
            "bleed_trump_late": self._strategy_bleed_trump_late,
            "win_cheap_trick": self._strategy_win_cheap_trick,
        }
        for strategy_name in self.strategy_names:
            strategy = strategy_map.get(strategy_name)
            if strategy is None:
                continue
            choice = strategy(legal_cards)
            if choice:
                return choice
        options = list(legal_cards)
        random.shuffle(options)
        return options[0]

    def _play_card(self) -> None:
        if not self.hand:
            self._refresh_hand()
            if not self.hand:
                return

        lead_card = self.current_trick[0][1] if self.current_trick else None
        options = self._legal_cards(lead_card)
        chosen = self._choose_card(options)

        for card in [chosen, *[card for card in options if card != chosen]]:
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
