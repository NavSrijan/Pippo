from typing import Literal
from enum import Enum
import datetime
from zoneinfo import ZoneInfo
import time

from discord.ext import commands, tasks
from discord import app_commands

import ipdb


class Schedules(commands.Cog):
    """Basic hello commands"""

    def __init__(self, bot):
        self.bot = bot

        self.gm.start()

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

    class Boolean_choice(Enum):
        true = 1
        false = 0

    @signup.command(name="greetings")
    async def greet(self, ctx, good_morning: Boolean_choice,
                    good_afternoon: Boolean_choice,
                    good_evening: Boolean_choice, good_night: Boolean_choice):
        """Signup for greetings."""
        user_id = ctx.author.id

        good_morning = bool(good_morning.value)
        good_evening = bool(good_evening.value)
        good_afternoon = bool(good_afternoon.value)
        good_night = bool(good_night.value)

        await self.bot.db.greetings.insert(user_id,
                              gm=good_morning,
                              ga=good_afternoon,
                              ge=good_evening,
                              gn=good_night)
        await ctx.reply("You are signed up!")

    @tasks.loop(time=datetime.time(hour=6,
                                   minute=0,
                                   tzinfo=ZoneInfo("Asia/Kolkata")))
    async def gm(self):
        """Wish good morning"""
        users = self.greetings.get_users("gm")
        for i in users:
            await self.bot.get_user(i[0]).send("Good Morning!")

    @tasks.loop(time=datetime.time(hour=13,
                                   minute=0,
                                   tzinfo=ZoneInfo("Asia/Kolkata")))
    async def ga(self):
        """Wish good afternoon"""
        users = self.greetings.get_users("ga")
        for i in users:
            await self.bot.get_user(i[0]).send("Good Afternoon!")

    @tasks.loop(time=datetime.time(hour=17,
                                   minute=0,
                                   tzinfo=ZoneInfo("Asia/Kolkata")))
    async def ge(self):
        """Wish good evening"""
        users = self.greetings.get_users("ge")
        for i in users:
            await self.bot.get_user(i[0]).send("Good Evening!")

    @tasks.loop(time=datetime.time(hour=22,
                                   minute=0,
                                   tzinfo=ZoneInfo("Asia/Kolkata")))
    async def gn(self):
        """Wish good night"""
        users = self.greetings.get_users("gn")
        for i in users:
            await self.bot.get_user(i[0]).send("Good Night!")


async def setup(bot):
    await bot.add_cog(Schedules(bot))
