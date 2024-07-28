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

class Actions(commands.Cog):
    """Actions commands"""

    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="kiss")
    async def kiss(self, ctx, user:discord.Member=None):
        """Kiss"""
        emb = discord.Embed()
        if ctx.author.nick:
            name2 = ctx.author.nick
        else:
            name2 = ctx.author.name
        if user==None:
            emb.title = f"{name2} kissed air"
        else:
            if user.nick:
                name = user.nick
            else:
                name = user.name
            if random.choices([True, False], weights=[60, 40])[0]:
                # ACCEPTANCE
                lines = [
                    "{} planted a soft kiss on {}'s lips.",
                    "The tender touch of {}'s lips met {}'s in a sweet, lingering kiss.",
                    "{} leaned in and gently pressed their lips against {}'s, creating a moment of pure bliss.",
                    "A passionate exchange of kisses occurred between {} and {}, leaving them both breathless.",
                    "The world seemed to fade away as {} and {} locked lips in a passionate embrace.",
                    "{} initiated a passionate kiss, igniting a spark of desire between them and {}.",
                    "In a moment of pure spontaneity, {} leaned in and kissed {}, setting their hearts ablaze.",
                    "The chemistry between {} and {} was undeniable, as their lips met in a fiery, unforgettable kiss.",
                    "{}'s soft lips brushed against {}'s, leaving them both longing for more.",
                    "The gentle touch of {}'s lips against {}'s sent shivers down their spines, creating a memory they would cherish forever."
                ]

                gifs = [
                        "https://media.tenor.com/28PRxZllZ88AAAAS/skitchura-skitchura-d.gif",
                        "https://media.tenor.com/FNHYYfHcKLkAAAAC/katrina-kaif-ranbir-kapoor.gif",
                        "https://media.tenor.com/X5krze_s5rIAAAAS/beyhadh2-mayra.gif",
                        "https://media.tenor.com/8sbfoBtT628AAAAC/ye-rishta-kya-kehlata-hai-indian-television-soap-opera.gif",
                        "https://media.tenor.com/weXHd8OOT0gAAAAC/kiss-enthiran.gif",
                        "https://media.tenor.com/MOfAaO_0iIYAAAAd/kiss-ramesh.gif",
                        "https://media.tenor.com/FmmWlSywFBkAAAAd/bollywood2-deepika-padukone.gif",
                        "https://media.tenor.com/r3iZ8UJc-AwAAAAd/%E1%83%9A%E1%83%90%E1%83%9B%E1%83%90%E1%83%96%E1%83%9D-flirti.gif",
                        "https://media.tenor.com/41b3mGyJrNsAAAAd/alia-bhatt-sidharth-malhotra.gif",
                        "https://media.tenor.com/wANmca86o1kAAAAS/petekao-dark-blue-kiss.gif"
                        ]
                
            else:
                # REJECTION
                lines = [
                    "{} gently turned away, avoiding {}'s attempt to kiss their lips.",
                    "Despite the anticipation, {} pulled back, preventing their lips from meeting {}'s.",
                    "{} hesitated, refraining from pressing their lips against {}'s, signaling a rejection.",
                    "{} quickly averted their gaze, denying {} the passionate exchange of kisses they desired.",
                    "{} gently pushed {} away, choosing not to lock lips in a passionate embrace.",
                    "With a hint of regret, {} gently declined {}'s attempt to initiate a passionate kiss.",
                    "{} stepped back, avoiding the fiery and unforgettable kiss {} yearned for.",
                    "{} offered a polite smile, signaling that their lips were off-limits to {}.",
                    "{} withdrew slightly, creating a physical distance that prevented {}'s soft lips from brushing against theirs.",
                    "{} politely refused {}'s advances, knowing that their lips meeting would only create a memory of heartache."
                        ]

                gifs = [
                        "https://media.tenor.com/P3FvJNYdca4AAAAC/%E0%A4%A8%E0%A4%B9%E0%A5%80%E0%A4%82-%E0%A4%A8%E0%A4%BE.gif",
                        "https://media.tenor.com/WJavYXjegxQAAAAC/crying-oru-indian-pranayakadha.gif",
                        "https://media.tenor.com/s3E5Yd67X88AAAAd/cry-about-it-mald.gif",
                        "https://media.tenor.com/KnvA9TyNb2cAAAAC/china-trespasses-indian-territory-bhosdike.gif",
                        "https://media.tenor.com/5xAy0jp9aCAAAAAC/vaak-kamal-haasan.gif",
                        "https://media.tenor.com/ONDeXUgmKRkAAAAS/hadeel928-%D8%AD%D8%B2%D9%86.gif",
                        "https://media.tenor.com/_lBztfGBlV8AAAAC/nikal.gif",
                        "https://media.tenor.com/-7M8TqyT0dsAAAAd/hrithik-roshan.gif"
                        ]


            emb.title = random.choice(lines).format(name, name2)
            emb.set_image(url=random.choice(gifs))

        await ctx.reply(embed=emb)

async def setup(bot):
    await bot.add_cog(Actions(bot))

