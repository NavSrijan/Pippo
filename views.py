from runtime import run_blocking
import discord
import random
import asyncio
from typing import List
from pathlib import Path

from flood import Flood
from functions import write_caption_on_image


def _captioned_art_file(embed, name, folder, thumbnail=False):
    art_dir = Path(__file__).resolve().parent / "imgs" / folder
    scenes = sorted(path for ext in ("jpg", "png", "webp") for path in art_dir.glob(f"scene_*.{ext}"))
    if not scenes:
        return None
    artwork = random.choice(scenes)
    filename = f"{name}.jpg"
    file = write_caption_on_image(artwork, embed.title, embed.description, filename)
    if thumbnail:
        embed.set_thumbnail(url=f"attachment://{filename}")
    else:
        embed.set_image(url=f"attachment://{filename}")
    return file


class HintsView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=60)
        self.hint_given = False
        self.random_letter_given = False
        self.synopsis_given = False
        self.out = None
        self.resolved = False

    async def finish(self):
        self.resolved = True
        self.stop()
        for child in self.children:
            child.disabled = True
        if self.out is not None:
            try:
                await self.out.edit(view=self)
            except discord.HTTPException:
                pass

    async def on_timeout(self):
        await self.finish()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if self.resolved:
            await interaction.response.send_message("This movie round has ended.", ephemeral=True)
            return False
        owner_id = getattr(self, "author_id", None)
        if owner_id is not None and interaction.user.id != owner_id:
            await interaction.response.send_message("Only the player who started this solo game can use hints.", ephemeral=True)
            return False
        return True

    def reset(self):
        self.hint_given = False
        self.random_letter_given = False
        self.synopsis_given = False
        for child in self.children:
            child.disabled = False

    @discord.ui.button(label='Reveal Cast', style=discord.ButtonStyle.green)
    async def green(self, interaction: discord.Interaction,
                    button: discord.ui.Button):
        if self.tries <= 1:
            await interaction.response.send_message("You need at least 2 tries to reveal the cast.", ephemeral=True)
            return
        button.disabled = True
        await interaction.response.defer()
        await interaction.followup.send(self.hint)
        if self.hint_given is False:
            self.tries -= 1
            self.hint_given = True
        refresh = getattr(self, "refresh_puzzle", None)
        if refresh:
            await refresh()
        await self.out.edit(view=self)

    @discord.ui.button(label='Random Letter', style=discord.ButtonStyle.blurple)
    async def blue(self, interaction: discord.Interaction,
                    button: discord.ui.Button):
        if self.tries <= 3:
            await interaction.response.send_message("You need at least 4 tries to reveal a letter.", ephemeral=True)
            return
        remaining_letters = getattr(self, "answer_letters", set()) - getattr(self, "revealed_letters", set())
        if len(remaining_letters) <= 1:
            await interaction.response.send_message("Only one letter remains. Save your tries and guess it!", ephemeral=True)
            return
        button.disabled = True
        await interaction.response.defer()
        if self.random_letter_given is False:
            self.random_letter = random.choice(sorted(remaining_letters))
            self.revealed_letters.add(self.random_letter)
            self.tries -= 2
            self.random_letter_given = True
        await interaction.followup.send(f"Random Letter revealed: **{self.random_letter.upper()}**")
        refresh = getattr(self, "refresh_puzzle", None)
        if refresh:
            await refresh()
        await self.out.edit(view=self)

    @discord.ui.button(label='Summary', style=discord.ButtonStyle.red)
    async def red(self, interaction: discord.Interaction,
                  button: discord.ui.Button):
        if self.tries <= 5:
            await interaction.response.send_message("You need at least 6 tries to reveal the synopsis.", ephemeral=True)
            return
        button.disabled = True
        await interaction.response.defer()
        await interaction.followup.send(f"Synopsis: **{self.synopsis}**")
        if self.synopsis_given is False:
            self.tries -= 5
            self.synopsis_given = True
        refresh = getattr(self, "refresh_puzzle", None)
        if refresh:
            await refresh()
        await self.out.edit(view=self)

class PlotsterView(discord.ui.View):

    def __init__(self, movie, solo_user_id=None, timeout=60):
        super().__init__(timeout=timeout)
        self.movie = movie
        self.solo_user_id = solo_user_id
        self.hint_cost = 0
        self.resolved = False
        self.out = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if self.solo_user_id is not None and interaction.user.id != self.solo_user_id:
            await interaction.response.send_message("Only the player who started this solo game can use hints.", ephemeral=True)
            return False
        if self.resolved:
            await interaction.response.send_message("This movie round is over.", ephemeral=True)
            return False
        return True

    async def reveal(self, interaction, button, message, cost):
        if button.disabled:
            await interaction.response.send_message("That hint has already been used this round.", ephemeral=True)
            return
        button.disabled = True
        self.hint_cost += cost
        await interaction.response.send_message(message)
        refresh = getattr(self, "refresh_embed", None)
        if refresh:
            await refresh()
        elif self.out:
            await self.out.edit(view=self)

    async def finish(self):
        if self.resolved:
            return
        self.resolved = True
        for item in self.children:
            item.disabled = True
        self.stop()
        if self.out:
            await self.out.edit(view=self)

    async def on_timeout(self):
        await self.finish()

    @discord.ui.button(label="Cast clue (-1 point)", style=discord.ButtonStyle.green)
    async def cast_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        cast = self.movie.get("actors") or "Cast information is not available."
        await self.reveal(interaction, button, f"🎭 **Cast clue:** {cast}", 1)

    @discord.ui.button(label="Film details (-1 point)", style=discord.ButtonStyle.blurple)
    async def details_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        movie = self.movie
        year = (movie.get("datePublished") or "").split("-")[0] or "unknown"
        genre = movie.get("genre") or "unknown"
        await self.reveal(interaction, button, f"📽️ **Film details:** {year} · {genre}", 1)

    @discord.ui.button(label="Plot summary (-2 points)", style=discord.ButtonStyle.red)
    async def synopsis_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        synopsis = self.movie.get("description") or "A plot summary is not available."
        await self.reveal(interaction, button, f"📝 **Plot summary:** {synopsis}", 2)



class QuizButton(discord.ui.Button):
    def __init__(self, label: str, option: str, index: int):
        super().__init__(style=discord.ButtonStyle.blurple, label=f"{label}. {option[:70]}", row=0)
        self.option_index = index

    async def callback(self, interaction: discord.Interaction):
        view = self.view
        if view.resolved:
            await interaction.response.send_message("This round is over.", ephemeral=True)
            return
        if interaction.user.id not in view.people_playing:
            await interaction.response.send_message("You are not playing this quiz.", ephemeral=True)
            return
        if interaction.user.id in view.users:
            await interaction.response.send_message("You already answered this round.", ephemeral=True)
            return
        view.users[interaction.user.id] = self.option_index
        await interaction.response.send_message("Answer locked in. Good luck!", ephemeral=True)
        if len(view.users) >= len(view.people_playing):
            await view.compare_answers()


class QuizsterView(discord.ui.View):
    def __init__(self, quiz_obj, timeout=60, people=None, people_playing=None,
                 skips=1, hints=3, streaks=None):
        super().__init__(timeout=timeout)
        self.quiz_obj = quiz_obj
        self.users = {}
        self.skipping_users = set()
        self.resolved = False
        self.skipped = False
        self.people = people if people is not None else {}
        self.people_playing = people_playing if people_playing is not None else []
        self.skips = skips
        self.hints = hints
        self.hint_given = False
        self.streaks = streaks if streaks is not None else {}
        self.round_results = {}
        for index, option in enumerate(quiz_obj.options):
            label = "ABCD"[index]
            self.add_item(QuizButton(label, str(option), index))

    async def on_timeout(self):
        await self.compare_answers()

    def disable_view(self):
        for child in self.children:
            child.disabled = True

    async def compare_answers(self):
        if self.resolved:
            return
        self.resolved = True
        if not self.skipped:
            answer_index = self.quiz_obj.answer_index
            for user_id in list(self.people_playing):
                answer = self.users.get(user_id)
                correct = answer == answer_index
                points = 0
                if correct:
                    self.streaks[user_id] = self.streaks.get(user_id, 0) + 1
                    points = 1
                    if self.streaks[user_id] >= 3:
                        points += 1
                        self.streaks[user_id] = 0
                else:
                    self.streaks[user_id] = 0
                    self.people[user_id][0] = max(0, self.people[user_id][0] - 1)
                    if self.people[user_id][0] == 0:
                        self.people_playing.remove(user_id)
                self.people[user_id][1] += points
                self.round_results[user_id] = {
                    "correct": correct,
                    "answered": answer is not None,
                    "points": points,
                    "bonus": max(0, points - 1),
                    "streak": self.streaks.get(user_id, 0),
                }
        self.disable_view()
        self.stop()
        if getattr(self, "response", None):
            await self.response.edit(view=self)

    @discord.ui.button(label="Hint", style=discord.ButtonStyle.green, row=1)
    async def hint_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.resolved:
            await interaction.response.send_message("This round is over.", ephemeral=True)
            return
        if interaction.user.id not in self.people_playing:
            await interaction.response.send_message("You are not playing this quiz.", ephemeral=True)
            return
        if self.hint_given:
            await interaction.response.send_message("The hint for this round has already been revealed.", ephemeral=True)
            return
        if self.hints <= 0:
            await interaction.response.send_message("Your team is out of hints.", ephemeral=True)
            return
        self.hint_given = True
        self.hints -= 1
        button.disabled = True
        await interaction.response.send_message(f"🔎 Quiz hint: {self.quiz_obj.hint}")
        if getattr(self, "response", None):
            await self.response.edit(view=self)

    @discord.ui.button(label="Skip", style=discord.ButtonStyle.red, row=1)
    async def skip_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.resolved:
            await interaction.response.send_message("This round is over.", ephemeral=True)
            return
        if interaction.user.id not in self.people_playing:
            await interaction.response.send_message("You are not playing this quiz.", ephemeral=True)
            return
        if self.skips <= 0:
            await interaction.response.send_message("Your team is out of skips.", ephemeral=True)
            return
        self.skipping_users.add(interaction.user.id)
        threshold = len(self.people_playing) // 2 + 1
        votes = len(self.skipping_users.intersection(self.people_playing))
        if votes >= threshold:
            self.skips -= 1
            self.skipped = True
            self.users.clear()
            await interaction.response.send_message("The team skipped this round.", ephemeral=True)
            await self.compare_answers()
        else:
            await interaction.response.send_message(f"Skip vote recorded ({votes}/{threshold}).", ephemeral=True)


