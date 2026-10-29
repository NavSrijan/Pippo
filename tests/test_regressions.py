"""Behavioral coverage for review findings and the runtime upgrade."""

import asyncio
import datetime
import importlib
import json
from types import SimpleNamespace as NS
from unittest.mock import AsyncMock, MagicMock, mock_open, patch

import discord
import pytest
from discord.ext import commands
from discord.ext.commands.view import StringView

from cogs.bollywood import BollywoodFlags, Games
from cogs.play import PlayMenuView
from config import database_options
from database import Coins
from utils.clash import judge_clash
from views import BingoView, HelpView


@pytest.mark.asyncio
async def test_replacing_bingo_board_cancels_old_timeout():
    player = NS(number_list=[[str(i * 5 + j + 1) for j in range(5)] for i in range(5)],
                cut=[], global_cut=[], msg=NS(edit=AsyncMock()))
    old = BingoView(NS(), player)
    current = BingoView(NS(), player)
    assert old.is_finished()
    # An already scheduled old callback must also be harmless.
    await old.on_timeout()
    player.msg.edit.assert_not_awaited()
    await current.on_timeout()
    assert player.msg.edit.call_args.kwargs['view'] is current
    assert all(item.disabled for item in current.children)
    current.stop()


@pytest.mark.asyncio
async def test_help_documents_one_solo_start_screen():
    bot = commands.Bot(command_prefix='.', help_command=None, intents=discord.Intents.none())
    await bot.add_cog(Games(bot))
    embed = HelpView(bot).generate_embed('games')
    assert 'Play solo' in '\n'.join(field.value for field in embed.fields)
    assert 'solo' not in BollywoodFlags.get_flags()
    await bot.close()


async def launcher_fixture():
    bot = commands.Bot(command_prefix='.', intents=discord.Intents.none())
    await bot._async_setup_hook()
    entered, release = asyncio.Event(), asyncio.Event()
    received = []

    @commands.max_concurrency(1, per=commands.BucketType.channel, wait=False)
    @commands.hybrid_command(name='bollywood')
    async def game(ctx, *, flags: BollywoodFlags):
        received.append(ctx._pippo_play_mode)
        entered.set()
        await release.wait()

    bot.add_command(game)
    message = NS(_state=bot._connection, author=NS(id=1), channel=NS(id=10),
                 guild=None, attachments=[], created_at=discord.utils.utcnow(), edited_at=None,
                 content='.play', id=123)
    ctx = commands.Context(message=message, bot=bot, prefix='.', view=StringView(''))
    ctx.send = AsyncMock()
    menu = PlayMenuView(bot, ctx)
    menu.selected_game = 'bollywood'
    game.dispatch_error = AsyncMock()
    return bot, menu, game, entered, release, received


@pytest.mark.asyncio
async def test_launcher_enforces_concurrency_and_releases_on_completion():
    bot, menu, game, entered, release, received = await launcher_fixture()
    task = asyncio.create_task(menu.launch(solo=True))
    await asyncio.wait_for(entered.wait(), 1)
    await menu.launch(solo=False)
    assert received == [True]
    assert isinstance(game.dispatch_error.call_args.args[1], commands.MaxConcurrencyReached)
    release.set()
    await task
    await menu.launch(solo=False)
    assert received == [True, False]
    menu.stop()
    await bot.close()


@pytest.mark.asyncio
async def test_launcher_runs_command_checks():
    bot, menu, game, _, _, received = await launcher_fixture()
    game.add_check(lambda ctx: False)
    await menu.launch(solo=True)
    assert received == []
    assert isinstance(game.dispatch_error.call_args.args[1], commands.CheckFailure)
    menu.stop()
    await bot.close()


