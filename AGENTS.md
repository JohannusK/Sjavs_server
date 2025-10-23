# Repository Guidelines

## Project Structure & Module Organization
Sjavs_server’s runtime code lives in `server/`, with `app.py` providing the TCP entry point and `game.py` plus `utils.py` encapsulating game state, rules, and helper classes. Runtime assets and mutable data are stored in `config/` (SQLite database, Hypercorn config, cache/index directories); avoid hard-coding secrets and keep code changes within `server/`. New gameplay features should land in modular files under `server/`, and shared exports should be wired through `server/__init__.py` for clean imports.

## Build, Test, and Development Commands
Create a virtual environment before hacking: `python -m venv .venv && source .venv/bin/activate`. Install dependencies as you add them with `pip install <package>` and capture them in `requirements.txt`. Run the server locally with `python server/app.py` (or `python -m server.app`) to accept socket clients, and use `python -m pdb server/app.py` when you need an interactive debugger.

## Coding Style & Naming Conventions
Follow PEP 8 with four-space indentation, snake_case for functions/modules, and PascalCase for classes such as `Game` or `Table`. Prefer explicit typing (the current code uses Python 3.10+ union syntax) and keep functions short with descriptive docstrings. Use f-strings for formatted output and log through print statements only when structured logging is unnecessary.

## Testing Guidelines
Adopt `pytest` for new tests; place suites under `tests/` mirroring the `server/` layout (for example `tests/test_game.py` covering `Game.process_command`). Target high-coverage assertions around state transitions, card-handling edge cases, and multiplayer messaging. Run `pytest` locally before opening a PR, and add fixtures for socket interactions rather than relying on live network sockets.

## Commit & Pull Request Guidelines
Match the existing concise, imperative commit style (`play next round`, `reset table`); scope each commit to a coherent change. Pull requests should summarize gameplay impacts, note any config or schema adjustments, and link related issues. Include manual test notes or reproduction steps and, when relevant, attach logs captured from `config/logs/` so reviewers can confirm behavior quickly.