# Bingo Views

def bingo_art_file(embed, name="bingo"):
    """Attach randomized Pippo Bingo art with the current title overlaid."""
    return _captioned_art_file(embed, name, "bingo")


def tictactoe_art_file(embed, name="tictactoe"):
    """Attach a randomized Pippo Tic Tac Toe scene with readable text."""
    return _captioned_art_file(embed, name, "tictactoe")


class BingoButton(discord.ui.Button):
    def __init__(self, glob, player, label: str, row, disabled=False,
                 style=discord.ButtonStyle.green, value=None):
        super().__init__(style=style, label=label, row=row, disabled=disabled)
        self.label = label
        self.value = label if value is None else value
        self.player = player
        self.glob = glob

    @staticmethod
    def format_call(number):
        return str(number)

    def check_winner(self, board, called):
        """Count completed rows, columns, and diagonals on a 5-by-5 card."""
        size = len(board)
        called = set(called)
        lines = list(board)
        lines.extend([[board[row][column] for row in range(size)] for column in range(size)])
        lines.append([board[index][index] for index in range(size)])
        lines.append([board[index][size - index - 1] for index in range(size)])
        return sum(all(value in called for value in line) for line in lines)

    def increase_turn(self):
        self.glob.turn = (self.glob.turn + 1) % len(self.glob.players)

    def select_bot_number(self, player):
        """Pick a random number from Pippo's own unmarked ticket, like the old game."""
        available = [
            value for row in player.number_list for value in row
            if value not in self.glob.called_numbers
        ]
        return random.choice(available) if available else None

    async def resolve_call(self, caller_id, label, channel):
        if label in self.glob.called_numbers or self.glob.finished:
            return self.glob.finished
        caller = self.glob.players[caller_id]
        caller.cut.append(label)
        self.glob.called_numbers.add(label)
        self.glob.call_history.append(label)
        if caller_id != getattr(self.glob, "bot_user_id", None):
            self.glob.idle_turns = 0
        self.increase_turn()

        winners = []
        player_ids = list(self.glob.players)
        for player_id, player in self.glob.players.items():
            if label not in player.global_cut:
                player.global_cut.append(label)
            lines = self.check_winner(player.number_list, player.global_cut)
            player.completed_lines = lines
            if lines >= 5:
                winners.append(player_id)

            if player.msg and player_id != getattr(self.glob, "bot_user_id", None):
                next_player = player_ids[self.glob.turn]
                bingo_marks = ":regional_indicator_b: :regional_indicator_i: :regional_indicator_n: :regional_indicator_g: :regional_indicator_o:"
                progress = " ".join(bingo_marks.split()[:min(lines, 5)]) or "No line yet"
                content = (
                    f"**Your board** · {lines}/5 lines complete\n"
                    f"Current turn: <@{next_player}>\n"
                    f"<@{caller_id}> called **{self.format_call(label)}**\n{progress}"
                )
                try:
                    player.view = BingoView(self.glob, player)
                    await player.msg.edit(content=content, view=player.view)
                except (discord.NotFound, discord.HTTPException):
                    pass

        if winners:
            self.glob.finished = True
            self.glob.game_finished.set()
            for player in self.glob.players.values():
                board_view = getattr(player, "view", None)
                if board_view:
                    board_view.stop()
            if len(winners) == 1:
                winner = winners[0]
                name = "🤖 Pippo" if winner == getattr(self.glob, "bot_user_id", None) else f"<@{winner}>"
                title = "Bingo!"
                description = f"{name} completed five lines after **{len(self.glob.called_numbers)} calls**."
            else:
                names = ["🤖 Pippo" if uid == getattr(self.glob, "bot_user_id", None) else f"<@{uid}>" for uid in winners]
                title = "Bingo tie!"
                description = f"{' and '.join(names)} completed five lines on the same call."
            result = discord.Embed(title=title, description=description, color=discord.Color.gold())
            result_file = await run_blocking(bingo_art_file, result, "bingo_win")
            if self.glob.out:
                try:
                    await self.glob.out.edit(content=description, view=None)
                except discord.HTTPException:
                    pass
            channel = channel or (getattr(self.glob, "out", None) and self.glob.out.channel)
            if result_file:
                if channel:
                    await channel.send(embed=result, file=result_file)
            else:
                if channel:
                    await channel.send(embed=result)
            for player in self.glob.players.values():
                if player.msg:
                    try:
                        await player.msg.edit(content="Game over! Check the channel for the winner.", view=None)
                    except discord.HTTPException:
                        pass
            return True

        if self.glob.out:
            next_player = player_ids[self.glob.turn]
            history = ", ".join(self.format_call(value) for value in self.glob.call_history[-12:])
            summary = f"Called **{self.format_call(label)}** · Next: <@{next_player}>\nRecent calls: {history}"
            try:
                await self.glob.out.edit(content=summary, view=None)
            except discord.HTTPException:
                pass
        return False

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        lock = getattr(self.glob, "lock", None)
        if lock is None:
            lock = asyncio.Lock()
            self.glob.lock = lock
        async with lock:
            if self.glob.finished:
                await interaction.followup.send("This Bingo game is over.", ephemeral=True)
                return
            if not self.glob.everyone_started:
                await interaction.followup.send("Wait for everyone to get their board first.", ephemeral=True)
                return
            if interaction.user.id not in self.glob.players:
                await interaction.followup.send("You are not in this Bingo game.", ephemeral=True)
                return
            if interaction.user.id != self.player.id:
                await interaction.followup.send("Only the owner of this board can call a number from it.", ephemeral=True)
                return
            player_ids = list(self.glob.players)
            if self.glob.turn >= len(player_ids) or player_ids[self.glob.turn] != interaction.user.id:
                await interaction.followup.send("It is not your turn.", ephemeral=True)
                return
            valid_numbers = {str(value) for row in self.player.number_list for value in row}
            if self.value == "FREE" or self.value not in valid_numbers or self.value in self.glob.called_numbers:
                await interaction.followup.send("That number has already been called.", ephemeral=True)
                return

            ended = await self.resolve_call(interaction.user.id, self.value, interaction.channel)
            bot_id = getattr(self.glob, "bot_user_id", None)
            if not ended and bot_id in self.glob.players and player_ids[self.glob.turn] == bot_id:
                bot_label = self.select_bot_number(self.glob.players[bot_id])
                if bot_label is not None:
                    await self.resolve_call(bot_id, bot_label, interaction.channel)


class BingoView(discord.ui.View):
    def __init__(self, glob, player, timeout=90):
        super().__init__(timeout=timeout)
        previous = getattr(player, "view", None)
        if previous is not None:
            previous.stop()
        self.player = player
        self.glob = glob
        player.view = self
        self.populate_buttons()

    def populate_buttons(self):
        for row_index, row in enumerate(self.player.number_list):
            for number in row:
                if number in self.player.global_cut:
                    self.add_item(BingoButton(self.glob, self.player, f"✓{number}", row=row_index, disabled=True, style=discord.ButtonStyle.red, value=number))
                else:
                    self.add_item(BingoButton(self.glob, self.player, number, row=row_index, value=number))

    async def on_timeout(self):
        lock = getattr(self.glob, "lock", None)
        if lock is None:
            lock = asyncio.Lock()
            self.glob.lock = lock
        async with lock:
            await self.handle_timeout()

    async def handle_timeout(self):
        if getattr(self.player, "view", None) is not self:
            return
        for child in self.children:
            child.disabled = True
        if not hasattr(self.glob, "everyone_started"):
            if self.player.msg:
                try:
                    await self.player.msg.edit(content="⏱️ Your Bingo board expired after inactivity. Start another game with `/play`.", view=self)
                except discord.HTTPException:
                    pass
            return
        if not self.glob.everyone_started or self.glob.finished:
            return
        player_ids = list(self.glob.players)
        if self.glob.turn >= len(player_ids) or player_ids[self.glob.turn] != self.player.id:
            history = ", ".join(BingoButton.format_call(value) for value in self.glob.call_history[-12:]) or "none"
            next_player = player_ids[self.glob.turn] if self.glob.turn < len(player_ids) else ""
            content = f"Current turn: <@{next_player}> · {len(self.glob.called_numbers)} calls so far\nRecent calls: {history}"
            try:
                self.player.view = BingoView(self.glob, self.player)
                await self.player.msg.edit(content=content, view=self.player.view)
            except discord.HTTPException:
                pass
            return

        self.glob.idle_turns += 1
        if self.glob.idle_turns >= max(4, len(player_ids) * 2):
            self.glob.finished = True
            self.glob.game_finished.set()
            result = discord.Embed(
                title="Bingo paused",
                description="The game ended after too many turns passed without a call.",
                color=discord.Color.orange(),
            )
            result_file = await run_blocking(bingo_art_file, result, "bingo_idle")
            if self.glob.out:
                try:
                    await self.glob.out.edit(content=result.description, view=None)
                except discord.HTTPException:
                    pass
            channel = getattr(self.glob.out, "channel", None)
            if channel:
                if result_file:
                    await channel.send(embed=result, file=result_file)
                else:
                    await channel.send(embed=result)
            for player in self.glob.players.values():
                board_view = getattr(player, "view", None)
                if board_view:
                    board_view.stop()
                if player.msg:
                    try:
                        await player.msg.edit(content="Bingo ended due to inactivity.", view=None)
                    except discord.HTTPException:
                        pass
            return

        timed_out_id = self.player.id
        self.glob.turn = (self.glob.turn + 1) % len(player_ids)
        next_player_id = player_ids[self.glob.turn]
        history = ", ".join(BingoButton.format_call(value) for value in self.glob.call_history[-12:]) or "none"
        summary = (
            f"⏱️ <@{timed_out_id}> missed a turn. Next: <@{next_player_id}> · "
            f"{len(self.glob.called_numbers)} calls so far\nRecent calls: {history}"
        )
        if self.glob.out:
            try:
                await self.glob.out.edit(content=summary, view=None)
            except discord.HTTPException:
                pass
        for player_id, player in self.glob.players.items():
            if player.msg and player_id != self.glob.bot_user_id:
                try:
                    player.view = BingoView(self.glob, player)
                    await player.msg.edit(content=summary, view=player.view)
                except discord.HTTPException:
                    pass
        bot_id = getattr(self.glob, "bot_user_id", None)
        if bot_id in self.glob.players and player_ids[self.glob.turn] == bot_id:
            bot = self.glob.players[bot_id]
            bot_button = BingoButton(self.glob, bot, "", row=0)
            bot_number = bot_button.select_bot_number(bot)
            if bot_number is not None:
                await bot_button.resolve_call(bot_id, bot_number, getattr(self.glob.out, "channel", None))


