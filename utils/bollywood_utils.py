from runtime import react, run_blocking, http_session, read_limited
import re
import html
import requests
import random
import csv
from functools import lru_cache
import os
from pathlib import Path
import asyncio
import datetime
import discord
from io import BytesIO
from discord.ext import commands
from PIL import Image, ImageDraw
from rapidfuzz import fuzz
from functions import write_caption_on_image, write_text_on_image
from views import HintsView, PlotsterView, QuizsterView, GameLobbyView

IMAGE_ROOT = Path(__file__).resolve().parents[1] / "imgs"
GAME_ART_DIRS = {
    "bollywood": IMAGE_ROOT / "bollywood_scenes",
    "hollywood": IMAGE_ROOT / "hollywood",
}
PLOTSTER_ART_DIR = IMAGE_ROOT / "plotster"
POSTER_ART_DIR = IMAGE_ROOT / "poster_scenes"


def random_game_art(game_type="bollywood"):
    """Choose a themed Pippo film-night scene, with the old art as fallback."""
    art_dir = GAME_ART_DIRS.get(game_type, GAME_ART_DIRS["bollywood"])
    scenes = sorted((*art_dir.glob("scene_*.webp"), *art_dir.glob("scene_*.png")))
    if scenes:
        return random.choice(scenes)
    if game_type == "hollywood":
        bollywood_scenes = sorted(GAME_ART_DIRS["bollywood"].glob("scene_*.webp"))
        if bollywood_scenes:
            return random.choice(bollywood_scenes)
    return IMAGE_ROOT / "b0.webp"


def random_plotster_art():
    scenes = sorted((*PLOTSTER_ART_DIR.glob("scene_*.png"), *PLOTSTER_ART_DIR.glob("scene_*.webp")))
    if scenes:
        return random.choice(scenes)
    return random_game_art("bollywood")


def random_poster_art():
    scenes = sorted(POSTER_ART_DIR.glob("scene_*.jpg"))
    if scenes:
        return random.choice(scenes)
    return random_plotster_art()

def return_folders_from_mode(mode):
    if mode == "bollywood":
        folders = ["data/bollywood/"]
    elif mode == "hollywood":
        folders = ["data/hollywood/"]
    elif mode == "mix":
        folders = ["data/bollywood/", "data/hollywood/"]
    return folders

class Quiz_Question:
    """Build a four-choice quiz question from usable movie metadata."""

    def __init__(self, get_movie, type_of_question: str):
        self.get_movie = get_movie
        self.type_of_question = type_of_question

    @staticmethod
    def actors(movie):
        return [name.strip() for name in (movie.get("actors") or "").split("|") if name.strip()]

    @staticmethod
    def release_year(movie):
        for value in (movie.get("datePublished"), movie.get("year")):
            match = re.search(r"(?:19|20)\d{2}", str(value or ""))
            if match:
                return int(match.group())
        return None

    def pick_movie(self, predicate=lambda _movie: True):
        # get_movie_plotster draws without replacement and reloads when its deck
        # is empty. Bound the search so sparse year ranges fail with a clear error.
        for _ in range(100):
            movie = self.get_movie()
            is_movie = not movie.get("type") or str(movie["type"]).casefold() == "movie"
            if is_movie and predicate(movie):
                return movie
        raise commands.BadArgument("There isn't enough cast or release-year data for a Quizster question in that range.")

    @staticmethod
    def finish(question, answer, distractors, movie, hint):
        choices = list(dict.fromkeys([str(answer), *(str(item) for item in distractors if str(item) != str(answer))]))
        if len(choices) < 2:
            raise commands.BadArgument("There isn't enough distinct movie data to build a Quizster question.")
        random.shuffle(choices)
        question.options = choices[:4]
        question.answer = str(answer)
        question.answer_index = question.options.index(str(answer))
        question.movie = movie
        question.hint = hint
        return question

    def return_question(self):
        if self.type_of_question == "MA":
            return self.movie_from_actor()
        if self.type_of_question == "AM":
            return self.actor_from_movie()
        if self.type_of_question == "YM":
            return self.year_from_movie()
        raise ValueError(f"Unknown Quizster question type: {self.type_of_question}")

    # Keep the original constructors available while sharing the validated logic.
    class MA:
        def __init__(self, get_movie):
            self.__dict__.update(Quiz_Question(get_movie, "MA").return_question().__dict__)

    class AM:
        def __init__(self, get_movie):
            self.__dict__.update(Quiz_Question(get_movie, "AM").return_question().__dict__)

    class YM:
        def __init__(self, get_movie):
            self.__dict__.update(Quiz_Question(get_movie, "YM").return_question().__dict__)

    def movie_from_actor(self):
        movie = self.pick_movie(lambda item: bool(self.actors(item)))
        actor = random.choice(self.actors(movie)[:2])
        distractors = []
        for _ in range(40):
            candidate = self.pick_movie(
                lambda item: item["name"] != movie["name"]
                and bool(self.actors(item))
                and actor.casefold() not in [a.casefold() for a in self.actors(item)]
            )
            distractors.append(candidate["name"])
            if len(distractors) == 3:
                break
        question = type("QuizQuestionData", (), {})()
        question.question = random.choice([
            f"Which movie featured **{actor}**?",
            f"**{actor}** appeared in which of these films?",
            f"Pick the movie that starred **{actor}**.",
        ])
        hint = f"Clue: the movie was released in {self.release_year(movie) or 'an unlisted year'} and its genre is {movie.get('genre') or 'not listed'}."
        return self.finish(question, movie["name"], distractors, movie, hint)

    def actor_from_movie(self):
        movie = self.pick_movie(lambda item: bool(self.actors(item)))
        cast = self.actors(movie)
        answer = random.choice(cast[:2])
        excluded = {name.casefold() for name in cast}
        distractors = []
        for _ in range(50):
            candidate = self.pick_movie()
            for actor in self.actors(candidate):
                if actor.casefold() not in excluded and actor.casefold() not in {a.casefold() for a in distractors}:
                    distractors.append(actor)
                    break
            if len(distractors) == 3:
                break
        question = type("QuizQuestionData", (), {})()
        question.question = random.choice([
            f"Which actor appeared in **{movie['name']}**?",
            f"Who was part of the cast of **{movie['name']}**?",
            f"Choose an actor who starred in **{movie['name']}**.",
        ])
        hint = f"Clue: **{movie['name']}** is a {movie.get('genre') or 'genre not listed'} film, released in {self.release_year(movie) or 'an unlisted year'}."
        return self.finish(question, answer, distractors, movie, hint)

    def year_from_movie(self):
        movie = self.pick_movie(lambda item: self.release_year(item) is not None)
        year = self.release_year(movie)
        distractors = set()
        while len(distractors) < 3:
            offset = random.choice([n for n in range(-8, 9) if n])
            candidate = year + offset
            if 1900 <= candidate <= datetime.datetime.now().year + 1:
                distractors.add(candidate)
        question = type("QuizQuestionData", (), {})()
        question.question = random.choice([
            f"In which year was **{movie['name']}** released?",
            f"When did **{movie['name']}** reach cinemas?",
            f"Choose the release year for **{movie['name']}**.",
        ])
        cast = ", ".join(self.actors(movie)[:2]) or "the movie's cast"
        hint = f"Clue: the film features {cast} and belongs to {movie.get('genre') or 'an unlisted genre'}."
        return self.finish(question, year, list(distractors), movie, hint)

