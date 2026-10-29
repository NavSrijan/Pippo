"""Prepare Pippo's configured database before the bot starts."""

import asyncio
import getpass
import os
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import unquote, urlsplit

import asyncpg


PROJECT_DIR = Path(__file__).resolve().parents[1]
CONTAINER_NAME = "pippo-postgres"
VOLUME_NAME = "pippo-postgres-data"
LOCAL_HOSTS = {"", "localhost", "127.0.0.1", "::1"}
_sudo_checked = False
_sudo_authorized = False


def database_settings():
    dsn = os.environ.get("DATABASE_URL", "")
    if dsn:
        parsed = urlsplit(dsn)
        return {
            "dsn": dsn,
            "host": parsed.hostname or "localhost",
            "port": parsed.port or 5432,
            "user": unquote(parsed.username or "") or getpass.getuser(),
            "password": unquote(parsed.password or ""),
            "database": unquote(parsed.path.lstrip("/")) or "pippobot_db",
        }

    return {
        "dsn": "",
        "host": os.environ.get("DATABASE_HOST", os.environ.get("db_host", "localhost")) or "localhost",
        "port": int(os.environ.get("DATABASE_PORT", "5432")),
        "user": os.environ.get("DATABASE_USER", os.environ.get("database_username", "")) or getpass.getuser(),
        "password": os.environ.get("DATABASE_PASSWORD", os.environ.get("database_password", "")),
        "database": os.environ.get("DATABASE_NAME", "pippobot_db"),
    }


def can_connect(host, port):
    candidates = ["127.0.0.1", "::1"] if host in {"localhost", ""} else [host]
    for candidate in candidates:
        try:
            with socket.create_connection((candidate, port), timeout=1.5):
                return True
        except OSError:
            continue
    return False


def run_command(args, *, env=None, timeout=20):
    return subprocess.run(args, capture_output=True, text=True, env=env, timeout=timeout)


def authorize_local_admin():
    """Ask for sudo once when the launcher has a terminal to do so."""
    global _sudo_checked, _sudo_authorized
    if not hasattr(os, "geteuid") or os.geteuid() == 0:
        return True
    if _sudo_checked:
        return _sudo_authorized
    _sudo_checked = True
    sudo = shutil.which("sudo")
    if not sudo:
        return False
    if not sys.stdin.isatty():
        return False
    try:
        # Do not capture output: sudo should be able to show its password prompt.
        _sudo_authorized = subprocess.run([sudo, "-v"], timeout=120).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        _sudo_authorized = False
    return _sudo_authorized


def start_system_postgres():
    commands = []
    systemctl = shutil.which("systemctl")
    service = shutil.which("service")
    if systemctl:
        commands.append([systemctl, "start", "postgresql"])
    if service:
        commands.append([service, "postgresql", "start"])
    if not commands:
        return False

    prefix = []
    if hasattr(os, "geteuid") and os.geteuid() != 0:
        sudo = shutil.which("sudo")
        if not sudo or not authorize_local_admin():
            return False
        prefix = [sudo, "-n"]

    for command in commands:
        try:
            result = run_command([*prefix, *command])
            if result.returncode == 0:
                return True
        except (OSError, subprocess.TimeoutExpired):
            continue
    return False


def start_docker_postgres(settings):
    docker = shutil.which("docker")
    if not docker:
        return False, "Docker is not installed."
    if not settings["password"]:
        return False, "Set a database password in .env before using the Docker fallback."
    if settings["host"] == "::1":
        return False, "The Docker fallback requires DATABASE_HOST=localhost or 127.0.0.1."

    docker_command = [docker]
    docker_check = run_command([docker, "info"])
    if docker_check.returncode != 0 and "permission denied" in docker_check.stderr.lower():
        sudo = shutil.which("sudo")
        if not sudo or not authorize_local_admin():
            return False, "Docker is installed, but this account cannot access its daemon. Run the launcher from a terminal with sudo access, or grant your account Docker access."
        docker_command = [sudo, "-n", "--preserve-env=POSTGRES_USER,POSTGRES_PASSWORD,POSTGRES_DB", docker]

    container = run_command([*docker_command, "container", "inspect", CONTAINER_NAME])
    if container.returncode == 0:
        try:
            running = run_command([*docker_command, "inspect", "--format={{.State.Running}}", CONTAINER_NAME])
            if running.returncode != 0:
                return False, running.stderr.strip() or "Could not inspect the PostgreSQL container."
            if running.stdout.strip() != "true":
                started = run_command([*docker_command, "start", CONTAINER_NAME])
                if started.returncode != 0:
                    return False, started.stderr.strip() or "Could not start the existing PostgreSQL container."
        except (OSError, subprocess.TimeoutExpired) as error:
            return False, str(error)
        return True, ""

    docker_env = os.environ.copy()
    docker_env.update({
        "POSTGRES_USER": settings["user"],
        "POSTGRES_PASSWORD": settings["password"],
        "POSTGRES_DB": settings["database"],
    })
    command = [
        *docker_command, "run", "--detach", "--name", CONTAINER_NAME,
        "--restart", "unless-stopped",
        "--env", "POSTGRES_USER", "--env", "POSTGRES_PASSWORD", "--env", "POSTGRES_DB",
        "--publish", f"127.0.0.1:{settings['port']}:5432",
        "--volume", f"{VOLUME_NAME}:/var/lib/postgresql",
        "postgres:18",
    ]
    try:
        result = run_command(command, env=docker_env, timeout=120)
    except (OSError, subprocess.TimeoutExpired) as error:
        return False, str(error)
    if result.returncode != 0:
        return False, result.stderr.strip() or result.stdout.strip() or "Docker could not start PostgreSQL."
    return True, ""


