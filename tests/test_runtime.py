"""Regression and concurrency checks; all Discord and provider delivery stays local."""
import asyncio
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import AsyncMock, MagicMock, patch
import json
import threading
import time

import aiohttp
import discord
from discord.ext import commands
from discord.ext.commands.view import StringView
from PIL import Image
import pytest

from runtime import PippoContext, PrefixCache, SessionBusy, TextSessions, ViewSessions, read_limited, run_blocking


@pytest.mark.asyncio
async def test_streamed_body_waits_for_every_chunk_and_eof():
    protocol = NS(_reading_paused=False, connected=True, resume_reading=lambda **kwargs: None)
    reader = aiohttp.StreamReader(protocol, limit=1024)
    reader.feed_data(b'first')
    task = asyncio.create_task(read_limited(NS(content_length=None, content=reader), 100))
    await asyncio.sleep(0)
    assert not task.done()
    reader.feed_data(b'-second')
    reader.feed_eof()
    assert await task == b'first-second'


@pytest.mark.asyncio
async def test_streamed_body_rejects_oversize_without_content_length():
    reader = aiohttp.StreamReader(NS(_reading_paused=False, connected=True, resume_reading=lambda **kwargs: None), limit=1024)
    reader.feed_data(b'123456')
    reader.feed_eof()
    with pytest.raises(ValueError):
        await read_limited(NS(content_length=None, content=reader), 5)


@pytest.mark.asyncio
async def test_prefix_burst_uses_one_database_read_then_invalidates():
    cache = PrefixCache(capacity=2)
    reads = 0
    async def loader():
        nonlocal reads
        reads += 1
        await asyncio.sleep(.005)
        return '!'
    assert await asyncio.gather(*(cache.get(1, loader) for _ in range(100))) == ['!'] * 100
    assert reads == 1
    cache.invalidate(1)
    assert await cache.get(1, loader) == '!'
    assert reads == 2
    await cache.get(2, loader)
    await cache.get(3, loader)
    assert len(cache.values) == 2


@pytest.mark.asyncio
async def test_media_burst_keeps_loop_responsive_and_limits_workers():
    lock = threading.Lock()
    active = peak = 0
    heartbeats = 0
    def work(number):
        nonlocal active, peak
        with lock:
            active += 1
            peak = max(active, peak)
        time.sleep(.01)
        with lock:
            active -= 1
        return number
    async def heartbeat():
        nonlocal heartbeats
        while not batch.done():
            heartbeats += 1
            await asyncio.sleep(.001)
    batch = asyncio.gather(*(run_blocking(work, n) for n in range(80)))
    await heartbeat()
    assert await batch == list(range(80))
    assert peak <= 4
    assert heartbeats > 10


def context(owner, channel, name='bollywood'):
    return NS(author=NS(id=owner), channel=NS(id=channel), command=NS(name=name))


def test_text_games_isolate_channels_and_release_for_next_player():
    registry = TextSessions(capacity=100)
    games = [context(n, n) for n in range(100)]
    for ctx in games:
        registry.acquire(ctx)
    with pytest.raises(SessionBusy):
        registry.acquire(context(101, 0, 'plotster'))
    registry.release(games[0])
    next_player = context(101, 0, 'plotster')
    registry.acquire(next_player)
    registry.release(games[0])
    assert registry.channels[0][0] is next_player
    for ctx in [*games[1:], next_player]:
        registry.release(ctx)
    assert not registry.channels