@pytest.mark.asyncio
async def test_clash_bot_duel_uses_requesters_creation():
    first = NS(id=1, display_name='First', mention='<@1>')
    second = NS(id=2, display_name='Second', mention='<@2>')
    pippo = NS(id=3, display_name='Pippo', mention='<@3>')
    users = {user.id: user for user in (first, second, pippo)}
    bot = NS(user=pippo, get_user=users.get)
    ctx = NS(author=second, guild=NS(get_member=users.get), _pippo_play_mode=True, _pippo_options={},
             send=AsyncMock(return_value=NS(edit=AsyncMock())))
    games_type = importlib.import_module('cogs.bollywood').Games
    with patch('cogs.bollywood.judge_clash', AsyncMock(return_value=(second, 'A lucky win'))) as judge:
        task = asyncio.create_task(games_type.ai_clash.callback(games_type(bot), ctx))
        async with asyncio.timeout(3):
            while ctx.send.call_args is None:
                await asyncio.sleep(0.001)
        view = ctx.send.call_args.kwargs['view']
        for user, button, creation in ((second, view.submit_button, 'Second creation'),):
            interaction = NS(user=user, client=bot, response=NS(send_modal=AsyncMock(), send_message=AsyncMock(), defer=AsyncMock()), followup=NS(send=AsyncMock()))
            await button.callback(interaction)
            modal = interaction.response.send_modal.call_args.args[0]
            modal.creation._value = creation
            await modal.on_submit(interaction)
        await asyncio.wait_for(task, 5)
        assert judge.call_args.args[:2] == (second, 'Second creation')
        assert judge.call_args.args[2] is pippo


class Widget:
    def __init__(self, value=''):
        self.value = value

    def get(self, *_):
        return self.value

    def delete(self, *_):
        self.value = ''

    def insert(self, _, value):
        self.value = str(value)

    def config(self, **_):
        pass


def editor_fixture(module, monkeypatch):
    monkeypatch.setattr(module, 'tk', NS(END='end'))
    monkeypatch.setattr(module, 'messagebox', MagicMock())
    node = {'id': 1, 'name': 'Room', 'description': 'Room description', 'connections': {
        direction: {'id': 0, 'description': f'Passage {direction}'} for direction in 'NESW'
    }}
    monkeypatch.setattr(module, 'objects', {'1': node}, raising=False)
    monkeypatch.setattr(module, 'file_path', 'unused.json', raising=False)
    for name in ['id_entry', 'name_entry', 'desc_entry', 'fetch_id_entry'] + [
        f'{direction}_{part}' for direction in ('north', 'east', 'south', 'west')
        for part in ('id_entry', 'desc_entry', 'label')
    ]:
        monkeypatch.setattr(module, name, Widget(), raising=False)
    module.fetch_id_entry.value = '1'
    monkeypatch.setattr(module.messagebox, 'showinfo', MagicMock())
    module.fetch_json()


@pytest.mark.parametrize('name', ['playground.json_gui', 'playground.gui_json'])
def test_room_edit_round_trip_preserves_keys_and_descriptions(name, monkeypatch):
    module = importlib.import_module(name)
    editor_fixture(module, monkeypatch)
    module.name_entry.value = 'Renamed'
    file = mock_open()
    with patch('builtins.open', file):
        module.save_json()
    assert list(module.objects) == ['1']
    module.fetch_json()
    assert module.name_entry.value == 'Renamed'
    assert all(module.objects['1']['connections'][d]['description'] == f'Passage {d}' for d in 'NESW')
    serialized = ''.join(call.args[0] for call in file().write.call_args_list)
    assert json.loads(serialized) == module.objects


def test_new_room_can_be_fetched_without_restarting_editor(monkeypatch):
    module = importlib.import_module('playground.json_gui')
    editor_fixture(module, monkeypatch)
    module.id_entry.value = '2'
    module.name_entry.value = 'New room'
    with patch('builtins.open', mock_open()):
        module.save_json()
    module.fetch_id_entry.value = '2'
    module.fetch_json()
    assert module.name_entry.value == 'New room'


@pytest.mark.asyncio
async def test_openrouter_structured_response_and_configurable_model(monkeypatch):
    monkeypatch.setenv('OPENROUTER_API_KEY', 'test-key')
    monkeypatch.setenv('OPENROUTER_MODEL', 'configured-model')
    monkeypatch.delenv('OPENROUTER_PRIVACY_MODE', raising=False)
    body = json.dumps({'choices': [{'message': {'content': json.dumps({'winner': 2, 'reason': 'Clever trick'})}}]}).encode()
    async def chunks(size):
        yield body
    response = NS(status=200, content_length=len(body), content=NS(iter_chunked=chunks))
    session = MagicMock()
    session.post.return_value.__aenter__ = AsyncMock(return_value=response)
    with patch('utils.clash.aiohttp.ClientSession') as client:
        client.return_value.__aenter__ = AsyncMock(return_value=session)
        first, second = NS(display_name='First'), NS(display_name='Second')
        winner, reason = await judge_clash(first, 'One', second, 'Two')
    assert winner is second and reason == 'Clever trick'
    assert session.post.call_args.args[0] == 'https://openrouter.ai/api/v1/chat/completions'
    assert session.post.call_args.kwargs['json']['model'] == 'configured-model'
    assert session.post.call_args.kwargs['json']['response_format']['json_schema']['strict'] is True
    assert session.post.call_args.kwargs['json']['provider'] == {
        'data_collection': 'deny', 'zdr': True, 'require_parameters': True,
    }
    assert session.post.call_args.kwargs['headers']['Authorization'] == 'Bearer test-key'


