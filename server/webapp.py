from __future__ import annotations

from pathlib import Path
from threading import Lock
from typing import Any, Dict, List, Optional
from uuid import uuid4
import time

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .bot_manager import BotManager
from .game import Game

app = FastAPI(title="Sjavs Web Gateway")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

game = Game()
bot_manager = BotManager(game)
game.attach_bot_manager(bot_manager)

session_lock = Lock()
sessions: Dict[str, Dict[str, Any]] = {}


class JoinRequest(BaseModel):
    name: str


class JoinResponse(BaseModel):
    token: str
    player_id: int
    message: str


class CommandRequest(BaseModel):
    token: str
    command: str


class CommandResponse(BaseModel):
    message: str


class UpdatesResponse(BaseModel):
    message: str


class StateResponse(BaseModel):
    scoreboard: Dict[str, int]
    current_turn: int
    trump: Optional[str]
    phase: str
    players: List[Dict[str, Any]]
    table_cards: List[str]
    hand: List[str]
    table_slots: List[Dict[str, Any]]
    last_winner: Optional[int]
    highlight_until: float
    recent_trick: List[Dict[str, Any]]
    recent_trick_expire: float


def require_session(token: str) -> Dict[str, Any]:
    with session_lock:
        session = sessions.get(token)
        if not session:
            raise HTTPException(status_code=401, detail="Invalid or expired token.")
        return session


@app.post("/join", response_model=JoinResponse)
def join(payload: JoinRequest) -> JoinResponse:
    name = payload.name.strip() or "Guest"
    join_command = f"Hallo, Eg eri {name}"
    with session_lock:
        reply = game.process_command(join_command)
        if reply == "full":
            raise HTTPException(status_code=409, detail="Table is full.")
        if not reply.startswith("P"):
            raise HTTPException(status_code=400, detail=reply)

        player_id = int(reply[1:])
        token = uuid4().hex
        sessions[token] = {"player_id": player_id, "name": name}
        game.last_reset_message = None
    return JoinResponse(token=token, player_id=player_id, message="Joined successfully.")


@app.post("/command", response_model=CommandResponse)
def command(payload: CommandRequest) -> CommandResponse:
    session = require_session(payload.token)
    player_id = session["player_id"]
    cmd = payload.command.strip()
    if not cmd:
        raise HTTPException(status_code=400, detail="Command may not be empty.")

    with session_lock:
        reply = game.process_command(f"P{player_id} {cmd}")
    return CommandResponse(message=reply)


@app.get("/updates", response_model=UpdatesResponse)
def updates(token: str) -> UpdatesResponse:
    session = require_session(token)
    player_id = session["player_id"]

    with session_lock:
        reply = game.process_command(f"P{player_id} GU")
    return UpdatesResponse(message=reply)


@app.get("/state", response_model=StateResponse)
def state(token: str) -> StateResponse:
    session = require_session(token)
    player_id = session["player_id"]

    with session_lock:
        scoreboard = dict(game.scoreboard)
        current_turn = game.current_turn
        trump = game.trump_suit
        phase = game.state
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
        if game.table and game.table.cards:
            table_cards = [str(card) for card in game.table.cards]
            table_slots = [
                {"id": owner.id, "name": owner.name, "card": str(card)}
                for owner, card in zip(game.table.cardOwners, game.table.cards)
            ]
            recent_trick = []
        else:
            table_cards = []
            table_slots = []
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
        player = game.players.get(player_id)
        if player is None:
            raise HTTPException(status_code=410, detail=game.last_reset_message or "Session reset. Please rejoin.")
        hand = [str(card) for card in getattr(player, "hand", [])]
        last_winner = game.last_trick_winner
        highlight_until = game.highlight_until
        recent_trick_expire = game.last_trick_expire

    return StateResponse(
        scoreboard=scoreboard,
        current_turn=current_turn,
        trump=trump,
        phase=phase,
        players=players,
        table_cards=table_cards,
        hand=hand,
        table_slots=table_slots,
        last_winner=last_winner,
        highlight_until=highlight_until,
        recent_trick=recent_trick,
        recent_trick_expire=recent_trick_expire,
    )


static_dir = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/", include_in_schema=False)
def root() -> FileResponse:
    return FileResponse(static_dir / "index.html")