@pytest.mark.asyncio
async def test_command_hooks_release_sessions_after_failure_and_cancellation():
    bot = commands.Bot(command_prefix='.', intents=discord.Intents.none())
    registry = TextSessions()
    @bot.before_invoke
    async def before(ctx):
        registry.acquire(ctx)
    @bot.after_invoke
    async def after(ctx):
        registry.release(ctx)
    @commands.command(name='bollywood')
    async def game(ctx):
        await asyncio.sleep(0)
        if ctx.author.id % 2:
            raise ValueError('test failure')
    bot.add_command(game)
    def ctx(n):
        message = NS(author=NS(id=n), channel=NS(id=n), guild=None, attachments=[],
                     _state=bot._connection, id=n, content='.bollywood')
        return commands.Context(message=message, bot=bot, prefix='.', view=StringView(''), command=game)
    results = await asyncio.gather(*(game.invoke(ctx(n)) for n in range(40)), return_exceptions=True)
    assert sum(isinstance(r, commands.CommandInvokeError) for r in results) == 20
    assert not registry.channels
    waiting = asyncio.Event()
    async def blocked(ctx):
        waiting.set()
        await asyncio.Future()
    game.callback = blocked
    task = asyncio.create_task(game.invoke(ctx(50)))
    await waiting.wait()
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)
    assert not registry.channels
    await bot.close()


@pytest.mark.asyncio
async def test_safe_reply_allows_deleted_reference():
    message = NS(to_reference=MagicMock(return_value='safe-ref'))
    ctx = NS(interaction=None, message=message, send=AsyncMock())
    await PippoContext.reply(ctx, 'hello')
    message.to_reference.assert_called_once_with(fail_if_not_exists=False)
    ctx.send.assert_awaited_once_with('hello', reference='safe-ref')


@pytest.mark.asyncio
async def test_duplicate_shop_clicks_charge_only_once():
    from cogs.shop import CharacterView
    purchase = AsyncMock(return_value=True)
    bot = NS(db=NS(characters=NS(purchase_cartoon_character=purchase)))
    view = CharacterView(bot, 'Show', [{'show_name': 'Show', 'character_name': 'Pippo'}], author_id=1)
    view.out = NS(edit=AsyncMock())
    selector = view.children[0]
    selector._values = ['Pippo']
    interactions = [NS(user=NS(id=1), response=NS(defer=AsyncMock()), followup=NS(send=AsyncMock())) for _ in range(20)]
    await asyncio.gather(*(selector.callback(i) for i in interactions))
    purchase.assert_awaited_once_with(1, 'Show', 'Pippo', cost=1000)
    view.out.edit.assert_awaited_once()
    assert view.is_finished()


@pytest.mark.asyncio
async def test_breed_buttons_resolve_once_and_other_games_stay_independent():
    from views import BreedGuessView
    views = [BreedGuessView('A', ['A','B','C','D']) for _ in range(30)]
    for view in views:
        view.out = NS(edit=AsyncMock())
    def interaction(uid):
        return NS(user=NS(id=uid, display_name=str(uid)), response=NS(defer=AsyncMock()), followup=NS(send=AsyncMock()))
    await asyncio.gather(*(view.children[n % 4].callback(interaction(n)) for view in views for n in range(4)))
    for view in views:
        assert view.is_finished()
        view.out.edit.assert_awaited_once()


@pytest.mark.asyncio
async def test_breed_quiz_runs_multiple_scored_rounds_on_one_message():
    from views import BreedGuessView

    second_question = {
        "answer": "E",
        "breeds": ["E", "F", "G", "H"],
        "embed": discord.Embed(title="Round 2/2"),
        "files": [],
    }
    next_round = AsyncMock(return_value=second_question)
    view = BreedGuessView(
        "A", ["A", "B", "C", "D"], total_rounds=2, next_round=next_round
    )
    view.out = NS(edit=AsyncMock())

    def interaction(user_id, display_name):
        return NS(
            user=NS(id=user_id, display_name=display_name),
            response=NS(defer=AsyncMock()),
            followup=NS(send=AsyncMock()),
        )

    with patch("views.asyncio.sleep", new_callable=AsyncMock):
        await view.children[0].callback(interaction(10, "Pippo Fan"))
        assert view.round_number == 2
        assert view.answer == "E"
        assert view.scores == {10: 1}
        assert view.attempted_users == set()
        await view.children[0].callback(interaction(11, "Pet Pal"))

    assert view.is_finished()
    assert view.scores == {10: 1, 11: 1}
    assert "Final scores" in view.embed.description
    next_round.assert_awaited_once()
    assert view.out.edit.await_count == 3