@lru_cache(maxsize=128)
def _movie_csv_rows(filename, modified_ns):
    with open(filename, newline="", encoding="utf-8") as source:
        return tuple(tuple(row.items()) for row in csv.DictReader(source))


class Bollywood_backend():
    QUIZ_TYPES = ["MA", "AM", "YM"]  #, "GM", "DM"]

    def __init__(self, starting_year, ending_year, difficulty="easy", folders=["data/bollywood/"]):
        self.folders = folders
        if starting_year < 1980:
            starting_year = 1980
        if ending_year < starting_year:
            raise commands.BadArgument("The ending year must not precede the starting year.")
        latest_year = discord.utils.utcnow().year + 1
        if ending_year > latest_year:
            raise commands.BadArgument(f"The ending year cannot be later than {latest_year}.")
        self.starting_year = starting_year
        self.ending_year = ending_year
        self.difficulty = difficulty

        self.variables_for_difficulty = {
            'easy': {
                'questions_to_read_from_each_year': 30,
                'tries': 10,
                'random_letter': True,
                'actors': True,
                'synopsis': True
            },
            'normal': {
                'questions_to_read_from_each_year': 50,
                'tries': 7,
                'random_letter': True,
                'actors': True,
                'synopsis': True
            }
        }
        self.done = []
        self.load_movies()

    def load_movies(self):
        self.movies = []
        starting_year = self.starting_year
        while starting_year <= self.ending_year:
            self.movies = self.movies + (self.read_movies(
                starting_year, self.variables_for_difficulty[self.difficulty]
                ['questions_to_read_from_each_year']))
            starting_year += 1
        if not self.movies:
            raise commands.BadArgument("No movie data is available for that year range.")

    def get_random_movie(self):
        i = random.choice(self.movies)
        return i



    def get_movie_plotster(self):
        if not self.movies:
            self.load_movies()
        def eligible_movies():
            return [
                movie for movie in self.movies
                if (movie.get("type") or "").casefold() == "movie"
                and ((movie.get("description") or "").strip() or (movie.get("keywords") or "").strip())
            ]

        candidates = eligible_movies()
        if not candidates:
            self.load_movies()
            candidates = eligible_movies()
        if not candidates:
            raise commands.BadArgument("No playable movie clues are available for that year range.")
        movie = random.choice(candidates)
        self.movies.remove(movie)
        return {key: html.unescape(value) if isinstance(value, str) else value for key, value in movie.items()}

    def get_quiz_question(self, type_of_question=None, difficulty="easy"):
        """Get an object suitable for the quiz question"""

        # Types of questions:
        ## 1. Movie from Actor: "MA"
        ## 2. Actor from Movie: "AM"
        ## 3. Genre of the movie: "GM"
        ## 4. Year of release: "YM"
        ## 5. Director of the movie: "DM"

        # Selecting a random type of question if the user has not provided one.
        #QUIZ_TYPES = ["MA", "AM", "YM"]  #, "GM", "DM"]
        weights = [40, 40, 20]
        if type_of_question is None:
            type_of_question = random.choices(self.QUIZ_TYPES, weights=weights)[0]

        # Fetching a movie question using the custom Quiz_Question class
        movie = Quiz_Question(
            self.get_movie_plotster,
            type_of_question=type_of_question).return_question()
        return movie

    def read_movies(self, year, n):
        movies = []
        for i in self.folders:
            path = Path(i) / f"{year}_data.csv"
            if path.is_file():
                movies.extend(self.read_csv(path)[:n])
        #movies = self.read_csv(f"{self.folder}{year}_data.csv")[:n]
        return movies

    def read_csv(self, filename):
        path = Path(filename).resolve()
        return [dict(row) for row in _movie_csv_rows(str(path), path.stat().st_mtime_ns)]


def check(ctx, message, solo_user_id=None):
    # Check if the message is from the same channel as the command
    return message.channel == ctx.channel and (solo_user_id is None or message.author.id == solo_user_id)

def get_text_after_substitution(movie_name, characters_to_exclude="", escape=True):
    """Hide unguessed letters while keeping already guessed letters visible."""
    revealed = {character.casefold() for character in characters_to_exclude if character.isalpha()}
    output = []
    for character in str(movie_name):
        if character.isalpha() and character.casefold() not in revealed:
            output.append(r"\_" if escape else "_")
        else:
            output.append(character)
    return "".join(output)

def correct_answer_embed(movie, correct=True):
    title = "You got the correct answer!" if correct else "The answer was:"
    desc = (
        f"Title: **{movie.get('name') or 'Unknown'}**\n"
        f"Type: {movie.get('type') or 'Movie'}\n"
        f"Genre: **{movie.get('genre') or 'Not listed'}**\n"
        f"Release date: {movie.get('datePublished') or 'Not listed'}\n"
        f"Cast: {movie.get('actors') or 'Not listed'}"
    )
    source_url = movie.get("url") or ""
    embed_options = {"url": source_url} if source_url.startswith(("https://", "http://")) else {}
    emb = discord.Embed(title=title, description=desc, **embed_options)
    poster_url = movie.get("poster_url") or ""
    if poster_url.startswith(("https://", "http://")):
        emb.set_image(url=poster_url)
    return emb

