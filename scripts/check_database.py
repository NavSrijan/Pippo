"""Verify Pippo can open its runtime PostgreSQL pool before Discord login."""

import asyncio
from pathlib import Path
import sys
import time
from urllib.parse import urlsplit

import asyncpg

PROJECT_DIR = Path(__file__).resolve().parents[1]
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from config import database_options


def endpoint(options):
    dsn = options.get("dsn")
    if dsn:
        parsed = urlsplit(dsn)
        return parsed.hostname or "localhost", parsed.port or 5432
    return options.get("host") or "localhost", options.get("port", 5432)


async def check_pool(options):
    pool = await asyncpg.create_pool(**options)
    await pool.close()


async def main():
    options = database_options()
    host, port = endpoint(options)
    deadline = time.monotonic() + 15
    last_error = None

    while True:
        try:
            await check_pool(options)
            print(f"PostgreSQL is accepting Pippo's configured pool at {host}:{port}.")
            return 0
        except (OSError, asyncpg.PostgresError, asyncio.TimeoutError) as error:
            last_error = error

        if time.monotonic() >= deadline:
            break
        await asyncio.sleep(1)

    print(
        f"PostgreSQL at {host}:{port} did not accept Pippo's configured connection after 15 seconds. "
        "Check that the server is running, the port is reachable, and the database credentials in .env match. "
        "No Discord login was attempted.",
        file=sys.stderr,
    )
    if isinstance(last_error, asyncpg.InvalidPasswordError):
        print("The server rejected the configured password.", file=sys.stderr)
    elif isinstance(last_error, asyncpg.InvalidCatalogNameError):
        print("The configured database does not exist.", file=sys.stderr)
    elif isinstance(last_error, OSError):
        print("The server refused or could not be reached at that host and port.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