@pytest.mark.asyncio
async def test_friends_breed_quiz_eliminates_wrong_choice_without_ending_round():
    from views import BreedGuessView

    view = BreedGuessView(
        "A", ["A", "B", "C", "D"], total_rounds=5,
        next_round=AsyncMock(return_value=None),
    )
    view.out = NS(edit=AsyncMock())

    def interaction(user_id):
        return NS(
            user=NS(id=user_id, display_name=f"Player {user_id}"),
            response=NS(defer=AsyncMock()),
            followup=NS(send=AsyncMock()),
        )

    with patch("views.asyncio.sleep", new_callable=AsyncMock):
        await view.children[1].callback(interaction(10))
        assert view.children[1].disabled
        assert view.children[1].style is discord.ButtonStyle.red
        assert not view.is_finished()
        await view.children[2].callback(interaction(10))
        assert not view.children[2].disabled
        assert view.out.edit.await_count == 1
        await view.children[0].callback(interaction(11))

    assert view.is_finished()
    assert view.scores == {11: 1}


@pytest.mark.asyncio
@pytest.mark.parametrize('outcome',list('FLAMES'))
async def test_flames_final_uses_original_local_outcome_image(outcome):
    from views import FlamesView
    view = FlamesView(1, 'A', 'B', 2, [('X','')], outcome, outcome)
    view.position = 1
    embed = await run_blocking(view.make_embed)
    assert embed.image.url == f'attachment://flames_{outcome}.png'
    assert view._outcome_art.fp.read() == Path(f'imgs_source/flames/{outcome}.png').read_bytes()
    for file in (view._pending_art, view._outcome_art):
        if file:
            file.close()
    view.stop()


@pytest.mark.asyncio
async def test_laser_restores_slow_same_message_reveal():
    from cogs.fun import Fun
    bot = NS(get_emoji=lambda _: None)
    cog = Fun(bot)
    message = NS(edit=AsyncMock())
    ctx = NS(author=NS(id=1, mention='<@1>'), reply=AsyncMock(return_value=message))
    with patch('cogs.fun.asyncio.sleep', new_callable=AsyncMock) as sleep:
        await Fun.laser.callback(cog, ctx)
    ctx.reply.assert_awaited_once()
    assert message.edit.await_count == 8
    assert sleep.await_count == 7
    assert all(call.args == (1.5,) for call in sleep.call_args_list)
    assert 'annihilated' in message.edit.call_args.kwargs['content']


@pytest.mark.asyncio
async def test_all_catalog_commands_register_and_copied_examples_parse():
    from bot import PippoBot, cogs, load_cogs
    bot = PippoBot()
    await load_cogs(bot, cogs)
    records = json.loads(Path('website/commands.json').read_text())
    for record in records:
        assert bot.get_command(record['command']) is not None, record['command']
    from cogs.bollywood import BollywoodFlags, PosterFlags
    conversions = {'quizster': PosterFlags, 'poster': PosterFlags}
    for record in records:
        if record['command'] in conversions:
            text = ''
            flags = await conversions[record['command']].convert(MagicMock(current_parameter=None, command=None),text)
            assert flags.mode.value in {"bollywood", "hollywood", "mix"}
    assert next(r['example'] for r in records if r['command']=='bingo') == '.bingo'
    from scripts.render_catalog import render_catalog
    page = Path('website/commands.html').read_text()
    assert render_catalog(page, records) == page
    await bot.close()


