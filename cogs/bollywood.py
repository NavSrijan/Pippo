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

    @commands.hybrid_command(name="clash")
    @commands.max_concurrency(1, per=commands.BucketType.channel, wait=False)
    async def ai_clash(self, ctx):
        "Fight with your opponent using any object, character, or anything."
        
        # Create UI components for the clash game
        class ClashSubmitView(discord.ui.View):
            def __init__(self, timeout=120):
                super().__init__(timeout=timeout)
                self.submissions = {}
                self.message = None
            
            @discord.ui.button(label="Submit Creation", style=discord.ButtonStyle.primary)
            async def submit_button(self, interaction: discord.Interaction, button: discord.ui.Button):
                # Create a modal for user submission
                modal = ClashSubmitModal(self)
                await interaction.response.send_modal(modal)
                
        class ClashSubmitModal(discord.ui.Modal, title="Submit Your Creation"):
            creation = discord.ui.TextInput(
                label="What will you fight with?",
                placeholder="Enter any object, concept, or character...",
                required=True,
                max_length=100
            )
            
            def __init__(self, view):
                super().__init__()
                self.view = view
            
            async def on_submit(self, interaction: discord.Interaction):
                user_id = interaction.user.id
                self.view.submissions[user_id] = self.creation.value
                
                # Acknowledge the submission
                await interaction.response.send_message(f"Your creation '{self.creation.value}' has been submitted!", ephemeral=True)
                
                # Update the main message
                participants = []
                for uid in self.view.submissions:
                    user = interaction.client.get_user(uid)
                    participants.append(f"✅ @{user.display_name}")
                
                # Update the embed with current submissions
                embed = discord.Embed(
                    title="Clash of Creations",
                    description=f"Submissions received:\n" + "\n".join(participants) + "\n\nThink of an object or concept you want to fight with.",
                    color=discord.Color.green()
                )
                await self.view.message.edit(embed=embed)
                
                # If we have 2 submissions, proceed with the clash after a short delay
                if len(self.view.submissions) >= 2:
                    await asyncio.sleep(2)  # Give a moment for users to see the final submission state
                    self.view.stop()
        
        # AI judging function using Google's Gemini API
        async def judge_clash(player1, player1_creation, player2, player2_creation):
            """Use Gemini API to judge clash submissions"""
            try:
                import requests
                import os
                import json

                # Get API key from environment variable
                api_key = os.environ['gemini_api_key']
                
                # Create the prompt for the battle
                prompt = f"""
                In an epic battle between two creations:
                - Player 1 ({player1.display_name}) is using: {player1_creation}
                - Player 2 ({player2.display_name}) is using: {player2_creation}
                
                Decide who would win this battle and why in a creative, entertaining way. It shouldn't prioritize superficial things. Make it quirky, fun, unexpectable. Don't go with emotions, go with absurdity. Don't make it too long, max 3 lines. no line 
                breaks.
                Respond in this exact format:
                WINNER: [Player 1 or Player 2]
                REASON: [A creative, detailed explanation of why this creation won]
                """
                
                # API endpoint for Gemini
                url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
                
                # Request payload
                payload = {
                    "contents": [{
                        "parts": [{
                            "text": prompt
                        }]
                    }],
                    "generationConfig": {
                        "temperature": 0.9,
                        "topP": 1,
                        "topK": 32,
                        "maxOutputTokens": 250
                    }
                }
                
                # Send request to Gemini API
                headers = {
                    "Content-Type": "application/json"
                }
                response = requests.post(
                    f"{url}?key={api_key}",
                    headers=headers,
                    data=json.dumps(payload)
                )
                
                # Parse the JSON response
                response_data = response.json()
                
                # Extract the text from the response
                response_text = response_data["candidates"][0]["content"]["parts"][0]["text"]
                if "WINNER: Player 1" in response_text:
                    winner = player1
                    winner_creation = player1_creation
                else:
                    winner = player2
                    winner_creation = player2_creation
                
                # Extract the reason
                reason_match = re.search(r"REASON: (.*?)(?=$|\n\n)", response_text, re.DOTALL)
                # print(f"DEBUG: Full response from Gemini: {response_text}")
                if reason_match:
                    reason = reason_match.group(1).strip()
                else:
                    # Fallback in case the API doesn't format as expected
                    reason = response_text.split("REASON:")[-1].strip() if "REASON:" in response_text else response_text
                
                return winner, reason
                
            except Exception as e:
                print(f"Error using Gemini API: {str(e)}")
                
                # Fallback to random choice if the API fails
                winner = random.choice([player1, player2])
                loser = player2 if winner == player1 else player1
                winner_creation = player1_creation if winner == player1 else player2_creation
                loser_creation = player2_creation if winner == player1 else player1_creation
                
                # Generate a fallback creative reason
                reasons = [
                    f"{winner_creation} absorbs the secret, making it deliciously illegible. Plus, who can resist warm, buttery carbs?",
                    f"{winner_creation} overwhelms {loser_creation} with its superior capabilities and strategic advantage.",
                    f"The sheer power of {winner_creation} is too much for {loser_creation} to handle in direct combat.",
                    f"{winner_creation} uses an unexpected technique that {loser_creation} simply cannot counter."
                ]
                
                reason = f"[API Fallback] {random.choice(reasons)}"
                return winner, reason
        
        # Execute clash
        try:
            # Display welcome message and rules
            welcome_embed = discord.Embed(
                title="Welcome to Clash of Creations! ⚔️", 
                description=(
                    "**How to Play:**\n"
                    "1. This is a **creative duel** between two players!\n"
                    "2. **Submit any object, concept, or person** you want to fight with\n"
                    "3. An **AI judge** 🤖 will determine the winner\n\n"
                    "⏱️ **You have two minutes to submit your creation**\n"
                    "Players who don't submit in time will forfeit the match\n\n"
                    "Ready to duel? Click 'Submit Creation' to begin!"
                ),
                color=discord.Color.gold()
            )
            
            # Create and send the view with the submit button
            view = ClashSubmitView()
            view.message = await ctx.send(embed=welcome_embed, view=view)
            
            # Wait for submissions (timeout handled by the view)
            timed_out = await view.wait()
            
            # If timed out or not enough participants
            if timed_out or len(view.submissions) < 2:
                await ctx.send("Not enough players submitted their creations in time. The clash has been canceled.")
                return
            
            # Get the first two players who submitted
            player_ids = list(view.submissions.keys())[:2]
            player1 = ctx.guild.get_member(player_ids[0])
            player2 = ctx.guild.get_member(player_ids[1])
            player1_creation = view.submissions[player_ids[0]]
            player2_creation = view.submissions[player_ids[1]]
            
            # Arena announcement
            arena_embed = discord.Embed(
                title="The Arena 🏟️",
                description=f"• @{player1.display_name}: {player1_creation}\n• @{player2.display_name}: {player2_creation}",
                color=discord.Color.red()
            )
            # You can add an image here if you have arena images
            await ctx.send(embed=arena_embed)
            
            # Add a short delay for suspense
            await asyncio.sleep(2)
            
            # Judge the clash
            winner, reason = await judge_clash(player1, player1_creation, player2, player2_creation)
            
            # Announce result
            result_embed = discord.Embed(
                title="The Victor 🏆",
                description=f"{winner.display_name} with {player1_creation if winner == player1 else player2_creation}",
                color=discord.Color.gold()
            )
            result_embed.add_field(name="Reason", value=reason, inline=False)
            # You can add a victory image here if you have one
            
            await ctx.send(embed=result_embed)
            
            # Add rematch button (implementing as a simple message for now)
            # await ctx.send("🔄 Rematch [2/2]")
        
        except Exception as e:
            await ctx.send(f"An error occurred during the clash: {str(e)}")

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
