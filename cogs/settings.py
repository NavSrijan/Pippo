from typing import Literal
from enum import Enum
import datetime
from zoneinfo import ZoneInfo

from discord.ext import commands, tasks
from discord import app_commands

from database import Servers
import ipdb
import discord


class Settings(commands.Cog):
    """Basic settings commands"""

    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="change_prefix")
    async def change_prefix(self, ctx, prefix: str):
        """Change your server's prefix to whatever you like. Default is """
        await self.bot.db.servers.prefix_add(ctx.guild.id, prefix)
        await ctx.reply(f"Your prefix has been updated to {prefix}")

    @commands.hybrid_command(name="leaderboard")
    async def leaderboard(self, ctx, command: str):
        """See the leaderboard of a particular command"""
        command_map = {"bollywood": "bollywood_points", "plotster": "plotster_points"}
        try:
            command = command_map[command.lower()]
            sql = f"SELECT * FROM {command} ORDER BY points DESC LIMIT 10"
            res = await self.bot.db.view(sql)
            desc = ""
            j=1
            for i in res:
                desc+=f"{j}. <@{i['user_id']}>: {i['points']}\n"
                j+=1
            await ctx.reply(embed=discord.Embed(title=f"{command} Leaderboard", description=desc))
        except:
            await ctx.reply("Command not found.")

    @commands.hybrid_command(name="suggest")
    async def suggest(self, ctx, feedback_text: str):
        """Feedback to the author"""
        THEWHISTLER = self.bot.THEWHISTLER
        if ctx.interaction:
            sugg = feedback_text
            thewhistler = self.bot.get_user(THEWHISTLER)
            emb = discord.Embed(description=sugg)
            emb.set_author(name=ctx.message.author.display_name +
                           " suggested.",
                           icon_url=ctx.message.author.avatar.url)
            emb.color = discord.Color.blurple()
            await thewhistler.send(embed=emb)
            await ctx.reply("Your suggestion has been noted.", ephemeral=True)
        else:
            sugg = ctx.message.content
            thewhistler = self.bot.get_user(THEWHISTLER)
            emb = discord.Embed(description=sugg)
            emb.set_author(name=ctx.message.author.display_name +
                           " suggested.",
                           icon_url=ctx.message.author.avatar.url)
            emb.color = discord.Color.blurple()
            await thewhistler.send(embed=emb)
            await ctx.reply("Your suggestion has been noted.", ephemeral=True)
            await ctx.message.delete()


async def setup(bot):
    await bot.add_cog(Settings(bot))