@pytest.mark.asyncio
async def test_every_game_uses_identical_mode_buttons_and_preserves_options():
    from bot import PippoBot, cogs, load_cogs
    from cogs.play import GAME_OPTIONS
    bot = PippoBot()
    await bot._async_setup_hook()
    await load_cogs(bot, cogs)
    for name, _, _ in GAME_OPTIONS:
        command = bot.get_command(name)
        message = NS(author=NS(id=1, display_name='Player'), channel=NS(id=10), guild=None,
                     _state=bot._connection, attachments=[], created_at=discord.utils.utcnow(),
                     edited_at=None, content='.'+name, id=123)
        ctx = commands.Context(message=message, bot=bot, prefix='.', view=StringView(''), command=command)
        ctx.send = AsyncMock(return_value=NS(edit=AsyncMock()))
        kwargs = {}
        if 'flags' in command.params:
            flags = await command.params['flags'].annotation.convert(MagicMock(current_parameter=None, command=None), '')
            kwargs['flags'] = flags
        await command.callback(command.cog, ctx, **kwargs)
        view = ctx.send.call_args.kwargs['view']
        labels = [getattr(item, 'label', None) for item in view.children]
        assert labels.count('Play solo') == 1, name
        assert labels.count('Play with friends') == 1, name
        assert 'solo' not in command.params, name
        assert ctx._pippo_menu_only
        interaction = NS(user=ctx.author, response=NS(edit_message=AsyncMock(), send_message=AsyncMock()))
        with patch.object(command, 'invoke', new_callable=AsyncMock) as invoke:
            await view.solo_button.callback(interaction)
            launched_ctx = invoke.call_args.args[0]
            assert launched_ctx._pippo_play_mode is True, name
            assert launched_ctx.reply is launched_ctx.send
            if 'flags' in kwargs:
                assert launched_ctx._pippo_options['flags'] is kwargs['flags']
            await view.solo_button.callback(interaction)
            invoke.assert_awaited_once()
        view.stop()
    await bot.close()


@pytest.mark.asyncio
async def test_plotster_second_round_and_score_deposit():
    import utils.bollywood_utils as game
    movies = [dict(name='First Film', description='An adventurer meets a mysterious stranger', keywords='adventurer|mystery'),
              dict(name='Second Film', description='A family discovers a forgotten secret', keywords='family|secret')]
    backend = NS(get_movie_plotster=MagicMock(side_effect=movies))
    channel = NS(id=1)
    user = NS(id=42, bot=False)
    messages = [NS(content='First Film', author=user, channel=channel, add_reaction=AsyncMock()),
                NS(content='exit', author=user, channel=channel, add_reaction=AsyncMock())]
    async def wait_for(event, **kwargs):
        message = messages.pop(0)
        assert kwargs['check'](message)
        return message
    bot = NS(get_prefixx=AsyncMock(return_value='.'), wait_for=wait_for)
    ctx = NS(author=user, channel=channel, message=NS(), send=AsyncMock(return_value=NS(edit=AsyncMock())))
    embed = lambda *a, **k: (discord.Embed(description=''), None)
    frame = lambda *a, **k: (discord.Embed(), discord.Embed(), None)
    timing = NS(sleep=AsyncMock(), get_running_loop=asyncio.get_running_loop, TimeoutError=asyncio.TimeoutError)
    with patch.object(game, 'Bollywood_backend', return_value=backend), \
         patch.object(game, 'plotster_game_start_embed', side_effect=embed), \
         patch.object(game, 'plotster_game_over_embed', side_effect=embed), \
         patch.object(game, 'plotster_guess_embed', side_effect=frame), \
         patch.object(game, 'deposit_score', new_callable=AsyncMock) as deposit, \
         patch.object(game, 'asyncio', timing):
        await game.play_plotster(ctx, bot, 'bollywood', 2020, 2023, solo=True)
    assert backend.get_movie_plotster.call_count == 2
    deposit.assert_awaited_once_with(bot, {42:6}, 1, 'plotster')