def guess_embed(movie, characters_to_exclude, persons, lives, tries,
                roundd, hints_obj=None, missed_letters=None, artwork_path=None,
                title_color=None, underscore_color="black"):
    movie_name = movie['name']
    # Create an embed message for the current guess state
    if len(persons) >= 1:
        persons_str = ""
        for i in persons:
            persons_str += f"<@{i}>: {persons[i]}\n"
    else:
        persons_str = ""
    color = discord.Color.from_str("#FAEBC0")
    color2 = discord.Color.from_str("#938448")
    missed_letters = missed_letters or set()
    lives_display = "❤️" * lives + "🖤" * max(0, 3 - lives)
    missed_display = ", ".join(sorted(letter.upper() for letter in missed_letters)) or "none"
    desc = (
        f"{get_text_after_substitution(movie['name'], characters_to_exclude)}\n"
        f"{persons_str}\nLives: {lives_display}\nTries: **{tries}/9**\n"
        f"Misses: {missed_display}"
    )
    emb = discord.Embed(description=desc, color=color2)
    emb2 = discord.Embed(title=f"Round: {roundd+1}", color=color)
    font_list = [str(Path(__file__).resolve().parents[1] / 'darling_coffee.ttf')]
    color_list = [title_color or random.choice(['#61451C', '#7A301D', '#31566B', '#4E6B3B'])]
    artwork_path = artwork_path or random_game_art()
    image = write_text_on_image(
        str(artwork_path),
        get_text_after_substitution(movie_name, characters_to_exclude, escape=False),
        font_list, color_list, start_location=(200, 200), underscore_color=underscore_color,
    )
    emb2.set_image(url=f"attachment://boll.jpg")
    return emb, emb2, image

def game_start_embed(game_type, help_mode=False):
    # Create an embed message for the game start
    if game_type == "bollywood":
        title = "Hangman but Bollywood?"
    elif game_type == "hollywood":
        title = "Hangman but Hollywood?"
    description = "Guess one letter at a time. You get **9 tries per movie** and **3 lives** for the game.\nCorrect letters earn individual points. Duplicate guesses do not cost a try."
    if game_type == "hollywood":
        description += " Send `title: <answer>` for a whole-title shot worth **3 bonus points**; a wrong title shot costs 2 tries."
    description += "\n\nHints: cast costs 1 try · revealed letter costs 2 tries · synopsis costs 5 tries."
    if not help_mode:
        description += "\n\n**STARTING IN 5 SECONDS.**"

    embed = discord.Embed(
        title=title,
        description=description,
        color=discord.Color.from_str("#1F2410"))
    artwork = random_game_art(game_type)
    filename = "pippo_film_night.jpg"
    embed.set_image(url=f"attachment://{filename}")
    return embed, write_caption_on_image(artwork, embed.title, embed.description, filename)

def game_over_embed(persons, score, game_type):
    # Create an embed message for game over
    if len(persons) >= 1:
        persons_str = ""
        for i in persons:
            persons_str += f"<@{i}>: {persons[i]}\n"
    else:
        persons_str = ""
    description = f"You solved **{score}** {'movie' if score == 1 else 'movies'}!\n\n{persons_str}"
    embed = discord.Embed(
        title="Game Over!",
        description=description,
        color=discord.Color.from_str("#D01819"))
    embed.set_footer(text="Run /play to start another game.")
    artwork = random_game_art(game_type)
    filename = "pippo_film_night.jpg"
    embed.set_image(url=f"attachment://{filename}")
    return embed, write_caption_on_image(artwork, embed.title, embed.description, filename)

async def deposit_score(bot, persons, score, game_type="bollywood"):
    # Update the score for each player in the database
    if not hasattr(bot, 'db') or not bot.db:
        return
    for i in persons:
        try:
            await bot.db.award_movie_score(i, persons[i], score, game_type)
        except Exception as e:
            print(f"Error depositing score: {e}")


def normalize_movie_title(value):
    return re.sub(r"[^a-z0-9]", "", value.casefold())


