from discord.ext import commands
import discord


class Info(commands.Cog):
    """Commands for analytics and events"""

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        try:
            thewhistler = self.bot.get_user(self.bot.THEWHISTLER) or await self.bot.fetch_user(self.bot.THEWHISTLER)
            if thewhistler:
                await thewhistler.send(f"Pippo joined server: {guild.name} ({guild.id})")
        except Exception as e:
            print(f"Could not notify owner of guild join: {e}")

        try:
            if hasattr(self.bot, 'db') and hasattr(self.bot.db, 'servers'):
                await self.bot.db.servers.prefix_add(guild.id, getattr(self.bot, 'prefix', '.'))
        except Exception as e:
            print(f"Could not register prefix for new guild: {e}")


async def setup(bot):
    await bot.add_cog(Info(bot))
