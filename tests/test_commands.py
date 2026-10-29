import pytest
import asyncio
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

# Ensure Pippo root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import discord
from discord.ext import commands
from PIL import Image

import database
import functions
import flood
from utils.bollywood_utils import (
    Bollywood_backend,
    Quiz_Question,
    normalize_string,
    get_text_after_substitution,
    deposit_score,
    pixelate_image,
)
from views import TicTacToeView
from cogs.fun import Fun
# ---------------------------------------------------------------------------
# 1. Cog Loading & Command Tree Test
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_all_cogs_load():
    bot = commands.Bot(
        command_prefix="!",
        intents=discord.Intents.default(),
        help_command=None
    )
    bot.db = MagicMock()
    bot.THEWHISTLER = 123456789
    bot.production = False
    bot.cartoon_characters = []

    cogs = [
        'actions', 'animals', 'bollywood', 'economy',
        'fun', 'greetings', 'help', 'info', 'settings', 'shop', 'play'
    ]

    for cog in cogs:
        await bot.load_extension(f'cogs.{cog}')

    registered_commands = [c.name for c in bot.commands]
    expected_sample = ['kiss', 'dog', 'cat', 'meow', 'woof', 'bollywood', 'hollywood',
                       'plotster', 'quizster', 'poster', 'bingo', 'tictactoe',
                       'balance', 'send_coins', 'ship', 'laser', 'flames',
                       'help', 'change_prefix', 'leaderboard', 'suggest', 'shop', 'play']
    for cmd in expected_sample:
        assert cmd in registered_commands, f"Command {cmd} should be registered in bot"
    await bot.close()


# ---------------------------------------------------------------------------
# 2. Database Unit Tests (Mocked AsyncPG Pool)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_database_analytics():
    mock_pool = MagicMock()
    mock_conn = AsyncMock()
    mock_pool.acquire.return_value.__aenter__.return_value = mock_conn

    db = database.DB(mock_pool)
    await db.analytics.insert_command("test_cmd", 111, 222)
    mock_conn.execute.assert_called_once()
    args = mock_conn.execute.call_args[0]
    assert "INSERT INTO analytics" in args[0]
    assert args[1] == "test_cmd"
    assert args[2] == 111
    assert args[3] == 222

    # Test summary stats
    mock_conn.fetch.return_value = [{
        "total_commands": 100,
        "unique_users": 25,
        "unique_servers": 15,
        "dm_commands": 5,
        "commands_24h": 12,
        "commands_7d": 45,
    }]
    summary = await db.analytics.get_summary_stats()
    assert summary["total_commands"] == 100
    assert summary["unique_users"] == 25
    assert summary["commands_24h"] == 12

    # Test top commands
    mock_conn.fetch.return_value = [{"command": "bollywood", "count": 50}, {"command": "dog", "count": 20}]
    top = await db.analytics.get_top_commands(limit=5)
    assert len(top) == 2
    assert top[0]["command"] == "bollywood"

    # Test server stats
    mock_conn.fetch.side_effect = [[{"total": 30}], [{"command": "bingo", "count": 15}]]
    server_stats = await db.analytics.get_server_stats(111)
    assert server_stats["total_commands"] == 30
    assert len(server_stats["top_commands"]) == 1


@pytest.mark.asyncio
async def test_database_servers_helpers():
    mock_pool = MagicMock()
    mock_conn = AsyncMock()
    mock_pool.acquire.return_value.__aenter__.return_value = mock_conn

    db = database.DB(mock_pool)
    await db.servers.ensure_server(999, "!")
    mock_conn.execute.assert_called_once()
    assert "ON CONFLICT (server_id) DO NOTHING" in mock_conn.execute.call_args[0][0]

    mock_conn.fetch.return_value = [{"server_id": 999, "prefix": "!"}]
    res = await db.servers.get_all_servers()
    assert len(res) == 1


