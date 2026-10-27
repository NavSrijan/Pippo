"""Interactive game discovery and launch menu."""

from copy import copy

import discord
from discord.ext import commands

from discord.ext.commands.view import StringView


GAME_OPTIONS = [
    ("bollywood", "Bollywood movie hangman", "🎬"),
    ("hollywood", "Hollywood movie hangman", "🎥"),
    ("plotster", "Guess a movie from its story", "📜"),
    ("quizster", "Multiple choice movie trivia", "🧠"),
    ("poster", "Guess the pixelated movie poster", "🖼️"),
    ("bingo", "5×5 number bingo", "🎱"),
    ("tictactoe", "Classic 3×3 strategy game", "❎"),
    ("memory", "Match all eight card pairs", "🃏"),
    ("flood", "Capture the most board territory", "🌈"),
    ("clash", "AI judged creative battle", "⚔️"),
    ("woof", "Guess the dog breed", "🐶"),
    ("meow", "Guess the cat breed", "🐱"),
    ("onewordstory", "Build a story one word at a time", "✍️"),
]
GAME_TITLES = {
    "bollywood": "Bollywood",
    "hollywood": "Hollywood",
    "plotster": "Plotster",
    "quizster": "Quizster",
    "poster": "Movie Poster",
    "bingo": "Bingo",
    "tictactoe": "Tic Tac Toe",
    "memory": "Memory Match",
    "flood": "Flood",
    "clash": "Clash of Creations",
    "woof": "Dog Breed Quiz",
    "meow": "Cat Breed Quiz",
    "onewordstory": "One Word Story",
}
GAME_CATEGORIES = {
    "movies": ("Movie Games", "🎬", {"bollywood", "hollywood", "plotster", "quizster", "poster"}),
    "party": ("Party Games", "🎉", {"bingo", "tictactoe", "memory", "flood", "clash"}),
    "animals": ("Animal Quizzes", "🐾", {"woof", "meow"}),
    "social": ("Social Games", "✍️", {"onewordstory"}),
}


