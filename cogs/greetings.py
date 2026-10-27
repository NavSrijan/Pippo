from typing import Literal
import datetime
from zoneinfo import ZoneInfo
import time

from discord.ext import commands, tasks
from discord import app_commands
import discord


class Schedules(commands.Cog):
    """Basic hello commands"""

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        for loop in (self.gm, self.ga, self.ge, self.gn):
            if not loop.is_running():
                loop.start()

    def cog_unload(self):
        for loop in (self.gm, self.ga, self.ge, self.gn):
            if loop.is_running():
                loop.cancel()

    @commands.hybrid_command(name="test", hidden=True)
    async def test(self, ctx):
        await ctx.reply("Test successful.")

    @commands.hybrid_command(name="ping")
    async def ping(self, ctx):
        start = time.perf_counter()
        message = await ctx.send("Ping...")
        end = time.perf_counter()
        duration = (end - start) * 1000
        await message.edit(content='Pong! {:.2f}ms'.format(duration))

    @commands.hybrid_group(name="signup")
    async def signup(self, ctx):
        """Signup for various commands."""
        if ctx.invoked_subcommand is None:
            await ctx.send("Not a valid command.")

    @signup.command(name="greetings")
    async def greet(self, ctx,
                    good_morning: bool = False,
                    good_afternoon: bool = False,
                    good_evening: bool = False,
                    good_night: bool = False):
        """Signup for greetings."""
        user_id = ctx.author.id

        await self.bot.db.greetings.insert(user_id,
                                          gm=good_morning,
                                          ga=good_afternoon,
                                          ge=good_evening,
                                          gn=good_night)
        await ctx.reply("You are signed up!")

    async def _send_greeting(self, cmd, text):
        try:
            users = await self.bot.db.greetings.get_users(cmd)
        except Exception as e:
            print(f"Error fetching {cmd} greeting users: {e}")
            return
        for i in users:
            try:
                user = self.bot.get_user(i[0]) or await self.bot.fetch_user(i[0])
                if user:
                    await user.send(text)
            except (discord.Forbidden, discord.HTTPException):
                pass
            except Exception as e:
                print(f"Failed to send greeting to {i[0]}: {e}")

    @tasks.loop(time=datetime.time(hour=6,
                                   minute=0,
                                   tzinfo=ZoneInfo("Asia/Kolkata")))
    async def gm(self):
        """Wish good morning"""
        await self._send_greeting("gm", "Good Morning!")

    @gm.before_loop
    async def before_gm(self):
        await self.bot.wait_until_ready()

    @tasks.loop(time=datetime.time(hour=13,
                                   minute=0,
                                   tzinfo=ZoneInfo("Asia/Kolkata")))
    async def ga(self):
        """Wish good afternoon"""
        await self._send_greeting("ga", "Good Afternoon!")

    @ga.before_loop
    async def before_ga(self):
        await self.bot.wait_until_ready()

    @tasks.loop(time=datetime.time(hour=17,
                                   minute=0,
                                   tzinfo=ZoneInfo("Asia/Kolkata")))
    async def ge(self):
        """Wish good evening"""
        await self._send_greeting("ge", "Good Evening!")

    @ge.before_loop
    async def before_ge(self):
        await self.bot.wait_until_ready()

    @tasks.loop(time=datetime.time(hour=22,
                                   minute=0,
                                   tzinfo=ZoneInfo("Asia/Kolkata")))
    async def gn(self):
        """Wish good night"""
        await self._send_greeting("gn", "Good Night!")

    @gn.before_loop
    async def before_gn(self):
        await self.bot.wait_until_ready()


async def setup(bot):
    await bot.add_cog(Schedules(bot))