@pytest.mark.asyncio
@pytest.mark.parametrize("correct", [False, True])
async def test_poster_guess_uses_reaction_without_extra_reply(correct):
    import utils.bollywood_utils as game
    movie = {'name':'First Film','type':'Movie','poster_url':'https://example.test/poster.jpg'}
    channel = NS(id=1)
    user = NS(id=1,bot=False)
    wrong = NS(content='First Film' if correct else 'Unrelated Title', author=user, channel=channel, add_reaction=AsyncMock(), reply=AsyncMock())
    end = NS(content='exit', author=user, channel=channel, add_reaction=AsyncMock(), reply=AsyncMock())
    bot = NS(wait_for=AsyncMock(side_effect=[wrong,end]))
    ctx = NS(author=user, channel=channel, prefix='.', send=AsyncMock(return_value=NS(edit=AsyncMock())))
    timing = NS(sleep=AsyncMock(), TimeoutError=asyncio.TimeoutError)
    with patch.object(game, 'Bollywood_backend', return_value=NS(movies=[movie])), \
         patch.object(game, 'pixelate_game_start_embed', return_value=(discord.Embed(),None)), \
         patch.object(game, 'pixelate_game_over_embed', return_value=(discord.Embed(),None)), \
         patch.object(game, 'pixelate_guess_embed', return_value=(discord.Embed(),discord.Embed(),None)), \
         patch.object(game, 'fetch_poster_image', new_callable=AsyncMock), \
         patch.object(game, 'asyncio', timing):
        await game.play_pixelate(ctx,bot,'bollywood',2020,2023,solo=True)
    wrong.add_reaction.assert_awaited_once_with('✅' if correct else '❌')
    wrong.reply.assert_not_awaited()
    assert ctx.send.await_count == 3  # Intro, reusable game message, final score.


@pytest.mark.asyncio
async def test_suggest_guidance_does_not_reply_to_deleted_message():
    from cogs.settings import Settings
    ctx = NS(interaction=None, message=NS(delete=AsyncMock()), reply=AsyncMock(), send=AsyncMock())
    await Settings.suggest.callback(Settings(NS()), ctx, feedback_text='private')
    ctx.message.delete.assert_awaited_once()
    ctx.reply.assert_not_awaited()
    ctx.send.assert_awaited_once()


@pytest.mark.asyncio
async def test_openrouter_reuses_shared_client_and_keeps_games_separate(monkeypatch):
    from utils.clash import judge_clash
    monkeypatch.setenv('OPENROUTER_API_KEY','test-only')
    session = NS(closed=False)
    def post(url, **kwargs):
        request = json.loads(kwargs['json']['messages'][1]['content'])
        body = json.dumps({'choices':[{'message':{'content':json.dumps({'winner':1,'reason':request['player1']['creation']})}}]}).encode()
        async def chunks(size):
            yield body
        response = NS(status=200,content_length=len(body),content=NS(iter_chunked=chunks))
        cm = MagicMock()
        cm.__aenter__ = AsyncMock(return_value=response)
        cm.__aexit__ = AsyncMock(return_value=False)
        return cm
    session.post = MagicMock(side_effect=post)
    bot = NS(http_session=session)
    players = [NS(display_name=f'Player {n}') for n in range(20)]
    with patch('runtime.aiohttp.ClientSession', side_effect=AssertionError('must reuse pooled client')):
        results = await asyncio.gather(*(judge_clash(p,f'Creation {n}',NS(display_name='Pippo'),'Bot',bot=bot) for n,p in enumerate(players)))
    for n,(winner,reason) in enumerate(results):
        assert winner is players[n]
        assert reason == f'Creation {n}'
    assert session.post.call_count == 20


def test_launcher_admin_environment_is_preserved_and_authorized(monkeypatch):
    from scripts import prepare_database as setup
    seen = []
    monkeypatch.setattr(setup.shutil, 'which', lambda name: '/usr/bin/'+name)
    monkeypatch.setattr(setup.os, 'geteuid', lambda: 1000)
    monkeypatch.setattr(setup, 'authorize_local_admin', lambda: seen.append('authorized') or True)
    def run(args, **kwargs):
        if args[-1]=='info': return NS(returncode=1,stderr='permission denied')
        if 'container' in args: return NS(returncode=1,stderr='not found')
        if 'run' in args:
            assert '--preserve-env=POSTGRES_USER,POSTGRES_PASSWORD,POSTGRES_DB' in args
            assert kwargs['env']['POSTGRES_PASSWORD']=='test-only'
        return NS(returncode=0,stderr='',stdout='')
    monkeypatch.setattr(setup,'run_command',run)
    settings={'user':'test','password':'test-only','database':'test','host':'localhost','port':55439}
    assert setup.start_docker_postgres(settings)[0]
    monkeypatch.setattr(setup.subprocess,'run', lambda *args, **kwargs: NS(returncode=0))
    assert setup.provision_system_database(settings)[0]
    assert seen == ['authorized','authorized']


