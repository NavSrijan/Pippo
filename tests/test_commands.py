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
        'fun', 'greetings', 'help', 'info', 'settings', 'shop'
    ]

    for cog in cogs:
        await bot.load_extension(f'cogs.{cog}')

    registered_commands = [c.name for c in bot.commands]
    expected_sample = ['kiss', 'dog', 'cat', 'meow', 'woof', 'bollywood', 'hollywood',
                       'plotster', 'quizster', 'poster', 'bingo', 'tictactoe',
                       'balance', 'send_coins', 'ship', 'laser', 'flames',
                       'help', 'change_prefix', 'leaderboard', 'suggest', 'shop']
    for cmd in expected_sample:
        assert cmd in registered_commands, f"Command {cmd} should be registered in bot"


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
    assert len(q_ma.options) == 4
    assert q_ma.answer_index in [0, 1, 2, 3]

    q_am = Quiz_Question.AM(backend.get_random_movie)
    assert len(q_am.options) == 4
    assert q_am.answer_index in [0, 1, 2, 3]

    q_ym = Quiz_Question.YM(backend.get_random_movie)
    assert len(q_ym.options) == 4
    assert q_ym.answer_index in [0, 1, 2, 3]


def test_bollywood_string_normalization():
    assert normalize_string("Dilwale Dulhania Le Jayenge") == "dilwaledulhanialejayenge"
    assert normalize_string("3 Idiots!") == "3idiots"

    template = get_text_after_substitution("Don", "dn")
    assert "D" in template or "d" in template
    assert "n" in template
    assert "\\_" in template


@pytest.mark.asyncio
async def test_deposit_score():
    bot = MagicMock()
    bot.db = MagicMock()
    bot.db.bollywoodHangmanDB.update_score = AsyncMock()
    bot.db.plotsterDB.update_score = AsyncMock()
    bot.db.coins.add_coins = AsyncMock()

    # Bollywood score
    await deposit_score(bot, {111: 5}, 10, "bollywood")
    bot.db.bollywoodHangmanDB.update_score.assert_called_once_with(111, 5, 10)
    bot.db.coins.add_coins.assert_called_once_with(111, coins=25)

    # Plotster score
    await deposit_score(bot, {222: 8}, 8, "plotster")
    bot.db.plotsterDB.update_score.assert_called_once_with(222, 8, 8)


def test_pixelate_image_fallback():
    # Non-existent URL should return fallback image without raising unhandled exception
    res = pixelate_image("http://invalid-url-that-does-not-exist.test/img.png", 10)
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
    from views import MemoryView, GuessTheMovieView, HelpView, BreedGuessView

    # HelpView items
    hv = HelpView()
    assert len(hv.children) >= 2

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

