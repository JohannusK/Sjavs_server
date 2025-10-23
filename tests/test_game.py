import importlib

import pytest
from typing import Optional

from server.game import Game
from server.utils import Card, Player, Table

SUIT_MAP = {
    "H": "Hearts",
    "C": "Clubs",
    "D": "Diamonds",
    "S": "Spades",
}

VALUE_MAP = {
    "A": 1,
    "K": 13,
    "Q": 12,
    "J": 11,
    "T": 10,
    "9": 9,
    "8": 8,
    "7": 7,
}


def make_card(code: str) -> Card:
    return Card(SUIT_MAP[code[1]], VALUE_MAP[code[0]])


class StubCard:
    def __init__(self, value: int) -> None:
        self.value = value


def register_four_players(game: Game) -> None:
    for name in ("Anna", "Bjorg", "Carl", "Dani"):
        game.process_command(f"Hallo, Eg eri {name}")


def test_app_module_importable():
    # The server entry point should be importable without ModuleNotFoundError.
    importlib.invalidate_caches()
    module = importlib.import_module("server.app")
    assert hasattr(module, "start_server")


def test_deal_cards_requires_deal_state():
    game = Game()
    # Directly calling deal_cards during init should return a helpful message instead of crashing.
    result = game.deal_cards(player_id=1, _type="split", split_position=12)
    assert "cannot deal cards" in result.lower()


def test_handle_trump_declaration_when_everyone_passes_restarts_round():
    game = Game()
    register_four_players(game)
    # Initial prompt should be to player 4 for split/banka.
    assert game.state == "deal"
    # Complete the deal so we can reach declaration stage.
    response = game.process_command("P4 split 16")
    assert response.strip() == ""
    assert game.state == "declaration"

    # Everyone passes on the declaration. This should trigger a redeal without throwing.
    for pid in (2, 3, 4, 1):
        reply = game.process_command(f"P{pid} M 0")
        assert reply.strip() == ""

    assert game.state == "deal"
    assert game.current_turn in game.players
    assert all(len(player.hand) == 0 for player in game.players.values())


def test_gu_command_without_id_suffix():
    game = Game()
    register_four_players(game)
    # Player check-in should not require repeating the identifier and must not crash.
    result = game.process_command("P1 GU")
    assert isinstance(result, str)


def test_table_clear_and_reset_handles_trumps():
    table = Table(trump="Hearts")
    players = [Player(f"P{idx}", id=idx) for idx in range(1, 5)]
    cards = [
        Card("Hearts", 9),   # First card defines suit
        Card("Clubs", 11),   # Trump Jack should win the trick
        Card("Hearts", 10),
        Card("Hearts", 8),
    ]
    table.cards.extend(cards)
    table.cardOwners.extend(players)
    table.firstCard = cards[0]

    winner = table.clear_and_reset()
    assert winner == players[1].id
    assert table.team_piles["Tit"]  # Winning team pile should now contain the cards
    assert table.cards == []
    assert table.cardOwners == []


def test_round_scoring_updates_scoreboard_for_declarer():
    game = Game()
    register_four_players(game)
    game.trump_owner = game.players[1]
    game.declaration_team = "Vit"
    game.trump_suit = "H"
    game.table = Table(trump="H")
    vit_cards = [
        "AH", "TH", "KH", "QH", "JH", "AC", "TC", "KC",
        "AD", "TD", "AS", "9S", "8D", "7C", "8H", "7S",
    ]
    tit_cards = [
        "TS", "KD", "KS", "QC", "QD", "QS", "JC", "JD",
        "JS", "9D", "9C", "9H", "8S", "7H", "8C", "7D",
    ]
    game.table.team_piles["Vit"] = [make_card(code) for code in vit_cards]
    game.table.team_piles["Tit"] = [make_card(code) for code in tit_cards]
    game.trick_winners = [1, 3, 1, 3, 1, 3, 1, 3]

    game._complete_round()

    assert game.scoreboard["Vit"] == 22
    assert game.scoreboard["Tit"] == 24
    assert game.next_game_bonus == 0
    assert game.state == "deal"


def test_round_scoring_draw_increases_bonus():
    game = Game()
    register_four_players(game)
    game.trump_owner = game.players[1]
    game.declaration_team = "Vit"
    game.trump_suit = "S"
    game.table = Table(trump="S")
    vit_values = [1, 1, 1, 10, 10, 13, 12] + [7] * 9
    tit_values = [1, 1, 10, 10, 13, 12, 11, 12, 13, 11] + [7] * 6
    game.table.team_piles["Vit"] = [StubCard(value) for value in vit_values]
    game.table.team_piles["Tit"] = [StubCard(value) for value in tit_values]
    game.trick_winners = [1, 2, 1, 2, 1, 2, 1, 2]

    game._complete_round()

    assert game.scoreboard["Vit"] == 24
    assert game.scoreboard["Tit"] == 24
    assert game.next_game_bonus == 2
    assert game.state == "deal"


def test_round_scoring_defenders_win_and_finish_match():
    game = Game()
    register_four_players(game)
    game.trump_owner = game.players[2]
    game.declaration_team = "Tit"
    game.trump_suit = "S"
    game.scoreboard["Vit"] = 3
    game.table = Table(trump="S")
    declarer_values = [10, 10, 11, 11, 11, 11] + [7] * 10
    defenders_values = [1, 1, 1, 10, 10, 13, 12, 13, 12, 11] + [7] * 6
    game.table.team_piles["Tit"] = [StubCard(value) for value in declarer_values]
    game.table.team_piles["Vit"] = [StubCard(value) for value in defenders_values]
    game.trick_winners = [1, 2, 3, 4, 1, 2, 3, 4]

    game._complete_round()

    assert game.scoreboard["Vit"] <= 0
    assert game.scoreboard["Tit"] == 24
    assert game.state == "end"
    assert game.game_over is True
    assert game.current_turn == 0


def test_bots_command_forwards_to_manager():
    game = Game()
    register_four_players(game)

    class DummyManager:
        def __init__(self) -> None:
            self.calls: list[Optional[int]] = []

        def ensure_bots(self, requested: Optional[int] = None) -> str:
            self.calls.append(requested)
            return "Bots added"

    dummy = DummyManager()
    game.attach_bot_manager(dummy)  # type: ignore[arg-type]

    result = game.process_command("P1 bots")
    assert result == "Bots added"
    assert dummy.calls == [None]

    result = game.process_command("P1 bots 2")
    assert result == "Bots added"
    assert dummy.calls == [None, 2]