def wait_for_server(host, port, timeout=40):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if can_connect(host, port):
            return True
        time.sleep(1)
    return False


def provision_system_database(settings):
    psql = shutil.which("psql")
    if not psql:
        return False, "psql is required to create the local database and role."
    command = [psql, "-d", "postgres", "-v", "ON_ERROR_STOP=1"]
    admin_env = os.environ.copy()
    admin_env.update({
        "PIPPO_DB_USER": settings["user"],
        "PIPPO_DB_PASSWORD": settings["password"],
        "PIPPO_DB_NAME": settings["database"],
    })
    if hasattr(os, "geteuid") and os.geteuid() != 0:
        sudo = shutil.which("sudo")
        if not sudo:
            return False, "Cannot administer the local PostgreSQL service; sudo is not installed."
        if not authorize_local_admin():
            return False, "Administrator authorization is required to prepare the local database."
        command = [sudo, "-n", "--preserve-env=PIPPO_DB_USER,PIPPO_DB_PASSWORD,PIPPO_DB_NAME", "-u", "postgres", *command]
    elif hasattr(os, "geteuid") and os.geteuid() == 0:
        runuser = shutil.which("runuser")
        if runuser:
            command = [runuser, "-u", "postgres", "--", *command]

    if settings["password"]:
        role_sql = r"""
SELECT format('CREATE ROLE %I LOGIN PASSWORD %L', :'pippo_user', :'pippo_password')
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :'pippo_user')
\gexec
SELECT format('ALTER ROLE %I LOGIN PASSWORD %L', :'pippo_user', :'pippo_password')
\gexec
"""
    else:
        role_sql = r"""
SELECT format('CREATE ROLE %I LOGIN', :'pippo_user')
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :'pippo_user')
\gexec
SELECT format('ALTER ROLE %I LOGIN', :'pippo_user')
\gexec
"""
    sql = r"""
\getenv pippo_user PIPPO_DB_USER
\getenv pippo_password PIPPO_DB_PASSWORD
\getenv pippo_database PIPPO_DB_NAME
""" + role_sql + r"""
SELECT format('CREATE DATABASE %I OWNER %I', :'pippo_database', :'pippo_user')
WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = :'pippo_database')
\gexec
SELECT format('ALTER DATABASE %I OWNER TO %I', :'pippo_database', :'pippo_user')
\gexec
"""
    try:
        result = subprocess.run(command, input=sql, capture_output=True, text=True, env=admin_env, timeout=30)
    except (OSError, subprocess.TimeoutExpired) as error:
        return False, str(error)
    if result.returncode != 0:
        return False, result.stderr.strip() or result.stdout.strip() or "Could not prepare the local database."
    return True, ""


async def apply_schema(settings):
    connection_args = {"timeout": 10}
    if settings["dsn"]:
        connection_args["dsn"] = settings["dsn"]
    else:
        connection_args.update({
            "host": settings["host"],
            "port": settings["port"],
            "user": settings["user"],
            "password": settings["password"] or None,
            "database": settings["database"],
        })
    connection = await asyncpg.connect(**connection_args)
    try:
        schema = (PROJECT_DIR / "schema.sql").read_text(encoding="utf-8")
        await connection.execute(schema)
    finally:
        await connection.close()


async def main():
    settings = database_settings()
    is_local = settings["host"] in LOCAL_HOSTS

    if is_local and not can_connect(settings["host"], settings["port"]):
        print("PostgreSQL is not running; trying to start a local service.")
        start_system_postgres()
        if not wait_for_server(settings["host"], settings["port"], timeout=20):
            print("No system PostgreSQL service became available; trying Docker.")
            started, reason = start_docker_postgres(settings)
            if not started:
                raise RuntimeError(f"Could not start PostgreSQL automatically: {reason}")
            if not wait_for_server(settings["host"], settings["port"]):
                raise RuntimeError("The PostgreSQL container started but the database port did not become ready.")

    if is_local:
        # If configured credentials cannot connect yet, create or align the local
        # role and database through the system PostgreSQL administrator.
        try:
            await apply_schema(settings)
        except asyncpg.InvalidCatalogNameError:
            prepared, reason = provision_system_database(settings)
            if not prepared:
                raise RuntimeError(f"Could not create the local database: {reason}") from None
            await apply_schema(settings)
        except asyncpg.InvalidPasswordError:
            prepared, reason = provision_system_database(settings)
            if not prepared:
                raise RuntimeError(f"Database credentials did not match .env, and the local role could not be updated: {reason}") from None
            await apply_schema(settings)
        except asyncpg.InvalidAuthorizationSpecificationError:
            prepared, reason = provision_system_database(settings)
            if not prepared:
                raise RuntimeError(f"The local database role could not be prepared: {reason}") from None
            await apply_schema(settings)
    else:
        await apply_schema(settings)

    print("Database is ready; starting Pippo.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as error:
        print(f"Database startup failed: {error}", file=sys.stderr)
        raise SystemExit(1)
