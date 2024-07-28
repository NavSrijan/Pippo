import re
import requests
import random
import csv
import os
import asyncio
import datetime
import discord
from io import BytesIO
import ipdb
from discord.ext import commands
from PIL import Image
from functions import write_text_on_image
from views import HintsView, PlotsterView, QuizsterView

hints_obj = HintsView()

def return_folders_from_mode(mode):
    if mode == "bollywood":
        folders = ["data/bollywood/"]
    elif mode == "hollywood":
        folders = ["data/hollywood/"]
    elif mode == "mix":
        folders = ["data/bollywood/", "data/hollywood/"]
    return folders

class Quiz_Question():

    def __init__(self, get_movie, type_of_question: str):
        # QUIZ_TYPES = ["MA", "AM", "GM", "YM", "DM"]
        self.get_movie = get_movie
        self.type_of_question = type_of_question
        self.QUIZ_TYPES = {"MA": self.MA, "AM": self.AM, "YM": self.YM}  # "GM", "YM", "DM"}

    def return_question(self):
        return self.QUIZ_TYPES[self.type_of_question](self.get_movie)

    class MA():
        """Movie from Actor"""

        def __init__(self, get_movie):
            movie = get_movie()
            movie_actors = movie['actors'].split("|")
            if len(movie_actors) > 2:
                self.actor = random.choice(movie_actors[:2])
            self.movies = [movie]
            while len(self.movies) != 4:
                movie_to_append = get_movie()
                actors = movie_to_append['actors'].split("|")
                if self.actor in actors:
                    continue
                self.movies.append(movie_to_append)
            self.actor = self.actor.strip()
            self.movie = self.movies[0]
            self.movie_name = self.movie['name']
            self.question_template = [
                "{} acted in which of the following movies?",
                "Which movie starred {}?",
                "{} played a role in which of the following movies?",
                "Which of these movies did {} appear in?",
                "In which movie did {} have a part?",
                "Which of these films featured {}?",
                "{} acted in which of the following movies?",
                "Which movie did {} have a role in?",
                "In which of these movies did {} appear?",
                "{} played a part in which of the following films?"
            ]

            self.question = random.choice(
                self.question_template).format(f"**{self.actor}**")
            self.answer = movie['name']
            self.options = [x['name'] for x in self.movies[1:]]
            self.answer_index = random.randint(0, len(self.options))
            self.options.insert(self.answer_index, self.movie_name)
            self.hint = movie['description']

    class AM():
        """Actor from Movie"""

        def __init__(self, get_movie):
            self.movie = get_movie()
            self.question_template = [
                "Which actor appeared in {}?", "Who acted in {}?",
                "Can you name an actor who was in {}?", "Who performed in {}?",
                "In {}, which actor had a role?", "Who was featured in {}?",
                "Which actor played a character in {}?",
                "Who had a part in {}?", "Who made an appearance in {}?",
                "In {}, who was the actor on screen?"
            ]
            self.question = random.choice(self.question_template).format(
                self.movie['name'])
            movie_actors = self.movie['actors'].split("|")
            if len(movie_actors) > 2:
                self.actor = random.choice(movie_actors[:2])
            else:
                self.actor = random.choice(movie_actors)
            self.movies = [self.movie]
            self.options = []
            while len(self.movies) != 4:
                movie_to_append = get_movie()
                actors = movie_to_append['actors'].split("|")
                for i in actors:
                    if i in movie_actors:
                        continue
                self.options.append(random.choice(actors).strip())
                self.movies.append(movie_to_append)
            self.actor = self.actor.strip()
            self.answer = self.actor
            self.answer_index = random.randint(0, len(self.options))
            self.options.insert(self.answer_index, self.actor)
            self.hint = self.movie['description']

    class YM():
        """Year from Movie"""

        def __init__(self, get_movie):
            self.movie = get_movie()
            self.extract_year()
            self.question_template = [
                "What was the year of release for the movie '{}'?",
                "When did the movie '{}' come out?",
                "At what time was the movie '{}' released?",
                "Which year did the movie '{}' hit the theaters?",
                "When was the movie '{}' made available to the public?",
                "In what year did the movie '{}' make its debut?",
                "What was the release date of the movie '{}'?",
                "When did the movie '{}' first appear on screen?",
                "At which year did the movie '{}' get released?",
                "In what year did the movie '{}' see the light of day?"
            ]
            self.question = random.choice(self.question_template).format(
                self.movie['name'])
            self.options = []
            while len(self.options) != 3:
                delta = random.randint(-12, 12)
                to_append = self.year + delta
                if to_append>=2023 or to_append == self.year or to_append in self.options:
                    continue
                self.options.append(to_append)

            self.answer = self.year
            self.answer_index = random.randint(0, len(self.options))
            self.options.insert(self.answer_index, self.year)

            self.hint = random.choice([self.movie['description'], self.movie['actors']])

        def extract_year(self):
            datee = self.movie["datePublished"]
            self.year = int(datee.split("-")[0])

