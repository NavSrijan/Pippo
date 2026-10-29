from cogs.play import offer_game_mode
from runtime import run_blocking
import asyncio
import csv
import random
import re
from typing import Union
import datetime
from enum import Enum
import os
import aiohttp
import logging

import discord
from flood import Flood
from discord.ext import commands
from utils.clash import judge_clash
from io import BytesIO


from views import PlotsterView, QuizsterView, BingoStartView, TicTacToeView, MemoryView, FloodView, GuessTheMovieView, ChallengeInviteView, GameLobbyView, NpatLobbyView, NpatRoundView, bingo_art_file, tictactoe_art_file, memory_art_file, flood_art_file, clash_art_file, npat_art_file
from utils.bollywood_utils import play_game, play_pixelate, play_plotster, play_quizster

log = logging.getLogger(__name__)

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
    mode: Poster_choice = commands.flag(default=Poster_choice.get_default(), description='Choose Bollywood, Hollywood, or mixed movies')
    starting_year: int = commands.flag(default=2010, description='The starting year')
    ending_year: int = commands.flag(default=discord.utils.utcnow().year, description='The ending year')
    timeout: int = commands.flag(default=15, description='The timeout period in seconds')

class BollywoodFlags(commands.FlagConverter):
    starting_year: int = commands.flag(default=2010, description='The starting year')
    ending_year: int = commands.flag(default=discord.utils.utcnow().year, description='The ending year')
    timeout: int = commands.flag(default=15, description='The timeout period in seconds')