class PlayMenuView(discord.ui.View):
    def __init__(self, bot, ctx, timeout=180):
        super().__init__(timeout=timeout)
        self.bot = bot
        self.ctx = ctx
        self.author_id = ctx.author.id
        self.selected_category = None
        self.selected_game = None
        self.selected_opponent = None
        self.game_select = discord.ui.Select(
            placeholder="Choose a category first",
            min_values=1,
            max_values=1,
            options=[discord.SelectOption(label="Choose a category first", value="none")],
            disabled=True,
            row=1,
        )
        self.game_select.callback = self.choose_game
        self.add_item(self.game_select)
        self.opponent_select = discord.ui.UserSelect(
            placeholder="Choose your opponent",
            min_values=1,
            max_values=1,
            disabled=True,
            row=2,
        )
        self.opponent_select.callback = self.choose_opponent
        self.add_item(self.opponent_select)

    def menu_text(self):
        if not self.selected_game:
            return (
                "🎮 **Choose a category, then a game**\n"
                "Then choose solo play or play with friends. "
                "The solo and multiplayer options keep the same behavior as their commands."
            )
        label, description, _ = next(option for option in GAME_OPTIONS if option[0] == self.selected_game)
        return f"🎮 **{GAME_TITLES[label]}**\n{description}\n\nChoose a play mode below."

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("Run `/play` to open your own game menu.", ephemeral=True)
            return False
        return True

    async def choose_opponent(self, interaction: discord.Interaction):
        opponent = self.opponent_select.values[0]
        if opponent.id == self.author_id or opponent.bot:
            await interaction.response.send_message("Choose another person from this server.", ephemeral=True)
            return
        self.selected_opponent = opponent
        self.stop()
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(content=f"Starting {GAME_TITLES[self.selected_game]} against {opponent.mention}…", view=self)
        await self.launch(solo=False, opponent=opponent)

    async def launch(self, solo: bool, opponent=None):
        name = self.selected_game
        command = self.bot.get_command(name)
        if command is None:
            await self.ctx.send(f"I couldn’t find the `{name}` game command. Try `/help` for the command list.")
            return

        # Use a fresh prefix context so the selected command runs its normal
        # checks, converters, cooldowns, concurrency guard, and invocation hooks.
        # Sending game messages through the channel also avoids the original
        # /play interaction token expiring during a long game.
        game_ctx = copy(self.ctx)
        game_ctx.interaction = None
        game_ctx.command = command
        game_ctx.invoked_with = name
        game_ctx.command_failed = False
        game_ctx.args = []
        game_ctx.kwargs = {}
        if name in {"bollywood", "hollywood", "plotster", "quizster", "poster"}:
            arguments = f"solo: {solo}"
        elif name in {"tictactoe", "memory"}:
            arguments = f"<@{opponent.id}>" if opponent else ""
        else:
            arguments = str(solo)
        game_ctx.view = StringView(arguments)
        try:
            await command.invoke(game_ctx)
        except commands.CommandError as error:
            await command.dispatch_error(game_ctx, error)
        else:
            self.bot.dispatch("command_completion", game_ctx)

    async def start_mode(self, interaction: discord.Interaction, solo: bool):
        if not self.selected_game:
            await interaction.response.send_message("Choose a game first.", ephemeral=True)
            return
        if not solo and self.selected_game in {"tictactoe", "memory"}:
            self.opponent_select.disabled = False
            await interaction.response.edit_message(content="Choose the person you want to challenge:", view=self)
            return

        self.stop()
        for child in self.children:
            child.disabled = True
        mode = "solo" if solo else "with friends"
        await interaction.response.edit_message(content=f"Starting {GAME_TITLES[self.selected_game]} {mode}…", view=self)
        await self.launch(solo=solo)

    @discord.ui.select(
        placeholder="Select a category...",
        min_values=1,
        max_values=1,
        options=[discord.SelectOption(label=label, emoji=emoji, value=value)
                 for value, (label, emoji, _) in GAME_CATEGORIES.items()],
        row=0,
    )
    async def select_category(self, interaction: discord.Interaction, select: discord.ui.Select):
        self.selected_category = select.values[0]
        valid_games = GAME_CATEGORIES[self.selected_category][2]
        self.game_select.options = [
            discord.SelectOption(label=GAME_TITLES[label], description=description, emoji=emoji, value=label)
            for label, description, emoji in GAME_OPTIONS if label in valid_games
        ]
        self.game_select.placeholder = "Select a game..."
        self.game_select.disabled = False
        self.selected_game = None
        self.selected_opponent = None
        self.opponent_select.disabled = True
        await interaction.response.edit_message(content=f"**{GAME_CATEGORIES[self.selected_category][0]}**\nChoose a game to continue.", view=self)

    async def choose_game(self, interaction: discord.Interaction):
        self.selected_game = self.game_select.values[0]
        self.selected_opponent = None
        self.opponent_select.disabled = True
        await interaction.response.edit_message(content=self.menu_text(), view=self)

    @discord.ui.button(label="Play solo", style=discord.ButtonStyle.success, emoji="🧍", row=3)
    async def solo_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.start_mode(interaction, solo=True)

    @discord.ui.button(label="Play with friends", style=discord.ButtonStyle.primary, emoji="👥", row=3)
    async def friends_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.start_mode(interaction, solo=False)

    @discord.ui.button(label="Close", style=discord.ButtonStyle.secondary, row=3)
    async def close_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.stop()
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(content="Game menu closed.", view=self)

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        if getattr(self, "message", None):
            try:
                await self.message.edit(content="This game menu expired. Run `/play` to open it again.", view=self)
            except Exception:
                pass


class Play(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="play")
    async def play(self, ctx):
        """Open the interactive game menu."""
        view = PlayMenuView(self.bot, ctx)
        view.message = await ctx.send(view.menu_text(), view=view)


async def setup(bot):
    await bot.add_cog(Play(bot))