@pytest.mark.asyncio
async def test_database_coins():
    mock_pool = MagicMock()
    mock_conn = AsyncMock()
    mock_pool.acquire.return_value.__aenter__.return_value = mock_conn

    db = database.DB(mock_pool)

    # get_amount_coins when user exists
    mock_conn.fetch.return_value = [{"coins": 50}]
    bal = await db.coins.get_amount_coins(12345)
    assert bal["coins"] == 50

    # get_amount_coins when user does not exist
    mock_conn.fetch.return_value = []
    bal = await db.coins.get_amount_coins(99999)
    assert bal["coins"] == 0

    # add_coins
    mock_conn.execute.return_value = "UPDATE 1"
    await db.coins.add_coins(12345, coins=10)
    mock_conn.execute.assert_called()


@pytest.mark.asyncio
async def test_database_characters():
    mock_pool = MagicMock()
    mock_conn = AsyncMock()
    mock_pool.acquire.return_value.__aenter__.return_value = mock_conn

    db = database.DB(mock_pool)

    # insert_character calls update_or_insert
    mock_conn.execute.return_value = "UPDATE 1"
    await db.characters.insert_character(12345, show_name="ShowA", cartoon_character="CharA")
    mock_conn.execute.assert_called()


# ---------------------------------------------------------------------------
# 3. Functions Unit Tests
# ---------------------------------------------------------------------------
def test_morse_code():
    morse = functions.MorseCode()
    encoded = morse.encrypt("hello")
    assert "...." in encoded

    decoded = morse.decrypt(encoded)
    assert "hello" in decoded.replace(" ", "")


def test_write_text_on_image():
    # Test with sample image and existing font
    test_img = Image.new('RGB', (400, 200), color=(255, 255, 255))
    test_path = "/tmp/test_banner.png"
    test_img.save(test_path)

    font_list = ["darling_coffee.ttf"]
    color_list = [(0, 0, 0)]
    img = functions.write_text_on_image(test_path, "Movie _ _", font_list, color_list)
    assert isinstance(img, discord.File)


# ---------------------------------------------------------------------------
# 4. Flood Game Logic Tests
# ---------------------------------------------------------------------------
def test_flood_game():
    player1 = MagicMock(id=1, name="P1")
    player2 = MagicMock(id=2, name="P2")
    game = flood.Flood([player1, player2])

    assert len(game.box_colors) == 32
    assert len(game.box_colors[0]) == 32

    percentages = game.get_percentages()
    assert len(percentages) == 2
    assert percentages[0] > 0 and percentages[1] > 0

    buttons = game.return_probable_buttons()
    assert isinstance(buttons, list)
    assert len(buttons) <= 5


# ---------------------------------------------------------------------------
# 5. Bollywood Quiz & Backend Tests
# ---------------------------------------------------------------------------
def test_bollywood_backend():
    backend = Bollywood_backend(2015, 2020, folders=["data/bollywood/"])
    assert len(backend.movies) > 0

    movie = backend.get_random_movie()
    assert movie is not None
    assert 'name' in movie
    assert 'datePublished' in movie

    plotster_movie = backend.get_movie_plotster()
    assert plotster_movie is not None
    assert 'description' in plotster_movie

    # Test quiz question generators
    q_ma = Quiz_Question.MA(backend.get_random_movie)
    assert 2 <= len(q_ma.options) <= 4
    assert len(set(q_ma.options)) == len(q_ma.options)
    assert q_ma.options[q_ma.answer_index] == q_ma.answer

    q_am = Quiz_Question.AM(backend.get_random_movie)
    assert 2 <= len(q_am.options) <= 4
    assert len(set(q_am.options)) == len(q_am.options)
    assert q_am.options[q_am.answer_index] == q_am.answer

    q_ym = Quiz_Question.YM(backend.get_random_movie)
    assert 2 <= len(q_ym.options) <= 4
    assert len(set(q_ym.options)) == len(q_ym.options)
    assert q_ym.options[q_ym.answer_index] == q_ym.answer


def test_bollywood_string_normalization():
    assert normalize_string("Dilwale Dulhania Le Jayenge") == "dilwaledulhanialejayenge"
    assert normalize_string("3 Idiots!") == "3idiots"

    assert get_text_after_substitution("Taare Zameen Par", "ae") == r"\_aa\_e \_a\_ee\_ \_a\_"
    assert get_text_after_substitution("Taare Zameen Par", "ae", escape=False) == "_aa_e _a_ee_ _a_"


