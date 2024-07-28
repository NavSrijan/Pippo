from typing import Literal
from enum import Enum
import datetime
from zoneinfo import ZoneInfo
import time
import random
import re
import requests
import json
import asyncio

from discord.ext import commands, tasks
import discord

import ipdb
import hashlib
import requests
from PIL import Image, ImageDraw, ImageOps
from io import BytesIO

class Economy(commands.Cog):
    """Economy commands"""

    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="balance", aliases=["bal", "khazana", "money", "cash", "paisa", "rupya"])
    async def balance(self, ctx):
        "How many coins do you have?"
        bal = await self.bot.db.coins.get_amount_coins(ctx.author.id)
        await ctx.reply(f"You have **{bal['coins']}** coins.")

    @commands.hybrid_command(name="add_coins", hidden=True)
    async def add_coins(self, ctx, user: discord.Member, coins=0):
        "Add coins to a user"
        if ctx.author.id == self.bot.THEWHISTLER:
            await self.bot.db.coins.add_coins(user.id, coins=coins)
            await ctx.reply(f"{coins} added to {user.mention}")

    @commands.hybrid_command(name="send_coins")
    async def send_coins(self, ctx, user: discord.Member, coins=0):
        """Send coins to another user"""
        await self.bot.db.coins.add_coins(user.id, coins=coins)
        await self.bot.db.coins.deduct_coins(ctx.author.id, coins=coins)
        await ctx.reply(f"{ctx.author.mention} sent {coins} coins to {user.mention}")



async def setup(bot):
    await bot.add_cog(Economy(bot))

