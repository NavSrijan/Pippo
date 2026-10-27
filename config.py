"""Environment configuration, retaining the original deployment variable names."""

import os


def env(name: str, legacy: str | None = None, default: str = "") -> str:
    return os.environ.get(name, os.environ.get(legacy, default) if legacy else default)


def production() -> bool:
    return env("PRODUCTION", "production", "false").lower() in {"true", "1", "yes"}


def database_options() -> dict:
    options = {
        "min_size": 1,
        "max_size": int(env("DATABASE_POOL_SIZE", default="5")),
        "command_timeout": 30,
    }
    dsn = env("DATABASE_URL")
    if dsn:
        options["dsn"] = dsn
    else:
        options.update(
            database=env("DATABASE_NAME", default="pippobot_db"),
            user=env("DATABASE_USER", "database_username") or None,
            password=env("DATABASE_PASSWORD", "database_password") or None,
            host=env("DATABASE_HOST", "db_host") or None,
            port=int(env("DATABASE_PORT", default="5432")),
        )
    return options