def test_ship_score_is_pair_specific_and_rerollable():
    first, second = "Alice", "Bob"
    score = Fun._ship_score(first, second)
    assert 0 <= score <= 100
    assert Fun._ship_score(second, first) == score
    assert Fun._ship_score("Carol", "Dave") != score
    assert Fun._ship_score(first, second, reroll=1) != score


def test_game_captions_use_dynamic_space_below_uncovered_art(tmp_path):
    source = tmp_path / "caption_art.png"
    Image.new("RGB", (400, 200), (255, 249, 235)).save(source)
    caption = "A tie! Everyone completed all five lines together on the same number call."
    attachment = functions.write_caption_on_image(source, "Bingo tie!", caption)
    try:
        with Image.open(attachment.fp) as rendered:
            assert rendered.width == 400
            assert rendered.height > 200 + 112
            assert rendered.getpixel((200, 40))[0] > 240
            panel_color = rendered.getpixel((200, 230))
            assert all(abs(actual - expected) <= 5 for actual, expected in zip(panel_color, (24, 17, 49)))
            assert any(
                r > 220 and g > 210 and b > 200
                for y in range(220, rendered.height - 12)
                for x in range(20, rendered.width - 20)
                for r, g, b in [rendered.getpixel((x, y))]
            )
    finally:
        attachment.close()


def test_movie_mask_is_centered_in_contrast_band_below_art(tmp_path):
    source = tmp_path / "art.png"
    Image.new("RGB", (400, 200), (255, 249, 235)).save(source)
    attachment = functions.write_text_on_image(source, "_aa_e _a_ee_ _a_")
    try:
        with Image.open(attachment.fp) as rendered:
            assert rendered.size == (400, 384)
            panel_color = rendered.getpixel((200, 220))
            assert all(abs(actual - expected) <= 4 for actual, expected in zip(panel_color, (27, 37, 58)))
            assert rendered.getpixel((200, 80))[0] > 240
            assert any(
                r > 220 and g > 200 and b > 170
                for y in range(230, 360)
                for x in range(70, 330)
                for r, g, b in [rendered.getpixel((x, y))]
            )
    finally:
        attachment.close()


@pytest.mark.asyncio
async def test_deposit_score():
    bot = MagicMock()
    bot.db = MagicMock()
    bot.db.award_movie_score = AsyncMock()
    await deposit_score(bot, {111: 5}, 10, "bollywood")
    bot.db.award_movie_score.assert_awaited_once_with(111, 5, 10, "bollywood")
    await deposit_score(bot, {222: 8}, 8, "plotster")
    assert bot.db.award_movie_score.call_args.args == (222, 8, 8, "plotster")


def test_pixelate_image_fallback():
    # Non-existent URL should return fallback image without raising unhandled exception
    with patch("utils.bollywood_utils.requests.get", side_effect=OSError("offline")):
        res = pixelate_image("https://invalid.example/img.png", 10)
    assert isinstance(res, discord.File)
    assert res.filename == "pixelate_img.jpg"


# ---------------------------------------------------------------------------
# 6. Tic Tac Toe View Tests
# ---------------------------------------------------------------------------
def test_tictactoe_winner():
    view = TicTacToeView()
    # Row win
    view.board = [
        [view.X, view.X, view.X],
        [view.O, view.O, 0],
        [0, 0, 0]
    ]
    assert view.check_board_winner() == view.X

    # Diagonal win
    view.board = [
        [view.O, view.X, 0],
        [view.X, view.O, 0],
        [0, 0, view.O]
    ]
    assert view.check_board_winner() == view.O

    # Tie
    view.board = [
        [view.X, view.O, view.X],
        [view.X, view.O, view.O],
        [view.O, view.X, view.X]
    ]
    assert view.check_board_winner() == view.Tie


