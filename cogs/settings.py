from typing import Literal
import datetime
from zoneinfo import ZoneInfo

from discord.ext import commands, tasks
from discord import app_commands
import discord


class SuggestModal(discord.ui.Modal, title="💡 Suggestion & Feedback"):
    subject = discord.ui.TextInput(
        label="Title / Feature Name",
        placeholder="Brief summary of your suggestion...",
        max_length=100,
        required=True
    )
    details = discord.ui.TextInput(
        label="Details",
        style=discord.TextStyle.paragraph,
        placeholder="Describe your idea or report the issue in detail...",
        max_length=1500,
        required=True
    )

    def __init__(self, bot):
        super().__init__()
        self.bot = bot

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        try:
            thewhistler = self.bot.get_user(self.bot.THEWHISTLER) or await self.bot.fetch_user(self.bot.THEWHISTLER)
        except discord.HTTPException:
            thewhistler = None
        if thewhistler:
            emb = discord.Embed(title=f"💡 Suggestion: {self.subject.value}", description=self.details.value, color=discord.Color.blurple())
            emb.set_author(name=f"{interaction.user.display_name} ({interaction.user.id})", icon_url=interaction.user.display_avatar.url)
            try:
                await thewhistler.send(embed=emb)
            except Exception:
                thewhistler = None
        text = "✅ Thank you! Your feedback has been sent directly to the developer." if thewhistler else "I couldn't deliver your feedback. Please try again later."
        await interaction.followup.send(text, ephemeral=True)


class LeaderboardSelect(discord.ui.Select):
    def __init__(self, current_key="bollywood"):
        options = [
            discord.SelectOption(label="Bollywood Hangman", emoji="🎬", value="bollywood", default=(current_key == "bollywood")),
            discord.SelectOption(label="Plotster", emoji="📜", value="plotster", default=(current_key == "plotster")),
            discord.SelectOption(label="Coin Wealth", emoji="🪙", value="coins", default=(current_key == "coins")),
        ]
        super().__init__(placeholder="Select leaderboard...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        choice = self.values[0]
        for opt in self.options:
            opt.default = (opt.value == choice)
        embed = await self.view.fetch_embed(choice)
        await interaction.response.edit_message(embed=embed, view=self.view)


class LeaderboardView(discord.ui.View):
    def __init__(self, db, initial_key="bollywood", timeout=120):
        super().__init__(timeout=timeout)
        self.db = db
        self.message = None
        self.add_item(LeaderboardSelect(initial_key))

    async def fetch_embed(self, cmd_key: str) -> discord.Embed:
        name_map = {
            "bollywood": ("Bollywood Hangman", "bollywood_points", "points", "🎬"),
            "plotster": ("Plotster", "plotster_points", "points", "📜"),
            "coins": ("Coin Wealth", "points", "coins", "🪙")
        }
        title, table, col, icon = name_map.get(cmd_key, ("Bollywood", "bollywood_points", "points", "🏆"))
        sql = f"SELECT user_id, {col} as score FROM {table} ORDER BY {col} DESC LIMIT 10"
        podium = {1: "🥇", 2: "🥈", 3: "🥉"}

        try:
            res = await self.db.view(sql)
            if not res:
                desc = "No scores recorded yet."
            else:
                desc = ""
                for rank, row in enumerate(res, 1):
                    badge = podium.get(rank, f"`#{rank}`")
                    uid = row['user_id']
                    score = row['score']
                    desc += f"{badge} <@{uid}> — **{score:,}** {col}\n"
        except Exception as e:
            print(f"Error fetching leaderboard {cmd_key}: {e}")
            desc = "Could not load leaderboard data."

        emb = discord.Embed(title=f"{icon} {title} Top 10 Leaderboard", description=desc, color=discord.Color.gold())
        emb.set_footer(text="Use the dropdown menu to switch categories.")
        return emb

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except Exception:
                pass


class Settings(commands.Cog):
    """Basic settings commands"""

    def __init__(self, bot):
        self.bot = bot

    @commands.has_permissions(manage_guild=True)
    @commands.hybrid_command(name="change_prefix")
    async def change_prefix(self, ctx, prefix: str):
        """Change your server's prefix to whatever you like. Default is ."""
        if ctx.guild is None:
            await ctx.reply("Prefix can only be changed inside a server.")
            return
        await self.bot.db.servers.prefix_add(ctx.guild.id, prefix)
        await ctx.reply(f"Your prefix has been updated to `{prefix}`")

    @change_prefix.error
    async def change_prefix_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.reply("You need `Manage Server` permission to change the prefix.")
        else:
            await ctx.reply("Could not change prefix. Please try again.")

    @commands.hybrid_command(name="leaderboard")
    async def leaderboard(self, ctx, command: str = "bollywood"):
        """See the interactive leaderboard (Bollywood, Plotster, Coins)"""
        cmd_key = command.lower()
        if cmd_key not in ("bollywood", "plotster", "coins"):
            cmd_key = "bollywood"

        view = LeaderboardView(self.bot.db, initial_key=cmd_key)
        embed = await view.fetch_embed(cmd_key)
        msg = await ctx.reply(embed=embed, view=view)
        view.message = msg

    @commands.hybrid_command(name="suggest")
    async def suggest(self, ctx, *, feedback_text: str = None):
        """Send feedback, ideas, or bug reports directly to the developer"""
        if ctx.interaction and not feedback_text:
            modal = SuggestModal(self.bot)
            await ctx.interaction.response.send_modal(modal)
            return

        if not feedback_text:
            await ctx.reply("Please provide your feedback or suggestion! Usage: `.suggest <your message>`", ephemeral=True)
            return

        if ctx.interaction:
            await ctx.defer(ephemeral=True)
        THEWHISTLER = self.bot.THEWHISTLER
        try:
            thewhistler = self.bot.get_user(THEWHISTLER) or await self.bot.fetch_user(THEWHISTLER)
        except Exception:
            thewhistler = None

        if thewhistler:
            emb = discord.Embed(title="💡 User Suggestion", description=feedback_text, color=discord.Color.blurple())
            emb.set_author(name=f"{ctx.author.display_name} ({ctx.author.id})", icon_url=ctx.author.display_avatar.url)
            try:
                await thewhistler.send(embed=emb)
            except discord.HTTPException:
                thewhistler = None

        if not thewhistler:
            await ctx.reply("I couldn't deliver your suggestion. Please try again later.", ephemeral=True)
            return
        await ctx.reply("✅ Your suggestion has been noted and delivered!", ephemeral=True)
        if not ctx.interaction and ctx.message:
            try:
                await ctx.message.delete()
            except (discord.Forbidden, discord.HTTPException):
                pass


async def setup(bot):
    await bot.add_cog(Settings(bot))
