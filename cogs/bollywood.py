import asyncio
import csv
import random
import re
from typing import Union
import datetime
from enum import Enum
import os
import aiohttp

import discord
from flood import Flood
from discord.ext import commands
from utils.clash import judge_clash
from io import BytesIO


from views import PlotsterView, QuizsterView, BingoStartView, TicTacToeView, MemoryView, FloodView, GuessTheMovieView, ChallengeInviteView, GameLobbyView
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
    ending_year: int = commands.flag(default=discord.utils.utcnow().year, description='The ending year')
    timeout: int = commands.flag(default=15, description='The timeout period in seconds')
    solo: bool = commands.flag(default=False, description='Play alone; only your guesses count')

class BollywoodFlags(commands.FlagConverter):
    starting_year: int = commands.flag(default=2010, description='The starting year')
    ending_year: int = commands.flag(default=discord.utils.utcnow().year, description='The ending year')
    timeout: int = commands.flag(default=15, description='The timeout period in seconds')
    solo: bool = commands.flag(default=False, description='Play alone; only your guesses count')

class Games(commands.Cog):
    """Games"""

    def __init__(self, bot):
        self.bot = bot


    @commands.max_concurrency(1, per=commands.BucketType.channel, wait=False)
    @commands.hybrid_command(name="bollywood")
    async def bollywood_game(self, ctx, *, flags: BollywoodFlags):
        """Guess Bollywood movies with friends, or use solo: True to play alone."""
        await play_game(ctx, self.bot, "bollywood", flags.starting_year, flags.ending_year, ["data/bollywood/"], flags.timeout, solo=flags.solo)
    
    @commands.max_concurrency(1, per=commands.BucketType.channel, wait=False)
    @commands.hybrid_command(name="hollywood")
    async def hollywood_game(self, ctx, *, flags: BollywoodFlags):
        """Guess Hollywood movies with friends, or use solo: True to play alone."""
        await play_game(ctx, self.bot, "hollywood", flags.starting_year, flags.ending_year, ["data/hollywood/"], flags.timeout, solo=flags.solo)

    @commands.max_concurrency(1, per=commands.BucketType.channel, wait=False)
    @commands.hybrid_command(name="plotster")
    async def plotster(self, ctx, *, flags: PosterFlags):
        """Play Plotster with friends, or use solo: True to play alone."""
        await play_plotster(ctx, self.bot, flags.mode.value, flags.starting_year, flags.ending_year, timeout=flags.timeout, solo=flags.solo)

    @commands.max_concurrency(1, per=commands.BucketType.channel, wait=False)
    @commands.hybrid_command(name="quizster")
    async def quizster(self, ctx, *, flags: PosterFlags):
        """Play the Bollywood quiz with friends, or use solo: True to play alone."""
        await play_quizster(ctx, self.bot, flags.mode.value, flags.starting_year, flags.ending_year, timeout=flags.timeout, solo=flags.solo)

    @commands.max_concurrency(1, per=commands.BucketType.channel, wait=False)
    @commands.hybrid_command(name="poster", aliases=["poster_guess", "depixelate", "pixelate"])
    #async def poster_guess(self, ctx, mode: Poster_choice = Poster_choice.get_default(), starting_year=2010, ending_year=2023, timeout=15):
    async def poster_guess(self, ctx, *, flags: PosterFlags):
        """Guess movie posters with friends, or use solo: True to play alone."""
        await play_pixelate(ctx, self.bot, flags.mode.value, flags.starting_year, flags.ending_year, timeout=flags.timeout, solo=flags.solo)

    @commands.max_concurrency(1, per=commands.BucketType.channel, wait=False)
    @commands.hybrid_command(name="bingo")
    async def bingo(self, ctx, solo: bool = False):
        """Play Bingo with friends, or set solo to play against Pippo."""

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

            Complete five lines across, down, or diagonally to win.
            Use the Join and Start buttons in the lobby. Once the game begins, each player selects Get my board.
            Select a number only on your turn. In solo mode, Pippo takes its turn automatically.
            """
            emb = discord.Embed(title="Bingo!", description=desc)
            return emb

        await ctx.send(embed=instructions_embed())
        bot_joined_id = None
        if solo:
            people = [ctx.author.id]
            bot_user = self.bot.user
            bot_joined_id = bot_user.id
            people.append(bot_joined_id)
            await ctx.send("🤖 **Solo Mode!** Pippo has joined the Bingo match as your opponent.")
        else:
            lobby = GameLobbyView(ctx.author.id, ctx.author.display_name, "Bingo")
            lobby.message = await ctx.send(lobby.render(), view=lobby)
            await lobby.wait()
            if not lobby.started:
                return
            people = lobby.joined_ids

        players = {}
        for i in people:
            players[i] = Player(i)

        view = BingoStartView(players, bot_user_id=bot_joined_id)
        msg = await ctx.send(view=view)
        view.out = msg

    @commands.max_concurrency(1, per=commands.BucketType.channel, wait=False)
    @commands.hybrid_command(name="tictactoe")
    async def tictactoe(self, ctx, opponent: discord.Member = None):
        """Play a game of Tic Tac Toe (Solo vs Bot or vs a Friend)"""
        if opponent:
            if opponent.id == ctx.author.id or opponent.bot:
                view = TicTacToeView(player_x=ctx.author, vs_bot=True)
                msg = await ctx.send(f"🎮 **Tic Tac Toe (Solo vs Pippo 🤖)**!\n{ctx.author.mention} (X) v/s Pippo (O)\nIt is your turn (X)!", view=view)
                view.message = msg
                return

            invite_view = ChallengeInviteView(ctx.author, opponent, "Tic Tac Toe")
            invite_msg = await ctx.send(f"⚔️ {opponent.mention}, **{ctx.author.display_name}** has challenged you to a game of **Tic Tac Toe**!", view=invite_view)
            invite_view.message = invite_msg
            await invite_view.wait()

            if invite_view.accepted is not True:
                return

            view = TicTacToeView(player_x=ctx.author, player_o=opponent)
            msg = await ctx.send(f"🎮 **Tic Tac Toe**: {ctx.author.mention} (X) v/s {opponent.mention} (O)\nIt is now {ctx.author.mention}'s turn (X)!", view=view)
            view.message = msg
        else:
            view = TicTacToeView(player_x=ctx.author, vs_bot=True)
            msg = await ctx.send(f"🎮 **Tic Tac Toe (Solo vs Pippo 🤖)**!\n{ctx.author.mention} (X) v/s Pippo (O)\nIt is your turn (X)!", view=view)
            view.message = msg

    @commands.hybrid_command(name="memory")
    async def memorygame(self, ctx, opponent: discord.Member = None):
        """Play Memory Match (Solo Challenge or 1v1 vs a Friend)"""
        if opponent is None or opponent.bot or opponent.id == ctx.author.id:
            view = MemoryView(ctx.author)
            out = await ctx.reply("🃏 **Solo Memory Challenge Started!**\nFlip two cards at a time to find all 8 matching pairs in the fewest moves.", view=view)
            view.out = out
            return

        invite_view = ChallengeInviteView(ctx.author, opponent, "Memory Match")
        invite_msg = await ctx.send(f"🃏 {opponent.mention}, **{ctx.author.display_name}** has challenged you to a game of **Memory Match**!", view=invite_view)
        invite_view.message = invite_msg
        await invite_view.wait()

        if invite_view.accepted is not True:
            return

        view = MemoryView(ctx.author, opponent)
        out = await ctx.reply(f"🎮 Game started! {ctx.author.mention}'s turn.", view=view)
        view.out = out

    @commands.hybrid_command(name="flood")
    async def flood(self, ctx, solo: bool = False):
        """Play Flood with friends, or set solo to challenge Pippo."""
        color_emojis = {
            "red": 1133798766802129086,
            "green": 1133798762339373077,
            "magenta": 1133798753690730576,
            "blue": 1133798757817917670,
            "yellow": 1133798749248958495,
            "top_left": 1134477415192727563,
            "bottom_right": 1134477412487417997,
            "discord_loading": 1134482068391333898
        }
        unicode_emojis = {
            "red": "🟥",
            "green": "🟩",
            "magenta": "🟪",
            "blue": "🟦",
            "yellow": "🟨",
            "top_left": "↖️",
            "bottom_right": "↘️",
            "discord_loading": "⏳"
        }
        emojis = {}
        for k, v in color_emojis.items():
            emojis[k] = self.bot.get_emoji(v) or unicode_emojis[k]

        user1 = ctx.author     
        view = FloodView(user1, emojis)
        if solo:
            view.players.append(self.bot.user)
            view.vs_bot = True
            view.bot = self.bot
            view.flood = Flood(view.players)
            view.clear_items()
            view.populate_buttons()
            emb = view.return_embed()
            out = await ctx.reply(embed=emb, view=view, file=view.flood.return_image())
        else:
            emb = discord.Embed(title="Flood!", description=f"Choose **Play vs Pippo** for solo play, or wait for a friend to accept. {emojis['discord_loading']}")
            emb.set_image(url="https://i.imgur.com/XgGA46z.png")
            out = await ctx.reply(embed=emb, view=view)
        view.out = out
        view.bot = self.bot

    @commands.hybrid_command(name="npat")
    async def name_place_animal_thing(self, ctx):
        "Play Name, Place, Animal and Thing with your friend, like you used to do in school."
        await ctx.reply("Work in progress.")

    @commands.hybrid_command(name="clash")
    @commands.max_concurrency(1, per=commands.BucketType.channel, wait=False)
    async def ai_clash(self, ctx, solo: bool = False):
        "Fight a friend or challenge Pippo with any object, character, or concept. Set solo to play Pippo."
        
        # Create UI components for the clash game
        class ClashSubmitView(discord.ui.View):
            def __init__(self, timeout=120, solo=False):
                super().__init__(timeout=timeout)
                self.submissions = {}
                self.message = None
                self.solo = solo
                self.owner_id = ctx.author.id if solo else None

            async def interaction_check(self, interaction: discord.Interaction) -> bool:
                if self.solo and self.owner_id is not None and interaction.user.id != self.owner_id:
                    await interaction.response.send_message("This is someone else's solo duel.", ephemeral=True)
                    return False
                return True

            async def on_timeout(self):
                for item in self.children:
                    item.disabled = True
                if self.message:
                    try:
                        status = "Lobby expired without a creation." if not self.submissions else "Lobby expired. The submitted creation will face Pippo."
                        await self.message.edit(content=f"⏱️ {status}", view=self)
                    except Exception:
                        pass
            
            @discord.ui.button(label="Submit Creation", style=discord.ButtonStyle.primary)
            async def submit_button(self, interaction: discord.Interaction, button: discord.ui.Button):
                modal = ClashSubmitModal(self, solo=self.solo)
                await interaction.response.send_modal(modal)

            @discord.ui.button(label="Duel Pippo 🤖", style=discord.ButtonStyle.secondary)
            async def duel_bot_button(self, interaction: discord.Interaction, button: discord.ui.Button):
                modal = ClashSubmitModal(self, solo=True)
                await interaction.response.send_modal(modal)
                
        class ClashSubmitModal(discord.ui.Modal, title="Submit Your Creation"):
            creation = discord.ui.TextInput(
                label="What will you fight with?",
                placeholder="Enter any object, concept, or character...",
                required=True,
                max_length=100
            )
            
            def __init__(self, view, solo=False):
                super().__init__()
                self.view = view
                self.solo = solo
            
            async def on_submit(self, interaction: discord.Interaction):
                user_id = interaction.user.id
                if self.view.is_finished() or (self.view.solo and user_id != self.view.owner_id):
                    await interaction.response.send_message("This duel is already closed.", ephemeral=True)
                    return
                self.view.submissions[user_id] = self.creation.value
                
                await interaction.response.send_message(f"Your creation '{self.creation.value}' has been submitted!", ephemeral=True)
                
                if self.solo:
                    self.view.solo = True
                    self.view.owner_id = user_id
                    self.view.stop()
                    for item in self.view.children:
                        item.disabled = True
                    if self.view.message:
                        await self.view.message.edit(content="✅ Creation submitted. Pippo is entering the arena…", view=self.view)
                    return

                # Update the main message
                participants = []
                for uid in self.view.submissions:
                    user = interaction.client.get_user(uid)
                    participants.append(f"✅ @{user.display_name if user else 'Player'}")
                
                embed = discord.Embed(
                    title="Clash of Creations",
                    description=f"Submissions received:\n" + "\n".join(participants) + "\n\nThink of an object or concept you want to fight with.",
                    color=discord.Color.green()
                )
                try:
                    await self.view.message.edit(embed=embed)
                except Exception:
                    pass
                
                if len(self.view.submissions) >= 2:
                    await asyncio.sleep(2)
                    self.view.stop()
                    for item in self.view.children:
                        item.disabled = True
                    if self.view.message:
                        await self.view.message.edit(content="✅ Both creations are in. The duel is starting…", view=self.view)
        
        # Execute clash
        try:
            # Display welcome message and rules
            welcome_embed = discord.Embed(
                title="Welcome to Clash of Creations! ⚔️", 
                description=(
                    "**How to Play:**\n"
                    "1. This is a **creative duel** between two players or against **Pippo 🤖**!\n"
                    "2. **Submit any object, concept, or person** you want to fight with\n"
                    "3. An **AI judge** 🤖 will determine the winner\n\n"
                    "⏱️ **You have two minutes to submit your creation**\n\n"
                    "Click **'Submit Creation'** to duel another player, or **'Duel Pippo 🤖'** for an instant solo battle!"
                ),
                color=discord.Color.gold()
            )
            
            # Create and send the view with the submit button
            view = ClashSubmitView(solo=solo)
            view.message = await ctx.send(embed=welcome_embed, view=view)
            
            # Wait for submissions (timeout handled by the view)
            timed_out = await view.wait()
            
            # If timed out or not enough participants
            if len(view.submissions) == 0:
                await ctx.send("No creations submitted in time. The clash has been canceled.")
                return
            
            if len(view.submissions) == 1 or view.solo:
                player_id = view.owner_id if view.solo else next(iter(view.submissions))
                p1 = ctx.guild.get_member(player_id) if ctx.guild else None
                player1 = p1 or await self.bot.fetch_user(player_id)
                player1_creation = view.submissions[player_id]
                player2 = self.bot.user
                bot_creations = [
                    "A sentient samosa armed with laser-guided mint chutney",
                    "A rogue pressure cooker whistling in hypersonic frequencies",
                    "An infinite loop of dramatic Bollywood thunderclaps and violin screeches",
                    "A flying autorickshaw with unyielding meter rates",
                    "A grandmother wielding an indestructible flying chappal",
                    "A hyper-caffeinated Bollywood background dancer that multiplies upon impact",
                    "A runaway Mumbai local train during peak rush hour",
                    "A cup of cutting chai heated to nuclear core temperatures",
                    "A Bollywood hero who catches bullets with his teeth while sliding under a horse",
                    "An uncle giving unsolicited career advice with 100,000 decibels of conviction"
                ]
                player2_creation = random.choice(bot_creations)
                await ctx.send(f"🤖 **Solo Duel!** Pippo enters the arena wielding: **{player2_creation}**!")
            else:
                # Get the first two players who submitted
                player_ids = list(view.submissions.keys())[:2]
                p1 = ctx.guild.get_member(player_ids[0]) if ctx.guild else None
                p2 = ctx.guild.get_member(player_ids[1]) if ctx.guild else None
                player1 = p1 or await self.bot.fetch_user(player_ids[0])
                player2 = p2 or await self.bot.fetch_user(player_ids[1])
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
            result_embed.add_field(name="Reason", value=reason[:1024], inline=False)
            # You can add a victory image here if you have one
            
            await ctx.send(embed=result_embed)
            
            # Add rematch button (implementing as a simple message for now)
            # await ctx.send("🔄 Rematch [2/2]")
        
        except Exception as e:
            await ctx.send(f"An error occurred during the clash: {str(e)}")


async def setup(bot):
    await bot.add_cog(Games(bot))