class BingoStartView(discord.ui.View):
    def __init__(self, players, bot_user_id=None, timeout=90):
        super().__init__(timeout=timeout)
        self.players = players
        self.bot_user_id = bot_user_id
        self.turn = 0
        self.called_numbers = set()
        self.call_history = []
        self.finished = False
        self.everyone_started = False
        self.lock = asyncio.Lock()
        self.idle_turns = 0
        self.game_finished = asyncio.Event()

    @discord.ui.button(label="Get my board", style=discord.ButtonStyle.green)
    async def start_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            player = self.players[interaction.user.id]
        except KeyError:
            await interaction.response.send_message("You are not in this game lobby.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        async with self.lock:
            if player.started:
                await interaction.followup.send("You already have a board. Wait for the game to begin.", ephemeral=True)
                return

            player.started = True
            details = f"Your board is ready. Waiting for all players to join. The first turn belongs to <@{next(iter(self.players))}>."
            board_view = BingoView(self, player)
            try:
                board_message = await interaction.followup.send(view=board_view, content=details, ephemeral=True)
            except discord.HTTPException:
                player.started = False
                board_view.stop()
                raise
            player.msg = board_message

            if self.bot_user_id and self.bot_user_id in self.players:
                bot_player = self.players[self.bot_user_id]
                bot_player.started = True
                bot_player.msg = self.out

            self.everyone_started = all(player.started for player in self.players.values())
            if self.everyone_started:
                await self.out.edit(content=f"🎱 Bingo is live! First turn: <@{next(iter(self.players))}>. Pick an uncalled number from your card.", view=None)
                for participant in self.players.values():
                    if participant.msg and participant.id != self.bot_user_id:
                        try:
                            await participant.msg.edit(
                                content=f"🎱 Bingo is live. First turn: <@{next(iter(self.players))}>. Call a number from your card on your turn."
                            )
                        except discord.HTTPException:
                            pass
                self.stop()
            else:
                waiting = ", ".join(f"<@{player.id}>" for player in self.players.values() if not player.started)
                await self.out.edit(content=f"Waiting for boards: {waiting}")

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        if getattr(self, "out", None):
            try:
                await self.out.edit(content="⏱️ Bingo lobby expired. Run `/bingo` to start another game.", view=self)
            except discord.HTTPException:
                pass
        self.game_finished.set()


# Challenge Invite View for 1v1 duels
class GameLobbyView(discord.ui.View):
    """Reusable button lobby for games with more than one participant."""

    def __init__(self, owner_id: int, owner_name: str, game_name: str, timeout=45, max_players=10):
        super().__init__(timeout=timeout)
        self.owner_id = owner_id
        self.owner_name = owner_name
        self.game_name = game_name
        self.max_players = max_players
        self.joined_ids = [owner_id]
        self.started = False
        self.message = None

    async def interaction_check(self, interaction):
        if self.is_finished():
            await interaction.response.send_message("This lobby has closed. Open a new game to join.", ephemeral=True)
            return False
        return True

    def render(self):
        mentions = ", ".join(f"<@{user_id}>" for user_id in self.joined_ids)
        return (
            f"🎮 **{self.game_name} lobby**\n"
            f"Players ({len(self.joined_ids)}/{self.max_players}): {mentions}\n"
            "Press **Join** to play, then the host presses **Start**. "
            "Start a new game and choose Play solo to play alone."
        )

    @discord.ui.button(label="Join", style=discord.ButtonStyle.success, emoji="🙋")
    async def join(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.bot:
            await interaction.response.send_message("Bots cannot join this lobby.", ephemeral=True)
            return
        if interaction.user.id not in self.joined_ids:
            if len(self.joined_ids) >= self.max_players:
                await interaction.response.send_message("This lobby is full.", ephemeral=True)
                return
            self.joined_ids.append(interaction.user.id)
        await interaction.response.edit_message(content=self.render(), view=self)

    @discord.ui.button(label="Start", style=discord.ButtonStyle.primary, emoji="▶️")
    async def start(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("Only the host can start this game.", ephemeral=True)
            return
        if len(self.joined_ids) < 2:
            await interaction.response.send_message(
                "Invite at least one player, or choose solo when starting the game.", ephemeral=True
            )
            return
        self.started = True
        self.stop()
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(content=f"✅ {self.game_name} is starting!", view=self)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.danger, emoji="✖️")
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("Only the host can cancel this lobby.", ephemeral=True)
            return
        self.stop()
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(content=f"{self.game_name} lobby cancelled.", view=self)

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        if self.message:
            try:
                await self.message.edit(content=f"⏱️ {self.game_name} lobby expired. Start a new game when you're ready.", view=self)
            except Exception:
                pass


def npat_art_file(embed, name="npat"):
    """Attach randomized NPAT art with the current round/result text."""
    return _captioned_art_file(embed, name, "npat")


def onewordstory_art_file(embed, name="onewordstory"):
    """Attach randomized Pippo storybook art with a readable caption."""
    return _captioned_art_file(embed, name, "onewordstory")


def ship_art_file(embed, name="ship"):
    """Attach a randomized Pippo matchmaker thumbnail with a short caption."""
    return _captioned_art_file(embed, name, "ship", thumbnail=True)


def flames_art_file(embed, name="flames"):
    """Attach randomized Pippo FLAMES art with a readable caption."""
    return _captioned_art_file(embed, name, "flames")


def laser_art_file(embed, name="laser"):
    """Attach randomized Pippo laser-tag art with the round text overlaid."""
    return _captioned_art_file(embed, name, "laser")


def cartoon_art_file(embed, name="cartoon"):
    """Attach a captioned Pippo cartoon-show thumbnail to a character card."""
    return _captioned_art_file(embed, name, "cartoon", thumbnail=True)


def eightball_art_file(embed, name="8ball"):
    """Attach randomized Pippo fortune-teller art with the question and verdict."""
    return _captioned_art_file(embed, name, "8ball")


def what_art_file(embed, name="what"):
    """Attach randomized captioned Pippo dictionary art."""
    return _captioned_art_file(embed, name, "what")


def kiss_art_file(embed, name="kiss"):
    """Attach randomized captioned Pippo greeting art."""
    return _captioned_art_file(embed, name, "kiss")


def animal_art_file(embed, species, name=None, folder=None):
    """Attach a randomized captioned Pippo animal thumbnail."""
    return _captioned_art_file(embed, name or species, folder or species, thumbnail=True)


class EightBallView(discord.ui.View):
    def __init__(self, owner_id, question, responses, render_card, current_response, timeout=90):
        super().__init__(timeout=timeout)
        self.owner_id = owner_id
        self.question = question
        self.responses = responses
        self.render_card = render_card
        self.current_response = current_response
        self.rerolls = 0
        self.lock = asyncio.Lock()
        self.message = None

    @discord.ui.button(label="Shake again · 3 left", style=discord.ButtonStyle.primary, emoji="🔮")
    async def shake_again(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("Only the person who asked the question can shake again.", ephemeral=True)
            return
        await interaction.response.defer()
        async with self.lock:
            if self.rerolls >= 3:
                await interaction.followup.send("The ball has used all three extra shakes. Ask `/8ball` a new question for another reading.", ephemeral=True)
                return
            choices = [response for response in self.responses if response != self.current_response]
            previous = self.current_response
            self.current_response = random.choice(choices)
            self.rerolls += 1
            embed, artwork = await run_blocking(self.render_card, self.current_response, self.rerolls + 1)
            remaining = 3 - self.rerolls
            button.label = f"Shake again · {remaining} left" if remaining else "All shakes used"
            button.disabled = remaining == 0
            try:
                await interaction.edit_original_response(
                    embed=embed,
                    view=self,
                    attachments=[artwork] if artwork else [],
                    allowed_mentions=discord.AllowedMentions.none(),
                )
            except discord.HTTPException:
                self.current_response = previous
                self.rerolls -= 1
                button.disabled = False
                button.label = f"Shake again · {3 - self.rerolls} left"
                await interaction.followup.send("The crystal ball did not settle. Try that shake once more.", ephemeral=True)

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except discord.HTTPException:
                pass


class DefinitionBrowserView(discord.ui.View):
    def __init__(self, owner_id, entries, query, render_card, timeout=120):
        super().__init__(timeout=timeout)
        self.owner_id = owner_id
        self.entries = entries
        self.query = query
        self.render_card = render_card
        self.index = 0
        self.lock = asyncio.Lock()
        self.message = None
        self._sync_buttons()

    def _sync_buttons(self):
        self.previous.disabled = self.index == 0
        self.next.disabled = self.index >= len(self.entries) - 1

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "Only the person who looked this up can browse its definitions.", ephemeral=True
            )
            return False
        return True

    async def _move(self, interaction, offset):
        await interaction.response.defer()
        async with self.lock:
            self.index = max(0, min(len(self.entries) - 1, self.index + offset))
            embed, artwork = await run_blocking(self.render_card, self.entries[self.index], self.index + 1, len(self.entries))
            self._sync_buttons()
            await interaction.edit_original_response(
                embed=embed,
                view=self,
                attachments=[artwork] if artwork else [],
                allowed_mentions=discord.AllowedMentions.none(),
            )

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.secondary, emoji="⬅️")
    async def previous(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._move(interaction, -1)

    @discord.ui.button(label="Next definition", style=discord.ButtonStyle.primary, emoji="➡️")
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._move(interaction, 1)

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except discord.HTTPException:
                pass


class KissConsentView(discord.ui.View):
    def __init__(self, target_id, render_result, timeout=60):
        super().__init__(timeout=timeout)
        self.target_id = target_id
        self.render_result = render_result
        self.message = None
        self.lock = asyncio.Lock()
        self.decided = False

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.target_id:
            await interaction.response.send_message(
                "This little greeting request is for the person it was sent to.", ephemeral=True
            )
            return False
        if self.decided:
            await interaction.response.send_message("This request has already been answered.", ephemeral=True)
            return False
        return True

    async def _choose(self, interaction, accepted):
        await interaction.response.defer()
        async with self.lock:
            if self.decided:
                return
            self.decided = True
            embed, artwork = await run_blocking(self.render_result, "accepted" if accepted else "declined")
            for item in self.children:
                item.disabled = True
            await interaction.edit_original_response(
                embed=embed,
                view=self,
                attachments=[artwork] if artwork else [],
                allowed_mentions=discord.AllowedMentions.none(),
            )
            self.stop()

    @discord.ui.button(label="Accept", style=discord.ButtonStyle.success, emoji="💛")
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._choose(interaction, True)

    @discord.ui.button(label="Pass", style=discord.ButtonStyle.secondary, emoji="🙌")
    async def decline(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._choose(interaction, False)

    async def on_timeout(self):
        if self.decided:
            return
        self.decided = True
        if self.message:
            try:
                embed, artwork = await run_blocking(self.render_result, "expired")
                await self.message.edit(
                    embed=embed,
                    view=None,
                    attachments=[artwork] if artwork else [],
                    allowed_mentions=discord.AllowedMentions.none(),
                )
            except discord.HTTPException:
                pass


class CartoonRouletteView(discord.ui.View):
    def __init__(self, owner_id, characters, render_card, current_character, timeout=90):
        super().__init__(timeout=timeout)
        self.owner_id = owner_id
        self.characters = characters
        self.render_card = render_card
        self.current_character = current_character
        self.seen = {self.character_key(current_character)}
        self.rolls = 0
        self.lock = asyncio.Lock()
        self.message = None

    @staticmethod
    def character_key(character):
        return (character["character_name"].strip().casefold(), character["show_name"].strip().casefold())

    @discord.ui.button(label="Spin again · 5 left", style=discord.ButtonStyle.primary, emoji="🎲")
    async def spin_again(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("Only the person who started this roulette can spin again.", ephemeral=True)
            return
        await interaction.response.defer()
        async with self.lock:
            if self.rolls >= 5:
                await interaction.followup.send("That roulette has used all five extra spins. Start `/cartoon` for a fresh draw.", ephemeral=True)
                return
            choices = [character for character in self.characters if self.character_key(character) not in self.seen]
            if not choices:
                choices = self.characters
                self.seen.clear()
            previous = self.current_character
            self.current_character = random.choice(choices)
            self.seen.add(self.character_key(self.current_character))
            self.rolls += 1
            embed, artwork = await run_blocking(self.render_card, self.current_character, self.rolls + 1)
            remaining = 5 - self.rolls
            button.label = f"Spin again · {remaining} left" if remaining else "All spins used"
            button.disabled = remaining == 0
            try:
                await interaction.edit_original_response(
                    embed=embed,
                    view=self,
                    attachments=[artwork] if artwork else [],
                    allowed_mentions=discord.AllowedMentions.none(),
                )
            except discord.HTTPException:
                self.current_character = previous
                self.rolls -= 1
                button.disabled = False
                button.label = f"Spin again · {5 - self.rolls} left"
                await interaction.followup.send("That spin did not load. Try the button once more.", ephemeral=True)

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except discord.HTTPException:
                pass


class NpatAnswerModal(discord.ui.Modal, title="Lock in all four answers"):
    def __init__(self, game):
        super().__init__(timeout=120)
        self.game = game
        self.name_answer = discord.ui.TextInput(label=f"Name (starts with {game.letter})", max_length=48)
        self.place_answer = discord.ui.TextInput(label=f"Place (starts with {game.letter})", max_length=48)
        self.animal_answer = discord.ui.TextInput(label=f"Animal (starts with {game.letter})", max_length=48)
        self.thing_answer = discord.ui.TextInput(label=f"Thing (starts with {game.letter})", max_length=48)
        for answer in (self.name_answer, self.place_answer, self.animal_answer, self.thing_answer):
            self.add_item(answer)

    async def on_submit(self, interaction: discord.Interaction):
        answers = {
            "Name": self.name_answer.value,
            "Place": self.place_answer.value,
            "Animal": self.animal_answer.value,
            "Thing": self.thing_answer.value,
        }
        accepted, message = await self.game.record_submission(interaction.user.id, answers)
        await interaction.response.send_message(message, ephemeral=True)
        if accepted and self.game.message and not self.game.is_finished():
            try:
                await self.game.message.edit(embed=self.game.status_embed(), view=self.game)
            except discord.HTTPException:
                pass


class NpatLobbyView(GameLobbyView):
    def render(self):
        mentions = ", ".join(f"<@{user_id}>" for user_id in self.joined_ids)
        return (
            "✏️ **Name, Place, Animal, Thing lobby**\n"
            f"Players ({len(self.joined_ids)}/{self.max_players}): {mentions}\n"
            "Join the game, then the host presses **Start**. Up to six players; five timed rounds."
        )


class OneWordStoryLobbyView(GameLobbyView):
    def render(self):
        mentions = ", ".join(f"<@{user_id}>" for user_id in self.joined_ids)
        return (
            "📖 **One Word Story lobby**\n"
            f"Players ({len(self.joined_ids)}/{self.max_players}): {mentions}\n"
            "Join the story, then the host starts four laps of one-word turns."
        )


class NpatRoundView(discord.ui.View):
    """Collect one private answer card per player for a timed NPAT round."""

    CATEGORIES = ("Name", "Place", "Animal", "Thing")

    def __init__(self, player_ids, player_names, letter, round_number, timeout=45):
        super().__init__(timeout=timeout)
        self.player_ids = set(player_ids)
        self.player_names = player_names
        self.letter = letter
        self.round_number = round_number
        self.submissions = {}
        self.message = None
        self.lock = asyncio.Lock()

    def status_embed(self):
        embed = discord.Embed(
            title=f"Round {self.round_number}/5 · Letter {self.letter}",
            description=(
                "Fill **Name, Place, Animal, Thing** with answers that start with the letter. "
                "Your card stays hidden until time is up. Unique answers score **10**; "
                "matching answers score **5** each. A four-for-four card earns **+5**."
            ),
            color=discord.Color.gold(),
        )
        ready = len(self.submissions)
        embed.add_field(name="Cards locked", value=f"{ready}/{len(self.player_ids)} players", inline=True)
        embed.add_field(name="Time", value="45 seconds", inline=True)
        embed.set_footer(text="Only the starting letter is checked automatically; keep answers in their category.")
        return embed

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.bot or interaction.user.id not in self.player_ids:
            await interaction.response.send_message("Only players in this NPAT round can submit answers.", ephemeral=True)
            return False
        if interaction.user.id in self.submissions:
            await interaction.response.send_message("Your card is already locked for this round.", ephemeral=True)
            return False
        return True

    async def record_submission(self, user_id, answers):
        async with self.lock:
            if self.is_finished() or user_id not in self.player_ids:
                return False, "This round is already closed."
            if user_id in self.submissions:
                return False, "Your card is already locked for this round."
            self.submissions[user_id] = answers
            all_locked = len(self.submissions) == len(self.player_ids)
            if all_locked:
                for child in self.children:
                    child.disabled = True
                self.stop()
        remaining = len(self.player_ids) - len(self.submissions)
        if all_locked:
            return True, "🔒 Card locked. Everyone is in; revealing the round now."
        return True, f"🔒 Card locked. {remaining} player{'s' if remaining != 1 else ''} still to submit."

    @discord.ui.button(label="Write my card", style=discord.ButtonStyle.primary, emoji="✏️")
    async def submit(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(NpatAnswerModal(self))

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        if self.message:
            try:
                await self.message.edit(embed=self.status_embed(), view=self)
            except discord.HTTPException:
                pass


class ChallengeInviteView(discord.ui.View):
    def __init__(self, challenger: discord.Member, opponent: discord.Member, game_name: str = "Game", timeout=60):
        super().__init__(timeout=timeout)
        self.challenger = challenger
        self.opponent = opponent
        self.game_name = game_name
        self.accepted = None
        self.message = None

    @discord.ui.button(label="Accept ⚔️", style=discord.ButtonStyle.success)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.opponent.id:
            await interaction.response.send_message("Only the challenged opponent can accept!", ephemeral=True)
            return
        self.accepted = True
        self.stop()
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(content=f"⚔️ **{self.opponent.display_name}** accepted the challenge from **{self.challenger.display_name}**!", view=self)

    @discord.ui.button(label="Decline ❌", style=discord.ButtonStyle.danger)
    async def decline(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.opponent.id and interaction.user.id != self.challenger.id:
            await interaction.response.send_message("You cannot decline this challenge!", ephemeral=True)
            return
        self.accepted = False
        self.stop()
        for item in self.children:
            item.disabled = True
        decliner = "Challenge cancelled." if interaction.user.id == self.challenger.id else f"**{self.opponent.display_name}** declined the challenge."
        await interaction.response.edit_message(content=decliner, view=self)

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        if hasattr(self, 'message') and self.message:
            try:
                await self.message.edit(content="⏱️ Challenge timed out.", view=self)
            except Exception:
                pass


def flood_art_file(embed, name="flood"):
    """Attach a randomized Flood thumbnail with the current result caption."""
    return _captioned_art_file(embed, name, "flood", thumbnail=True)


def clash_art_file(embed, name="clash"):
    """Attach a randomized Clash arena with the result text overlaid."""
    return _captioned_art_file(embed, name, "clash")


def memory_art_file(embed, name="memory"):
    """Attach randomized Pippo Memory art with readable game text."""
    return _captioned_art_file(embed, name, "memory")


# Tic Tac Toe
class TicTacToeButton(discord.ui.Button['TicTacToeView']):
    def __init__(self, x: int, y: int):
        super().__init__(style=discord.ButtonStyle.secondary, label='\u200b', row=y)
        self.x = x
        self.y = y

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        async with self.view.lock:
            await self._move(interaction)

    async def _move(self, interaction: discord.Interaction):
        assert self.view is not None
        view: TicTacToeView = self.view
        if view.is_finished():
            await interaction.followup.send("This Tic Tac Toe game is over.", ephemeral=True)
            return
        state = view.board[self.y][self.x]
        if state in (view.X, view.O):
            return

        # Player validation
        if view.vs_bot:
            if interaction.user != view.player_x:
                await interaction.followup.send("Only you can play in this solo match!", ephemeral=True)
                return
        elif view.player_x and view.player_o:
            if interaction.user not in (view.player_x, view.player_o):
                await interaction.followup.send("This game is between other players!", ephemeral=True)
                return
            if view.current_player == view.X and interaction.user != view.player_x:
                await interaction.followup.send("It is Player X's turn!", ephemeral=True)
                return
            if view.current_player == view.O and interaction.user != view.player_o:
                await interaction.followup.send("It is Player O's turn!", ephemeral=True)
                return
        elif view.player_x and not view.player_o:
            if view.current_player == view.X and interaction.user != view.player_x:
                await interaction.followup.send("Only Player X can play the first move!", ephemeral=True)
                return
            if view.current_player == view.O:
                if interaction.user == view.player_x:
                    await interaction.followup.send("Waiting for another player to play O!", ephemeral=True)
                    return
                view.player_o = interaction.user

        if view.current_player == view.X:
            self.style = discord.ButtonStyle.danger
            self.label = 'X'
            self.disabled = True
            view.board[self.y][self.x] = view.X
            view.current_player = view.O
            o_name = "Pippo 🤖" if view.vs_bot else (view.player_o.mention if view.player_o else "O")
            content = f"It is now {o_name}'s turn (O)"
        else:
            self.style = discord.ButtonStyle.success
            self.label = 'O'
            self.disabled = True
            view.board[self.y][self.x] = view.O
            view.current_player = view.X
            x_name = view.player_x.mention if view.player_x else "X"
            content = f"It is now {x_name}'s turn (X)"

        winner = view.check_board_winner()
        game_over = False
        if winner is not None:
            game_over = True
            if winner == view.X:
                winner_name = view.player_x.mention if view.player_x else "X"
                content = f"🏆 **{winner_name}** won! Run `/play` to start another game."
            elif winner == view.O:
                winner_name = "Pippo 🤖" if view.vs_bot else (view.player_o.mention if view.player_o else "O")
                content = f"🏆 **{winner_name}** won! Run `/play` to start another game."
            else:
                content = "🤝 It's a tie! Run `/play` to start another game."

            for child in view.children:
                child.disabled = True
            view.stop()
        elif view.vs_bot and view.current_player == view.O:
            # Bot AI plays its turn
            await run_blocking(view.bot_move)
            bot_winner = view.check_board_winner()
            if bot_winner is not None:
                game_over = True
                if bot_winner == view.O:
                    content = "🤖 **Pippo** won! Run `/play` to start another game."
                elif bot_winner == view.Tie:
                    content = "🤝 It's a tie! Run `/play` to start another game."
                for child in view.children:
                    child.disabled = True
                view.stop()
            else:
                content = f"It is now {view.player_x.mention}'s turn (X)!"

        await interaction.edit_original_response(content=content, view=view)
        if game_over and interaction.channel:
            result = discord.Embed(title="Tic Tac Toe · Game over", description=content, color=discord.Color.gold())
            artwork = await run_blocking(tictactoe_art_file, result, "tictactoe_result")
            try:
                if artwork:
                    await interaction.channel.send(embed=result, file=artwork)
                else:
                    await interaction.channel.send(embed=result)
            except discord.HTTPException:
                pass


class TicTacToeView(discord.ui.View):
    children: List[TicTacToeButton]
    X = -1
    O = 1
    Tie = 2

    def __init__(self, player_x: discord.Member = None, player_o: discord.Member = None,
                 vs_bot: bool = False, difficulty="normal", timeout=120):
        super().__init__(timeout=timeout)
        self.lock = asyncio.Lock()
        self.player_x = player_x
        self.player_o = player_o
        self.vs_bot = vs_bot
        self.difficulty = difficulty if difficulty in {"easy", "normal", "hard"} else "normal"
        self.current_player = self.X
        self.message = None
        self.board = [
            [0, 0, 0],
            [0, 0, 0],
            [0, 0, 0],
        ]

        for x in range(3):
            for y in range(3):
                self.add_item(TicTacToeButton(x, y))

    def _apply_bot_cell(self, r, c):
        self.board[r][c] = self.O
        for btn in self.children:
            if btn.x == c and btn.y == r:
                btn.label = 'O'
                btn.style = discord.ButtonStyle.success
                btn.disabled = True
                break
        self.current_player = self.X

    def bot_move(self):
        empty = [(r, c) for r in range(3) for c in range(3) if self.board[r][c] == 0]
        if not empty:
            return
        if self.difficulty == "easy":
            r, c = random.choice(empty)
            self._apply_bot_cell(r, c)
            return

        scored_moves = []
        for r, c in empty:
            self.board[r][c] = self.O
            score = self._minimax(self.X, depth=1, alpha=-100, beta=100)
            self.board[r][c] = 0
            scored_moves.append((score, (r, c)))

        best_score = max(score for score, _ in scored_moves)
        best_moves = [move for score, move in scored_moves if score == best_score]
        weaker_moves = [move for score, move in scored_moves if score < best_score]
        if self.difficulty == "normal" and weaker_moves and random.random() < 0.24:
            r, c = random.choice(weaker_moves)
        else:
            r, c = random.choice(best_moves)
        self._apply_bot_cell(r, c)

    def _minimax(self, turn, depth, alpha, beta):
        result = self.check_board_winner()
        if result == self.O:
            return 10 - depth
        if result == self.X:
            return depth - 10
        if result == self.Tie:
            return 0

        empty = [(r, c) for r in range(3) for c in range(3) if self.board[r][c] == 0]
        if turn == self.O:
            best = -100
            for r, c in empty:
                self.board[r][c] = self.O
                best = max(best, self._minimax(self.X, depth + 1, alpha, beta))
                self.board[r][c] = 0
                alpha = max(alpha, best)
                if beta <= alpha:
                    break
            return best

        best = 100
        for r, c in empty:
            self.board[r][c] = self.X
            best = min(best, self._minimax(self.O, depth + 1, alpha, beta))
            self.board[r][c] = 0
            beta = min(beta, best)
            if beta <= alpha:
                break
        return best

    def check_board_winner(self):
        for across in self.board:
            value = sum(across)
            if value == 3:
                return self.O
            elif value == -3:
                return self.X

        for line in range(3):
            value = self.board[0][line] + self.board[1][line] + self.board[2][line]
            if value == 3:
                return self.O
            elif value == -3:
                return self.X

        diag = self.board[0][2] + self.board[1][1] + self.board[2][0]
        if diag == 3:
            return self.O
        elif diag == -3:
            return self.X

        diag = self.board[0][0] + self.board[1][1] + self.board[2][2]
        if diag == 3:
            return self.O
        elif diag == -3:
            return self.X

        if all(i != 0 for row in self.board for i in row):
            return self.Tie

        return None

    async def on_timeout(self):
        async with self.lock:
            if self.check_board_winner() is not None:
                return
            for child in self.children:
                child.disabled = True
            if hasattr(self, 'message') and self.message:
                try:
                    await self.message.edit(content="⏱️ Tic Tac Toe ended after inactivity. Run `/play` to start another game.", view=self)
                except Exception:
                    pass


# Modern Interactive Help Views
class HelpCategorySelect(discord.ui.Select):
    def __init__(self, bot, prefix="."):
        self.bot = bot
        self.prefix = prefix
        options = [
            discord.SelectOption(label="Home", emoji="🏠", description="Overview & category guide", value="home", default=True),
            discord.SelectOption(label="Games & Trivia", emoji="🎮", description="Bollywood, Bingo, TicTacToe, Flood, Memory, Clash", value="games"),
            discord.SelectOption(label="Economy & Shop", emoji="🪙", description="Coins, balances, transfers, and cartoon shop", value="economy"),
            discord.SelectOption(label="Fun & Social", emoji="🎉", description="Ship, Flames, Cartoons, 8Ball, Urban Dictionary", value="fun"),
            discord.SelectOption(label="Animals", emoji="🐾", description="Dogs, Cats, Meow/Woof trivia, and Breed Matchers", value="animals"),
            discord.SelectOption(label="Settings & Utility", emoji="⚙️", description="Prefix, Leaderboard, Greetings, Suggestions", value="settings"),
        ]
        super().__init__(placeholder="Select a category to browse...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        if self.view.author_id and interaction.user.id != self.view.author_id:
            await interaction.response.send_message("Only the user who requested this help menu can browse categories.", ephemeral=True)
            return

        choice = self.values[0]
        for option in self.options:
            option.default = (option.value == choice)

        embed = self.view.generate_embed(choice)
        await interaction.response.edit_message(embed=embed, view=self.view)


class HelpView(discord.ui.View):
    CATEGORY_COGS = {
        "games": {"Games"},
        "economy": {"Economy", "Shop"},
        "fun": {"Fun", "Actions"},
        "animals": {"Animals"},
        "settings": {"Settings", "Schedules", "Help", "Play", "Info"},
    }

    def __init__(self, bot=None, author_id=None, prefix=".", timeout=120):
        super().__init__(timeout=timeout)
        self.bot = bot
        self.author_id = author_id
        self.prefix = prefix
        self.message = None

        if self.bot:
            self.add_item(HelpCategorySelect(self.bot, prefix=self.prefix))

        server_url = "https://discord.gg/ugcEEd8pAP"
        self.add_item(discord.ui.Button(label='Support Server', emoji='💬', url=server_url))
        vote_url = "https://top.gg/bot/1066895131485163570/vote"
        self.add_item(discord.ui.Button(label='Vote on Top.gg', emoji='⭐', url=vote_url))

    def generate_embed(self, category: str) -> discord.Embed:
        category_info = {
            "games": ("🎮 Games & Trivia", "Movie games, trivia, and party games.", discord.Color.gold()),
            "economy": ("🪙 Economy & Shop", "Balances, coin transfers, and shop commands.", discord.Color.green()),
            "fun": ("🎉 Fun & Social", "Social games and pop-culture commands.", discord.Color.magenta()),
            "animals": ("🐾 Animals", "Pet photos, breed quizzes, and breed matchers.", discord.Color.teal()),
            "settings": ("⚙️ Settings & Utilities", "Server setup, leaderboards, and feedback.", discord.Color.blue()),
        }
        if category in category_info:
            title, description, color = category_info[category]
            emb = discord.Embed(title=title, description=description, color=color)
            commands = []
            if self.bot:
                commands = [
                    command for command in self.bot.walk_commands()
                    if not command.hidden and command.cog_name in self.CATEGORY_COGS[category]
                ]
            for command in sorted(commands, key=lambda item: item.name):
                prefix_command = f"{self.prefix}{command.qualified_name}"
                slash_command = f"/{command.qualified_name}"
                summary = command.short_doc or command.help or "No description available."
                if command.name in {"bollywood", "hollywood", "plotster", "quizster", "poster", "bingo", "flood", "clash", "woof", "meow", "onewordstory", "memory", "tictactoe", "npat"}:
                    summary += " Start the command, then choose Play solo or Play with friends."
                emb.add_field(
                    name=f"`{prefix_command}` · `{slash_command}`",
                    value=summary[:1024],
                    inline=False,
                )
            if not commands:
                emb.description += "\nNo commands are available in this category right now."
            return emb

        if category == "home":
            emb = discord.Embed(
                title="👋 Welcome to Pippo!",
                description=(
                    "Pick a category from the menu to see available commands.\n\n"
                    f"For an interactive game menu, run `/play` or `{self.prefix}play`. "
                    f"You can also use slash commands or the `{self.prefix}` prefix."
                ),
                color=discord.Color.gold(),
            )
            category_titles = {
                "games": "🎮 Games & Trivia",
                "economy": "🪙 Economy & Shop",
                "fun": "🎉 Fun & Social",
                "animals": "🐾 Animals",
                "settings": "⚙️ Settings & Utilities",
            }
            for key, title in category_titles.items():
                available = (
                    [command for command in self.bot.walk_commands()
                     if not command.hidden and command.cog_name in self.CATEGORY_COGS[key]]
                    if self.bot else []
                )
                emb.add_field(name=title, value=f"{len(available)} commands · select the category for details.", inline=False)
            emb.set_footer(text="Use /help <command> or the prefix help command for a command’s details.")
            return emb

        return discord.Embed(title="Help", description="Choose a category from the menu above.", color=discord.Color.gold())

    async def on_timeout(self):
        for child in self.children:
            if isinstance(child, discord.ui.Select):
                child.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except Exception:
                pass


# BreedGuessView
class AnimalPhotoView(discord.ui.View):
    def __init__(self, owner_id, fetch_photo, first_url, species, timeout=120):
        super().__init__(timeout=timeout)
        self.owner_id = owner_id
        self.fetch_photo = fetch_photo
        self.species = species
        self.seen_urls = {first_url}
        self.photo_number = 1
        self.lock = asyncio.Lock()
        self.message = None
        self.another_animal.label = f"Another {species} · 3 left"

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                f"Only the person who started this {self.species.title()} Parade can fetch the next photo.", ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="Another pet · 3 left", style=discord.ButtonStyle.primary, emoji="🐾")
    async def another_animal(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        async with self.lock:
            if self.photo_number >= 4:
                await interaction.followup.send(
                    f"This {self.species.title()} Parade has shown all four photos. Start `/{self.species}` for another set.",
                    ephemeral=True,
                )
                return
            result = await self.fetch_photo(self.photo_number + 1, self.seen_urls)
            if result is None:
                await interaction.followup.send(f"The {self.species} photo feed is taking a break. Try again in a moment.", ephemeral=True)
                return
            embed, photo, thumbnail, photo_url = result
            old_number = self.photo_number
            self.photo_number += 1
            self.seen_urls.add(photo_url)
            remaining = 4 - self.photo_number
            button.label = f"Another {self.species} · {remaining} left" if remaining else "Parade complete"
            button.disabled = remaining == 0
            try:
                await interaction.edit_original_response(
                    embed=embed,
                    view=self,
                    attachments=[photo] + ([thumbnail] if thumbnail else []),
                    allowed_mentions=discord.AllowedMentions.none(),
                )
            except discord.HTTPException:
                self.photo_number = old_number
                self.seen_urls.discard(photo_url)
                button.disabled = False
                button.label = f"Another {self.species} · {4 - old_number} left"
                await interaction.followup.send("Pippo couldn't post that photo. Please try the button again.", ephemeral=True)

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except discord.HTTPException:
                pass


class BreedGuessButton(discord.ui.Button):
    def __init__(self, label: str, view, answer=False, row=1, disabled=False, style=discord.ButtonStyle.grey):
        super().__init__(style=style, label=label, row=row, disabled=disabled)
        self.label = label
        self.answer = answer

    async def callback(self, interaction: discord.Interaction):
        if self.view.author_id is not None and interaction.user.id != self.view.author_id:
            await interaction.response.send_message("Only the player who started this solo quiz can answer.", ephemeral=True)
            return
        await interaction.response.defer()
        view = self.view
        async with view.lock:
            if view.resolved or view.is_finished() or self not in view.children:
                await interaction.followup.send("That breed round has already moved on.", ephemeral=True)
                return
            if interaction.user.id in view.attempted_users:
                await interaction.followup.send("You've already guessed this round; let another player try.", ephemeral=True)
                return
            view.attempted_users.add(interaction.user.id)
            if self.answer:
                view.scores[interaction.user.id] = view.scores.get(interaction.user.id, 0) + 1
                view.player_names[interaction.user.id] = interaction.user.display_name
                await view.resolve_round(winner=interaction.user.display_name)
            else:
                self.style = discord.ButtonStyle.red
                self.disabled = True
                if view.author_id is not None or view.total_rounds == 1:
                    await view.resolve_round(wrong_label=self.label)
                elif view.out:
                    await view.out.edit(view=view)


class BreedGuessView(discord.ui.View):
    def __init__(self, answer, breeds, timeout=60, author_id=None, embed=None,
                 *, total_rounds=1, next_round=None):
        super().__init__(timeout=timeout)
        self.answer = answer
        self.author_id = author_id
        self.out = None
        self.embed = embed or discord.Embed(title="Can you guess the breed?", color=discord.Color.blue())
        self.resolved = False
        self.lock = asyncio.Lock()
        self.round_number = 1
        self.total_rounds = max(1, total_rounds)
        self.next_round = next_round
        self.scores = {}
        self.player_names = {}
        self.attempted_users = set()
        self._add_choices(breeds)

    def _add_choices(self, breeds):
        for breed in breeds:
            self.add_item(BreedGuessButton(breed, self, answer=(breed == self.answer)))

    def _scoreboard(self):
        if not self.scores:
            return "No points scored yet."
        rows = sorted(
            self.scores.items(),
            key=lambda pair: (-pair[1], self.player_names.get(pair[0], "").casefold()),
        )[:10]
        return "\n".join(
            f"{index}. {discord.utils.escape_markdown(self.player_names.get(user_id, 'Player'))}: {score}"
            for index, (user_id, score) in enumerate(rows, start=1)
        )

    async def resolve_round(self, winner=None, *, wrong_label=None, timed_out=False):
        self.resolved = True
        for child in self.children:
            child.disabled = True
            if getattr(child, "answer", False):
                child.style = discord.ButtonStyle.green

        result = self.embed.copy()
        if winner:
            result.title = "Correct!" if self.total_rounds == 1 else f"Round {self.round_number}/{self.total_rounds} · Correct!"
            result.description = f"**{discord.utils.escape_markdown(winner)}** earns a point.\n\n{self._scoreboard()}"
            result.color = discord.Color.green()
        elif timed_out:
            result.title = "Time's up!" if self.total_rounds == 1 else f"Round {self.round_number}/{self.total_rounds} · Time's up"
            result.description = f"The breed was **{discord.utils.escape_markdown(self.answer)}**.\n\n{self._scoreboard()}"
            result.color = discord.Color.gold()
        elif self.author_id is not None:
            result.title = f"Round {self.round_number}/{self.total_rounds} · Keep going!"
            result.description = f"The breed was **{discord.utils.escape_markdown(self.answer)}**.\n\n{self._scoreboard()}"
            result.color = discord.Color.gold()
        elif wrong_label is not None:
            result.title = "Not quite!"
            result.description = f"You chose **{discord.utils.escape_markdown(wrong_label)}**. The breed was **{discord.utils.escape_markdown(self.answer)}**."
            result.color = discord.Color.red()

        is_complete = self.round_number >= self.total_rounds
        if is_complete and self.total_rounds > 1:
            result.title = "Breed quiz complete!"
            last_result = (
                f"**{discord.utils.escape_markdown(winner)}** earns the final point.\n\n"
                if winner else f"The final breed was **{discord.utils.escape_markdown(self.answer)}**.\n\n"
            )
            result.description = f"{last_result}Final scores\n{self._scoreboard()}"

        if self.out:
            await self.out.edit(embed=result, view=self, allowed_mentions=discord.AllowedMentions.none())

        if is_complete or self.next_round is None or timed_out:
            self.embed = result
            self.stop()
            return

        await asyncio.sleep(1.25)
        try:
            question = await self.next_round()
        except Exception:
            question = None
        if not question:
            result.title = "Breed quiz ended early"
            result.description = f"Pippo couldn't load the next photo. Final scores\n{self._scoreboard()}"
            self.embed = result
            self.stop()
            if self.out:
                await self.out.edit(embed=result, view=self, allowed_mentions=discord.AllowedMentions.none())
            return

        self.round_number += 1
        self.answer = question["answer"]
        self.embed = question["embed"]
        self.clear_items()
        self._add_choices(question["breeds"])
        self.attempted_users.clear()
        self.resolved = False
        if self.out:
            await self.out.edit(
                embed=self.embed,
                view=self,
                attachments=question["files"],
                allowed_mentions=discord.AllowedMentions.none(),
            )

    async def on_timeout(self):
        async with self.lock:
            if self.resolved:
                return
            try:
                await self.resolve_round(timed_out=True)
            except discord.HTTPException:
                self.stop()


# MemoryView

class MemoryButton(discord.ui.Button):
    def __init__(self, label: str, row: int, disabled=False, style=discord.ButtonStyle.grey):
        super().__init__(style=style, label=label, row=row, disabled=disabled)
        self.revealed = False

    async def callback(self, interaction: discord.Interaction):
        view: MemoryView = self.view
        submitted_turn = view.turn_token
        await interaction.response.defer()
        async with view.lock:
            if view.is_finished():
                await interaction.followup.send("This Memory Match game is over.", ephemeral=True)
                return
            if submitted_turn != view.turn_token:
                await interaction.followup.send("That turn has already passed. Check whose turn it is.", ephemeral=True)
                return
            if interaction.user.id != view.players[view.turn].id:
                await interaction.followup.send("It is not your turn.", ephemeral=True)
                return
            if self.disabled or self.revealed or self in view.temp_clicked:
                await interaction.followup.send("Choose a face-down card you have not selected yet.", ephemeral=True)
                return

            index = view.children.index(self)
            self.label = view.emojis[index]
            self.style = discord.ButtonStyle.blurple
            view.temp_clicked.append(self)
            if len(view.temp_clicked) == 1:
                await view.out.edit(content=view.status("👀 First card revealed."), view=view)
                return

            first, second = view.temp_clicked
            first_index = view.children.index(first)
            second_index = view.children.index(second)
            view.moves += 1
            current_player = view.turn
            is_match = view.emojis[first_index] == view.emojis[second_index]

            if is_match:
                view.scores[current_player] += 1
                view.streaks[current_player] += 1
                view.pairs_found += 1
                view.revealed.extend((first, second))
                for card in (first, second):
                    card.revealed = True
                    card.style = discord.ButtonStyle.green
                    card.disabled = True
                view.temp_clicked.clear()

                if view.check_winner():
                    if view.is_solo:
                        stars = 3 if view.moves <= 12 else 2 if view.moves <= 20 else 1
                        content = (
                            f"🏆 **You found all eight pairs!** {view.moves} moves · "
                            f"{'⭐' * stars} · Run `/memory` to play again."
                        )
                    elif view.scores[0] == view.scores[1]:
                        content = f"🤝 Memory Match is a tie at **{view.scores[0]}** pairs each. Run `/memory` to play again."
                    else:
                        winner = view.scores.index(max(view.scores))
                        content = f"🏆 {view.players[winner].mention} wins with **{view.scores[winner]}** pairs! Run `/memory` to play again."
                    for card in view.children:
                        card.disabled = True
                    view.stop()
                    finished = True
                else:
                    streak = view.streaks[current_player]
                    player_label = "Match" if view.is_solo else view.players[current_player].mention
                    content = view.status(f"✨ {player_label} found a pair and keeps the turn!")
                    if streak >= 2:
                        content += f" 🔥 **{streak} in a row!**"
                    finished = False
            else:
                view.streaks[current_player] = 0
                for card in view.children:
                    card.disabled = True
                first.style = second.style = discord.ButtonStyle.red
                await view.out.edit(content="❌ No match. Cards flip back in one second; a miss passes the turn.", view=view)
                await asyncio.sleep(1)
                if view.is_finished():
                    return
                for card_index, card in enumerate(view.children):
                    card.disabled = card.revealed
                    card.label = view.emojis[card_index] if card.revealed else "‎ "
                    card.style = discord.ButtonStyle.green if card.revealed else discord.ButtonStyle.grey
                view.temp_clicked.clear()
                if not view.is_solo:
                    view.change_turn()
                    content = view.status(f"↪️ No match. {view.players[view.turn].mention} takes the turn.")
                else:
                    content = view.status("🃏 No match. Keep searching.")
                finished = False

            await view.out.edit(content=content, view=view)
            if finished:
                await view.send_result_art(interaction.channel, content)


class MemoryView(discord.ui.View):
    def __init__(self, user1, user2=None):
        super().__init__(timeout=120)
        self.is_solo = user2 is None
        self.players = [user1] if self.is_solo else [user1, user2]
        self.turn = 0
        self.turn_token = 0
        self.lock = asyncio.Lock()
        self.temp_clicked = []
        self.revealed = []
        self.out = None
        self.scores = [0] if self.is_solo else [0, 0]
        self.streaks = [0] if self.is_solo else [0, 0]
        self.moves = 0
        self.pairs_found = 0

        faces = [
            "😭", "😔", "😡", "😏", "😋", "🤤", "😘", "😟", "🤓", "😎", "🤩", "😣", "😿", "😙", "😁",
            "😗", "😐", "😮", "😈", "🤡", "👉", "😼", "😾", "😺", "🤜", "💪", "🙌", "😛", "👩‍🦱", "👁️",
            "👇", "🦷", "👨‍🌾", "🕵️‍♀️", "👷‍♀️", "👮‍♂️", "💂", "🦻", "💆‍♀️", "🤷‍♂️", "👶", "🙇‍♂️",
            "🙍‍♂️", "👛", "🩴", "👗", "👒", "🦺", "🦇", "🐒", "🦋", "🐡", "🦟", "🐸", "🦶", "🥀",
            "🎋", "🐲", "🥗", "🍑", "🍈", "🥑", "🥔", "🥯", "🥕", "🍆", "⚾", "⚽", "🏀",
        ]
        faces = list(dict.fromkeys(faces))
        self.emojis = random.sample(faces, 8) * 2
        random.shuffle(self.emojis)
        self.populate_buttons()

    def populate_buttons(self):
        for index in range(16):
            self.add_item(MemoryButton("‎ ", row=index // 4))

    def status(self, note=""):
        if self.is_solo:
            progress = f"Pairs: **{self.pairs_found}/8** · Moves: **{self.moves}**"
            return f"{note}\n{progress}" if note else f"🃏 **Solo Memory Challenge**\n{progress}"
        scoreboard = " · ".join(
            f"{player.mention} **{self.scores[index]}**"
            for index, player in enumerate(self.players)
        )
        turn = f"{self.players[self.turn].mention}'s turn"
        return f"{note}\n{scoreboard}\n{turn}" if note else f"{scoreboard}\n{turn}"

    def change_turn(self):
        self.turn = (self.turn + 1) % len(self.players)
        self.turn_token += 1

    def check_winner(self):
        return len(self.revealed) == 16

    async def send_result_art(self, channel, content):
        if not channel:
            return
        embed = discord.Embed(title="Pippo Memory Match", description=content, color=discord.Color.gold())
        artwork = await run_blocking(memory_art_file, embed, "memory_result")
        try:
            if artwork:
                await channel.send(embed=embed, file=artwork)
            else:
                await channel.send(embed=embed)
        except discord.HTTPException:
            pass

    async def on_timeout(self):
        async with self.lock:
            if self.pairs_found == 8:
                return
            for child in self.children:
                child.disabled = True
            if self.out:
                try:
                    await self.out.edit(content="⏱️ Memory Match ended after inactivity. Run `/memory` to start another game.", view=self)
                except discord.HTTPException:
                    pass


# FloodView 

class FloodButton(discord.ui.Button):
    def __init__(self, label: str, row=0, disabled=False, style=discord.ButtonStyle.grey, emoji=None, color=None):
        super().__init__(style=style, label=label, row=row, disabled=disabled, emoji=emoji)
        self.color = color

    async def callback(self, interaction: discord.Interaction):
        view: FloodView = self.view
        submitted_turn = view.turn_token
        await interaction.response.defer()
        async with view.lock:
            if view.is_finished():
                await interaction.followup.send("This Flood game is over.", ephemeral=True)
                return
            if submitted_turn != view.turn_token:
                await interaction.followup.send("That turn has already passed. Check the board for the current player.", ephemeral=True)
                return
            if interaction.user.id != view.players[view.turn].id:
                await interaction.followup.send("It is not your turn.", ephemeral=True)
                return

            view.flood.replace_pixels(interaction.user.id, self.color)
            view.change_turn()
            view.clear_items()
            view.populate_buttons()
            if await view.check_winner():
                return

            if view.vs_bot and view.players[view.turn].id == view.bot.user.id:
                bot_id = view.bot.user.id
                candidates = view.flood.return_probable_buttons(bot_id)
                if candidates:
                    gains = {color: view.flood.territory_gain(bot_id, color) for color in candidates}
                    best_gain = max(gains.values())
                    best = [color for color in candidates if gains[color] == best_gain]
                    view.flood.replace_pixels(bot_id, random.choice(best))
                view.change_turn()
                view.clear_items()
                view.populate_buttons()
                if await view.check_winner():
                    return

            await view.update_msg(embed=view.return_embed(), file=view.flood.return_image())


class FloodView(discord.ui.View):
    def __init__(self, user1, emojis):
        super().__init__(timeout=90)
        self.players = [user1]
        self.emojis = emojis
        self.turn = 0
        self.turn_token = 0
        self.lock = asyncio.Lock()
        self.vs_bot = False
        self.ended = False
        self.bot = None
        self.flood = None
        self.out = None
        self.colors = {
            (255, 0, 0): "red",
            (0, 255, 0): "green",
            (0, 0, 255): "blue",
            (255, 255, 0): "yellow",
            (255, 0, 255): "magenta",
        }

    def populate_buttons(self):
        if not self.flood or self.turn >= len(self.players):
            return
        user_id = self.players[self.turn].id
        choices = self.flood.return_probable_buttons(user_id)
        gains = {color: self.flood.territory_gain(user_id, color) for color in choices}
        for color in choices:
            name = self.colors[color]
            self.add_item(FloodButton(f"Expand +{gains[color]}", color=color, emoji=self.emojis[name]))

    async def update_msg(self, embed=None, file=None):
        if embed is None:
            embed = self.return_embed()
        art = await run_blocking(flood_art_file, embed, "flood_scene")
        attachments = [attachment for attachment in (file, art) if attachment is not None]
        await self.out.edit(view=self, embed=embed, attachments=attachments)

    def change_turn(self):
        self.turn = (self.turn + 1) % len(self.players)
        self.turn_token += 1

    async def check_winner(self):
        areas = [player["total_pixels"] for player in self.flood.players.values()]
        percentages = self.flood.get_percentages()
        winner_indexes = [index for index, percent in enumerate(percentages) if percent > 50]
        title = None
        description = None
        if winner_indexes:
            winner = self.players[winner_indexes[0]]
            is_bot = self.bot and winner.id == self.bot.user.id
            name = "Pippo 🤖" if is_bot else winner.display_name
            title = f"🏆 {name} wins Flood!"
            description = f"{name} captured **{percentages[winner_indexes[0]]:.1f}%** of the board."
        elif sum(areas) >= self.flood.GRID_SIZE ** 2:
            top_area = max(areas)
            leaders = [index for index, area in enumerate(areas) if area == top_area]
            if len(leaders) == 1:
                winner = self.players[leaders[0]]
                is_bot = self.bot and winner.id == self.bot.user.id
                name = "Pippo 🤖" if is_bot else winner.display_name
                title = f"🏆 {name} wins Flood!"
                description = f"The board is full. {name} finished with **{percentages[leaders[0]]:.1f}%**."
            else:
                title = "🤝 Flood is a draw!"
                description = f"The board filled evenly at **{percentages[leaders[0]]:.1f}%** each."

        if title is None:
            return False

        self.ended = True
        self.stop()
        self.clear_items()
        embed = discord.Embed(title=title, description=f"{description}\nRun `/flood` to play again.", color=discord.Color.gold())
        embed.set_image(url="attachment://flood.png")
        await self.update_msg(embed=embed, file=self.flood.return_image())
        return True

    async def on_timeout(self):
        async with self.lock:
            if self.ended:
                return
            for child in self.children:
                child.disabled = True
            if self.out:
                try:
                    await self.out.edit(content="⏱️ Flood ended after inactivity. Run `/flood` to start another game.", view=self)
                except discord.HTTPException:
                    pass

    def return_embed(self):
        percentages = self.flood.get_percentages()
        current_turn = f"{self.players[self.turn].mention}'s turn"
        scores = "\n".join(
            f"{self.emojis['top_left'] if index == 0 else self.emojis['bottom_right']} "
            f"{player.mention}: **{percentages[index]:.1f}%**"
            for index, player in enumerate(self.players)
        )
        embed = discord.Embed(
            title="Pippo Flood · Territory Tug-of-War",
            description=f"Pick a colour to absorb its connected tiles. First past **50%** wins.\n\n{current_turn}\n{scores}",
            color=discord.Color.blue(),
        )
        embed.set_image(url="attachment://flood.png")
        return embed

    @discord.ui.button(label='Join the match', style=discord.ButtonStyle.green)
    async def start(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        async with self.lock:
            if interaction.user.id == self.players[0].id:
                await interaction.followup.send("You cannot join your own challenge.", ephemeral=True)
                return
            if len(self.players) != 1:
                await interaction.followup.send("This match already has two players.", ephemeral=True)
                return
            self.players.append(interaction.user)
            self.flood = Flood(self.players)
            self.clear_items()
            self.populate_buttons()
            await self.update_msg(embed=self.return_embed(), file=self.flood.return_image())



# GuessTheMovie

class GuessTheMovieButton(discord.ui.Button):
    def __init__(self, label:str, correct="", row=0, disabled=False, style=discord.ButtonStyle.grey):
        super().__init__(style=style, label=label, row=row, disabled=disabled)
        self.correct = correct

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()

        if self.correct == self.label:
            self.style = discord.ButtonStyle.green
            for i in self.view.children:
                i.disabled = True
        else:
            self.style = discord.ButtonStyle.red
            for i in self.view.children:
                i.disabled = True
                if i.label == self.correct:
                    i.style = discord.ButtonStyle.green

        await self.view.update_msg()

class GuessTheMovieView(discord.ui.View):

    def __init__(self, movie, other):
        super().__init__(timeout=60)
        self.populate_buttons(movie, other)

    def populate_buttons(self, movie, other):
        other.append(movie)
        random.shuffle(other)
        for i in other:
            btn = GuessTheMovieButton(i, correct=movie)
            self.add_item(btn)

    async def update_msg(self):
        await self.out.edit(view=self)


class ShipView(discord.ui.View):
    def __init__(self, cog, ctx, first, second):
        super().__init__(timeout=120)
        self.cog = cog
        self.ctx = ctx
        self.first = first
        self.second = second
        self.out = None
        self.rerolls = 0
        self.lock = asyncio.Lock()

    @discord.ui.button(label="Reroll this pair · 3 left", style=discord.ButtonStyle.primary, emoji="🎲")
    async def reroll(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("Only the person who started this reading can reroll it.", ephemeral=True)
            return
        await interaction.response.defer()
        async with self.lock:
            if self.rerolls >= 3:
                await interaction.followup.send("This pair has used all three rerolls. Start `/ship` for a fresh reading.", ephemeral=True)
                return
            self.rerolls += 1
            embed, files = await self.cog.make_ship_result(self.first, self.second, reroll=self.rerolls)
            remaining = 3 - self.rerolls
            button.label = f"Reroll this pair · {remaining} left" if remaining else "All rerolls used"
            button.disabled = remaining == 0
            try:
                await interaction.edit_original_response(
                    embed=embed,
                    view=self,
                    attachments=files,
                    allowed_mentions=discord.AllowedMentions.none(),
                )
            except discord.HTTPException:
                self.rerolls -= 1
                button.disabled = False
                button.label = f"Reroll this pair · {3 - self.rerolls} left"
                await interaction.followup.send("That reroll did not load. Try the button once more.", ephemeral=True)

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        if self.out:
            try:
                await self.out.edit(view=self)
            except discord.HTTPException:
                pass


FLAMES_IMAGES = {letter: Path(__file__).resolve().parent / "imgs" / "flames" / f"{letter}.png" for letter in "FLAMES"}


class FlamesView(discord.ui.View):
    def __init__(self, owner_id, first_name, second_name, count, steps, relation, outcome):
        super().__init__(timeout=90)
        self.owner_id = owner_id
        self.first_name = first_name
        self.second_name = second_name
        self.count = count
        self.steps = steps
        self.relation = relation
        self.outcome = outcome
        self.position = 0
        self.message = None
        self.lock = asyncio.Lock()

    def make_embed(self):
        first = discord.utils.escape_markdown(self.first_name).replace("@", "@\u200b")
        second = discord.utils.escape_markdown(self.second_name).replace("@", "@\u200b")
        if self.position == len(self.steps):
            embed = discord.Embed(
                title=f"🔥 {self.relation}",
                description=f"**{first}** + **{second}**\n\nThe last letter standing is **{self.outcome}**.",
                color=discord.Color.orange(),
            )
            embed.add_field(name="Burn order", value=" → ".join(letter for letter, _ in self.steps), inline=False)
            embed.set_footer(text="Just a school-day name game · for fun")
        else:
            remaining = "FLAMES" if self.position == 0 else self.steps[self.position - 1][1]
            burned = " → ".join(letter for letter, _ in self.steps[:self.position]) or "Nothing yet"
            next_letter = self.steps[self.position][0]
            embed = discord.Embed(
                title="🔥 FLAMES · burn the letters",
                description=(
                    f"**{first}** + **{second}**\n"
                    f"Counting number: **{self.count}**\n\n"
                    f"Still in the ring: **{' · '.join(remaining)}**\n"
                    f"Burned: {burned}\n\n"
                    f"Next up: **{next_letter}**"
                ),
                color=discord.Color.orange(),
            )
            embed.set_footer(text=f"Step {self.position}/5 · Only the person who started can reveal the next letter")
        artwork = flames_art_file(embed, f"flames_step_{self.position}")
        self._pending_art = artwork
        self._outcome_art = None
        if self.position == len(self.steps):
            if artwork:
                embed.set_thumbnail(url=f"attachment://{artwork.filename}")
            self._outcome_art = discord.File(FLAMES_IMAGES[self.outcome], filename=f"flames_{self.outcome}.png")
            embed.set_image(url=f"attachment://{self._outcome_art.filename}")
        return embed

    @discord.ui.button(label="Burn next letter", style=discord.ButtonStyle.danger, emoji="🔥")
    async def burn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("Only the person who started this round can reveal the letters.", ephemeral=True)
            return
        await interaction.response.defer()
        async with self.lock:
            if self.position >= len(self.steps):
                await interaction.followup.send("The FLAMES result is already revealed.", ephemeral=True)
                return
            self.position += 1
            if self.position >= len(self.steps):
                button.disabled = True
                self.stop()
            embed = await run_blocking(self.make_embed)
            await interaction.edit_original_response(
                embed=embed,
                view=self,
                attachments=[art for art in (self._pending_art, self._outcome_art) if art is not None],
                allowed_mentions=discord.AllowedMentions.none(),
            )

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except discord.HTTPException:
                pass
