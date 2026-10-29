# Pippo

Pippo is a Discord bot for movie trivia, party games, and social commands, with an Indian touch.

[Invite Pippo](https://top.gg/bot/1066895131485163570) or [buy me a coffee](https://buymeacoffee.com/thewhistler) to support development.

## Requirements

- Python **3.11+**. Python **3.15** is the current target; CI covers 3.11, 3.14, and 3.15.
- PostgreSQL (integration tests use PostgreSQL 18).
- A Discord application with a bot token. Enable **Message Content** and **Server Members** privileged intents in the developer portal. Invite with the `bot` and `applications.commands` scopes, plus permissions to send messages, embed links, attach files, read history, and add reactions.

Run all commands below from the repository root so the bot can find its bundled data, fonts, and images.

## Installation

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
cp .env.example .env
```

Fill in `.env`. The `./run.sh` launcher loads it automatically. To run `python bot.py` directly, load it into your shell first:

```bash
set -a
source .env
set +a
```

`DISCORD_TOKEN` and database credentials are required. Use `DATABASE_URL`, or set `DATABASE_USER`, `DATABASE_PASSWORD`, `DATABASE_HOST`, `DATABASE_PORT`, and `DATABASE_NAME` separately. The database name defaults to `pippobot_db`. The pool defaults to five connections and can be adjusted with `DATABASE_POOL_SIZE`.

Existing deployments can keep using `tc_token`, `database_username`, `database_password`, `db_host`, `production`, and `topgg`. The uppercase equivalents take precedence. Set `OPENROUTER_API_KEY` for Clash judging; `openrouter_api_key` is also accepted for compatibility.

Start the bot with:

```bash
./run.sh
```

The launcher creates `.venv` if needed, installs the runtime dependencies, prepares the schema, starts a local PostgreSQL service when possible, then verifies the exact database pool settings before it logs in to Discord. If the database is unreachable, it stops with a diagnostic instead of failing later in bot startup. If system service or Docker access needs administrator rights, run it in a terminal so it can request your sudo password. The Docker fallback needs Docker running and a database password in `.env`. Remote database URLs must point to an existing database whose user can apply `schema.sql`. Set `PIPPO_PYTHON` to choose a different Python executable.

`schema.sql` creates missing tables, preserves existing records, and permits analytics for direct messages. Apply it to existing deployments too. Startup now stops on database or cog-loading failures instead of publishing a partially working command tree. Shutdown closes the database pool and optional Top.gg client.

## Playing

Run `/play` to choose a category, game, and solo or multiplayer mode. `/help` lists commands and their options. Prefix commands use `.` by default; server managers can change it with `/change_prefix`.

Movie-game flags use `name: value` syntax for prefix commands:

```text
.bollywood
.poster mode: hollywood starting_year: 2010 ending_year: 2023
```

Every game opens the same start screen: choose **Play solo** or **Play with friends**. `/play` uses that screen too. There are no separate solo flags or positional booleans to remember. Friend challenges in Tic Tac Toe and Memory then ask for an opponent. Tic Tac Toe keeps its Easy, Normal, and Hard difficulty options.

The bundled movie dataset ends in **2023**. The engine reads whatever year CSVs exist in `data/bollywood/` and `data/hollywood/`, skips missing years, and accepts additional files named `YYYY_data.csv` with the existing columns. Updating software does not refresh or license movie data automatically.

## Optional integrations and tools

- **Clash AI judge:** set `OPENROUTER_API_KEY`. `OPENROUTER_MODEL` defaults to `openai/gpt-oss-120b` and can be changed without editing code. Judging uses a strict JSON schema and validates the winner ID. By default, requests require providers that deny data collection, support zero data retention, and support the required structured output. If a selected model has no eligible route, Clash explicitly identifies the random fallback. Set `OPENROUTER_PRIVACY_MODE=standard` only if you accept the selected provider’s data policy; this retains structured-output routing but removes the data-collection and zero-retention restrictions. `OPENROUTER_SITE_URL` and `OPENROUTER_APP_NAME` identify the app in OpenRouter.
- **Top.gg:** set `PRODUCTION=true` and `TOPGG_TOKEN` to enable server-count posting.
- **Map importer:** set `GOOGLE_API_KEY` and `GOOGLE_SHEET_ID` before running the Sheets helper. Restrict the key to the required API. A previously embedded key was removed; rotate it in its owning Google Cloud project if still active.
- **Room editors:** `python playground/json_gui.py` or `python playground/gui_json.py`. These optional desktop tools need the operating system's Tk package (often `python3-tk`). Importing them does not open a window.

`playground/`, `colors/`, and `databaseOLD.py` contain standalone experiments or legacy utilities, not production cogs. Some require their own optional services or packages. The supported bot entry point is `bot.py`.

## Development and verification

```bash
python -m pip install -r requirements.lock
python -m pip check
python -m pytest -q
```

`requirements.txt` pins direct runtime dependencies; `requirements-dev.txt` adds tests. `requirements.lock` records the complete cross-platform development dependency resolution as of **2026-10-27**. Regenerate it after changing dependencies:

```bash
uv pip compile requirements-dev.txt --universal --python-version 3.11 --output-file requirements.lock
```

PostgreSQL integration tests are opt-in locally. They create a unique schema in the database you supply, test migrations and concurrent updates, and remove only that schema afterward:

```bash
TEST_DATABASE_URL=postgresql://localhost/pippo_test python -m pytest -q
```

CI runs both unit and PostgreSQL integration tests. Offline tests cover game launching, concurrency guards, shared solo/friends mode screens, Bingo view replacement, Clash submissions and response parsing, room-editor round trips, and shutdown. Live Discord, OpenRouter, Google Sheets, and Top.gg calls require a separate smoke test with your credentials.

Contributions are welcome through issues and pull requests.

### Concurrent command use

See [LOAD_PROGRESS.md](LOAD_PROGRESS.md) for the command audit and measured local load results. Button games have independent boards. Chat-guessing games reserve their channel until they finish; use another channel or a Discord thread for an independent simultaneous chat game. Finished/failed/cancelled commands release their reservations.

Rendering uses four workers. Outgoing API connections are pooled and bounded; `DATABASE_POOL_SIZE` controls PostgreSQL connections (default five). Busy menus and per-user command bursts receive an explanation instead of building unlimited work. Start every game normally and choose **Play solo** or **Play with friends**.

Run `.venv/bin/python scripts/load_check.py --jobs 80` for a local rendering/event-loop check, and `.venv/bin/python scripts/render_catalog.py` after changing `website/commands.json`.
