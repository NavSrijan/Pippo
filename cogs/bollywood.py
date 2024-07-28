import asyncio
import csv
import random
import re
from typing import Union
import datetime
from enum import Enum

import discord
import ipdb
from discord.ext import commands
from fuzzywuzzy import fuzz
from io import BytesIO


from views import PlotsterView, QuizsterView, BingoStartView, TicTacToeView, MemoryView, FloodView, GuessTheMovieView
from utils.bollywood_utils import play_game, play_pixelate, play_plotster, play_quizster

"""
Choices
"""
class Poster_choice(Enum):
    bollywood = "bollywood"
    hollywood = "hollywood"
    mix = "mix"

    @staticmethod
    def get_default():
        return Poster_choice.bollywood

"""
Flags
"""
class PosterFlags(commands.FlagConverter):
    mode: Poster_choice = commands.flag(default=Poster_choice.get_default(), description='Mode of the poster guessing')
    starting_year: int = commands.flag(default=2010, description='The starting year')
    ending_year: int = commands.flag(default=2023, description='The ending year')
    timeout: int = commands.flag(default=15, description='The timeout period in seconds')

class BollywoodFlags(commands.FlagConverter):
    starting_year: int = commands.flag(default=2010, description='The starting year')
    ending_year: int = commands.flag(default=2023, description='The ending year')
    timeout: int = commands.flag(default=15, description='The timeout period in seconds')