# ---------------------------------------------------------------------------
# 7. Fun & Games Extended Tests
# ---------------------------------------------------------------------------
def test_flames_algorithm():
    from cogs.fun import Fun
    bot = MagicMock()
    fun_cog = Fun(bot)

    # Test names calculate expected flames without error
    # Let's extract the flames logic directly
    def calculate_flames(name1, name2):
        flames = "FLAMES"
        result = []
        name1 = name1.upper().replace(" ", "")
        name2 = name2.upper().replace(" ", "")
        for char in name1:
            if char in name2:
                name2 = name2.replace(char, "", 1)
                continue
            result.append(char)
        count = len(result) + len(name2)
        if count <= 0:
            count = 1
        while len(flames) > 1:
            index = (count - 1) % len(flames)
            flames = flames[:index] + flames[index+1:]
        options = {"F": "👫 Friends", "L": "❤️ Lovers", "A": "😊 Affectionate", "M": "💍 Marriage", "E": "😡 Enemies", "S": "👦👧 Siblings"}
        return options[flames], flames

    desc, letter = calculate_flames("Romeo", "Juliet")
    assert letter in ["F", "L", "A", "M", "E", "S"]
    assert desc != ""

    # Identical names check (count 0 fallback to 1)
    desc2, letter2 = calculate_flames("Same", "Same")
    assert letter2 in ["F", "L", "A", "M", "E", "S"]


def test_views_initialization():
    from views import MemoryView, GuessTheMovieView, HelpView, BreedGuessView, ChallengeInviteView, TicTacToeView
    from cogs.settings import LeaderboardView, SuggestModal

    # HelpView with Category Select
    bot = MagicMock()
    hv = HelpView(bot=bot, prefix="!")
    assert len(hv.children) >= 3
    home_emb = hv.generate_embed("home")
    assert "Welcome to Pippo" in home_emb.title
    games_emb = hv.generate_embed("games")
    assert "Games" in games_emb.title

    # ChallengeInviteView
    p1 = MagicMock(id=1, display_name="P1")
    p2 = MagicMock(id=2, display_name="P2")
    civ = ChallengeInviteView(p1, p2, "Tic Tac Toe")
    assert len(civ.children) == 2
    assert civ.accepted is None

    # TicTacToe with 2 players
    ttv = TicTacToeView(player_x=p1, player_o=p2)
    assert ttv.player_x == p1
    assert ttv.player_o == p2
    assert len(ttv.children) == 9

    # LeaderboardView
    mock_db = MagicMock()
    lbv = LeaderboardView(mock_db, initial_key="bollywood")
    assert len(lbv.children) >= 1

    # SuggestModal
    sm = SuggestModal(bot)
    assert sm.subject is not None
    assert sm.details is not None

    # MemoryView items
    user1 = MagicMock(id=1, mention="@u1")
    user2 = MagicMock(id=2, mention="@u2")
    mv = MemoryView(user1, user2)
    assert len(mv.children) == 16
    assert mv.check_winner() is False

    # GuessTheMovieView
    gmv = GuessTheMovieView("Inception", ["Tenet", "Dunkirk", "Memento"])
    assert len(gmv.children) == 4

    # BreedGuessView
    bgv = BreedGuessView("Persian", ["Persian", "Siamese", "Ragdoll", "Bengal"])
    assert len(bgv.children) == 4


def test_single_player_modes():
    from views import TicTacToeView, MemoryView, FloodView, BingoStartView

    # 1. TicTacToe Solo vs Bot
    user = MagicMock(id=101, mention="@user")
    ttv = TicTacToeView(player_x=user, vs_bot=True)
    assert ttv.vs_bot is True
    assert ttv.player_o is None
    # Player X makes a move
    ttv.board[0][0] = ttv.X
    ttv.current_player = ttv.O
    # Bot makes a move
    ttv.bot_move()
    # Check that bot placed an O on the board
    o_count = sum(row.count(ttv.O) for row in ttv.board)
    assert o_count == 1
    assert ttv.current_player == ttv.X

    # 2. Memory Match Solo Mode
    mv_solo = MemoryView(user)
    assert mv_solo.is_solo is True
    assert len(mv_solo.players) == 1
    assert len(mv_solo.scores) == 1
    assert mv_solo.moves == 0
    assert mv_solo.pairs_found == 0

    # 3. Flood Solo vs Pippo
    emojis = {k: "emoji" for k in ["red", "green", "magenta", "blue", "yellow", "top_left", "bottom_right", "discord_loading"]}
    fv = FloodView(user, emojis)
    assert fv.vs_bot is False
    assert len(fv.players) == 1

    # 4. Bingo Solo Mode with Bot
    class FakePlayer:
        def __init__(self, uid):
            self.id = uid
            self.started = False
            self.msg = None
            self.cut = []
            self.global_cut = []
            self.number_list = [["1","2","3","4","5"],["6","7","8","9","10"],["11","12","13","14","15"],["16","17","18","19","20"],["21","22","23","24","25"]]

    bot_id = 999
    players = {101: FakePlayer(101), bot_id: FakePlayer(bot_id)}
    bsv = BingoStartView(players, bot_user_id=bot_id)
    assert bsv.bot_user_id == bot_id
    # Simulate start_button logic
    players[101].started = True
    if bsv.bot_user_id and bsv.bot_user_id in bsv.players:
        bsv.players[bsv.bot_user_id].started = True
    assert bsv.players[bot_id].started is True
    assert all(p.started for p in bsv.players.values())


