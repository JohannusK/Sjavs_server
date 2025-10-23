from __future__ import annotations

import time
from collections import defaultdict
from typing import DefaultDict, TYPE_CHECKING

from .utils import Deck, Card, Player, Table

if TYPE_CHECKING:  # pragma: no cover
    from .bot_manager import BotManager


class Game:
    def __init__(self) -> None:
        self.deck: Deck | None = None
        self.table: Table | None = None

        self.nPlayers: int = 0
        self.teamp: dict[str, list[int]] = {"Vit": [1, 3], "Tit": [2, 4]}
        self.STATES: list[str] = [
            "init",
            "deal",
            "declaration",
            "first_card",
            "play",
            "end",
        ]
        self.state: str = "init"
        self.game_over: bool = True
        self.players: dict[int, Player] = {}
        self.updatesForPlayers: DefaultDict[int, list[str]] = defaultdict(list)
        self.dealer_position: int = 1
        self.current_turn: int = 0  # init to so sanity checks unter game_init don't freak out
        self.deal_method: str = "fours"
        self.trump_length: int = 0  # Length of the longest trump suit declared
        self.trump_suit: str | None = None  # Suit of the declared trump
        self.trump_owner: Player | None = None
        self.declaration_count: int = 1
        self.declaration_team: str | None = None
        self.scoreboard: dict[str, int] = {"Vit": 24, "Tit": 24}
        self.next_game_bonus: int = 0
        self.trick_winners: list[int] = []
        self.bot_manager: BotManager | None = None
        self.last_trick_winner: int | None = None
        self.highlight_until: float = 0.0
        self.last_trick_cards: list[tuple[int, str]] = []
        self.last_trick_expire: float = 0.0
        self.last_reset_message: str | None = None

    def handle_trump_declaration(self, command: str, player_id: int) -> str:
        parts = command.split()
        try:
            declaration = int(parts[1])
        except (IndexError, ValueError):
            declaration = 0
        if player_id != self.current_turn:
            return "Not your turn"

        current_player = self.players[player_id]
        maxmeld = current_player.find_highest_trump_declaration()
        digits = "".join(ch for ch in maxmeld if ch.isdigit())
        maxmeld_length = int(digits) if digits else 0
        maxmeld_suits = "".join(ch for ch in maxmeld if ch.isalpha()).upper()

        if declaration == 0 or maxmeld_length < 5:
            response = f"{str(player_id)} {current_player.name} passes."
            self.declaration_count += 1
        elif (
            declaration >= 5
            and maxmeld_length >= declaration
            and (
                declaration > self.trump_length
                or ("C" in maxmeld_suits and declaration == self.trump_length)
            )
        ):
            response = f"{str(player_id)} {current_player.name} declares {declaration}"
            if declaration == self.trump_length and "C" in maxmeld_suits:
                response += " Better"
                self.trump_suit = "C"
            self.trump_length = declaration
            self.trump_owner = current_player
            self.declaration_team = self._team_for_player(player_id)
            self.declaration_count += 1
        else:
            return "Invalid declaration"

        # Update all players


        self.broadcast_players(response)

        # Move to the next player
        self.current_turn = (self.current_turn % self.nPlayers) + 1

        if self.declaration_count > self.nPlayers:
            if self.trump_owner is None:
                self.broadcast_players("No player declared trump. Redealing.")
                self._redeal_after_failed_declaration()
                return " "
            self.current_turn = self.trump_owner.id
            self.broadcast_players(
                f"Declarations complete. {self.trump_owner.name} has the highest declaration."
            )
            self.updatesForPlayers[self.trump_owner.id].append(
                "What suit is your declaration?"
            )
            return " "
        self.updatesForPlayers[self.current_turn].append(
            f"{self.players[self.current_turn].name}'s turn to declare."
        )

        return " "

    def get_state(self, info: bool = False) -> str:
        if not info:
            return self.state
        return (
                self.state
                + "\n"
                + {"init": f"{self.nPlayers} have joined"}.get(
            self.state, "Not Implemented"
        )
        )

    def _reset_round_state(self) -> None:
        self.trump_length = 0
        self.trump_suit = None
        self.trump_owner = None
        self.declaration_count = 1
        self.current_turn = 0
        self.deal_method = "fours"
        self.declaration_team = None
        self.trick_winners = []
        self.last_trick_winner = None
        self.highlight_until = 0.0

    @staticmethod
    def _team_for_player(player_id: int) -> str:
        return "Vit" if player_id % 2 == 1 else "Tit"

    def attach_bot_manager(self, manager: "BotManager") -> None:
        self.bot_manager = manager
        self.last_reset_message = None

    def _check_player_timeouts(self) -> bool:
        timed_out = [pid for pid, player in self.players.items() if player.time_since_last_update() > 60]
        if timed_out:
            names = [self.players[pid].name for pid in timed_out if pid in self.players]
            name_text = ", ".join(names) if names else ", ".join(str(pid) for pid in timed_out)
            reason = f"Inactivity timeout: {name_text}"
            self._force_reset(reason)
            return True
        return False

    def _force_reset(self, reason: str) -> None:
        message = f"Game reset due to inactivity. ({reason})"
        for pid in list(self.updatesForPlayers.keys()):
            self.updatesForPlayers[pid].append(message)
        self.deck = None
        self.table = None
        self.state = "init"
        self.game_over = True
        self.players.clear()
        self.updatesForPlayers.clear()
        self.nPlayers = 0
        self.trump_length = 0
        self.trump_suit = None
        self.trump_owner = None
        self.declaration_count = 1
        self.declaration_team = None
        self.current_turn = 0
        self.deal_method = "fours"
        self.dealer_position = 1
        self.trick_winners = []
        self.last_trick_winner = None
        self.highlight_until = 0.0
        self.scoreboard = {"Vit": 24, "Tit": 24}
        self.next_game_bonus = 0
        self.last_reset_message = message

    def _redeal_after_failed_declaration(self) -> None:
        self.deck = Deck()
        self.deck.shuffle()
        self.table = None
        self._reset_round_state()
        for player in self.players.values():
            player.hand.clear()
        self.state = "deal"
        self.ask_for_split_or_banka(((self.dealer_position - 1) % 4) or 4)

    def setup_game(self) -> None:
        self.deck = Deck()
        self.deck.shuffle()
        self.table = None
        self._reset_round_state()
        for player in self.players.values():
            player.hand.clear()
        self.state = "deal"
        self.ask_for_split_or_banka(((self.dealer_position - 1) % 4) or 4)
        self.game_over = False

    def deal_cards(self, player_id: int, _type: str, split_position: int = 0) -> str:
        """
        Split or banka and deal the cards accordingly.
        params:
            _type: split or banka
            split_position: only applies to split and is the amount of cards to split
        """

        if self.state != "deal":
            return f"Cannot deal cards while in '{self.state}' state."

        if self.current_turn != player_id:
            return self.get_state()

        if (_type == "split") and (10 <= split_position <= 22):
            self.deck.cut(split_position)
            self.deal_method = "fours"
            self.broadcast_players("Deck split and cards dealt in fours")
        elif _type == "banka":
            self.deal_method = "eights"
            self.broadcast_players("Deck unchanged and cards dealt in eights.")
        else:
            return "Invalid split position, try again"

        cards_per_player = 8
        deal_rounds = 2 if self.deal_method == "fours" else 1

        for _round in range(deal_rounds):
            for pid in range(1, self.nPlayers + 1):
                player = self.players[pid]
                cards_to_deal = cards_per_player // deal_rounds
                for _ in range(cards_to_deal):
                    if not player.draw(self.deck):
                        return "Deck ran out of cards while dealing."
        # Notify all players that cards have been dealt
        self.broadcast_players(f"Received {cards_per_player} cards.")

        self.current_turn = (self.dealer_position + 1) % 4 or 4
        self.state = "declaration"
        self.broadcast_players(f"{self.players[self.current_turn].name} hvat meldar tú?")
        return " "

    def ask_for_split_or_banka(self, player_id: int) -> None:
        self.current_turn = player_id
        self.updatesForPlayers[player_id].append("Choose 'split <position>' or 'banka'")

    def broadcast_players(self, msg: str) -> None:
        for player in self.players.values():
            self.updatesForPlayers[player.id].append(msg)

    def process_command(self, command: str) -> str:
        """
        ```init
        `Hallo, Eg eri {myname}`
            docs:
                registrer a new player with name {myname}
            return:
                full: there is no empty space for you
                P{player_id}: you are registrerd as player number {player_id}
        ```

        #Player commands
        all player commands start `P{player_id}`
        example:
            `P1 list players`

        ##subcommands:

        `list players`:
            lists all the players

        `state [info]`:
            get the state of the game
            if info more verbose

        ### init state
        `maxmeld`:
            finds your longest suits
            returns f"{longest_length} in {' and '.join(longest_suits)}"

        `M {n}`:
            declare a trump lenght of {n}
            return:
                " ": all good
                "Not your turn": Not your turn
                "Invalid declaration": Invalid declaration
        `S {sute}`:
            declaration of suit
            return:
                " ": all good
                "Invalid suit"

        `split {n}`
            split the deck and start dealing
            return:
                " ": all good
                "Invalid split position, try again"

        `banka`:
            deale the cards
            return:
                " ": all good

        `say ? ? {message}`:
            brodcast a message to all players
            return:
                " ": all good

        `GU`:
            heart beat, sends updates to player
            return:
                "No new updates."
                "Player not found."
        `show`:
            get the hand of the player
            return:
                the hand


        `quit`:
            sets a boolinan to True
            return:
                "Game over."

        default:
            return:
                 "Unknown command."
        """
        #print(command)
        if command.startswith("Hallo"):
            self._check_player_timeouts()
            if self.nPlayers >= 4:
                return "full"
            self.nPlayers += 1
            name = command[14:].strip() or f"Player {self.nPlayers}"
            self.players[self.nPlayers] = Player(name, self.nPlayers)
            # Touch the defaultdict so the list exists for subsequent updates.
            self.updatesForPlayers[self.nPlayers]
            if self.nPlayers == 4:
                self.setup_game()
            self.last_reset_message = None
            return f"P{self.nPlayers}"

        elif command.startswith("P"):
            if self._check_player_timeouts():
                return self.last_reset_message or "Game reset. Please rejoin."
            player_segment, sep, rest = command.partition(" ")
            try:
                player_id = int(player_segment[1:])
            except ValueError:
                return "Unknown player."
            command = rest.strip()
            player = self.players.get(player_id)
            if player is None:
                return self.last_reset_message or "Unknown player."
            player.update_last_time()

            normalized = command.lower()

            if normalized == "bots" or normalized.startswith("bots "):
                if self.bot_manager is None:
                    return "Bot manager unavailable."
                parts = command.split()
                requested = None
                if len(parts) > 1 and parts[1].isdigit():
                    requested = int(parts[1])
                return self.bot_manager.ensure_bots(requested)

            if normalized.startswith("list players"):
                player_list = "".join(
                    f"ID {id}: {player.name}, Last Update: {player.time_since_last_update():.2f}s ago\n"
                    for id, player in self.players.items()
                )
                if self.current_turn:
                    return f"Turn: {self.current_turn}\nCurrent Players:\n{player_list}"
                else:
                    return f"Current Players:\n{player_list}"

            elif normalized.startswith("state"):
                print(self.state)
                # TODO implement
                return "Not Implemented"
            elif normalized == "maxmeld":
                return str(self.players[player_id].find_highest_trump_declaration())
            elif command.upper() == "MA":
                for i in [2, 3, 4, 1]:
                    tmp = self.players[i].find_highest_trump_declaration()
                    fart = self.handle_trump_declaration("M " + tmp[0], i)
                    if fart == "Invalid declaration":
                        self.handle_trump_declaration("M 0", i)
                if self.trump_owner:
                    suit_hint = self.players[self.trump_owner.id].find_highest_trump_declaration()[1]
                    self.process_command(f"P{self.trump_owner.id} S {suit_hint}")

            elif command.startswith("M "):  # Trump declaration starts with 'M '
                return self.handle_trump_declaration(command, player_id)
            elif command.startswith('IPython'):
                import IPython
                IPython.embed()
                exit()
            elif normalized.startswith("s "):
                parts = command.split()
                if len(parts) < 2:
                    return "Invalid suit"
                suit = parts[1][0].upper()
                if (
                    suit in self.players[player_id].find_highest_trump_declaration()[1:]
                    and self.current_turn == player_id
                ):
                    self.trump_suit = suit
                    self.broadcast_players(f"The current trump is {suit}")
                    self.table = Table(suit)
                    self.state = "first_card"
                    self.current_turn = ((self.dealer_position + 1) % 4) or 4
                    self.updatesForPlayers[self.current_turn].append("Play a card")
                    return " "
                return "Invalid suit"
            elif command.upper().startswith("P "):
                # Plays a card
                parts = command.split()
                if len(parts) < 2:
                    return "Invalid card"
                if not self.table:
                    return "No active trick."
                card = parts[1]
                if self.current_turn != player_id:
                    return "Not your turn"
                current_player = self.players[player_id]
                if self.state == "first_card":
                    tmp = self.table.play_first_card(card, current_player)
                    if tmp == "OK":
                        self.broadcast_players(
                            f"{player_id} Player {current_player.name} has played {card}"
                        )
                        self.state = "play"
                        self.current_turn = ((self.current_turn + 1) % 4) or 4
                        self.updatesForPlayers[self.current_turn].append("Your turn!")
                    return tmp
                if self.state == "play":
                    tmp = self.table.play_other_card(card, current_player)
                    if tmp == "OK":
                        self.broadcast_players(
                            f"{player_id} Player {current_player.name} has played {card}"
                        )
                        if len(self.table.cards) == 4:
                            trick_snapshot = [
                                (owner.id, str(card))
                                for owner, card in zip(self.table.cardOwners, self.table.cards)
                            ]
                            winner = self.table.clear_and_reset()
                            self.last_trick_cards = trick_snapshot
                            self.last_trick_expire = time.time() + 2.0
                            self.trick_winners.append(winner)
                            self.current_turn = winner
                            self.broadcast_players(
                                f"Player {self.players[self.current_turn].name} vann"
                            )
                            self.last_trick_winner = winner
                            self.highlight_until = time.time() + 2.5
                            if any(player.hand for player in self.players.values()):
                                self.state = "first_card"
                                self.updatesForPlayers[self.current_turn].append("Play a card")
                            else:
                                self._complete_round()
                        else:
                            self.current_turn = ((self.current_turn + 1) % 4) or 4
                            self.updatesForPlayers[self.current_turn].append("Your turn!")
                    return tmp
                return "Okkurt er galið"

            elif normalized.startswith("split"):
                # Here, the deck is split and dealt in fours
                try:
                    split_position = int(command.split()[-1])
                except ValueError:
                    split_position = -1
                return self.deal_cards(player_id, "split", split_position)
            elif normalized.startswith("banka"):
                # If 'banka', the deck remains unchanged and dealt in eights
                return self.deal_cards(player_id, "banka")
            elif normalized.startswith("say"):
                self.broadcast_players(
                    f"{self.players[player_id].name} says: {command[4:].strip()}"
                )
                return " "

            elif normalized.startswith("gu"):
                heartbeat_suffix = command[2:].strip()
                target_id = player_id
                if heartbeat_suffix:
                    if not heartbeat_suffix.isdigit():
                        return "Unknown player."
                    target_id = int(heartbeat_suffix)
                player = self.players.get(target_id)
                if player:
                    player.update_last_time()  # Update the player's last interaction time
                    updates = self.updatesForPlayers.get(target_id, [])
                    if updates:
                        response = "\n".join(updates)
                        self.updatesForPlayers[target_id].clear()
                        return response
                    return "No new updates."
                return "Player not found."
            elif normalized.startswith("show"):
                return self.players.get(player_id).show_hand()

            elif normalized.startswith("deal"):
                try:
                    num_cards = int(command.split(" ")[-1])
                except ValueError:
                    return "Invalid deal command."
                for pid, player in self.players.items():
                    player.draw(self.deck, num_cards)  # Assuming draw method can handle the deck directly
                    self.updatesForPlayers[pid].append(
                        f"{num_cards} cards dealt to {player.name}"
                    )
                return "Dealt cards to each player."

            elif normalized == "quit":
                self.game_over = True
                return "Game over."

            return "Unknown command."

    def _complete_round(self) -> None:
        if not self.table:
            return

        vit_points = self.table.sum_cards_list("Vit")
        tit_points = self.table.sum_cards_list("Tit")
        messages, match_finished = self._apply_round_scoring(vit_points, tit_points)
        for msg in messages:
            self.broadcast_players(msg)

        # Reset table state for the next round or match.
        self.table.cards.clear()
        self.table.cardOwners.clear()
        self.table.firstCard = None
        self.table.team_piles = {'Vit': [], 'Tit': []}
        self.last_trick_cards = []
        self.last_trick_expire = 0.0

        if match_finished:
            self.table = None
            self._reset_round_state()
            self.state = "end"
            self.game_over = True
            self.current_turn = 0
            return

        self.table = None
        self.dealer_position = ((self.dealer_position + 1) % 4) or 4
        self.setup_game()

    def _apply_round_scoring(self, vit_points: int, tit_points: int) -> tuple[list[str], bool]:
        messages: list[str] = [
            f"Round totals — Vit: {vit_points}, Tit: {tit_points}."
        ]

        declarer_team = self.declaration_team
        if declarer_team is None:
            messages.append("Round finished without a registered declarer. Redealing.")
            return messages, False

        defenders_team = "Tit" if declarer_team == "Vit" else "Vit"
        declarer_points = vit_points if declarer_team == "Vit" else tit_points

        if declarer_points == 60 and vit_points == 60:
            self.next_game_bonus += 2
            messages.append(
                f"The round is a 60-60 draw. Next game value increases by 2 "
                f"(carryover now {self.next_game_bonus})."
            )
            return messages, False

        clubs_trump = self.trump_suit == "C"
        single_player_sweep = (
            len(self.trick_winners) == 8
            and len(set(self.trick_winners)) == 1
            and self._team_for_player(self.trick_winners[0]) == declarer_team
        )

        winning_team = declarer_team
        base_points = 0
        reason = ""

        if single_player_sweep:
            winning_team = declarer_team
            base_points = 24 if clubs_trump else 16
            reason = "Single player from declarer's side won every trick"
        elif declarer_points == 120:
            winning_team = declarer_team
            base_points = 16 if clubs_trump else 12
            reason = "Declarer side won every trick"
        elif declarer_points >= 90:
            winning_team = declarer_team
            base_points = 8 if clubs_trump else 4
            reason = "Declarer side scored 90-120 points"
        elif declarer_points >= 61:
            winning_team = declarer_team
            base_points = 4 if clubs_trump else 2
            reason = "Declarer side scored 61-89 points"
        elif declarer_points >= 31:
            winning_team = defenders_team
            base_points = 8 if clubs_trump else 4
            reason = "Defenders held declarers to 31-59 points"
        else:
            winning_team = defenders_team
            if declarer_points == 0:
                base_points = 16
                reason = "Defenders won every trick"
            else:
                base_points = 16 if clubs_trump else 8
                reason = "Defenders held declarers under 31 points"

        bonus_applied = self.next_game_bonus
        total_award = base_points + bonus_applied
        if bonus_applied:
            messages.append(f"Including carryover bonus of {bonus_applied} points.")
        self.next_game_bonus = 0

        previous_score = self.scoreboard[winning_team]
        self.scoreboard[winning_team] = previous_score - total_award

        messages.append(
            f"{winning_team} subtracts {total_award} points ({reason})."
        )
        messages.append(self._scoreboard_snapshot())

        match_finished = any(score <= 0 for score in self.scoreboard.values())
        if match_finished:
            winners = [team for team, score in self.scoreboard.items() if score <= 0]
            for team in winners:
                opponent = "Tit" if team == "Vit" else "Vit"
                messages.append(f"{team} wins the rubber!")
                if self.scoreboard[opponent] == 24:
                    messages.append("Double victory — opponents remained on 24.")
        return messages, match_finished

    def _scoreboard_snapshot(self) -> str:
        vit = max(self.scoreboard["Vit"], 0)
        tit = max(self.scoreboard["Tit"], 0)
        return f"Scoreboard — Vit: {vit}, Tit: {tit}."