@pytest.mark.asyncio
async def test_openrouter_missing_key_uses_labelled_offline_fallback(monkeypatch):
    monkeypatch.delenv('OPENROUTER_API_KEY', raising=False)
    monkeypatch.delenv('openrouter_api_key', raising=False)
    first, second = NS(display_name='First'), NS(display_name='Second')
    with patch('utils.clash.aiohttp.ClientSession') as client:
        winner, reason = await judge_clash(first, 'One', second, 'Two')
    client.assert_not_called()
    assert winner in (first, second)
    assert 'Random fallback' in reason


@pytest.mark.parametrize('debited,expected', [(1, True), (None, False)])
@pytest.mark.asyncio
async def test_coin_transfer_checks_balance_inside_transaction(debited, expected):
    pool, con = MagicMock(), AsyncMock()
    pool.acquire.return_value.__aenter__.return_value = con
    transaction = MagicMock()
    con.transaction = MagicMock(return_value=transaction)
    con.fetchval.return_value = debited
    coins = Coins(pool)
    assert await coins.transfer(1, 2, 100) is expected
    transaction.__aenter__.assert_awaited_once()
    assert 'coins >= $1' in con.fetchval.call_args.args[0]
    credits = [call for call in con.execute.call_args_list if 'coins = coins +' in call.args[0]]
    assert len(credits) == int(expected)
    transaction.__aexit__.assert_awaited_once()


def test_database_url_overrides_legacy_config(monkeypatch):
    monkeypatch.setenv('DATABASE_URL', 'postgresql://localhost/pippo_test')
    monkeypatch.setenv('db_host', 'legacy-host')
    options = database_options()
    assert options['dsn'] == 'postgresql://localhost/pippo_test'
    assert 'host' not in options


@pytest.mark.asyncio
async def test_bot_close_releases_pool_without_starting_discord():
    from bot import PippoBot
    bot = PippoBot()
    pool = AsyncMock()
    bot.pool = pool
    await bot.close()
    pool.close.assert_awaited_once()
    assert bot.pool is None


@pytest.mark.asyncio
async def test_quiz_resolution_counts_unanswered_players_once():
    from views import QuizsterView
    quiz = NS(movie={'actors': 'A', 'description': 'Plot', 'rating': '5', 'genre': 'Drama',
                     'duration': '120', 'datePublished': '2020-01-01'}, hint='Hint', answer_index=0, options=['A','B','C','D'])
    view = QuizsterView(quiz)
    view.people = {1: [3, 0], 2: [1, 0]}
    view.people_playing = [1, 2]
    view.users = {1: 0}
    view.response = NS(edit=AsyncMock())
    await asyncio.gather(view.compare_answers(), view.compare_answers())
    assert view.people == {1: [3, 1], 2: [0, 0]}
    assert view.people_playing == [1]
    view.response.edit.assert_awaited_once()


@pytest.mark.asyncio
async def test_skip_does_not_score_or_allow_another_skip():
    from views import QuizsterView
    quiz = NS(movie={'actors': 'A', 'description': 'Plot', 'rating': '5', 'genre': 'Drama',
                     'duration': '120', 'datePublished': '2020-01-01'}, hint='Hint', answer_index=0, options=['A','B','C','D'])
    view = QuizsterView(quiz)
    view.people = {1: [3, 0]}
    view.people_playing = [1]
    view.skips = 1
    view.response = NS(edit=AsyncMock())
    interaction = NS(user=NS(id=1), response=NS(defer=AsyncMock(), send_message=AsyncMock()), followup=NS(send=AsyncMock()))
    await view.skip_button.callback(interaction)
    assert view.skipped and view.resolved and view.is_finished()
    assert view.skips == 0 and view.people == {1: [3, 0]}
    await view.compare_answers()
    assert view.people == {1: [3, 0]}