@pytest.mark.asyncio
@pytest.mark.parametrize('api_available',[True,False])
async def test_animal_pipeline_reads_chunked_photo_and_uses_same_breed_fallback(api_available):
    from cogs.animals import Animals
    output = BytesIO()
    Image.new('RGB',(80,80),'orange').save(output,'PNG')
    payload = output.getvalue()
    url = 'https://cdn2.thedogapi.com/images/test.png'
    session = NS(closed=False)
    def get(target, **kwargs):
        cm = MagicMock()
        cm.__aexit__ = AsyncMock(return_value=False)
        if 'images/search' in target:
            if not api_available:
                cm.__aenter__ = AsyncMock(side_effect=asyncio.TimeoutError())
            else:
                cm.__aenter__ = AsyncMock(return_value=NS(status=200,json=AsyncMock(return_value=[{'url':url}])))
        else:
            async def chunks(size):
                for offset in range(0,len(payload),7):
                    await asyncio.sleep(0)
                    yield payload[offset:offset+7]
            cm.__aenter__ = AsyncMock(return_value=NS(status=200,content_length=None,
                headers={'Content-Type':'image/png'},content=NS(iter_chunked=chunks)))
        return cm
    session.get = MagicMock(side_effect=get)
    cog = Animals(NS(http_session=session))
    with patch('cogs.animals.animal_art_file', return_value=None):
        result = await cog.fetch_animal_photo('dog',1,set(),breed_id=1,fallback_url=url)
    assert result is not None
    embed,photo,thumbnail,photo_url = result
    assert photo_url == url
    assert photo.fp.read(2) == b'\xff\xd8'
    photo.close()


@pytest.mark.asyncio
async def test_expired_breed_timeout_does_not_overwrite_answer():
    from views import BreedGuessView
    view = BreedGuessView('A',['A','B','C','D'])
    view.out = NS(edit=AsyncMock())
    i = NS(user=NS(id=1,display_name='Player'), response=NS(defer=AsyncMock()), followup=NS(send=AsyncMock()))
    await view.children[0].callback(i)
    await view.on_timeout()
    assert view.embed.title == 'Correct!'
    view.out.edit.assert_awaited_once()
    i.followup.send.assert_not_awaited()


@pytest.mark.asyncio
async def test_prefix_invalidation_during_read_never_restores_stale_value():
    cache = PrefixCache()
    entered,release=asyncio.Event(),asyncio.Event()
    async def old():
        entered.set()
        await release.wait()
        return '.'
    first=asyncio.create_task(cache.get(1,old))
    await entered.wait()
    cache.invalidate(1)
    assert await cache.get(1,AsyncMock(return_value='!')) == '!'
    release.set()
    assert await first == '.'
    assert await cache.get(1,AsyncMock(side_effect=AssertionError('must use new cache'))) == '!'


@pytest.mark.asyncio
async def test_view_capacity_releases_completed_menus_for_following_users():
    registry=ViewSessions(capacity=3,user_limit=2)
    views=[discord.ui.View() for _ in range(4)]
    registry.reserve(1,views[0]); registry.reserve(1,views[1])
    with pytest.raises(SessionBusy): registry.reserve(1,views[2])
    registry.reserve(2,views[2])
    with pytest.raises(SessionBusy): registry.reserve(3,views[3])
    views[0].stop()
    registry.reserve(3,views[3])
    assert len(registry.entries)==3
    for view in views:view.stop()