class Bollywood_backend():
    QUIZ_TYPES = ["MA", "AM", "YM"]  #, "GM", "DM"]

    def __init__(self, starting_year, ending_year, difficulty="easy", folders=["data/bollywood/"]):
        self.folders = folders
        if starting_year < 1980:
            starting_year = 1980
        if ending_year > 2023:
            ending_year = 2023
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

    def get_random_movie(self):
        i = random.choice(self.movies)
        return i



    def get_movie_plotster(self):
        if len(self.movies) <= 1:
            self.load_movies()
        movies_to_remove = []
        i = random.choice(self.movies)
        movies_to_remove.append(i)

        while i['description'] == "":
            i = random.choice(self.movies)
            movies_to_remove.append(i)

        for m in movies_to_remove:
            try:
                self.movies.remove(m)
            except:
                pass
        return i

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
            movies = movies + self.read_csv(f"{i}{year}_data.csv")[:n]
        #movies = self.read_csv(f"{self.folder}{year}_data.csv")[:n]
        return movies

    def read_csv(self, filename):
        with open(filename, "r") as csvf:
            csvr = csv.DictReader(csvf)
            rows = list(csvr)
        return rows


def check(ctx, message):
    # Check if the message is from the same channel as the command
    return message.channel == ctx.channel

def get_text_after_substitution(movie_name, characters_to_exclude="", escape=True):
    # Generate the movie name with unguessed letters replaced by underscores
    regex = "(?![:{}])[A-Za-z]"
    replacement = "\\_" if escape else "‎_"
    text = re.sub(regex.format(characters_to_exclude),
                replacement,
                movie_name,
                flags=re.IGNORECASE)
    return text

def correct_answer_embed(movie, correct=True):
    # Create an embed message for correct or incorrect answers
    if correct is True:
        title = "You got the correct answer!"
    else:
        title = "The answer was:"
    desc = f"Title: **{movie['name']}**\nType: {movie['type']}\nGenre: **{movie['genre']}**\nDate Publised: {movie['datePublished']}\nDuration: {movie['duration']}\nCast: {movie['actors']}"
    emb = discord.Embed(title=title,
                        description=desc,
                        url=movie['url'])
    emb.set_image(url=movie['poster_url'])
    return emb

def guess_embed(movie, characters_to_exclude, persons, lives, tries,
                roundd):
    movie_name = movie['name']
    # Create an embed message for the current guess state
    if len(persons) >= 1:
        persons_str = ""
        for i in persons:
            persons_str += f"<@{i}>: {persons[i]}"
    else:
        persons_str = ""
    color = discord.Color.from_str("#FAEBC0")
    color2 = discord.Color.from_str("#938448")
    desc = f"{get_text_after_substitution(movie['name'], characters_to_exclude)}\n{persons_str}\nLives:{lives}\nTries:{tries}"
    emb = discord.Embed(description=desc, color=color2)
    emb2 = discord.Embed(title=f"Round: {roundd+1}", color=color)
    font_list = ['darling_coffee.ttf']  # Update with the correct path to your font files
    color_list = ['#938448']
    image = write_text_on_image(f"imgs/b{9-hints_obj.tries}.webp", get_text_after_substitution(movie_name, characters_to_exclude, escape=False), font_list, color_list, start_location=(200, 200))
    emb2.set_image(url=f"attachment://boll.jpg")
    return emb, emb2, image