def test_newer_movie_data_and_missing_years_are_supported(tmp_path):
    from utils.bollywood_utils import Bollywood_backend
    folder = tmp_path / 'movies'
    folder.mkdir()
    (folder / '2026_data.csv').write_text('name,description\nFuture Film,Plot\n')
    backend = Bollywood_backend(2024, 2026, folders=[str(folder)])
    assert backend.get_random_movie()['name'] == 'Future Film'
    with pytest.raises(commands.BadArgument):
        Bollywood_backend(2026, 2024, folders=[str(folder)])


def test_pixelation_uses_current_pillow_for_valid_rgba_images():
    from io import BytesIO
    from PIL import Image
    from utils.bollywood_utils import pixelate_image
    source = BytesIO()
    Image.new('RGBA', (120, 120), (255, 0, 0, 255)).save(source, format='PNG')
    with patch('utils.bollywood_utils.requests.get', return_value=NS(status_code=200, content=source.getvalue())):
        result = pixelate_image('https://example.test/poster.png', 10)
    rendered = Image.open(result.fp)
    assert rendered.size == (120, 120)
    assert rendered.getpixel((0, 0))[0] > 240
    result.close()


@pytest.mark.asyncio
@pytest.mark.parametrize('submissions', [{}, {1: 'A brave samosa'}])
async def test_clash_friends_timeout_does_not_start_a_solo_duel(submissions):
    module = importlib.import_module('cogs.bollywood')
    user = NS(id=1, display_name='Player')
    ctx = NS(author=user, _pippo_play_mode=False,
             send=AsyncMock(return_value=NS(edit=AsyncMock())))
    async def expire(view):
        view.submissions.update(submissions)
        view.stop()
        await view.on_timeout()
    with patch.object(discord.ui.View, 'wait', expire), \
         patch.object(module, 'clash_art_file', return_value=None), \
         patch.object(module, 'judge_clash', AsyncMock()) as judge:
        await module.Games.ai_clash.callback(module.Games(NS()), ctx)
    judge.assert_not_awaited()
    message = ctx.send.return_value
    assert 'expired' in message.edit.call_args.kwargs['embed'].title
    if submissions:
        assert 'Play solo' in message.edit.call_args.kwargs['embed'].description


@pytest.mark.asyncio
async def test_openrouter_standard_privacy_mode_allows_selected_provider_policy(monkeypatch):
    monkeypatch.setenv('OPENROUTER_API_KEY', 'test-key')
    monkeypatch.setenv('OPENROUTER_MODEL', 'meta/muse-spark-1.3-contributor')
    monkeypatch.setenv('OPENROUTER_PRIVACY_MODE', 'standard')
    body = json.dumps({'choices': [{'message': {'content': json.dumps({'winner': 1, 'reason': 'A'})}}]}).encode()
    async def chunks(size):
        yield body
    response = NS(status=200, content_length=len(body), content=NS(iter_chunked=chunks))
    session = MagicMock()
    session.post.return_value.__aenter__ = AsyncMock(return_value=response)
    with patch('utils.clash.aiohttp.ClientSession') as client:
        client.return_value.__aenter__ = AsyncMock(return_value=session)
        await judge_clash(NS(display_name='First'), 'A', NS(display_name='Second'), 'B')
    request = session.post.call_args.kwargs['json']
    assert request['model'] == 'meta/muse-spark-1.3-contributor'
    assert request['provider'] == {'require_parameters': True}


@pytest.mark.asyncio
async def test_application_command_tree_serializes_with_discord_description_limits():
    from bot import PippoBot, cogs, load_cogs
    bot = PippoBot()
    await bot._async_setup_hook()
    await load_cogs(bot, cogs)
    commands_json = [command.to_dict(bot.tree) for command in bot.tree.get_commands()]
    def validate(node):
        if isinstance(node, dict):
            for key, value in node.items():
                if key == 'description' and isinstance(value, str):
                    assert len(value) <= 100, f'{node.get("name", "command")}: {len(value)} character description'
                validate(value)
        elif isinstance(node, list):
            for value in node:
                validate(value)
    for command in commands_json:
        validate(command)
    await bot.close()
