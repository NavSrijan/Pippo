#!/usr/bin/env bash
set -euo pipefail

PIPPO_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$PIPPO_DIR"
export PYTHONPATH="$PIPPO_DIR${PYTHONPATH:+:$PYTHONPATH}"

if [[ -f "$PIPPO_DIR/.env" ]]; then
    set -a
    # shellcheck disable=SC1091
    source "$PIPPO_DIR/.env"
    set +a
fi

if [[ -n "${PIPPO_PYTHON:-}" ]]; then
    BOT_PYTHON="$PIPPO_PYTHON"
else
    SYSTEM_PYTHON="$(command -v python3 || true)"
    if [[ -z "$SYSTEM_PYTHON" ]]; then
        echo "Python 3 was not found. Install Python 3.11+ or set PIPPO_PYTHON to its executable." >&2
        exit 1
    fi
    if [[ ! -x "$PIPPO_DIR/.venv/bin/python" ]]; then
        echo "Creating Pippo's virtual environment..."
        "$SYSTEM_PYTHON" -m venv "$PIPPO_DIR/.venv" || {
            echo "Could not create .venv. Install your OS Python venv package, then run ./run.sh again." >&2
            exit 1
        }
    fi
    BOT_PYTHON="$PIPPO_DIR/.venv/bin/python"
fi

if [[ ! -x "$BOT_PYTHON" ]] && ! command -v "$BOT_PYTHON" >/dev/null 2>&1; then
    echo "Python executable not found: $BOT_PYTHON" >&2
    exit 1
fi

if ! "$BOT_PYTHON" -c 'import sys; raise SystemExit(sys.version_info < (3, 11))'; then
    echo "Pippo requires Python 3.11 or newer. Set PIPPO_PYTHON to a supported interpreter." >&2
    exit 1
fi

if [[ -z "${DISCORD_TOKEN:-${tc_token:-}}" ]]; then
    echo "Set DISCORD_TOKEN in .env before starting Pippo." >&2
    exit 1
fi

echo "Checking Pippo's Python dependencies..."
if ! "$BOT_PYTHON" -m pip install -r "$PIPPO_DIR/requirements.txt"; then
    echo "Could not install Pippo's Python dependencies. Check your network and Python/pip setup, then run ./run.sh again." >&2
    exit 1
fi

echo "Preparing PostgreSQL and applying the database schema..."
"$BOT_PYTHON" "$PIPPO_DIR/scripts/prepare_database.py"
echo "Checking the exact database connection Pippo will use..."
"$BOT_PYTHON" "$PIPPO_DIR/scripts/check_database.py"
echo "Starting the Discord bot..."
exec "$BOT_PYTHON" "$PIPPO_DIR/bot.py" "$@"