def game_start_embed(game_type, help_mode=False):
    # Create an embed message for the game start
    if game_type == "bollywood":
        title = "Hangman but Bollywood?"
        url="https://media.discordapp.net/attachments/874937163161174067/1095347657326735401/9e0e2415e39ac3e78a8f405410d66328.png?width=476&height=476"
    elif game_type == "hollywood":
        title = "Hangman but Hollywood?"
        url = "https://media.discordapp.net/attachments/1092244601525510154/1140271390226927647/movie-2545676_1280.png?width=976&height=660"
    description = "Basic hangman rules.\nYou have **9** tries to guess the movie.\nYou have **3** lives.\nEach player gains individual letter points.\nCosts:\nHint: 1 try\nRandom Letter: 2 tries\nSynopsis: 5 tries"
    if not help_mode:
        description += "\n\n**STARTING IN 5 SECODNS.**"

    embed = discord.Embed(
        title=title,
        description=description,
        color=discord.Color.from_str("#1F2410"))
    embed.set_image(
            url=url
    )
    return embed

def game_over_embed(persons, score, game_type):
    if game_type == "bollywood" or game_type == "plotster":
        url="https://media.discordapp.net/attachments/874937163161174067/1095345904116052100/e1480d8fee8fd002ed774630325092df.png"
    elif game_type == "hollywood":
        url="https://media.discordapp.net/attachments/874937163161174067/1095345904116052100/e1480d8fee8fd002ed774630325092df.png"
    # Create an embed message for game over
    if len(persons) >= 1:
        persons_str = ""
        for i in persons:
            persons_str += f"<@{i}>: {persons[i]}"
    else:
        persons_str = ""
    embed = discord.Embed(
        title="Game Over!",
        description=f"Score: **{score}**\n\n{persons_str}",
        color=discord.Color.from_str("#D01819"))
    embed.set_image(
            url=url
    )
    return embed

async def deposit_score(persons, score):
    # Update the score for each player in the database
    for i in persons:
        await self.bot.db.bollywoodHangmanDB.update_score(i, persons[i], score)
        await self.bot.db.coins.add_coins(i, coins=5*persons[i])

async def play_game(ctx, bot, game_type, starting_year, ending_year, folders, timeout=60):
    # Initialize the Bollywood backend with the specified year range and data folder
    bollywood_backend = Bollywood_backend(starting_year, ending_year, folders=folders)

    # Limit the timeout to 60 seconds if it's set higher than 120 seconds
    if timeout > 120:
        timeout = 60
    lives = 1  # Set initial number of lives

    regex = "[A-Za-z]"  # Regex pattern for matching alphabetic characters

    score = 0
    persons = {}
    # Embed before the game starts, containing the help message
    await ctx.channel.send(embed=game_start_embed(game_type))
    await asyncio.sleep(5) # Time to read the help message
    while lives != 0:
        hints_obj.tries = 9
        hints_obj.reset()
        answer = ""
        while len(answer) == 0:
            movie = bollywood_backend.get_random_movie()
            movie_name = movie['name']
            answer = set(re.findall(regex, movie_name.lower()))
        characters_to_exclude = ""
        counter = 0
        hints_obj.hint = f"Cast: **{movie['actors']}**"
        hints_obj.random_letter = random.choice(list(answer))
        hints_obj.synopsis = movie['description']
        while hints_obj.tries > 0:
            embed, embed_pic, image = guess_embed(movie, characters_to_exclude,
                                        persons, lives, hints_obj.tries,
                                        score)
            if counter % 5 == 0:
                current_msg = await ctx.channel.send(embeds=(embed_pic,
                                                            embed),
                                                    view=hints_obj, file=image)
                hints_obj.out = current_msg
            else:
                await current_msg.edit(embeds=(embed_pic, embed), attachments=[image])
            counter += 1

            try:
                msg = await bot.wait_for('message',
                                            check=lambda m: check(ctx, m),
                                            timeout=timeout)
            except asyncio.exceptions.TimeoutError:
                await ctx.send("Looks like you didn't wanna play...")
                await ctx.channel.send(embed=correct_answer_embed(movie, correct=False))
                try:
                    await deposit_score(persons, score)
                except:
                    pass
                return

            prefix = await bot.get_prefixx(bot, ctx.message)
            if msg.content.lower() in [f"{prefix}exit", f"{prefix}end"]:
                await ctx.send("Exiting...")
                try:
                    await deposit_score(persons, score)
                except:
                    pass
                return
            if len(msg.content) == 1 and msg.content.lower() in movie_name.lower() and msg.content.lower() not in characters_to_exclude:
                # Update individual scores
                await msg.add_reaction("\U00002705")
                try:
                    persons[msg.author.id] += 1
                except:
                    persons[msg.author.id] = 1

                characters_to_exclude += msg.content
                # Check if all letters have been guessed
                if len(answer) == len(characters_to_exclude):
                    await ctx.channel.send(embed=correct_answer_embed(movie))
                    await asyncio.sleep(3)
                    score += 1
                    break
            elif len(msg.content) == 1 and msg.content.lower() not in movie_name.lower():
                hints_obj.tries -= 1
                await msg.add_reaction("\U0000274C")

            if hints_obj.tries == 0:
                await ctx.channel.send(embed=correct_answer_embed(movie, correct=False))
                await asyncio.sleep(3)
                lives -= 1
                continue
    await ctx.channel.send(embed=game_over_embed(persons, score, game_type))
    await deposit_score(persons, score)