async def play_game(ctx, bot, game_type, starting_year, ending_year, folders, timeout=60, solo=False):
    # Initialize the Bollywood backend with the specified year range and data folder
    bollywood_backend = await run_blocking(Bollywood_backend, starting_year, ending_year, folders=folders)
    playable_movies = [
        movie for movie in bollywood_backend.movies
        if re.search(r"[A-Za-z]", movie.get("name", ""))
        and (game_type != "hollywood" or (movie.get("type") or "").casefold() == "movie")
    ]
    if not playable_movies:
        if game_type == "hollywood":
            raise commands.BadArgument("No Hollywood movie titles are available for that year range.")
        raise commands.BadArgument("No titles with English letters are available for that year range.")
    movie_deck = []

    def draw_movie():
        if not movie_deck:
            movie_deck.extend(playable_movies)
            random.shuffle(movie_deck)
        return movie_deck.pop()

    timeout = max(5, min(int(timeout), 120))
    lives = 3

    regex = "[A-Za-z]"  # Regex pattern for matching alphabetic characters

    score = 0
    round_number = 0
    persons = {}
    # Embed before the game starts, containing the help message
    start_embed, start_image = await run_blocking(game_start_embed, game_type)
    start_embed.description += "\n\n" + ("Solo game: only your guesses and hint buttons count." if solo else "Everyone in this channel can guess.")
    await ctx.send(embed=start_embed, file=start_image)
    await asyncio.sleep(5) # Time to read the help message
    prefix = await bot.get_prefixx(bot, ctx.message)
    while lives != 0:
        hints_obj = HintsView()
        hints_obj.author_id = ctx.author.id if solo else None
        ctx._active_game_view = hints_obj
        round_number += 1
        hints_obj.tries = 9
        hints_obj.reset()
        movie = draw_movie()
        movie_name = movie['name']
        answer = set(re.findall(regex, movie_name.lower()))
        revealed_letters = set()
        missed_letters = set()
        artwork_path = random_game_art(game_type)
        title_colors = ['#FFF1C2', '#FFFFFF', '#FFD166'] if game_type == "hollywood" else ['#61451C', '#7A301D', '#31566B', '#4E6B3B']
        title_color = random.choice(title_colors)
        hints_obj.answer_letters = answer
        hints_obj.revealed_letters = revealed_letters
        counter = 0
        hints_obj.hint = f"Cast: **{movie.get('actors') or 'Cast details unavailable'}**"
        hints_obj.synopsis = movie.get('description') or "No synopsis is available for this title."
        while hints_obj.tries > 0:
            if answer.issubset(revealed_letters):
                await ctx.send(embed=correct_answer_embed(movie))
                await asyncio.sleep(1)
                score += 1
                break
            embed, embed_pic, image = await run_blocking(
                guess_embed, movie, "".join(sorted(revealed_letters)), persons,
                lives, hints_obj.tries, round_number - 1, hints_obj=hints_obj,
                missed_letters=missed_letters, artwork_path=artwork_path,
                title_color=title_color,
                underscore_color="#FFF1C2" if game_type == "hollywood" else "black",
            )
            if counter % 5 == 0:
                current_msg = await ctx.send(embeds=(embed_pic,
                                                            embed),
                                                    view=hints_obj, file=image)
                hints_obj.out = current_msg

                async def refresh_puzzle():
                    updated = await run_blocking(
                        guess_embed, movie, "".join(sorted(revealed_letters)),
                        persons, lives, hints_obj.tries, round_number - 1,
                        hints_obj=hints_obj, missed_letters=missed_letters,
                        artwork_path=artwork_path, title_color=title_color,
                        underscore_color="#FFF1C2" if game_type == "hollywood" else "black",
                    )
                    await current_msg.edit(
                        embeds=(updated[1], updated[0]), attachments=[updated[2]], view=hints_obj
                    )

                hints_obj.refresh_puzzle = refresh_puzzle
            else:
                await current_msg.edit(embeds=(embed_pic, embed), attachments=[image])
            counter += 1

            try:
                msg = await bot.wait_for('message',
                                            check=lambda m: not m.author.bot and check(ctx, m, ctx.author.id if solo else None)
                                            and (len(m.content) == 1 or m.content.casefold() in {f"{prefix}exit", f"{prefix}end"}
                                                 or (game_type == "hollywood" and m.content.casefold().startswith("title:"))),
                                            timeout=timeout)
            except asyncio.exceptions.TimeoutError:
                await hints_obj.finish()
                await ctx.send("Looks like you didn't wanna play...")
                await ctx.send(embed=correct_answer_embed(movie, correct=False))
                try:
                    await deposit_score(bot, persons, score, game_type)
                except:
                    pass
                return

            prefix = await bot.get_prefixx(bot, ctx.message)
            if msg.content.lower() in [f"{prefix}exit", f"{prefix}end"]:
                await hints_obj.finish()
                await ctx.send("Exiting...")
                try:
                    await deposit_score(bot, persons, score, game_type)
                except:
                    pass
                return
            guess = msg.content.lower()
            if len(msg.content) == 1 and guess in revealed_letters | missed_letters:
                await react(msg, "🔁")
                continue
            if len(msg.content) == 1 and not guess.isalpha():
                await react(msg, "❔")
                continue
            if game_type == "hollywood" and msg.content.casefold().startswith("title:"):
                title_guess = msg.content.partition(":")[2].strip()
                if not title_guess:
                    await react(msg, "❔")
                    continue
                if normalize_movie_title(title_guess) == normalize_movie_title(movie_name):
                    persons[msg.author.id] = persons.get(msg.author.id, 0) + 3
                    await react(msg, "✅")
                    await ctx.send(embed=correct_answer_embed(movie))
                    await asyncio.sleep(1)
                    score += 1
                    break
                hints_obj.tries = max(0, hints_obj.tries - 2)
                await react(msg, "❌")
                if hints_obj.tries == 0:
                    await ctx.send(embed=correct_answer_embed(movie, correct=False))
                    await asyncio.sleep(3)
                    lives -= 1
                    continue
                continue
            if len(msg.content) > 1:
                continue
            if len(msg.content) == 1 and guess in answer:
                # Update individual scores
                await react(msg, "\U00002705")
                try:
                    persons[msg.author.id] += 1
                except:
                    persons[msg.author.id] = 1

                revealed_letters.add(guess)
                # Check whether every distinct title letter has been revealed.
                if answer.issubset(revealed_letters):
                    await ctx.send(embed=correct_answer_embed(movie))
                    await asyncio.sleep(3)
                    score += 1
                    break
            elif len(msg.content) == 1 and guess not in answer:
                missed_letters.add(guess)
                hints_obj.tries -= 1
                await react(msg, "\U0000274C")

            if hints_obj.tries == 0:
                await ctx.send(embed=correct_answer_embed(movie, correct=False))
                await asyncio.sleep(3)
                lives -= 1
                continue
        await hints_obj.finish()
    end_embed, end_image = await run_blocking(game_over_embed, persons, score, game_type)
    await ctx.send(embed=end_embed, file=end_image)
    await deposit_score(bot, persons, score, game_type)