class Games(commands.Cog):
    """Games"""

    def __init__(self, bot):
        self.bot = bot


    @commands.max_concurrency(1, per=commands.BucketType.channel, wait=False)
    @commands.hybrid_command(name="bollywood")
    async def bollywood_game(self, ctx, *, flags: BollywoodFlags):
        """A Hangman like game but for bollywood movies!"""
        await play_game(ctx, self.bot, "bollywood", flags.starting_year, flags.ending_year, ["data/bollywood/"], flags.timeout)
    
    @commands.max_concurrency(1, per=commands.BucketType.channel, wait=False)
    @commands.hybrid_command(name="hollywood")
    async def hollywood_game(self, ctx, *, flags: BollywoodFlags):
        """A Hangman like game but for hollywood movies!"""
        await play_game(ctx, self.bot, "hollywood", flags.starting_year, flags.ending_year, ["data/hollywood/"], flags.timeout)

    @commands.max_concurrency(1, per=commands.BucketType.channel, wait=False)
    @commands.hybrid_command(name="plotster")
    async def plotster(self, ctx, *, flags: PosterFlags):
        """Plotster game function"""
        await play_plotster(ctx, self.bot, flags.mode.value, flags.starting_year, flags.ending_year, timeout=flags.timeout)

    @commands.max_concurrency(1, per=commands.BucketType.channel, wait=False)
    @commands.hybrid_command(name="quizster")
    async def quizster(self, ctx, *, flags: PosterFlags):
        """Quiz based on bollywood movies"""
        await play_quizster(ctx, self.bot, flags.mode.value, flags.starting_year, flags.ending_year, timeout=flags.timeout)

    @commands.max_concurrency(1, per=commands.BucketType.channel, wait=False)
    @commands.hybrid_command(name="poster", aliases=["poster_guess", "depixelate", "pixelate"])
    #async def poster_guess(self, ctx, mode: Poster_choice = Poster_choice.get_default(), starting_year=2010, ending_year=2023, timeout=15):
    async def poster_guess(self, ctx, *, flags: PosterFlags):
        """Guess the movie from its poster!"""
        await play_pixelate(ctx, self.bot, flags.mode.value, flags.starting_year, flags.ending_year, timeout=flags.timeout)

    @commands.max_concurrency(1, per=commands.BucketType.channel, wait=False)
    @commands.hybrid_command(name="bingo")
    async def bingo(self, ctx, time_to_enter:int=15):
        """Bingo!"""

        # Functions

        class Player():
            def __init__(self, user_id):
                self.id = user_id
                self.started = False
                self.cut = []
                self.global_cut = []
                self.generate_random_ints_list(26)

            def generate_random_ints_list(self, n):
                ll = list(range(1,n))
                ll = [str(x) for x in ll]
                random.shuffle(ll)
                self.number_list = []
                for i in range(int(len(ll)/5)):
                    self.number_list.append(ll[5*i:5*(i+1)])


        def instructions_embed():
            desc = """
            Remember the game of bingo we used to play in classrooms? No? 

            There is a 5x5 matrix and you need to fill at least 5 lines, either horizontall, vertically or diagonally.
            The first person to do so, wins.

            Select a number when it's your turn.
            """
            emb = discord.Embed(title="Bingo!", description=desc)
            return emb

        # Variables
        time_to_enter = min(time_to_enter, 60)

        # Taking players entry
        await ctx.send(embed=instructions_embed())
        await ctx.send("React on this to enter.")
        msg = await ctx.send(embed=discord.Embed(title="BINGO!"))
        await msg.add_reaction("\U0001F39F")
        time_temp_msg = await ctx.send(discord.utils.format_dt(datetime.datetime.now()+datetime.timedelta(seconds=time_to_enter), style="R"))
        await asyncio.sleep(time_to_enter)
        await time_temp_msg.delete()
        msg = await msg.fetch()
        rec = msg.reactions[0]
        people = [user.id async for user in rec.users()]
        people.remove(self.bot.user.id)
        players = {}
        for i in people:
            players[i] = Player(i)

        view = BingoStartView(players)
        msg = await ctx.send(view=view)
        view.out = msg

    @commands.max_concurrency(1, per=commands.BucketType.channel, wait=False)
    @commands.hybrid_command(name="tictactoe")
    async def tictactoe(self, ctx):
        """TIC TAC TOE"""
        await ctx.send('Tic Tac Toe: X goes first', view=TicTacToeView())

    @commands.hybrid_command(name="memory")
    async def memorygame(self, ctx, user2: discord.Member):
        """Challenge a friend to a game of memory"""
        user1 = ctx.author     
        view = MemoryView(user1, user2)
        out  = await ctx.reply(f"{user1.mention}'s turn.'", view=view)
        view.out = out

    @commands.hybrid_command(name="flood")
    async def flood(self, ctx):
        """Challenge a friend to a game of flood"""
        emojis = {}
        color_emojis = {"red":1133798766802129086, "green": 1133798762339373077, "magenta": 1133798753690730576, "blue": 1133798757817917670, "yellow": 1133798749248958495, "top_left":1134477415192727563, "bottom_right":1134477412487417997, "discord_loading": 1134482068391333898}
        for i in color_emojis:
            emojis[i] = self.bot.get_emoji(color_emojis[i])

        user1 = ctx.author     
        view = FloodView(user1, emojis)
        emb = discord.Embed(title="Flood!", description=f"Looking for someone to accept! {emojis['discord_loading']}")
        emb.set_image(url="https://i.imgur.com/XgGA46z.png")
        out  = await ctx.reply(embed=emb, view=view)
        view.out = out
        view.bot = self.bot

    @commands.hybrid_command(name="npat")
    async def name_place_animal_thing(self, ctx):
        "Play Name, Place, Animal and Thing with your friend, like you used to do in school."
        await ctx.reply("Work in progress.")


    @memorygame.error
    async def memorygame_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            prefixx = ctx.prefix
            await ctx.reply(f"You need to mention a user to challenge! Usage: `{prefixx}memory @user`")
        else:
            await ctx.reply("An error occurred. Please try again later.")
            raise error  # Re-raise the error so that it's still logged by the bot


    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.MaxConcurrencyReached):
            await ctx.send("An instance is already running.")
        elif isinstance(error, commands.CommandOnCooldown):
            em = discord.Embed(
                title="Tham ja bhai!",
                description=f"Try again in {error.retry_after:.2f}s.",
                color=discord.Color.fuchsia())
            await ctx.send(embed=em)
        else:
            print(repr(error))


async def setup(bot):
    await bot.add_cog(Games(bot))