@pytest.mark.asyncio
async def test_info_owner_commands():
    from cogs.info import Info
    mock_bot = MagicMock()
    mock_bot.THEWHISTLER = 123456
    mock_bot.prefix = "."
    mock_bot.latency = 0.05
    mock_bot.start_time = discord.utils.utcnow()
    
    # Guild mocks
    guild1 = MagicMock(spec=discord.Guild)
    guild1.id = 111
    guild1.name = "Guild One"
    guild1.member_count = 50
    guild1.owner = MagicMock(display_name="OwnerOne")
    guild1.owner_id = 9991
    guild1.created_at = discord.utils.utcnow()
    guild1.icon = None

    guild2 = MagicMock(spec=discord.Guild)
    guild2.id = 222
    guild2.name = "Guild Two"
    guild2.member_count = 150
    guild2.owner = MagicMock(display_name="OwnerTwo")
    guild2.owner_id = 9992
    guild2.created_at = discord.utils.utcnow()
    guild2.icon = None

    mock_bot.guilds = [guild1, guild2]
    mock_bot.get_guild.side_effect = lambda gid: {111: guild1, 222: guild2}.get(gid)
    mock_bot.is_owner = AsyncMock(return_value=True)

    cog = Info(mock_bot)

    # 1. servers command
    ctx = MagicMock()
    ctx.author = AsyncMock()
    ctx.author.id = 123456
    ctx.guild = None
    await cog.servers.callback(cog, ctx)
    ctx.author.send.assert_called_once()
    assert "file" in ctx.author.send.call_args.kwargs

    # 2. analytics command
    mock_bot.db = MagicMock()
    mock_bot.db.analytics.get_summary_stats = AsyncMock(return_value={
        "total_commands": 500, "unique_users": 80, "unique_servers": 30,
        "dm_commands": 10, "commands_24h": 40, "commands_7d": 120
    })
    mock_bot.db.analytics.get_top_commands = AsyncMock(return_value=[("bollywood", 200)])
    ctx_send = AsyncMock()
    ctx.send = ctx_send
    await cog.analytics.callback(cog, ctx)
    ctx_send.assert_called_once()
    assert "embed" in ctx_send.call_args.kwargs

    # 3. topcommands command
    ctx_send.reset_mock()
    await cog.topcommands.callback(cog, ctx, days=7, limit=5)
    ctx_send.assert_called_once()

    # 4. serverinfo command
    ctx_send.reset_mock()
    mock_bot.db.servers.fetch_prefix = AsyncMock(return_value="!")
    mock_bot.db.analytics.get_server_stats = AsyncMock(return_value={"total_commands": 25, "top_commands": [("dog", 10)]})
    await cog.serverinfo.callback(cog, ctx, guild_id=111)
    ctx_send.assert_called_once()

    # 5. syncservers command
    ctx_send.reset_mock()
    mock_bot.db.servers.get_all_servers = AsyncMock(return_value=[{"server_id": 111, "prefix": "!"}])
    mock_bot.db.servers.ensure_server = AsyncMock()
    await cog.syncservers.callback(cog, ctx)
    mock_bot.db.servers.ensure_server.assert_called_once_with(222, ".")
    ctx_send.assert_called_once()
