from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from threading import Lock, Thread
from typing import Any, Dict, List, Optional
from uuid import uuid4
import time

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .app import HOST as TCP_HOST, PORT as TCP_PORT, start_server
from .bot_manager import BotManager
from .game import Game

app = FastAPI(title="Sjavs Web Gateway")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@dataclass
class LobbyRecord:
    lobby_id: str
    name: str
    game: Game
    bot_manager: BotManager
    created_at: float


legacy_tcp_game = Game()
legacy_tcp_bot_manager = BotManager(legacy_tcp_game)
legacy_tcp_game.attach_bot_manager(legacy_tcp_bot_manager)
tcp_thread: Optional[Thread] = None

session_lock = Lock()
sessions: Dict[str, Dict[str, Any]] = {}
lobbies: Dict[str, LobbyRecord] = {}
EMPTY_LOBBY_TTL_SECONDS = 120


class CreateLobbyRequest(BaseModel):
    name: Optional[str] = None


class LeaveRequest(BaseModel):
    token: str


class LobbyResponse(BaseModel):
    lobby_id: str
    name: str
    phase: str
    player_count: int
    max_players: int
    can_join: bool
    can_start: bool


class LobbyListResponse(BaseModel):
    lobbies: List[LobbyResponse]


class JoinRequest(BaseModel):
    name: str
    lobby_id: str


class JoinResponse(BaseModel):
    token: str
    player_id: int
    lobby_id: str
    lobby_name: str
    message: str


class CommandRequest(BaseModel):
    token: str
    command: str


class CommandResponse(BaseModel):
    message: str


class UpdatesResponse(BaseModel):
    message: str


class StateResponse(BaseModel):
    player_id: int
    lobby_id: str
    lobby_name: str
    scoreboard: Dict[str, int]
    round_history: List[Dict[str, int]]
    last_round_winner_team: Optional[str]
    last_round_result_key: int
    last_round_result_kind: Optional[str]
    trick_count: int
    round_score: Dict[str, int]
    current_turn: int
    trump: Optional[str]
    phase: str
    host_id: int
    max_players: int
    can_start: bool
    players: List[Dict[str, Any]]
    table_cards: List[str]
    hand: List[str]
    playable_cards: List[str]
    table_slots: List[Dict[str, Any]]
    last_winner: Optional[int]
    last_trick_winning_card: Optional[str]
    highlight_until: float
    recent_trick: List[Dict[str, Any]]
    recent_trick_expire: float


def make_lobby_name(index: int) -> str:
    return f"Table {index}"


def create_lobby_record(name: Optional[str] = None) -> LobbyRecord:
    lobby_index = len(lobbies) + 1
    lobby_id = uuid4().hex[:8]
    lobby_name = (name or "").strip() or make_lobby_name(lobby_index)
    game = Game()
    bot_manager = BotManager(game)
    game.attach_bot_manager(bot_manager)
    return LobbyRecord(
        lobby_id=lobby_id,
        name=lobby_name,
        game=game,
        bot_manager=bot_manager,
        created_at=time.time(),
    )


def get_lobby_or_404(lobby_id: str) -> LobbyRecord:
    lobby = lobbies.get(lobby_id)
    if lobby is None:
        raise HTTPException(status_code=404, detail="Lobby not found.")
    return lobby


def cleanup_empty_lobbies(now: Optional[float] = None) -> None:
    current_time = now if now is not None else time.time()
    expired_lobby_ids = [
        lobby_id
        for lobby_id, lobby in lobbies.items()
        if not lobby.game.players and current_time - lobby.created_at >= EMPTY_LOBBY_TTL_SECONDS
    ]
    if not expired_lobby_ids:
        return

    expired_set = set(expired_lobby_ids)
    for lobby_id in expired_lobby_ids:
        lobby = lobbies.pop(lobby_id, None)
        if lobby is not None:
            lobby.bot_manager.stop_all()

    for token, session in list(sessions.items()):
        if session["lobby_id"] in expired_set:
            del sessions[token]


def require_session(token: str) -> tuple[Dict[str, Any], LobbyRecord]:
    with session_lock:
        cleanup_empty_lobbies()
        session = sessions.get(token)
        if not session:
            raise HTTPException(status_code=401, detail="Invalid or expired token.")
        lobby = lobbies.get(session["lobby_id"])
        if lobby is None:
            raise HTTPException(status_code=410, detail="Lobby no longer exists.")
        return session, lobby


