"""Run against an explicitly supplied disposable PostgreSQL database."""

import asyncio
import os
from pathlib import Path
from uuid import uuid4

import asyncpg
import pytest
import pytest_asyncio

from database import DB

pytestmark = pytest.mark.skipif(not os.environ.get('TEST_DATABASE_URL'), reason='TEST_DATABASE_URL is not set')


@pytest_asyncio.fixture
async def db():
    dsn = os.environ['TEST_DATABASE_URL']
    schema = 'pippo_test_' + uuid4().hex
    admin = await asyncpg.connect(dsn)
    pool = None
    try:
        await admin.execute(f'CREATE SCHEMA {schema}')
        pool = await asyncpg.create_pool(dsn, min_size=1, max_size=5,
                                        server_settings={'search_path': schema})
        async with pool.acquire() as con:
            sql = Path('schema.sql').read_text()
            await con.execute(sql)
            # The documented migration must be safe to reapply.
            await con.execute(sql)
        yield DB(pool)
    finally:
        if pool:
            await pool.close()
        await admin.execute(f'DROP SCHEMA IF EXISTS {schema} CASCADE')
        await admin.close()


async def test_concurrent_transfers_cannot_overspend(db):
    await db.coins.add_coins(1, coins=100)
    results = await asyncio.gather(*(db.coins.transfer(1, user, 60) for user in range(2, 12)))
    assert sum(results) == 1
    balances = await db.view('SELECT coins FROM points')
    assert sum(row['coins'] for row in balances) == 100
    assert all(row['coins'] >= 0 for row in balances)


async def test_concurrent_scores_preserve_every_increment(db):
    await asyncio.gather(*(db.bollywoodHangmanDB.update_score(1, 1, 1) for _ in range(20)))
    result = await db.view('SELECT points, rounds FROM bollywood_points WHERE user_id=1')
    assert dict(result[0]) == {'points': 20, 'rounds': 20}


async def test_guild_prefix_character_upserts_and_dm_analytics(db):
    await asyncio.gather(*(db.servers.prefix_add(10, '!') for _ in range(5)))
    assert await db.servers.fetch_prefix(10) == '!'
    await db.characters.insert_character(1, cartoon_character='Pippo')
    await db.characters.insert_character(1, dog_breed='Beagle')
    row = await db.characters.get_character(1)
    assert row['cartoon_character'] == 'Pippo' and row['dog_breed'] == 'Beagle'
    await db.analytics.insert_command('play', None, 1)
    rows = await db.view('SELECT server_id FROM analytics')
    assert rows[0]['server_id'] is None
