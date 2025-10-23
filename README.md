# Sjavs_server

## Overview
`Sjavs_server` hosts a TCP implementation of the Faroese four-player variant of Sjavs. The runtime code lives in the `server/` package and accepts socket clients via `python -m server.app` (or `python server/app.py` when run from the repository root).

## Running the Server
1. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```
2. Install dependencies as you add them and capture them in `requirements.txt`.
3. Start the socket server:
   ```bash
   python -m server.app
   ```

### Browser Front-End
The repository also supplies a lightweight browser client served via FastAPI. Install the optional dependencies and launch the web gateway:

```bash
pip install fastapi uvicorn
uvicorn server.webapp:app --reload --port 8000
```

Then open `http://127.0.0.1:8000` in your browser, join with a name, and interact through the UI (bots can be added via the dedicated button).

## Running Tests
Pytest ships with many globally installed plugins on some systems. If you see import errors from unrelated packages, run:
```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest
```
This repository ships a small regression suite in `tests/` that covers the server handshake and representative card-flow logic.

### Filling Empty Seats
While waiting in the lobby you can ask the server to auto-fill the remaining seats with built-in bots by typing `bots` (or `bots 3` to request a specific count) from any connected client. The server launches the bots in-process so you only need a single client window for testing.

## Local Bot Helpers
To populate three seats with random-but-legal bots so you can join as the fourth player, start the server and run:
```bash
python scripts/random_bots.py --host 127.0.0.1 --port 65432 --bots 3
```
The bots will handle declarations, suit choices, and trick play for their seats; connect with your client to take the remaining position.

## Game Rules (4-player Sjavs)
The implementation follows the tournament rules taught in Tórshavn. Below is a concise reference for future contributors.

- **Players**: Four people play in fixed partnerships (1 & 3 vs. 2 & 4) seated alternately.
- **Deck**: Use the 32-card pack (remove 2-6). Permanent highest trumps, from high to low, are: Q of Clubs (QC), Q of Spades (QS), J of Clubs (JC), J of Spades (JS), J of Hearts (JH), J of Diamonds (JD). Remaining cards rank A, 10, K, Q, J, 9, 8, 7 inside their suits. Card points total 120 (A=11, 10=10, K=4, Q=3, J=2, others=0).
- **Deal**: Dealer shuffles; right-hand neighbor may cut (dealer then deals 4-4). If the neighbor taps instead of cutting, the dealer deals 8-8. Everyone receives eight cards.
- **Trump Declarations**: The player left of the dealer speaks first, announcing the length (>=5) of their best potential trump suit or "pass" if none. Later players must pass unless they can claim a longer suit, or an equal-length club suit. If nobody can declare, the same dealer reshuffles and redeals.
- **Naming Trump**: The winning declarer chooses the trump suit. If they have multiple suits of equal length including clubs, they must select clubs.
- **Play**: Dealer's left-hand neighbor leads the first trick; winners lead subsequent tricks. Players must follow suit when possible; otherwise they may play any card. Trick winners collect the cards for their team piles.
- **Scoring**: Declarer side scores based on total trick points:
  - All tricks: 12 points (16 if clubs are trump)
  - 90-120: 4 (8 if clubs)
  - 61-89: 2 (4 if clubs)
  - 31-59: defenders score 4 (8 if clubs)
  - 0-30 or defenders winning every trick: defenders score 8 or 16 (club bonus applies).
  A 60-60 split carries no score but increases the next game's stake by two (four if defenders achieved the draw). Winning every trick as a single declarer earns 16 (24 if clubs).
- **Rubber**: Each side starts on 24 points and subtracts earned scores downward. Reaching (or passing) zero wins the rubber; a 24-0 finish counts as a double victory.

Variations for other player counts exist, but the current server only models the four-player game described above.