def lobby_summary(lobby: LobbyRecord) -> LobbyResponse:
    game = lobby.game
    player_count = len(game.players)
    phase = game.state
    can_join = phase in {"init", "lobby"} and player_count < 4
    can_start = phase == "lobby" and player_count == 4
    return LobbyResponse(
        lobby_id=lobby.lobby_id,
        name=lobby.name,
        phase=phase,
        player_count=player_count,
        max_players=4,
        can_join=can_join,
        can_start=can_start,
    )


def playable_cards_for_player(game: Game, player_id: int) -> List[str]:
    player = game.players.get(player_id)
    if player is None or game.current_turn != player_id:
        return []
    if game.state == "first_card":
        return [str(card) for card in player.hand]
    if game.state != "play" or not game.table or not game.table.firstCard:
        return []

    must_follow = any(
        card.is_suit(game.table.firstCard, game.table.trump)
        for card in player.hand
    )
    if not must_follow:
        return [str(card) for card in player.hand]
    return [
        str(card)
        for card in player.hand
        if card.is_suit(game.table.firstCard, game.table.trump)
    ]


@app.get("/lobbies", response_model=LobbyListResponse)
def list_lobbies() -> LobbyListResponse:
    with session_lock:
        cleanup_empty_lobbies()
        items = sorted(lobbies.values(), key=lambda lobby: lobby.created_at)
        return LobbyListResponse(lobbies=[lobby_summary(lobby) for lobby in items])


@app.post("/lobbies", response_model=LobbyResponse)
def create_lobby(payload: CreateLobbyRequest) -> LobbyResponse:
    with session_lock:
        cleanup_empty_lobbies()
        lobby = create_lobby_record(payload.name)
        lobbies[lobby.lobby_id] = lobby
        return lobby_summary(lobby)


@app.post("/join", response_model=JoinResponse)
def join(payload: JoinRequest) -> JoinResponse:
    name = payload.name.strip() or "Guest"
    with session_lock:
        cleanup_empty_lobbies()
        lobby = get_lobby_or_404(payload.lobby_id)
        game = lobby.game
        if game.state not in {"init", "lobby"}:
            raise HTTPException(status_code=409, detail="Game already in progress.")
        join_command = f"Hallo, Eg eri {name}"
        reply = game.process_command(join_command)
        if reply == "full":
            raise HTTPException(status_code=409, detail="Table is full.")
        if not reply.startswith("P"):
            raise HTTPException(status_code=400, detail=reply)

        player_id = int(reply[1:])
        token = uuid4().hex
        sessions[token] = {
            "player_id": player_id,
            "name": name,
            "lobby_id": lobby.lobby_id,
        }
        game.last_reset_message = None
    return JoinResponse(
        token=token,
        player_id=player_id,
        lobby_id=lobby.lobby_id,
        lobby_name=lobby.name,
        message="Joined successfully.",
    )


@app.post("/command", response_model=CommandResponse)
def command(payload: CommandRequest) -> CommandResponse:
    session, lobby = require_session(payload.token)
    player_id = session["player_id"]
    cmd = payload.command.strip()
    if not cmd:
        raise HTTPException(status_code=400, detail="Command may not be empty.")

    with session_lock:
        reply = lobby.game.process_command(f"P{player_id} {cmd}")
    return CommandResponse(message=reply)


