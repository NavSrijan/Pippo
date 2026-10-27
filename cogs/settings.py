from typing import Literal
import datetime
from zoneinfo import ZoneInfo

from discord.ext import commands, tasks
from discord import app_commands
import discord


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
    async def leaderboard(self, ctx, command: str):
        """See the leaderboard of a particular command"""
        command_map = {"bollywood": "bollywood_points", "plotster": "plotster_points"}
        name_map = {"bollywood": "Bollywood", "plotster": "Plotster"}
        cmd_key = command.lower()
        if cmd_key not in command_map:
            await ctx.reply(f"Command '{command}' not found. Available leaderboards: `bollywood`, `plotster`.")
            return

        table_name = command_map[cmd_key]
        sql = f"SELECT user_id, points FROM {table_name} ORDER BY points DESC LIMIT 10"
        try:
            res = await self.bot.db.view(sql)
            if not res:
                desc = "No scores recorded yet."
            else:
                desc = ""
                for j, i in enumerate(res, 1):
                    desc += f"{j}. <@{i['user_id']}>: {i['points']}\n"
            await ctx.reply(embed=discord.Embed(title=f"{name_map[cmd_key]} Leaderboard", description=desc, color=discord.Color.gold()))
        except Exception as e:
            await ctx.reply("Could not load leaderboard at this moment.")

    @commands.hybrid_command(name="suggest")
    async def suggest(self, ctx, feedback_text: str):
        """Feedback to the author"""
        THEWHISTLER = self.bot.THEWHISTLER
        try:
            thewhistler = self.bot.get_user(THEWHISTLER) or await self.bot.fetch_user(THEWHISTLER)
        except Exception:
            thewhistler = None

        if thewhistler:
            emb = discord.Embed(description=feedback_text, color=discord.Color.blurple())
            emb.set_author(name=f"{ctx.author.display_name} suggested.", icon_url=ctx.author.display_avatar.url)
            try:
                await thewhistler.send(embed=emb)
            except Exception:
                pass

        await ctx.reply("Your suggestion has been noted.", ephemeral=True)
        if not ctx.interaction and ctx.message:
            try:
                await ctx.message.delete()
            except (discord.Forbidden, discord.HTTPException):
                pass


async def setup(bot):
    await bot.add_cog(Settings(bot))
