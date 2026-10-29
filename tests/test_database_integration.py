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


async def test_one_hundred_purchases_cannot_overdraw(db):
    await db.coins.add_coins(1, coins=5500)
    results = await asyncio.gather(*(
        db.characters.purchase_cartoon_character(1, 'Show', f'Character {n}') for n in range(100)
    ))
    assert sum(results) == 5
    assert (await db.coins.get_amount_coins(1))['coins'] == 500
    assert (await db.characters.get_character(1))['cartoon_character'].startswith('Character ')


async def test_purchase_rolls_back_charge_when_character_save_fails(db):
    await db.coins.add_coins(1, coins=2000)
    await db.execute("ALTER TABLE characters ADD CONSTRAINT reject_test_identity CHECK (cartoon_character <> 'Rejected')")
    with pytest.raises(asyncpg.CheckViolationError):
        await db.characters.purchase_cartoon_character(1, 'Show', 'Rejected')
    assert (await db.coins.get_amount_coins(1))['coins'] == 2000
    assert await db.characters.get_character(1) is None


async def test_opposing_transfers_and_scores_under_load(db):
    for uid in range(1, 11):
        await db.coins.add_coins(uid, coins=1000)
    await asyncio.gather(*(
        db.coins.transfer((n % 10) + 1, ((n + 1) % 10) + 1, 1) for n in range(300)
    ))
    await asyncio.gather(*(db.plotsterDB.update_score((n % 10) + 1, 1, 1) for n in range(200)))
    balances = await db.view('SELECT coins FROM points')
    assert sum(row['coins'] for row in balances) == 10000
    assert all(row['coins'] >= 0 for row in balances)
    scores = await db.view('SELECT points, rounds FROM plotster_points')
    assert sum(row['points'] for row in scores) == 200
    assert sum(row['rounds'] for row in scores) == 200


async def test_score_and_coin_awards_remain_consistent_under_load(db):
    await asyncio.gather(*(db.award_movie_score(1, 1, 1, 'plotster') for _ in range(100)))
    score = (await db.view('SELECT points, rounds FROM plotster_points WHERE user_id=1'))[0]
    assert score['points'] == score['rounds'] == 100
    assert (await db.coins.get_amount_coins(1))['coins'] == 500


async def test_transfer_can_credit_large_existing_balances(db):
    await db.coins.add_coins(1, coins=2_000_000_000)
    await db.coins.add_coins(2, coins=2_000_000_000)
    assert await db.coins.transfer(1, 2, 2_000_000_000)
    assert (await db.coins.get_amount_coins(2))['coins'] == 4_000_000_000


async def test_existing_integer_coin_migration_keeps_balances(db):
    await db.execute('ALTER TABLE points ALTER COLUMN coins TYPE INTEGER')
    await db.coins.add_coins(1,coins=123)
    await db.execute(Path('schema.sql').read_text())
    assert (await db.coins.get_amount_coins(1))['coins']==123
    assert (await db.view("SELECT data_type FROM information_schema.columns WHERE table_schema=current_schema() AND table_name='points' AND column_name='coins'"))[0]['data_type']=='bigint'