@pytest.mark.asyncio
async def test_parallel_tictactoe_clicks_cannot_double_move_on_same_square():
    from views import TicTacToeView
    player=NS(id=1,display_name='Player',mention='<@1>')
    view=TicTacToeView(player_x=player,vs_bot=True,difficulty='hard')
    def interaction():
        return NS(user=player,channel=None,response=NS(defer=AsyncMock()),
                  followup=NS(send=AsyncMock()),edit_original_response=AsyncMock())
    interactions=[interaction() for _ in range(20)]
    await asyncio.gather(*(view.children[0].callback(i) for i in interactions))
    assert sum(row.count(view.X) for row in view.board)==1
    assert sum(row.count(view.O) for row in view.board)==1
    assert sum(i.edit_original_response.await_count for i in interactions)==1
    view.stop()


@pytest.mark.asyncio
async def test_prefix_questions_phrases_and_subcommand_help_keep_all_words():
    from bot import PippoBot,cogs,load_cogs
    bot=PippoBot()
    await bot._async_setup_hook()
    await load_cogs(bot,cogs)
    cases=[('8ball','question','Will tomorrow be a good day?'),
           ('what','query','once in a blue moon'),('help','command','shop character')]
    for name,key,text in cases:
        command=bot.get_command(name)
        message=NS(author=NS(id=1),channel=NS(id=1),guild=None,attachments=[],_state=bot._connection,content='.'+name+' '+text,id=1)
        ctx=commands.Context(message=message,bot=bot,prefix='.',view=StringView(text),command=command)
        await command._parse_arguments(ctx)
        assert ctx.kwargs[key]==text
    await bot.close()


def test_extreme_movie_year_range_rejected_before_reading_files():
    from utils.bollywood_utils import Bollywood_backend
    with patch.object(Bollywood_backend,'load_movies',side_effect=AssertionError('must validate before scanning')):
        with pytest.raises(commands.BadArgument,match='ending year'):
            Bollywood_backend(1980,10**12)


@pytest.mark.asyncio
async def test_cancelled_media_keeps_admission_until_thread_finishes():
    import runtime
    started=0
    lock=threading.Lock()
    release=threading.Event()
    def work():
        nonlocal started
        with lock: started += 1
        release.wait(timeout=5)
        return 1
    with patch.object(runtime._workers,'submit',wraps=runtime._workers.submit) as submit:
        originals=[asyncio.create_task(run_blocking(work)) for _ in range(4)]
        followers=[]
        try:
            async with asyncio.timeout(2):
                while started < 4: await asyncio.sleep(.001)
            for task in originals: task.cancel()
            await asyncio.gather(*originals,return_exceptions=True)
            followers=[asyncio.create_task(run_blocking(lambda: 2)) for _ in range(20)]
            await asyncio.sleep(.02)
            assert submit.call_count==4  # Nothing else enters the executor while threads remain busy.
            release.set()
            assert await asyncio.gather(*followers)==[2]*20
        finally:
            release.set()
            await asyncio.gather(*originals,*followers,return_exceptions=True)


@pytest.mark.asyncio
async def test_cancelled_media_closes_undelivered_attachment(tmp_path):
    entered=threading.Event()
    release=threading.Event()
    path=tmp_path/'cancelled.jpg'
    path.write_bytes(b'bytes')
    attachment=discord.File(path)
    def work():
        entered.set()
        release.wait(timeout=5)
        return (discord.Embed(),attachment)
    task=asyncio.create_task(run_blocking(work))
    try:
        async with asyncio.timeout(2):
            while not entered.is_set(): await asyncio.sleep(.001)
        task.cancel()
        await asyncio.gather(task,return_exceptions=True)
        release.set()
        async with asyncio.timeout(2):
            while not attachment.fp.closed: await asyncio.sleep(.001)
    finally:
        release.set()
        await asyncio.gather(task,return_exceptions=True)