@app.post("/leave", response_model=CommandResponse)
def leave(payload: LeaveRequest) -> CommandResponse:
    with session_lock:
        session, lobby = require_session(payload.token)
        player_id = session["player_id"]
        game = lobby.game
        if game.state not in {"init", "lobby", "end"}:
            raise HTTPException(status_code=409, detail="You can only leave from the waiting room or after the game ends.")

        try:
            seat_map = game.remove_player(player_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        del sessions[payload.token]

        for token, other_session in list(sessions.items()):
            if other_session["lobby_id"] != lobby.lobby_id:
                continue
            old_id = other_session["player_id"]
            if old_id in seat_map:
                other_session["player_id"] = seat_map[old_id]

        if not game.players:
            lobby.bot_manager.stop_all()
            del lobbies[lobby.lobby_id]

    return CommandResponse(message="Left room.")


@app.get("/updates", response_model=UpdatesResponse)
def updates(token: str) -> UpdatesResponse:
    session, lobby = require_session(token)
    player_id = session["player_id"]

    with session_lock:
        reply = lobby.game.process_command(f"P{player_id} GU")
    return UpdatesResponse(message=reply)


@app.get("/state", response_model=StateResponse)
def state(token: str) -> StateResponse:
    session, lobby = require_session(token)
    player_id = session["player_id"]
    game = lobby.game

    with session_lock:
        scoreboard = dict(game.scoreboard)
        round_history = list(game.round_history)
        last_round_winner_team = game.last_round_winner_team
        last_round_result_key = game.last_round_result_key
        last_round_result_kind = game.last_round_result_kind
        trick_count = len(game.trick_winners)
        round_score = {"Vit": 0, "Tit": 0}
        if game.table:
            round_score = {
                "Vit": game.table.sum_cards_list("Vit"),
                "Tit": game.table.sum_cards_list("Tit"),
            }
        current_turn = game.current_turn
        trump = game.trump_suit
        phase = game.state
        host_id = 1
        max_players = 4
        can_start = phase == "lobby" and len(game.players) == max_players
        players = []
        for pid, player in sorted(game.players.items()):
            ping = player.time_since_last_update()
            players.append(
                {
                    "id": pid,
                    "name": player.name,
                    "ping": ping,
                    "ok": ping <= 0.7,
                }
            )
        now = time.time()
        if game.last_trick_cards and now < game.last_trick_expire:
            recent_trick = [
                {"id": pid, "card": card}
                for pid, card in game.last_trick_cards
            ]
        else:
            recent_trick = []
            if now >= game.last_trick_expire:
                game.last_trick_cards = []
                game.last_trick_expire = 0.0

        if game.table and game.table.cards:
            table_cards = [str(card) for card in game.table.cards]
            table_slots = [
                {"id": owner.id, "name": owner.name, "card": str(card)}
                for owner, card in zip(game.table.cardOwners, game.table.cards)
            ]
        else:
            table_cards = []
            table_slots = []
        player = game.players.get(player_id)
        if player is None:
            raise HTTPException(
                status_code=410,
                detail=game.last_reset_message or "Session reset. Please rejoin.",
            )
        hand = [str(card) for card in getattr(player, "hand", [])]
        playable_cards = playable_cards_for_player(game, player_id)
        last_winner = game.last_trick_winner
        last_trick_winning_card = (
            str(game.table.last_winning_card)
            if game.table and game.table.last_winning_card
            else None
        )
        highlight_until = game.highlight_until
        recent_trick_expire = game.last_trick_expire

    return StateResponse(
        player_id=player_id,
        lobby_id=lobby.lobby_id,
        lobby_name=lobby.name,
        scoreboard=scoreboard,
        round_history=round_history,
        last_round_winner_team=last_round_winner_team,
        last_round_result_key=last_round_result_key,
        last_round_result_kind=last_round_result_kind,
        trick_count=trick_count,
        round_score=round_score,
        current_turn=current_turn,
        trump=trump,
        phase=phase,
        host_id=host_id,
        max_players=max_players,
        can_start=can_start,
        players=players,
        table_cards=table_cards,
        hand=hand,
        playable_cards=playable_cards,
        table_slots=table_slots,
        last_winner=last_winner,
        last_trick_winning_card=last_trick_winning_card,
        highlight_until=highlight_until,
        recent_trick=recent_trick,
        recent_trick_expire=recent_trick_expire,
    )


static_dir = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/", include_in_schema=False)
def root() -> FileResponse:
    return FileResponse(static_dir / "index.html")


@app.on_event("startup")
def launch_tcp_server() -> None:
    global tcp_thread
    if tcp_thread and tcp_thread.is_alive():
        return

    def runner() -> None:
        try:
            start_server(
                host=TCP_HOST,
                port=TCP_PORT,
                game_instance=legacy_tcp_game,
                bot_manager=legacy_tcp_bot_manager,
            )
        except OSError as exc:  # pragma: no cover
            print(f"TCP server failed to start: {exc}")

    tcp_thread = Thread(target=runner, daemon=True)
    tcp_thread.start()