class Games(commands.Cog):
    """Games"""

    def __init__(self, bot):
        self.bot = bot


    @commands.max_concurrency(1, per=commands.BucketType.member, wait=False)
    @commands.hybrid_command(name="bollywood")
    async def bollywood_game(self, ctx, *, flags: BollywoodFlags):
        """Guess Bollywood movies with friends, or choose Play solo on the start screen."""
        if await offer_game_mode(ctx, "bollywood", flags=flags):
            return
        solo = ctx._pippo_play_mode
        flags = ctx._pippo_options.get("flags", flags)
        await play_game(ctx, self.bot, "bollywood", flags.starting_year, flags.ending_year, ["data/bollywood/"], flags.timeout, solo=solo)
    
    @commands.max_concurrency(1, per=commands.BucketType.member, wait=False)
    @commands.hybrid_command(name="hollywood")
    async def hollywood_game(self, ctx, *, flags: BollywoodFlags):
        """Guess Hollywood movie titles; send title: <answer> for a bonus shot."""
        if await offer_game_mode(ctx, "hollywood", flags=flags):
            return
        solo = ctx._pippo_play_mode
        flags = ctx._pippo_options.get("flags", flags)
        await play_game(ctx, self.bot, "hollywood", flags.starting_year, flags.ending_year, ["data/hollywood/"], flags.timeout, solo=solo)

    @commands.max_concurrency(1, per=commands.BucketType.member, wait=False)
    @commands.hybrid_command(name="plotster")
    async def plotster(self, ctx, *, flags: PosterFlags):
        """Solve movie mysteries from keywords; use hints or play solo."""
        if await offer_game_mode(ctx, "plotster", flags=flags):
            return
        solo = ctx._pippo_play_mode
        flags = ctx._pippo_options.get("flags", flags)
        await play_plotster(ctx, self.bot, flags.mode.value, flags.starting_year, flags.ending_year, timeout=flags.timeout, solo=solo)

    @commands.max_concurrency(1, per=commands.BucketType.member, wait=False)
    @commands.hybrid_command(name="quizster")
    async def quizster(self, ctx, *, flags: PosterFlags):
        """Play Bollywood, Hollywood, or mixed movie trivia with friends or solo."""
        if await offer_game_mode(ctx, "quizster", flags=flags):
            return
        solo = ctx._pippo_play_mode
        flags = ctx._pippo_options.get("flags", flags)
        await play_quizster(ctx, self.bot, flags.mode.value, flags.starting_year, flags.ending_year, timeout=flags.timeout, solo=solo)

    @commands.max_concurrency(1, per=commands.BucketType.member, wait=False)
    @commands.hybrid_command(name="poster", aliases=["poster_guess", "depixelate", "pixelate"])
    #async def poster_guess(self, ctx, mode: Poster_choice = Poster_choice.get_default(), starting_year=2010, ending_year=2023, timeout=15):
    async def poster_guess(self, ctx, *, flags: PosterFlags):
        """Name a movie from its poster; earlier guesses score more. Play solo or with friends."""
        if await offer_game_mode(ctx, "poster", flags=flags):
            return
        solo = ctx._pippo_play_mode
        flags = ctx._pippo_options.get("flags", flags)
        await play_pixelate(ctx, self.bot, flags.mode.value, flags.starting_year, flags.ending_year, timeout=flags.timeout, solo=solo)

    @commands.max_concurrency(1, per=commands.BucketType.member, wait=False)
    @commands.hybrid_command(name="bingo")
    async def bingo(self, ctx):
        """Play old-school 1–25 classroom Bingo with friends or Pippo solo."""
        if await offer_game_mode(ctx, "bingo"):
            return
        solo = ctx._pippo_play_mode

        # Functions

        class Player():
            def __init__(self, user_id):
                self.id = user_id
                self.started = False
                self.cut = []
                self.global_cut = []
                self.msg = None
                self.view = None
                self.completed_lines = 0
                self.generate_random_ints_list(25)

            def generate_random_ints_list(self, n):
                numbers = [str(value) for value in range(1, n + 1)]
                random.shuffle(numbers)
                self.number_list = [numbers[index:index + 5] for index in range(0, 25, 5)]


        def instructions_embed():
            desc = (
                "Old-school classroom Bingo: everyone gets a shuffled **1–25** ticket. Complete **five lines** "
                "across, down, or diagonally to win.\n\n"
                "On your turn, choose an unmarked number on your ticket. Everyone marks that number if it is "
                "on their ticket. In solo mode, Pippo picks from its own ticket."
            )
            emb = discord.Embed(title="🎱 Pippo Bingo", description=desc, color=discord.Color.from_rgb(95, 67, 140))
            return emb, bingo_art_file(emb, "bingo_start")

        instructions, art = await run_blocking(instructions_embed)
        if art:
            await ctx.send(embed=instructions, file=art)
        else:
            await ctx.send(embed=instructions)
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
        await view.game_finished.wait()

    @commands.max_concurrency(1, per=commands.BucketType.member, wait=False)
    @discord.app_commands.choices(difficulty=[
        discord.app_commands.Choice(name="Easy", value="easy"),
        discord.app_commands.Choice(name="Normal", value="normal"),
        discord.app_commands.Choice(name="Hard", value="hard"),
    ])
    @discord.app_commands.describe(
        opponent="Preselect a friend for Play with friends; choose Play solo to face Pippo.",
        difficulty="Pippo's solo difficulty: easy, normal, or hard.",
    )
    @commands.hybrid_command(name="tictactoe")
    async def tictactoe(self, ctx, opponent: discord.Member = None, difficulty: str = "normal"):
        """Play Tic Tac Toe with a friend or Pippo at easy, normal, or hard difficulty."""
        if await offer_game_mode(ctx, "tictactoe", opponent=opponent, difficulty=difficulty):
            return
        solo = ctx._pippo_play_mode
        opponent = ctx._pippo_options.get("opponent", opponent)
        difficulty = ctx._pippo_options.get("difficulty", difficulty)
        difficulty = difficulty.strip().lower()
        if difficulty not in {"easy", "normal", "hard"}:
            await ctx.send("Choose a difficulty of `easy`, `normal`, or `hard`.")
            return

        async def start_board(view, content, title):
            embed = discord.Embed(
                title=title,
                description="Tap an empty square to place your mark. First to three in a row wins.",
                color=discord.Color.from_rgb(54, 112, 190),
            )
            artwork = await run_blocking(tictactoe_art_file, embed, "tictactoe_start")
            options = {"content": content, "embed": embed, "view": view}
            if artwork:
                options["file"] = artwork
            view.message = await ctx.send(**options)

        if opponent:
            if opponent.bot and opponent.id != getattr(self.bot.user, "id", None):
                await ctx.send("I can challenge a human or play solo, but I can't start a match against another bot.")
                return
            if opponent.id == ctx.author.id or opponent.bot:
                view = TicTacToeView(player_x=ctx.author, vs_bot=True, difficulty=difficulty)
                content = (
                    f"🎮 **Solo vs Pippo** · {ctx.author.mention} (X) vs Pippo (O)\n"
                    f"Difficulty: **{difficulty.title()}** · Your move!"
                )
                await start_board(view, content, f"Pippo's Tic Tac Toe · {difficulty.title()}")
                return

            invite_view = ChallengeInviteView(ctx.author, opponent, "Tic Tac Toe")
            invite_msg = await ctx.send(f"⚔️ {opponent.mention}, **{ctx.author.display_name}** has challenged you to a game of **Tic Tac Toe**!", view=invite_view)
            invite_view.message = invite_msg
            await invite_view.wait()

            if invite_view.accepted is not True:
                return

            view = TicTacToeView(player_x=ctx.author, player_o=opponent)
            content = f"🎮 **Tic Tac Toe** · {ctx.author.mention} (X) vs {opponent.mention} (O)\n{ctx.author.mention}, you move first."
            await start_board(view, content, "Tic Tac Toe · Challenge accepted")
        else:
            view = TicTacToeView(player_x=ctx.author, vs_bot=True, difficulty=difficulty)
            content = (
                f"🎮 **Solo vs Pippo** · {ctx.author.mention} (X) vs Pippo (O)\n"
                f"Difficulty: **{difficulty.title()}** · Your move!"
            )
            await start_board(view, content, f"Pippo's Tic Tac Toe · {difficulty.title()}")

    @commands.hybrid_command(name="memory")
    async def memorygame(self, ctx, opponent: discord.Member = None):
        """Match eight pairs solo or challenge a friend; pairs keep your turn."""
        if await offer_game_mode(ctx, "memory", opponent=opponent):
            return
        solo = ctx._pippo_play_mode
        opponent = ctx._pippo_options.get("opponent", opponent)
        async def start_board(view, content):
            embed = discord.Embed(
                title="Pippo Memory Match",
                description="Find all eight pairs. A match keeps your turn; a miss passes it. Solo games earn up to three stars for fewer moves.",
                color=discord.Color.from_rgb(54, 112, 190),
            )
            artwork = await run_blocking(memory_art_file, embed, "memory_start")
            options = {"content": content, "embed": embed, "view": view}
            if artwork:
                options["file"] = artwork
            view.out = await ctx.reply(**options)

        if opponent and opponent.bot and opponent.id != getattr(self.bot.user, "id", None):
            await ctx.send("I can challenge a human or play solo, but I can't start a match against another bot.")
            return
        if opponent is None or opponent.bot or opponent.id == ctx.author.id:
            view = MemoryView(ctx.author)
            await start_board(view, "🃏 **Solo Memory Challenge** · Match eight pairs in as few moves as you can.")
            return

        invite_view = ChallengeInviteView(ctx.author, opponent, "Memory Match")
        invite_msg = await ctx.send(f"🃏 {opponent.mention}, **{ctx.author.display_name}** has challenged you to a game of **Memory Match**!", view=invite_view)
        invite_view.message = invite_msg
        await invite_view.wait()

        if invite_view.accepted is not True:
            return

        view = MemoryView(ctx.author, opponent)
        await start_board(view, f"🎮 **Game started!** {ctx.author.mention} flips first.")

    @commands.hybrid_command(name="flood")
    async def flood(self, ctx):
        """Play Flood with friends, or choose Play solo to challenge Pippo."""
        if await offer_game_mode(ctx, "flood"):
            return
        solo = ctx._pippo_play_mode
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
        view.bot = self.bot
        if solo:
            view.players.append(self.bot.user)
            view.vs_bot = True
            view.flood = Flood(view.players)
            view.clear_items()
            view.populate_buttons()
            emb = view.return_embed()
            art = await run_blocking(flood_art_file, emb, "flood_scene")
            files = [view.flood.return_image()]
            if art:
                files.append(art)
            out = await ctx.reply(embed=emb, view=view, files=files)
        else:
            emb = discord.Embed(
                title="Pippo Flood · Territory Tug-of-War",
                description=f"Join this two-player match. Claim colours and race past 50%. {emojis['discord_loading']}",
                color=discord.Color.blue(),
            )
            art = await run_blocking(flood_art_file, emb, "flood_scene")
            if art:
                emb.set_image(url="attachment://flood_scene.jpg")
                out = await ctx.reply(embed=emb, view=view, file=art)
            else:
                out = await ctx.reply(embed=emb, view=view)
        view.out = out

    @commands.hybrid_command(name="npat")
    @commands.max_concurrency(1, per=commands.BucketType.member, wait=False)
    async def name_place_animal_thing(self, ctx):
        "Play five timed Name, Place, Animal and Thing rounds with up to five friends."
        if await offer_game_mode(ctx, "npat"):
            return
        solo = ctx._pippo_play_mode
        if solo:
            player_ids = [ctx.author.id]
        else:
            lobby = NpatLobbyView(ctx.author.id, ctx.author.display_name, "Name Place Animal Thing", max_players=6)
            lobby.message = await ctx.send(lobby.render(), view=lobby)
            await lobby.wait()
            if not lobby.started:
                return
            player_ids = list(lobby.joined_ids)
        scores = {user_id: 0 for user_id in player_ids}
        letters = random.sample("ABCDEFGHIJKLMNOPRSTUVWY", 5)
        categories = ("Name", "Place", "Animal", "Thing")

        for round_number, letter in enumerate(letters, start=1):
            view = NpatRoundView(player_ids, {}, letter, round_number, timeout=45)
            prompt = view.status_embed()
            artwork = await run_blocking(npat_art_file, prompt, "npat_round")
            send_options = {"embed": prompt, "view": view}
            if artwork:
                send_options["file"] = artwork
            view.message = await ctx.send(**send_options)
            await view.wait()

            valid_answers = {category: {} for category in categories}
            round_points = {user_id: 0 for user_id in player_ids}
            for user_id, answers in view.submissions.items():
                for category, answer in answers.items():
                    cleaned = " ".join(answer.split())
                    if cleaned and cleaned[0].casefold() == letter.casefold():
                        key = " ".join(cleaned.casefold().split())
                        valid_answers[category].setdefault(key, []).append(user_id)

            for category in categories:
                for owners in valid_answers[category].values():
                    points = 10 if len(owners) == 1 else 5
                    for user_id in owners:
                        round_points[user_id] += points

            result = discord.Embed(
                title=f"Round {round_number} reveal · {letter}",
                description="Unique answers score **10**, shared answers score **5** each. Starting letters are checked automatically; categories are honour system.",
                color=discord.Color.green(),
            )
            for user_id in player_ids:
                answers = view.submissions.get(user_id)
                if answers is None:
                    result.add_field(name=f"<@{user_id}> · no card", value="No answers locked before time ran out. **+0**", inline=False)
                    continue
                lines = []
                correct_count = 0
                for category in categories:
                    answer = " ".join(answers[category].split())
                    key = " ".join(answer.casefold().split())
                    owners = valid_answers[category].get(key, []) if answer and answer[0].casefold() == letter.casefold() else []
                    if owners:
                        correct_count += 1
                        points = 10 if len(owners) == 1 else 5
                        note = "unique · 10" if points == 10 else f"shared · {points}"
                    else:
                        points = 0
                        note = "wrong letter / blank · 0"
                    escaped_answer = discord.utils.escape_markdown(answer or "—")
                    lines.append(f"**{category}:** {escaped_answer} ({note})")
                bonus = 5 if correct_count == len(categories) else 0
                round_points[user_id] += bonus
                scores[user_id] += round_points[user_id]
                if bonus:
                    lines.append("✨ **Perfect card bonus: +5**")
                result.add_field(
                    name=f"<@{user_id}> · +{round_points[user_id]} this round",
                    value="\n".join(lines),
                    inline=False,
                )
            result.set_footer(text=f"Round {round_number}/5 · Match answers wisely: shared answers score, blanks don't.")
            result_art = await run_blocking(npat_art_file, result, "npat_reveal")
            edit_options = {
                "embed": result,
                "view": None,
                "attachments": [result_art] if result_art else [],
                "allowed_mentions": discord.AllowedMentions.none(),
            }
            try:
                await view.message.edit(**edit_options)
            except discord.HTTPException:
                if result_art:
                    await ctx.send(embed=result, file=result_art, allowed_mentions=discord.AllowedMentions.none())
                else:
                    await ctx.send(embed=result, allowed_mentions=discord.AllowedMentions.none())

        ranking = sorted(player_ids, key=lambda user_id: scores[user_id], reverse=True)
        top_score = scores[ranking[0]] if ranking else 0
        winners = [user_id for user_id in ranking if scores[user_id] == top_score]
        final = discord.Embed(
            title="🏆 NPAT final scores",
            description=(
                f"{' and '.join(f'<@{user_id}>' for user_id in winners)} "
                f"{'win' if len(winners) == 1 else 'tie'} with **{top_score}** points!"
            ),
            color=discord.Color.gold(),
        )
        final.add_field(
            name="Leaderboard",
            value="\n".join(f"**{position}.** <@{user_id}> — **{scores[user_id]}**" for position, user_id in enumerate(ranking, start=1)),
            inline=False,
        )
        final_art = await run_blocking(npat_art_file, final, "npat_winner")
        if final_art:
            await ctx.send(embed=final, file=final_art, allowed_mentions=discord.AllowedMentions.none())
        else:
            await ctx.send(embed=final, allowed_mentions=discord.AllowedMentions.none())

    @commands.hybrid_command(name="clash")
    @commands.max_concurrency(1, per=commands.BucketType.member, wait=False)
    async def ai_clash(self, ctx):
        "Challenge a friend or Pippo to a creative duel."
        if await offer_game_mode(ctx, "clash"):
            return
        solo = ctx._pippo_play_mode
        
        # Create UI components for the clash game
        class ClashSubmitView(discord.ui.View):
            def __init__(self, timeout=120, solo=False):
                super().__init__(timeout=timeout)
                self.submissions = {}
                self.message = None
                self.solo = solo
                self.owner_id = ctx.author.id if solo else None
                self.lock = asyncio.Lock()
                self.starting = False

            async def update_status(self, embed):
                artwork = await run_blocking(clash_art_file, embed, "clash_lobby")
                if self.message:
                    try:
                        await self.message.edit(embed=embed, view=self, attachments=[artwork] if artwork else [])
                    except discord.HTTPException:
                        pass

            async def interaction_check(self, interaction: discord.Interaction) -> bool:
                if self.solo and self.owner_id is not None and interaction.user.id != self.owner_id:
                    await interaction.response.send_message("This is someone else's solo duel.", ephemeral=True)
                    return False
                return True

            async def on_timeout(self):
                for item in self.children:
                    item.disabled = True
                if self.message:
                    if self.submissions and not self.solo:
                        title = "⏱️ Clash lobby expired"
                        description = "A second fighter did not join. Run `/clash` and choose Play solo to face Pippo."
                    else:
                        title = "⏱️ Clash lobby expired"
                        description = "No creations were submitted. Run `/clash` to open another arena."
                    embed = discord.Embed(title=title, description=description, color=discord.Color.orange())
                    await self.update_status(embed)
            
            @discord.ui.button(label="Submit Creation", style=discord.ButtonStyle.primary)
            async def submit_button(self, interaction: discord.Interaction, button: discord.ui.Button):
                modal = ClashSubmitModal(self, solo=self.solo)
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
                view = self.view
                await interaction.response.defer(ephemeral=True)
                async with view.lock:
                    if view.is_finished() or view.starting or (view.solo and user_id != view.owner_id):
                        await interaction.followup.send("This duel is already closed.", ephemeral=True)
                        return
                    if self.solo and any(uid != user_id for uid in view.submissions):
                        await interaction.followup.send(
                            "A friend has already submitted. Finish that duel or open a fresh solo clash.",
                            ephemeral=True,
                        )
                        return
                    if not self.solo and user_id not in view.submissions and len(view.submissions) >= 2:
                        await interaction.followup.send("Both fighter slots are full.", ephemeral=True)
                        return

                    view.submissions[user_id] = self.creation.value.strip()
                    start_solo = self.solo
                    start_duel = not start_solo and len(view.submissions) >= 2
                    if start_solo:
                        view.solo = True
                        view.owner_id = user_id
                        view.submissions = {user_id: self.creation.value.strip()}
                    if start_duel:
                        view.starting = True

                    await interaction.followup.send("Your creation is locked in. The arena is getting ready…", ephemeral=True)
                    if start_solo:
                        for item in view.children:
                            item.disabled = True
                        embed = discord.Embed(
                            title="✅ Solo creation locked in",
                            description="Pippo is entering the arena.",
                            color=discord.Color.green(),
                        )
                        await view.update_status(embed)
                        view.stop()
                        return

                    participants = []
                    for uid in view.submissions:
                        user = interaction.client.get_user(uid)
                        participants.append(user.display_name if user else "Player")
                    embed = discord.Embed(
                        title="Clash of Creations",
                        description="Fighters in the arena:\n" + "\n".join(f"⚔️ {name}" for name in participants),
                        color=discord.Color.green(),
                    )
                    if start_duel:
                        embed.description += "\n\nBoth creations are in. The duel is starting…"
                        for item in view.children:
                            item.disabled = True
                    await view.update_status(embed)
                    if start_duel:
                        view.stop()
        
        # Execute clash
        try:
            # Display welcome message and rules
            welcome_embed = discord.Embed(
                title="Welcome to Clash of Creations! ⚔️", 
                description=(
                    "**How to Play:**\n"
                    "1. This is a **creative duel** between two players or against **Pippo 🤖**!\n"
                    "2. **Submit any object, character, or concept** you want to fight with\n"
                    "3. An **AI judge** 🤖 will determine the winner\n\n"
                    "Matches keep your creation private until both fighters are ready.\n"
                    "⏱️ **You have two minutes to submit**\n\n"
                    "Submit your creation to enter the selected game mode."
                ),
                color=discord.Color.gold()
            )
            welcome_art = await run_blocking(clash_art_file, welcome_embed, "clash_start")
            
            # Create and send the view with the submit button
            view = ClashSubmitView(solo=solo)
            if welcome_art:
                view.message = await ctx.send(embed=welcome_embed, view=view, file=welcome_art)
            else:
                view.message = await ctx.send(embed=welcome_embed, view=view)
            
            # Wait for submissions (timeout handled by the view)
            await view.wait()
            
            # If timed out or not enough participants
            if not view.submissions or (not view.solo and len(view.submissions) < 2):
                return
            
            if view.solo:
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
                title=f"{player1.display_name} vs {player2.display_name} · The Arena 🏟️",
                description="Two wildly different creations enter. The judge is weighing their strengths…",
                color=discord.Color.red()
            )
            arena_embed.add_field(name=player1.display_name, value=player1_creation, inline=False)
            arena_embed.add_field(name=player2.display_name, value=player2_creation, inline=False)
            arena_art = await run_blocking(clash_art_file, arena_embed, "clash_arena")
            if arena_art:
                await ctx.send(embed=arena_embed, file=arena_art)
            else:
                await ctx.send(embed=arena_embed)
            
            # Add a short delay for suspense
            await asyncio.sleep(2)
            
            # Judge the clash
            winner, reason = await judge_clash(player1, player1_creation, player2, player2_creation, bot=self.bot)
            
            # Announce result
            result_embed = discord.Embed(
                title="The Victor 🏆",
                description=f"**{winner.display_name}** wins with **{player1_creation if winner == player1 else player2_creation}**.",
                color=discord.Color.gold()
            )
            result_embed.add_field(name="Judge's verdict", value=reason[:1024], inline=False)
            result_art = await run_blocking(clash_art_file, result_embed, "clash_result")
            if result_art:
                await ctx.send(embed=result_embed, file=result_art)
            else:
                await ctx.send(embed=result_embed)
        
        except Exception:
            log.exception("Clash failed")
            await ctx.send("The duel hit a snag before the verdict. Please start another `/clash`.")


async def setup(bot):
    await bot.add_cog(Games(bot))
