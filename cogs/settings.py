import asyncio
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
                await thewhistler.send(embed=emb, allowed_mentions=discord.AllowedMentions.none())
            except Exception:
                thewhistler = None
        text = "✅ Thank you! Your feedback has been sent directly to the developer." if thewhistler else "I couldn't deliver your feedback. Please try again later."
        await interaction.followup.send(text, ephemeral=True)


class LeaderboardSelect(discord.ui.Select):
    def __init__(self, current_key="bollywood"):
        options = [
            discord.SelectOption(label="Movie Games (shared)", emoji="🎬", value="bollywood", default=(current_key == "bollywood")),
            discord.SelectOption(label="Plotster", emoji="📜", value="plotster", default=(current_key == "plotster")),
            discord.SelectOption(label="Coin Wealth", emoji="🪙", value="coins", default=(current_key == "coins")),
        ]
        super().__init__(placeholder="Select leaderboard...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        choice = self.values[0]
        await interaction.response.defer()
        async with self.view.lock:
            if self.view.is_finished():
                await interaction.followup.send("This leaderboard menu expired. Open `/leaderboard` again.", ephemeral=True)
                return
            for opt in self.options:
                opt.default = (opt.value == choice)
            embed = await self.view.fetch_embed(choice)
            await interaction.edit_original_response(embed=embed, view=self.view)


class LeaderboardView(discord.ui.View):
    def __init__(self, db, initial_key="bollywood", timeout=120):
        super().__init__(timeout=timeout)
        self.db = db
        self.lock = asyncio.Lock()
        self.message = None
        self.add_item(LeaderboardSelect(initial_key))

    async def fetch_embed(self, cmd_key: str) -> discord.Embed:
        name_map = {
            "bollywood": ("Movie Games · Bollywood, Hollywood & Poster", "bollywood_points", "points", "🎬"),
            "plotster": ("Plotster", "plotster_points", "points", "📜"),
            "coins": ("Coin Wealth", "points", "coins", "🪙")
        }
        title, table, col, icon = name_map.get(cmd_key, ("Bollywood", "bollywood_points", "points", "🏆"))
        sql = f"SELECT user_id, {col} as score FROM {table} WHERE {col} IS NOT NULL ORDER BY {col} DESC, user_id ASC LIMIT 10"
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
        footer = "Use the dropdown menu to switch categories."
        if cmd_key == "bollywood":
            footer += " Movie scores combine Bollywood and Hollywood hangman plus Poster."
        emb.set_footer(text=footer)
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
        """Set a short server prefix, or use `reset` to restore the default dot."""
        if ctx.guild is None:
            await ctx.reply("Prefix can only be changed inside a server.")
            return

        prefix = prefix.strip()
        if prefix.casefold() in {"reset", "default"}:
            prefix = "."
            reset = True
        else:
            reset = False
            if not prefix:
                await ctx.reply("The prefix cannot be empty. Use `reset` to restore the default `.`.", ephemeral=True)
                return
            if any(character.isspace() for character in prefix):
                await ctx.reply("A prefix cannot contain spaces or other whitespace.", ephemeral=True)
                return
            if len(prefix) > 10:
                await ctx.reply("A prefix can be at most 10 characters long.", ephemeral=True)
                return

        await self.bot.db.servers.prefix_add(ctx.guild.id, prefix)
        if getattr(self.bot, "prefix_cache", None) is not None:
            self.bot.prefix_cache.invalidate(ctx.guild.id)
        if reset:
            await ctx.reply("Your server prefix has been reset to `.`.")
        else:
            safe_prefix = discord.utils.escape_markdown(prefix)
            await ctx.reply(f"Your prefix has been updated to `{safe_prefix}`.")

    @change_prefix.error
    async def change_prefix_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.reply("You need `Manage Server` permission to change the prefix.")
        else:
            await ctx.reply("Could not change prefix. Please try again.")

    @commands.hybrid_command(name="leaderboard")
    async def leaderboard(self, ctx, command: Literal["bollywood", "plotster", "coins"] = "bollywood"):
        """See the interactive movie-game, Plotster, or coin leaderboard."""
        cmd_key = command.lower()
        if cmd_key not in ("bollywood", "plotster", "coins"):
            cmd_key = "bollywood"

        view = LeaderboardView(self.bot.db, initial_key=cmd_key)
        embed = await view.fetch_embed(cmd_key)
        msg = await ctx.reply(embed=embed, view=view)
        view.message = msg

    @commands.hybrid_command(name="suggest")
    async def suggest(self, ctx, *, feedback_text: str = None):
        """Send private feedback to the developer using the slash-command form."""
        if ctx.interaction and not feedback_text:
            modal = SuggestModal(self.bot)
            await ctx.interaction.response.send_modal(modal)
            return

        if not ctx.interaction:
            if ctx.message:
                try:
                    await ctx.message.delete()
                except (discord.Forbidden, discord.HTTPException):
                    pass
            await ctx.send("Use `/suggest` to open a private feedback form. Prefix commands are visible in this channel.")
            return

        if not feedback_text:
            await ctx.reply("Open `/suggest` and enter your feedback in the private form.", ephemeral=True)
            return

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
                await thewhistler.send(embed=emb, allowed_mentions=discord.AllowedMentions.none())
            except discord.HTTPException:
                thewhistler = None

        if not thewhistler:
            await ctx.reply("I couldn't deliver your suggestion. Please try again later.", ephemeral=True)
            return
        await ctx.reply("✅ Your suggestion has been noted and delivered!", ephemeral=True)


async def setup(bot):
    await bot.add_cog(Settings(bot))
