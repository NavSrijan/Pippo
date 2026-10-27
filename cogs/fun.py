from typing import Literal
import datetime
import time
import random
import re
import json
import asyncio
import csv
import hashlib
from io import BytesIO
from PIL import Image, ImageDraw, ImageOps

from discord.ext import commands
import discord
from views import ShipView

def load_csv(filename):
    data = []
    with open(filename, 'r') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            data.append(dict(row))
    return data

class Fun(commands.Cog):
    """Fun commands"""

    def __init__(self, bot):
        self.bot = bot
        self.bot.cartoon_characters = load_csv("data/cartoons/character_dataset.csv")

    async def avatar_concatenation(self,
                                   user1,
                                   user2,
                                   heart=True) -> discord.File:
        # Get the avatar images of both users
        bytes1, bytes2 = await asyncio.gather(
            user1.display_avatar.read(), user2.display_avatar.read()
        )
        image1 = Image.open(BytesIO(bytes1)).convert('RGBA')
        image2 = Image.open(BytesIO(bytes2)).convert('RGBA')

        if heart:
            heart_path = "imgs/heart.webp"
        else:
            heart_path = "imgs/bheart.png"
        heart = Image.open(heart_path).convert('RGBA')

        # Resize images to a common size
        size = (min(image1.size[0], image2.size[0]), min(image1.size[1], image2.size[1]))
        image1 = image1.resize(size)
        image2 = image2.resize(size)

        # Create circular masks
        mask = Image.new('L', size, 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0) + size, fill=255)

        # Apply masks to images
        image1.putalpha(mask)
        image2.putalpha(mask)

        # Calculate center position for heart
        heart_size = (size[0] // 2, size[1] // 2)
        heart_position = (size[0] - heart_size[0] // 2,
                          size[1] // 2 - heart_size[1] // 2)

        # Resize heart image and paste it onto the combined image
        heart = heart.resize(heart_size)
        combined = Image.new('RGBA', (size[0] * 2, size[1]),
                             (255, 255, 255, 255))
        combined.paste(image1, (0, 0))
        combined.paste(image2, (size[0], 0))
        combined.paste(heart, heart_position, mask=heart)

        result = combined.convert('RGB')

        with BytesIO() as output:
            result.save(output, format='JPEG', quality=20, optimize=True)
            output.seek(0)
            return discord.File(output, filename='avatar.jpg')

    @commands.cooldown(1, 3, commands.BucketType.user)
    @commands.hybrid_command(name="ship")
    async def ship(self,
                   ctx,
                   user1 = None,
                   user2 = None):
        """Ship command to ship people"""
        user_regex = r'<@!?(\d+)>'
        if user1 is not None and isinstance(user1, str):
            m1 = re.match(user_regex, user1)
            if m1 is not None and ctx.guild:
                fetched = ctx.guild.get_member(int(m1.group(1)))
                if fetched:
                    user1 = fetched
        if user2 is not None and isinstance(user2, str):
            m2 = re.match(user_regex, user2)
            if m2 is not None and ctx.guild:
                fetched = ctx.guild.get_member(int(m2.group(1)))
                if fetched:
                    user2 = fetched

        if user1 is None:
            user1 = ctx.author
        elif user1 is not None and user2 is None:
            user2 = user1
            user1 = ctx.author
        if user2 is None:
            if ctx.guild and len(ctx.guild.members) > 1:
                members_pool = [m for m in ctx.guild.members if m.id != user1.id]
                user2 = random.choice(members_pool) if members_pool else ctx.author
            else:
                user2 = "Pippo"

        def hash_comp(a="Ram", b="Shyam"):
            h1 = int(hashlib.md5(a.encode()).hexdigest(), 16)
            h2 = int(hashlib.md5(b.encode()).hexdigest(), 16)

            total = h1 + h2
            percentage = total % 101

            return percentage

        u1 = getattr(user1, 'display_name', str(user1))
        u2 = getattr(user2, 'display_name', str(user2))

        score = hash_comp(u1, u2)
        heart = score >= 50

        words = [
            'Apathetic 😐', 'Apathetic 😐', '🤷 Disinterested', '🙄 Polite',
            '😊 Caring', '❤️ Affectionate', '💕 Devoted', '🙌 Adoring',
            '😍 Passionate', '🔥 Enamored', '💞 Soulmates'
        ]

        filled = [
            '<:h1:1103886857365893180>', '<:h1:1103886857365893180>',
            '<:h2:1103888875807584256>', '<:h3:1103888922653753405>',
            '<:h4:1103888918828564570>', '<:h5:1103888914743304262>',
            '<:h6:1103888910507061249>', '<:h7:1103888908250529933>',
            '<:h8:1103888904349814854>', '<:h9:1103888900352655420>',
            '<:h10:1103888897567629363>'
        ]

        empty = "⬜️"
        combined_name = ":butterfly: " + u1[:max(1, len(u1) // 2)] + u2[len(u2) // 2:]
        names = f":maple_leaf:`{u1}`\n:maple_leaf:`{u2}`\n"
        idx = min(10, max(0, int(round(score, -1) / 10)))
        desc = f"{int(score)}% " + idx * filled[idx] + (10 - idx) * empty + f" {words[idx]}"

        if not isinstance(user1, str) and not isinstance(user2, str):
            try:
                file = await self.avatar_concatenation(user1, user2, heart=heart)
                emb = discord.Embed(title=combined_name, description=desc, color=discord.Color.magenta())
                emb.set_image(url='attachment://avatar.jpg')
                view = ShipView(self.bot, ctx)
                msg = await ctx.send(names, embed=emb, file=file, view=view)
                view.out = msg
            except Exception:
                emb = discord.Embed(title=combined_name, description=desc, color=discord.Color.magenta())
                await ctx.send(names, embed=emb)
        else:
            emb = discord.Embed(title=combined_name, description=desc, color=discord.Color.magenta())
            await ctx.send(names, embed=emb)

    @commands.hybrid_command(name="laser")
    async def laser(self, ctx, user: discord.Member = None):
        """Laser strike animation against a mentioned user"""
        mo = str(self.bot.get_emoji(1011452564195246120) or "🛰️")
        las = str(self.bot.get_emoji(1011452560147746939) or "🔴")
        mol = str(self.bot.get_emoji(1011452558444871731) or "⚡")
        explode = str(self.bot.get_emoji(1011458958046793740) or "💥")

        if user is None:
            user = ctx.author

        text = f"{user.mention}" + ' ' * (30) + mo
        msg = await ctx.reply(text)

        for i in range(0, 6):
            await asyncio.sleep(1.5)
            text = f"{user.mention}" + ' ' * ((6 - i - 1) * 6) + las * i + mol
            await msg.edit(content=text)
        text = f"{explode}" + ' ' * ((6 - 5 - 1) * 6) + las * 5 + mol
        await msg.edit(content=text)
        await asyncio.sleep(1.5)
        text = f"{explode}" + ' ' * (30) + mo + f"\n{ctx.author.mention} annihilated {user.mention}"
        await msg.edit(content=text)

    @commands.cooldown(1, 3, commands.BucketType.user)
    @commands.hybrid_command(name="cartoon")
    async def cartoon(self, ctx):
        """Gets a random cartoon image"""
        if not hasattr(self.bot, 'cartoon_characters') or not self.bot.cartoon_characters:
            self.bot.cartoon_characters = load_csv("data/cartoons/character_dataset.csv")

        car = random.choice(self.bot.cartoon_characters)
        emb = discord.Embed(title=f"**{car['character_name']}** from **{car['show_name']}**", color=discord.Color.dark_purple())
        emb.set_image(url=car['image_link'])
        await ctx.reply(embed=emb)

    @commands.hybrid_command(name="cartoonme")
    async def cartoonme(self, ctx, user: discord.Member=None):
        """Which cartoon character are you?"""
        if not hasattr(self.bot, 'cartoon_characters') or not self.bot.cartoon_characters:
            self.bot.cartoon_characters = load_csv("data/cartoons/character_dataset.csv")

        def generate_random_number(user_id, n):
            return random.Random(user_id).randint(0, n)

        def fetch_value(characters, character_name):
            for character in characters:
                if character['character_name'] == character_name:
                    return character
            return None

        if user is None:
            user = ctx.author

        idd = user.id
        character_name = await self.bot.db.characters.get_character(user.id)
        if character_name is None:
            number = generate_random_number(idd, len(self.bot.cartoon_characters)-1)
            character = self.bot.cartoon_characters[number]
        else:
            character = fetch_value(self.bot.cartoon_characters, character_name['cartoon_character'])
            if not character:
                number = generate_random_number(idd, len(self.bot.cartoon_characters)-1)
                character = self.bot.cartoon_characters[number]

        emb = discord.Embed(title=f"{user.display_name} is **{character['character_name']}** from {character['show_name']}", color=discord.Color.gold())
        emb.set_image(url=character['image_link'])
        await ctx.reply(embed=emb)

    @commands.hybrid_command(name="8ball")
    async def _8ball(self, ctx, question: str):
        """Want to know your fate?"""
        responses = [
            "It is certain.", "It is decidedly so.", "Without a doubt.",
            "Yes definitely.", "You may rely on it.", "As I see it, yes.",
            "Most likely.", "Outlook good.", "Yes.", "Signs point to yes.",
            "Reply hazy, try again.", "Ask again later.", "Better not tell you now.",
            "Cannot predict now.", "Concentrate and ask again.",
            "Don't count on it.", "My reply is no.", "My sources say no.",
            "Outlook not so good.", "Very doubtful."
        ]
        await ctx.reply(f"🎱 **{random.choice(responses)}**")

    @commands.max_concurrency(1, per=commands.BucketType.channel, wait=False)
    @commands.hybrid_command(name="onewordstory")
    async def onewordstory(self, ctx, solo: bool = False):
        """Make a collaborative one-word story, or set solo to write by yourself."""
        prefix = await self.bot.get_prefixx(self.bot, ctx.message)

        def instruction_embed():
            mode = "Only your words will be added." if solo else "Everyone in the channel can contribute."
            emb = discord.Embed(
                title="One Word Story",
                description=f"{mode}\nSend one word at a time. Type `{prefix}end` to finish.",
                color=discord.Color.blue(),
            )
            return emb

        def check(message):
            return (
                message.channel == ctx.channel
                and not message.author.bot
                and (not solo or message.author.id == ctx.author.id)
                and len(message.content.strip().split()) == 1
            )

        await ctx.reply(embed=instruction_embed())

        timeout = 60
        para = ""

        while True:
            try:
                msg = await self.bot.wait_for('message', check=check, timeout=timeout)
                if msg.content.strip().lower() == f"{prefix}end":
                    break
                para += f" {msg.content.strip()}"
                try:
                    await msg.add_reaction("\U0001F39F")
                except Exception:
                    pass
            except asyncio.exceptions.TimeoutError:
                await ctx.send("Story timeout! Looks like the session has ended.")
                break

        final_text = para.strip() if para.strip() else "No story was written!"
        await ctx.channel.send(embed=discord.Embed(title="The final paragraph", description=final_text, color=discord.Color.green()))

    @commands.hybrid_command(name="flames")
    async def flames(self, ctx, user1=None, user2=None):
        """Remember the Flames from your school days?"""
        user_regex = r'<@!?(\d+)>'
        if user1 is not None and isinstance(user1, str):
            m1 = re.match(user_regex, user1)
            if m1 is not None and ctx.guild:
                fetched = ctx.guild.get_member(int(m1.group(1)))
                if fetched:
                    user1 = fetched
        if user2 is not None and isinstance(user2, str):
            m2 = re.match(user_regex, user2)
            if m2 is not None and ctx.guild:
                fetched = ctx.guild.get_member(int(m2.group(1)))
                if fetched:
                    user2 = fetched

        if user1 is None:
            user1 = ctx.author
        elif user1 is not None and user2 is None:
            user2 = user1
            user1 = ctx.author
        if user2 is None:
            if ctx.guild and len(ctx.guild.members) > 1:
                members_pool = [m for m in ctx.guild.members if m.id != user1.id]
                user2 = random.choice(members_pool) if members_pool else ctx.author
            else:
                user2 = "Pippo"

        def calculate_flames(name1, name2):
            flames = "FLAMES"
            result = []

            name1 = name1.upper().replace(" ", "")
            name2 = name2.upper().replace(" ", "")

            for char in name1:
                if char in name2:
                    name2 = name2.replace(char, "", 1)
                    continue
                result.append(char)

            count = len(result) + len(name2)
            if count <= 0:
                count = 1

            while len(flames) > 1:
                index = (count - 1) % len(flames)
                flames = flames[:index] + flames[index+1:]

            options = {"F": "👫 Friends", "L": "❤️ Lovers", "A": "😊 Affectionate", "M": "💍 Marriage", "E": "😡 Enemies", "S": "👦👧 Siblings"}
            return options[flames], flames

        def get_img_url(letter):
            options = {
                "F": "https://media.discordapp.net/attachments/1092244601525510154/1142797002778869910/F.png?width=400&height=300",
                "L": "https://media.discordapp.net/attachments/1092244601525510154/1142797004469174292/L.png?width=400&height=300",
                "A": "https://media.discordapp.net/attachments/1092244601525510154/1142797003345121350/A.png?width=400&height=300",
                "M": "https://media.discordapp.net/attachments/1092244601525510154/1142797003630313502/M.png?width=400&height=300",
                "E": "https://media.discordapp.net/attachments/1092244601525510154/1142797003928129626/E.png?width=400&height=300",
                "S": "https://media.discordapp.net/attachments/1092244601525510154/1142797004154609774/S.png?width=400&height=300"
            }
            return options.get(letter, "")

        name1 = getattr(user1, 'display_name', str(user1))
        name2 = getattr(user2, 'display_name', str(user2))
        relation, letter = calculate_flames(name1, name2)
        names = f":maple_leaf:`{name1}`\n:maple_leaf:`{name2}`\n"
        emb = discord.Embed(title="Flames", description=f"**{relation}**", color=discord.Color.red())
        img = get_img_url(letter)
        if img:
            emb.set_image(url=img)
        await ctx.reply(names, embed=emb)

    @commands.hybrid_command(name="what", aliases=["define", "ub", "urban_dictionary", "urban"])
    async def meaning(self, ctx, query: str):
        """
        Query Urban dictionary to get the meaning of the word.
        syntax: .what {word}
        """
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=8)) as session:
                async with session.get(f"https://api.urbandictionary.com/v0/define?term={query}") as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        res = data.get('list', [])
                    else:
                        res = []
        except Exception as e:
            await ctx.reply("Could not reach Urban Dictionary right now.")
            return

        if not res:
            await ctx.reply(f"No definitions found for **{query}** on Urban Dictionary.")
            return

        toSend = f"**Urban Dictionary: {query}**\n"
        j = 1
        for i in res:
            defn = i.get('definition', '').replace("[", "").replace("]", "")
            if len(defn) <= 600:
                toSend += f"```{j}. {defn}```\n"
                j += 1
            if j == 4:
                break
        await ctx.reply(toSend)


async def setup(bot):
    await bot.add_cog(Fun(bot))