"""
Poster pixelate
"""
def pixelate_image(image_url, pixel_size, source_image=None):
    """Return a progressively clearer poster image as a Discord attachment."""
    try:
        if source_image is None:
            response = requests.get(image_url, timeout=(5, 12), headers={"User-Agent": "PippoBot/1.0"})
            if response.status_code != 200:
                raise ValueError(f"poster request returned HTTP {response.status_code}")
            if len(response.content) > 15_000_000:
                raise ValueError("poster image exceeds the 15 MB download limit")
            with Image.open(BytesIO(response.content)) as opened:
                image = opened.convert("RGB")
        else:
            image = source_image.copy().convert("RGB")

        image.thumbnail((1400, 1400), Image.Resampling.LANCZOS)
        width, height = image.size
        block_size = max(1, int(pixel_size))
        reduced_size = (max(1, width // block_size), max(1, height // block_size))
        image = image.resize(reduced_size, Image.Resampling.BILINEAR)
        image = image.resize((width, height), Image.Resampling.NEAREST)
    except Exception as error:
        print(f"Could not load a movie poster for pixelation: {type(error).__name__}")
        image = Image.new("RGB", (720, 1000), color=(45, 37, 76))
        # A visible fallback keeps the game usable if a catalogue poster is offline.
        for y in range(0, 1000, 100):
            for x in range(0, 720, 90):
                shade = (63, 49, 104) if (x // 90 + y // 100) % 2 else (105, 64, 114)
                ImageDraw.Draw(image).rectangle((x, y, x + 89, y + 99), fill=shade)

    output = BytesIO()
    image.save(output, format="JPEG", optimize=True, quality=78)
    return discord.File(BytesIO(output.getvalue()), filename="pixelate_img.jpg")


def load_poster_image(image_url):
    """Fetch a poster once per title; each reveal step reuses this decoded image."""
    response = requests.get(image_url, timeout=(5, 12), headers={"User-Agent": "PippoBot/1.0"})
    response.raise_for_status()
    if len(response.content) > 15_000_000:
        raise ValueError("poster image exceeds the 15 MB download limit")
    with Image.open(BytesIO(response.content)) as image:
        image.load()
        return image.convert("RGB")


def _decode_poster(data):
    with Image.open(BytesIO(data)) as source:
        if source.width * source.height > 20_000_000:
            raise ValueError("Poster exceeds the pixel limit")
        source.thumbnail((1400, 1400), Image.Resampling.LANCZOS)
        return source.convert("RGB")


async def fetch_poster_image(bot, image_url):
    # Network waits use pooled asynchronous connections, leaving media workers for CPU work.
    async with http_session(bot) as session:
        async with session.get(image_url, timeout=15, max_redirects=3) as response:
            response.raise_for_status()
            data = await read_limited(response, 15_000_000)
    return await run_blocking(_decode_poster, data)


def pixelate_game_start_embed(help_mode=False, solo=False, mode="bollywood"):
    mode_label = {"bollywood": "Bollywood", "hollywood": "Hollywood", "mix": "Mixed"}.get(mode, "Movie")
    description = (
        "Name the movie from its poster. Each miss or timeout clears another pixel layer; "
        "you get six chances per poster. Earlier answers score more.\n\n"
        "You have **3 shared lives**. Miss all six reveals and the team loses one life. "
        "Three correct posters in a row by one player earn **+2 bonus points and one life** (up to 3)."
    )
    if solo:
        description += "\n\n**Solo mode:** only your guesses count."
    else:
        description += "\n\n**Movie night:** anyone in this channel can guess."
    if not help_mode:
        description += "\n\nSend `exit` at any time to end the game."
    embed = discord.Embed(
        title=f"🎬 {mode_label} Poster Decoder",
        description=description,
        color=discord.Color.from_rgb(53, 41, 94),
    )
    artwork = random_poster_art()
    filename = "pippo_poster.jpg"
    embed.set_image(url=f"attachment://{filename}")
    return embed, write_caption_on_image(artwork, embed.title, embed.description, filename)


def pixelate_guess_embed(movie, scores, lives, round_number, stage_number, max_points, streaks,
                         source_image, feedback=""):
    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)[:8]
    scoreboard = "\n".join(f"<@{user_id}> · **{points} pts**" for user_id, points in ranked) or "No points yet"
    current_streak = max(streaks.values(), default=0)
    description = (
        f"**Lives:** {'❤️' * lives}{'🖤' * (3 - lives)}\n"
        f"**Solve now:** +{max_points} point{'s' if max_points != 1 else ''}\n"
        f"**Best streak:** {current_streak}/3\n\n{scoreboard}"
    )
    status = discord.Embed(description=description, color=discord.Color.from_rgb(94, 68, 134))
    status.set_footer(text=feedback or "Miss or wait for the timer to reveal more of the poster.")
    poster = discord.Embed(
        title=f"Poster {round_number} · Reveal {stage_number}/6",
        color=discord.Color.from_rgb(255, 214, 112),
    )
    image = pixelate_image(
        movie.get("poster_url", ""), [96, 72, 52, 36, 24, 12][stage_number - 1],
        source_image=source_image,
    )
    poster.set_image(url="attachment://pixelate_img.jpg")
    return status, poster, image


def pixelate_game_over_embed(scores, solved, lives, reason="Game over"):
    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    score_text = "\n".join(f"<@{user_id}> — **{points} points**" for user_id, points in ranked[:10]) or "No points scored."
    embed = discord.Embed(
        title="🎞️ Movie night complete",
        description=f"{reason}\nPosters solved: **{solved}** · Lives left: **{lives}**\n\n{score_text}",
        color=discord.Color.gold(),
    )
    embed.set_footer(text="Run /poster to play again.")
    artwork = random_poster_art()
    filename = "pippo_poster_end.jpg"
    embed.set_image(url=f"attachment://{filename}")
    return embed, write_caption_on_image(artwork, embed.title, embed.description, filename)


def normalize_string(value):
    return re.sub(r"[^a-z0-9]", "", str(value).casefold())


def compare_movie_name(movie_name, guess):
    target = normalize_string(movie_name)
    candidate = normalize_string(guess)
    if not target or not candidate:
        return False
    return target == candidate or fuzz.ratio(target, candidate) >= 90


async def play_pixelate(ctx, bot, mode, starting_year, ending_year, timeout=60, solo=False):
    mode = str(mode).casefold()
    folders = return_folders_from_mode(mode)
    timeout = max(5, min(int(timeout), 60))
    backend = await run_blocking(Bollywood_backend, starting_year, ending_year, folders=folders)
    movie_pool = [
        movie for movie in backend.movies
        if (movie.get("type") or "").casefold() == "movie"
        and re.search(r"[A-Za-z]", movie.get("name") or "")
        and (movie.get("poster_url") or "").startswith(("https://", "http://"))
    ]
    if not movie_pool:
        raise commands.BadArgument("No movie posters are available for that mode and year range.")

    lives = 3
    solved = 0
    scores = {}
    streaks = {}
    failed_posters = set()
    deck = []
    poster_round = 0
    start_embed, start_file = await run_blocking(pixelate_game_start_embed, solo=solo, mode=mode)
    await ctx.send(embed=start_embed, file=start_file)
    await asyncio.sleep(3)

    current_msg = None
    ended_by_player = False
    while lives > 0:
        if not deck:
            deck = [movie for movie in movie_pool if movie.get("poster_url") not in failed_posters]
            random.shuffle(deck)
        if not deck:
            await ctx.send("I couldn't load the available movie posters, so this game has to stop.")
            break

        movie = deck.pop()
        try:
            poster_image = await fetch_poster_image(bot, movie["poster_url"])
        except Exception as error:
            failed_posters.add(movie.get("poster_url"))
            print(f"Skipping an unavailable movie poster: {type(error).__name__}")
            continue

        poster_round += 1
        solved_this_poster = False
        feedback = ""
        for stage_index in range(6):
            stage_number = stage_index + 1
            points_available = 6 - stage_index
            # Poster rounds count misses too; solved counts only correct titles.
            status, poster_embed, image = await run_blocking(
                pixelate_guess_embed, movie, scores, lives, poster_round,
                stage_number, points_available, streaks, poster_image, feedback,
            )
            if current_msg is None:
                current_msg = await ctx.send(embeds=(poster_embed, status), file=image)
            else:
                await current_msg.edit(embeds=(poster_embed, status), attachments=[image])

            try:
                guess_message = await bot.wait_for(
                    "message",
                    check=lambda message: not message.author.bot and check(ctx, message, ctx.author.id if solo else None),
                    timeout=timeout,
                )
            except asyncio.TimeoutError:
                feedback = "⏳ Time's up — the poster is clearer now."
                continue

            guess = guess_message.content.strip()
            prefix = getattr(ctx, "prefix", ".") or "."
            if guess.casefold() in {"exit", "end", f"{prefix}exit".casefold(), f"{prefix}end".casefold()}:
                ended_by_player = True
                break
            if not compare_movie_name(movie.get("name", ""), guess):
                feedback = ""
                try:
                    await react(guess_message, "❌")
                except discord.HTTPException:
                    pass
                continue

            user_id = guess_message.author.id
            try:
                await react(guess_message, "✅")
            except discord.HTTPException:
                pass
            scores[user_id] = scores.get(user_id, 0) + points_available
            streaks[user_id] = streaks.get(user_id, 0) + 1
            bonus = 0
            if streaks[user_id] >= 3:
                bonus = 2
                scores[user_id] += bonus
                streaks[user_id] = 0
                if lives < 3:
                    lives += 1
            solved += 1
            await asyncio.sleep(2)
            solved_this_poster = True
            break

        if ended_by_player:
            break
        if not solved_this_poster:
            lives -= 1
            streaks.clear()
            await ctx.send(embed=correct_answer_embed(movie, correct=False))
            await ctx.send(f"💔 The team lost a life. **{lives}** {'life' if lives == 1 else 'lives'} left.")
        if lives > 0:
            await asyncio.sleep(1)

    reason = "You ended the game." if ended_by_player else "The team ran out of lives." if lives == 0 else "Game stopped."
    end_embed, end_file = pixelate_game_over_embed(scores, solved, lives, reason)
    await ctx.send(embed=end_embed, file=end_file)
    if scores:
        await deposit_score(bot, scores, solved, "bollywood")


"""
Plotster
"""

def fuzzy_match(word, word_list):
    ratios = [fuzz.ratio(word, w.lower()) for w in word_list]
    best_ratio = max(ratios)
    if best_ratio >= 90:
        return word_list[ratios.index(best_ratio)]
    return ""

def convert_movie_to_sendable(movie_name, words_guessed):

    def func(mov):
        return r"\_" * len(mov.group(0))

    if len(words_guessed) != 0:
        regex = r"\b(?!{}\b)([a-zA-Z])+\b".format(
            '|'.join(words_guessed))
        movie = re.sub(regex, func, movie_name, flags=re.IGNORECASE)
    else:
        regex = r"[A-Za-z]"
        movie = re.sub(regex, r"\_", movie_name)

    return movie

def get_answer(movie):
    regex = "[a-zA-Z]+"
    words = re.findall(regex, movie)

    return set(words)

def plotster_keywords(movie):
    title_words = set(re.findall(r"[a-z0-9]+", html.unescape(movie.get("name", "")).casefold()))
    keywords = []
    seen = set()
    for keyword in (movie.get("keywords") or "").split(","):
        keyword = html.unescape(keyword).strip()
        normalized = normalize_string(keyword)
        if normalized and normalized not in seen and not any(word in normalized for word in title_words if len(word) > 2):
            keywords.append(keyword)
            seen.add(normalized)
    if not keywords:
        for genre in (movie.get("genre") or "").split("|"):
            genre = genre.strip()
            if genre and normalize_string(genre) not in seen:
                keywords.append(genre)
                seen.add(normalize_string(genre))
    random.shuffle(keywords)
    return keywords


def plotster_game_start_embed(help_mode=False):
    description = (
        "Solve each movie mystery from a short keyword ladder. You get **3 guesses per title** and **3 lives** for the game; "
        "each wrong guess reveals another keyword. A correct answer earns up to **6 points**: wrong guesses and hints lower the reward.\n\n"
        "Reveal cast or film details for 1 point, or the full plot for 2. Each hint button works once per title. "
        "Use `skip` to give up on a title, or `exit` to end the game."
    )
    if not help_mode:
        description += "\n\n**MYSTERY STARTS IN 5 SECONDS.**"
    embed = discord.Embed(title="Plotster: Pippo's Movie Mystery", description=description,
                          color=discord.Color.from_str("#1F2410"))
    artwork = random_plotster_art()
    filename = "plotster.jpg"
    embed.set_image(url=f"attachment://{filename}")
    return embed, write_caption_on_image(artwork, embed.title, embed.description, filename)


def plotster_guess_embed(movie, persons, lives, round_number, time_left,
                         revealed_keywords, guesses_left, hint_cost, artwork):
    persons_str = "\n".join(f"<@{user_id}>: {points}" for user_id, points in persons.items()) or "No points yet"
    clues = "\n".join(f"• {keyword}" for keyword in revealed_keywords) or "No keywords available yet"
    max_points = max(1, 3 + guesses_left - hint_cost)
    lives_display = "❤️" * lives + "🖤" * (3 - lives)
    desc = (
        f"**Movie clues**\n{clues}\n\n"
        f"Guesses left: **{guesses_left}/3** · Game lives: {lives_display}\n"
        f"Solve now for up to **{max_points} points**.\n\n**Players**\n{persons_str}"
    )
    embed = discord.Embed(description=desc, color=discord.Color.from_str("#203B55"))
    embed.set_footer(text=f"Time left: {max(0, time_left):.0f}s · Wrong guesses reveal more keywords")
    frame = discord.Embed(title=f"Mystery {round_number} · Plotster", color=discord.Color.from_str("#F6C968"))
    filename = "plotster_clue.jpg"
    frame.set_image(url=f"attachment://{filename}")
    return embed, frame, write_caption_on_image(artwork, frame.title, desc, filename)


def plotster_game_over_embed(persons, score):
    players = "\n".join(f"<@{user_id}>: **{points} points**" for user_id, points in persons.items()) or "No movie points this run."
    embed = discord.Embed(
        title="Mystery Night Over",
        description=f"You solved **{score}** {'movie' if score == 1 else 'movies'}.\n\n{players}",
        color=discord.Color.from_str("#D01819"),
    )
    embed.set_footer(text="Run /play to start another movie game.")
    artwork = random_plotster_art()
    filename = "plotster.jpg"
    embed.set_image(url=f"attachment://{filename}")
    return embed, write_caption_on_image(artwork, embed.title, embed.description, filename)


async def play_plotster(ctx, bot, mode, starting_year, ending_year, timeout=60, solo=False):
    game_type = "plotster"
    timeout = max(10, min(timeout, 120))
    folders = return_folders_from_mode(mode)
    backend = await run_blocking(Bollywood_backend, starting_year, ending_year, folders=folders)
    next_movie = await run_blocking(backend.get_movie_plotster)  # Validate the selected year range before starting.

    lives = 3
    score = 0
    persons = {}
    start_embed, start_image = await run_blocking(plotster_game_start_embed)
    start_embed.description += "\n\n" + ("Solo game: only your guesses and hints count." if solo else "Everyone in this channel can guess and use the shared hints.")
    await ctx.send(embed=start_embed, file=start_image)
    await asyncio.sleep(5)
    prefix = await bot.get_prefixx(bot, ctx.message)
    loop = asyncio.get_running_loop()
    round_number = 0

    while lives > 0:
        movie = next_movie if next_movie is not None else await run_blocking(backend.get_movie_plotster)
        next_movie = None
        round_number += 1
        keywords = plotster_keywords(movie)
        if not keywords:
            keywords = ["A movie mystery", "The plot is your clue"]
        revealed_keywords = keywords[:min(2, len(keywords))]
        next_keyword = len(revealed_keywords)
        guesses_left = 3
        deadline = loop.time() + timeout
        artwork = random_plotster_art()
        view = PlotsterView(movie, solo_user_id=ctx.author.id if solo else None, timeout=timeout)
        ctx._active_game_view = view
        embed, frame, art_file = await run_blocking(plotster_guess_embed,
            movie, persons, lives, round_number, timeout, revealed_keywords,
            guesses_left, view.hint_cost, artwork,
        )
        current_msg = await ctx.send(
            embeds=(frame, embed), file=art_file, view=view,
        )
        view.out = current_msg

        async def refresh_round_embed():
            remaining = deadline - loop.time()
            refreshed_embed, refreshed_frame, refreshed_art = await run_blocking(plotster_guess_embed,
                movie, persons, lives, round_number, remaining, revealed_keywords,
                guesses_left, view.hint_cost, artwork,
            )
            await current_msg.edit(
                embeds=(refreshed_frame, refreshed_embed), view=view,
                attachments=[refreshed_art],
            )

        view.refresh_embed = refresh_round_embed
        round_over = False

        while guesses_left > 0 and lives > 0 and not round_over:
            remaining = deadline - loop.time()
            if remaining <= 0:
                lives -= 1
                await view.finish()
                await ctx.send("⏱️ Time ran out. Pippo loses one life.")
                await ctx.send(embed=correct_answer_embed(movie, correct=False))
                break

            try:
                msg = await bot.wait_for(
                    "message",
                    check=lambda m: not m.author.bot and check(ctx, m, ctx.author.id if solo else None),
                    timeout=remaining,
                )
            except asyncio.TimeoutError:
                lives -= 1
                await view.finish()
                await ctx.send("⏱️ Time ran out. Pippo loses one life.")
                await ctx.send(embed=correct_answer_embed(movie, correct=False))
                break

            content = msg.content.strip()
            command = content.casefold()
            if command in {f"{prefix}exit".casefold(), f"{prefix}end".casefold(), "exit", "end"}:
                await view.finish()
                over_embed, over_image = await run_blocking(plotster_game_over_embed, persons, score)
                await ctx.send(embed=over_embed, file=over_image)
                await deposit_score(bot, persons, score, game_type)
                return
            if command in {f"{prefix}skip".casefold(), "skip"}:
                lives -= 1
                await view.finish()
                await react(msg, "⏭️")
                await ctx.send("Skipped. Pippo loses one life.")
                await ctx.send(embed=correct_answer_embed(movie, correct=False))
                break

            normalized_guess = normalize_string(content)
            if not normalized_guess:
                await react(msg, "❔")
                continue
            normalized_title = normalize_string(movie.get("name", ""))
            matched = normalized_guess == normalized_title
            if not matched and len(normalized_guess) >= 5:
                matched = fuzz.ratio(normalized_guess, normalized_title) >= 92
            if matched:
                points = max(1, 3 + guesses_left - view.hint_cost)
                persons[msg.author.id] = persons.get(msg.author.id, 0) + points
                score += 1
                await view.finish()
                await react(msg, "🎯")
                round_over = True
                continue

            guesses_left -= 1
            await react(msg, "❌")
            if next_keyword < len(keywords):
                clue = keywords[next_keyword]
                revealed_keywords.append(clue)
                next_keyword += 1


            if guesses_left == 0:
                lives -= 1
                await view.finish()
                await ctx.send("Out of guesses. Pippo loses one life.")
                await ctx.send(embed=correct_answer_embed(movie, correct=False))
                break

            remaining = deadline - loop.time()
            embed, frame, art_file = await run_blocking(plotster_guess_embed,
                movie, persons, lives, round_number, remaining, revealed_keywords,
                guesses_left, view.hint_cost, artwork,
            )
            await current_msg.edit(embeds=(frame, embed), view=view, attachments=[art_file])

    over_embed, over_image = await run_blocking(plotster_game_over_embed, persons, score)
    await ctx.send(embed=over_embed, file=over_image)
    await deposit_score(bot, persons, score, game_type)


def quizster_art_file(embed):
    scenes = sorted((IMAGE_ROOT / "quizster").glob("scene_*.png"))
    artwork = random.choice(scenes) if scenes else random_plotster_art()
    filename = "quizster.jpg"
    embed.set_image(url=f"attachment://{filename}")
    return write_caption_on_image(artwork, embed.title, embed.description, filename)


def create_question_embed(movie, round_number, mode="bollywood") -> discord.Embed:
    """Create the question and list only the choices that have buttons."""
    labels = "ABCD"
    options = "\n".join(f"{labels[index]}. {option}" for index, option in enumerate(movie.options))
    mode_label = {"bollywood": "Bollywood", "hollywood": "Hollywood", "mix": "Bollywood + Hollywood"}.get(mode, "Movies")
    embed = discord.Embed(
        title=f"{mode_label} Quiz · Round {round_number}",
        description=f"{movie.question}\n\n{options}",
        color=discord.Color.from_rgb(106, 77, 191),
    )
    embed.set_footer(text="Pick one answer. Your team has 3 lives, 3 hints, and 1 majority-vote skip.")
    return embed


def create_game_over_embed(score_dict, winner_id=None, solo=False) -> discord.Embed:
    """Show the final standings, including a best score when nobody survives."""
    ranked = sorted(score_dict.items(), key=lambda item: (item[1][1], item[1][0]), reverse=True)
    standings = "\n".join(
        f"**{index}.** <@{user_id}> — **{values[1]} pts**, {values[0]} {'life' if values[0] == 1 else 'lives'} left"
        for index, (user_id, values) in enumerate(ranked[:10], start=1)
    ) or "No scores were recorded."
    if solo:
        title = "Quiz complete!"
        description = f"You scored **{score_dict[winner_id][1] if winner_id in score_dict else 0}** points.\n\n{standings}"
    elif winner_id is not None:
        title = "Quizster champion!"
        description = f"<@{winner_id}> is the last player standing.\n\n{standings}"
    else:
        title = "Quiz over!"
        description = f"Nobody survived all three lives. Top score takes the bragging rights.\n\n{standings}"
    embed = discord.Embed(title=title, description=description, color=discord.Color.gold())
    embed.set_footer(text="Run /quizster to play another round.")
    return embed


def create_score_card_embed(score_dict, answers: dict, view, final=False):
    """Reveal the correct answer and show each player's round result."""
    movie = view.quiz_obj
    answer_label = "ABCD"[movie.answer_index]
    answer_embed = discord.Embed(
        title="Round recap",
        description=f"Correct answer: **{answer_label}. {movie.options[movie.answer_index]}**",
        color=discord.Color.green(),
    )
    if view.skipped:
        answer_embed.description += "\nThe team used a skip; no lives or points changed."
    else:
        rows = []
        for user_id in view.people:
            result = view.round_results.get(user_id)
            if result is None:
                continue
            if result["correct"]:
                line = f"<@{user_id}> got it right: **+{result['points']} pt{'s' if result['points'] != 1 else ''}**"
                if result["bonus"]:
                    line += " (3-answer streak bonus!)"
            elif result["answered"]:
                line = f"<@{user_id}> chose the wrong answer and lost a life."
            else:
                line = f"<@{user_id}> ran out of time and lost a life."
            rows.append(line)
        if rows:
            answer_embed.description += "\n\n" + "\n".join(rows)
    score_rows = [
        f"<@{user_id}> — **{score} pts** · {life} {'life' if life == 1 else 'lives'}"
        for user_id, (life, score) in score_dict.items()
    ]
    score_embed = discord.Embed(
        title="Scoreboard",
        description="\n".join(score_rows) or "No players remain.",
        color=discord.Color.blurple(),
    )
    return answer_embed, score_embed


def create_instructions_embed(mode="bollywood", help_mode=False, solo=False) -> discord.Embed:
    """Explain the actual round and team-resource rules before the lobby opens."""
    mode_label = {"bollywood": "Bollywood", "hollywood": "Hollywood", "mix": "Bollywood and Hollywood"}.get(mode, "Bollywood")
    description = (
        f"Take on **{mode_label}** multiple-choice movie trivia. Each correct answer earns 1 point; "
        "every third correct answer in a row adds a bonus point.\n\n"
        "**Team resources:** 3 lives, 3 shared hints, and 1 skip that passes on a majority vote. "
        "A wrong answer or timeout costs a life. Skipping costs no life.\n\n"
        "The round ends when everyone answers or the timer runs out."
    )
    if not help_mode:
        if solo:
            description += "\n\n**Solo mode:** answer as many rounds as you can before losing all three lives."
        else:
            description += "\n\n**Join the lobby, then press Start when your team is ready.**"
    embed = discord.Embed(title="Quizster · Movie Trivia", description=description, color=discord.Color.blurple())
    embed.set_footer(text="Answer buttons are private to active players; hints and round answers are shared with everyone.")
    return embed


async def play_quizster(ctx, bot, mode, starting_year, ending_year, timeout=60, solo=False):
    mode = str(mode).casefold()
    if mode not in {"bollywood", "hollywood", "mix"}:
        raise commands.BadArgument("Choose Bollywood, Hollywood, or Mix mode.")
    timeout = max(10, min(int(timeout), 60))
    folders = return_folders_from_mode(mode)
    backend = await run_blocking(Bollywood_backend, starting_year, ending_year, folders=folders)

    player_lives = 3
    skips_left = 1
    hints_left = 3
    rounds = 0
    instructions_embed = create_instructions_embed(mode, solo=solo)
    instructions_file = await run_blocking(quizster_art_file, instructions_embed)

    if solo:
        participants = [ctx.author.id]
        solo_player_id = ctx.author.id
        await ctx.send("🧠 **Solo Quizster** — beat your high score before you run out of lives.", embed=instructions_embed, file=instructions_file)
    else:
        lobby = GameLobbyView(ctx.author.id, ctx.author.display_name, "Quizster")
        lobby.message = await ctx.send(embed=instructions_embed, file=instructions_file, content=lobby.render(), view=lobby)
        await lobby.wait()
        if not lobby.started:
            await ctx.send("Quizster lobby closed. Start `/quizster` again when you’re ready.")
            return
        participants = list(dict.fromkeys(lobby.joined_ids))
        if not participants:
            await ctx.send("No one joined the quiz.")
            return

    player_data = {user_id: [player_lives, 0] for user_id in participants}
    streaks = {user_id: 0 for user_id in participants}

    while participants and (solo or len(participants) > 1):
        rounds += 1
        question = await run_blocking(backend.get_quiz_question)
        view = QuizsterView(
            question, timeout=timeout, people=player_data, people_playing=participants,
            skips=skips_left, hints=hints_left, streaks=streaks,
        )
        question_embed = create_question_embed(question, rounds, mode)
        question_file = await run_blocking(quizster_art_file, question_embed)
        question_msg = await ctx.send(embed=question_embed, file=question_file, view=view)
        view.response = question_msg
        timeout_msg = await ctx.send(
            f"⏳ Time left: {discord.utils.format_dt(discord.utils.utcnow() + datetime.timedelta(seconds=timeout), style='R')}"
        )
        await view.wait()
        if not view.resolved:
            await view.compare_answers()
        try:
            await timeout_msg.delete()
        except discord.NotFound:
            pass
        await ctx.send(embeds=create_score_card_embed(view.people, view.users, view))

        player_data = view.people
        participants = [user_id for user_id in participants if player_data[user_id][0] > 0]
        skips_left = view.skips
        hints_left = view.hints
        streaks = view.streaks
        if solo and (not participants or player_data[solo_player_id][0] <= 0):
            break
        if not solo and len(participants) <= 1:
            break
        await ctx.send(f"**Round {rounds} complete.** Next question in 4 seconds…")
        await asyncio.sleep(4)

    winner_id = participants[0] if not solo and len(participants) == 1 else (solo_player_id if solo else None)
    game_over = create_game_over_embed(player_data, winner_id=winner_id, solo=solo)
    game_over_file = await run_blocking(quizster_art_file, game_over)
    await ctx.send(embed=game_over, file=game_over_file)
