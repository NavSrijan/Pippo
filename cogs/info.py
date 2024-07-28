from discord.ext import commands, tasks
from discord import app_commands

from database import Servers
import ipdb


class Info(commands.Cog):
    """Commands for analytics"""

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        thewhistler = self.bot.get_user(self.bot.THEWHISTLER)
        await thewhistler.send(guild.name)
        servers = Servers()
        servers.insert_new_entry(guild.id, self.bot.prefix)


async def setup(bot):
    await bot.add_cog(Info(bot))