"""
Poster pixelate
"""
def pixelate_image(image_url, pixel_size):
    # Open the image
    response = requests.get(image_url)
    if response.status_code == 200:
        image_data = response.content
        image = Image.open(BytesIO(image_data))
        
        # Calculate the size of the pixelated image
        width, height = image.size
        pixelated_width = (width // pixel_size) * pixel_size
        pixelated_height = (height // pixel_size) * pixel_size
        
        # Resize the image to reduce detail, then resize it back to its original size
        image = image.resize((pixelated_width // pixel_size, pixelated_height // pixel_size), Image.BILINEAR)
        image = image.resize((pixelated_width, pixelated_height), Image.NEAREST)
        
        with BytesIO() as output:
            image.save(output, format='JPEG', optimize=True, quality=40)
            output.seek(0)
            return discord.File(output, filename='pixelate_img.jpg')
    else:
        raise Exception(f"Failed to fetch image from URL: {url}")

def pixelate_game_start_embed(help_mode=False):
    # Create an embed message for the game start
    description = "Guess the movie from the image\nIt will get less blurry every time you fail to guess it."
    if not help_mode:
        description += "**\n\n STARTING IN 5 SECONDS.**"
    url = "https://media.discordapp.net/attachments/1092244601525510154/1266466417692246087/depixelate.jpg?ex=66a54043&is=66a3eec3&hm=85168dbf91cac55c2ea70ae9d369301368f3286917a88716fc543d7892c9a99c&=&format=webp&width=1042&height=625"
    embed = discord.Embed(
        title="DePixelate the Movie Poster!",
        description=description,
        color=discord.Color.from_str("#1F2410"))
    embed.set_image(
            url=url
    )
    return embed

def pixelate_guess_embed(movie,  persons, lives, roundd, quality):
    movie_name = movie['name']
    # Create an embed message for the current guess state
    if len(persons) >= 1:
        persons_str = ""
        for i in persons:
            persons_str += f"<@{i}>: {persons[i]}"
    else:
        persons_str = ""
    color = discord.Color.from_str("#FAEBC0")
    color2 = discord.Color.from_str("#938448")
    desc = f"{persons_str}\nLives:{lives}"
    emb = discord.Embed(description=desc, color=color2)
    emb2 = discord.Embed(title=f"Round: {roundd+1}", color=color)
    image = pixelate_image(movie['poster_url'], quality)
    emb2.set_image(url=f"attachment://pixelate_img.jpg")
    return emb, emb2, image

def pixelate_game_over_embed(persons, score):
    url="https://media.discordapp.net/attachments/874937163161174067/1095345904116052100/e1480d8fee8fd002ed774630325092df.png"
    # Create an embed message for game over
    if len(persons) >= 1:
        persons_str = ""
        for i in persons:
            persons_str += f"<@{i}>: {persons[i]}"
    else:
        persons_str = ""
    embed = discord.Embed(
        title="Game Over!",
        description=f"Score: **{score}**\n\n{persons_str}",
        color=discord.Color.from_str("#D01819"))
    embed.set_image(
            url=url
    )
    return embed

def normalize_string(s):
    return re.sub(r'\W+', '', s).lower()

def compare_movie_name(movie_name, guess):
    normalized_input = normalize_string(movie_name)
    normalized_movie_name = normalize_string(guess)
    return normalized_input == normalized_movie_name


async def play_pixelate(ctx, bot, mode, starting_year, ending_year, timeout=60):
    # Limit the timeout to 60 seconds if it's set higher than 120 seconds
    if timeout > 120:
        timeout = 60

    folders = return_folders_from_mode(mode)

    bollywood_backend = Bollywood_backend(starting_year, ending_year, folders=folders)

    lives = 1  # Set initial number of lives
    score = 0
    persons = {}
    # Embed before the game starts, containing the help message
    await ctx.channel.send(embed=pixelate_game_start_embed())
    await asyncio.sleep(5) # Time to read the help message

    while lives!=0:
        movie = bollywood_backend.get_random_movie()
        counter = 0
        quality = 100

        while quality > 0:
            embed, embed_pic, image = pixelate_guess_embed(movie, persons, lives, score, quality)

            if counter % 5 == 0:
                current_msg = await ctx.channel.send(embeds=(embed_pic,
                                                            embed), file=image)
            else:
                await current_msg.edit(embeds=(embed_pic, embed), attachments=[image])
            counter += 1

            try:
                msg = await bot.wait_for('message',
                                            check=lambda m: check(ctx, m),
                                            timeout=timeout)
            except asyncio.exceptions.TimeoutError:
                await ctx.send("Looks like you didn't wanna play...")
                await ctx.channel.send(embed=correct_answer_embed(movie, correct=False))
                await ctx.channel.send(embed=pixelate_game_over_embed(persons, score))

                try:
                    await deposit_score(persons, score)
                except:
                    pass
                return

            prefix = await bot.get_prefixx(bot, ctx.message)
            if msg.content.lower() in [f"{prefix}exit", f"{prefix}end"]:
                await ctx.channel.send(embed=correct_answer_embed(movie, correct=False))
                await ctx.channel.send(embed=pixelate_game_over_embed(persons, score))
                await ctx.send("Exiting...")
                try:
                    await deposit_score(persons, score)
                except:
                    pass
                return

            if compare_movie_name(movie['name'], msg.content):
                await ctx.channel.send(embed=correct_answer_embed(movie))
                await asyncio.sleep(3)
                try:
                    persons[msg.author.id] += quality
                except:
                    persons[msg.author.id] = quality
                score += 1
                break

            quality -=10

            if quality <= 0:
                await ctx.channel.send(embed=correct_answer_embed(movie, correct=False))
                await asyncio.sleep(3)
                lives -= 1
                continue

    await ctx.channel.send(embed=pixelate_game_over_embed(persons, score))
    try:
        await deposit_score(persons, score)
    except:
        pass


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
        movie = re.sub(regex, "\_", movie_name)

    return movie

def get_answer(movie):
    regex = "[a-zA-Z]+"
    words = re.findall(regex, movie)

    return set(words)

def plotster_game_start_embed(help_mode=False):
    description = "You need to guess the movie from the **keywords** mentioned.\nYou can use the buttons each round once."
    if not help_mode:
        description +="**\n STARTING IN 5 SECONDS.**"
    embed = discord.Embed(
        title="Plotster",
        description=description,
        color=discord.Color.from_str("#1F2410"))
    embed.set_image(
        url=
        "https://media.discordapp.net/attachments/1092244601525510154/1100614666830491689/lagaann_dalle_pippo.png?width=432&height=432"
    )
    return embed

def plotster_guess_embed(movie, persons, lives, roundd,
                time_left):
    if len(persons) >= 1:
        persons_str = ""
        for i in persons:
            persons_str += f"<@{i}>: {persons[i]}"
    else:
        persons_str = ""
    color = discord.Color.from_str("#FAEBC0")
    color2 = discord.Color.from_str("#938448")
    desc = f"**{movie['description']}**\n\n{persons_str}\nLives:{lives}\n"
    emb = discord.Embed(description=desc, color=color2)
    emb2 = discord.Embed(title=f"Round: {roundd}", color=color)
    emb2.set_image(url="https://media.discordapp.net/attachments/874937163161174067/1095347657326735401/9e0e2415e39ac3e78a8f405410d66328.png?width=476&height=476")
    emb.set_footer(text=f"Time Left: {time_left:0,.2f}")
    return emb, emb2

async def play_plotster(ctx, bot, mode, starting_year, ending_year, timeout=60):
    game_type = "plotster"
    # Limit the timeout to 60 seconds if it's set higher than 120 seconds
    if timeout > 120:
        timeout = 60

    folders = return_folders_from_mode(mode)

    bollywood_backend = Bollywood_backend(starting_year, ending_year, folders=folders)

    lives = 1  # Set initial number of lives
    score = 0
    persons = {}
    # Embed before the game starts, containing the help message
    await ctx.channel.send(embed=plotster_game_start_embed())
    await asyncio.sleep(5) # Time to read the help message
    prefix = await bot.get_prefixx(bot, ctx.message)

    while lives != 0:
        movie = bollywood_backend.get_movie_plotster()
        movie_name = movie['name']
        print(movie_name)
        counter = 0
        time_remaining = asyncio.get_event_loop().time() + timeout
        while asyncio.get_event_loop().time() < time_remaining:
            time_left = time_remaining - asyncio.get_event_loop().time()
            embed, embed_pic = plotster_guess_embed(movie, persons,
                                           lives, score, time_left)

            if counter % 5 == 0:
                current_msg = await ctx.channel.send(embeds=(embed_pic,
                                                             embed))
            else:
                await current_msg.edit(embeds=(embed_pic, embed))

            try:
                msg = await bot.wait_for('message', 
                                              check=lambda m: check(ctx, m),
                                              timeout=time_left)
            except asyncio.exceptions.TimeoutError:
                lives -= 1
                if counter == 0:
                    await ctx.send(
                        embed=correct_answer_embed(movie, correct=False))
                    await ctx.channel.send(embed=game_over_embed(persons, score, game_type))
                    await ctx.send("Looks like you didn't wanna play...")
                    try:
                        await deposit_score(persons, score - 1)
                    except:
                        pass
                    return
                else:
                    await ctx.send(
                        embed=correct_answer_embed(movie, correct=False))
                    await asyncio.sleep(3)
                    break

            counter += 1

            if msg.content.lower() == f"{prefix}exit":
                await ctx.send(
                    embed=correct_answer_embed(movie, correct=False))
                await ctx.channel.send(embed=game_over_embed(persons, score, game_type))
                await ctx.send("Exiting...")
                try:
                    await deposit_score(persons, score - 1)
                except:
                    pass
                return
            elif msg.content.lower() == f"{prefix}skip":
                await ctx.send("Skipping.")
                await ctx.send(
                    embed=correct_answer_embed(movie, correct=False))
                lives -= 1
                await asyncio.sleep(3)
                break

            #Games logic
            guess_correct = compare_movie_name(movie['name'], msg.content)
            if guess_correct:
                try:
                    persons[msg.author.id] += 1
                except:
                    persons[msg.author.id] = 1

                await ctx.send(embed=correct_answer_embed(movie, correct=True))
                score += 1
                await asyncio.sleep(3)
                break

    await ctx.channel.send(embed=game_over_embed(persons, score, game_type))
    await deposit_score(persons, score)


def create_question_embed(movie, round_number) -> discord.Embed:
    """Create an embed containing the question and options"""
    img_url = "https://media.discordapp.net/attachments/1092244601525510154/1105104823394770944/TheWhistler_Girl_dancing_with_her_friends_in_a_fort_in_Jaipur_I_58d0b885-7d02-46a1-9a65-202ddd2684c7.png?width=849&height=476"
    options = "\n".join([f"{ABC}. {option}" for ABC, option in zip(["A", "B", "C", "D"], movie.options)])
    description = f"{movie.question}\n\n{options}"
    embed = discord.Embed(title=f"Round: {round_number}", description=description)
    embed.set_image(url=img_url)
    return embed

def create_game_over_embed(user_id, score) -> discord.Embed:
    """Create an embed for game over"""
    img_url = "https://media.discordapp.net/attachments/1092244601525510154/1105039621794058240/TheWhistler_Bollywood_styled_and_in_the_style_of_Scott_C_happy__a51aeaec-5979-447f-98f6-e86a27025d99.png?width=476&height=476"
    description = f"<@{user_id}> won with {score} points."
    embed = discord.Embed(title="GAME OVER!", description=description, color=discord.Color.gold())
    embed.set_image(url=img_url)
    return embed

def create_score_card_embed(score_dict, answers: dict, correct_answer: int, final=False):
    """Create an embed displaying the score card"""
    embed = discord.Embed(title="Score Card")
    scorecard = "\n".join([f"<@{user_id}>\n```Lives: {life}  Score: {score}```" for user_id, (life, score) in score_dict.items()])

    correct_users = [f"<@{user_id}>" for user_id, answer in answers.items() if answer == correct_answer]
    incorrect_users = [f"<@{user_id}> (Option {['A', 'B', 'C', 'D'][answer]})" for user_id, answer in answers.items() if answer != correct_answer]
    result = f"{', '.join(correct_users)} got the correct answer.\n\n{', '.join(incorrect_users)}"
    if not correct_users:
        result = f"No one got the correct answer.\n\n{', '.join(incorrect_users)}"

    embed.description = scorecard
    answer_embed = discord.Embed(title="Answers", description=result)
    return answer_embed, embed

def create_instructions_embed(help_mode=False) -> discord.Embed:
    """Create an embed displaying the game instructions"""
    description = """
    Answer questions related to Bollywood movies.

    **Hints: 3**
    **Lives: 3**
    **Skip: 1**
    """
    if not help_mode:
        description += "\n\n**STARTING IN 5 SECONDS**"
    img_url = "https://media.discordapp.net/attachments/1092244601525510154/1106960875761442997/pixel-style-an-indian-man-and-a-woman-with-hands-on-each-others-shoulders-happy-watching-a-sunset-423169440.png?width=476&height=476"
    embed = discord.Embed(title="Quizster", description=description)
    embed.set_image(url=img_url)
    return embed

async def play_quizster(ctx, bot, mode, starting_year, ending_year, timeout=60):
    game_type = "quizster"
    timeout = min(timeout, 60)  # Limit the timeout to 60 seconds

    folders = return_folders_from_mode(mode)
    bollywood_backend = Bollywood_backend(starting_year, ending_year, folders=folders)
    
    lives, skips, hints, rounds = 3, 1, 3, 0
    instructions_embed = create_instructions_embed()

    await ctx.send("React on this to enter.")
    msg = await ctx.send(embed=instructions_embed)
    await msg.add_reaction("\U0001F39F")

    time_to_enter = 5
    time_temp_msg = await ctx.send(discord.utils.format_dt(datetime.datetime.now() + datetime.timedelta(seconds=time_to_enter), style="R"))
    await asyncio.sleep(time_to_enter)
    await time_temp_msg.delete()

    msg = await msg.fetch()
    participants = [user.id async for user in msg.reactions[0].users() if user.id != bot.user.id]
    solo = len(participants) < 2

    player_data = {user_id: [lives, 0] for user_id in participants}
    
    while len(participants) > 1 or (solo and player_data.get(ctx.author.id, [0])[0] > 0):
        rounds += 1
        movie = bollywood_backend.get_quiz_question()
        view = QuizsterView(movie, timeout=timeout)
        view.people = player_data
        view.people_playing = participants
        view.skips = skips
        view.hints = hints

        question_embed = create_question_embed(movie, rounds)
        question_msg = await ctx.send(embed=question_embed, view=view)
        timeout_msg = await ctx.send(discord.utils.format_dt(datetime.datetime.now() + datetime.timedelta(seconds=timeout), style="R"))
        
        view.response = question_msg
        try:
            await asyncio.wait_for(view.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            view.disable_view()
            await question_msg.edit(content="Timed out!", view=view)
            await view.compare_answers()

        await timeout_msg.delete()
        await asyncio.sleep(1.5)
        
        score_embeds = create_score_card_embed(view.people, view.users, view.quiz_obj.answer_index)
        await ctx.send(embeds=score_embeds)
        
        player_data = view.people
        participants = [user_id for user_id, (life, _) in player_data.items() if life > 0]
        view.people_playing = participants
        skips = view.skips
        hints = view.hints
        people_answered = view.users

        if not participants or len(view.users) == 0:
            await ctx.send("No one gave an answer. The game is over.")
            break

        if len(participants) > 1 or solo:
            await ctx.send(embed=discord.Embed(title="Next round begins in 5 seconds."))
            await asyncio.sleep(5)
        elif solo and player_data[ctx.author.id][0] == 0:
            break

    winner_id = participants[0] if participants else ctx.author.id if solo and player_data[ctx.author.id][0] > 0 else None
    if winner_id:
        await ctx.send(embed=create_game_over_embed(winner_id, player_data[winner_id][1]))
    else:
        await ctx.send("No one was able to win.")
