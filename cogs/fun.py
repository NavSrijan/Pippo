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
from views import BreedGuessView, ShipView
import csv

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

    async def avatar_concatenation(ctx,
                                   user1: discord.User,
                                   user2: discord.User,
                                   heart=True) -> None:
        # Get the avatar images of both users
        avatar1 = user1.avatar.url
        avatar2 = user2.avatar.url

        # Open the avatar images using Pillow
        image1 = Image.open(requests.get(avatar1,
                                         stream=True).raw).convert('RGBA')
        image2 = Image.open(requests.get(avatar2,
                                         stream=True).raw).convert('RGBA')
        if heart:
            heart_path = "imgs/heart.webp"
        else:
            heart_path = "imgs/bheart.png"
        heart = Image.open(heart_path).convert('RGBA')

        # Resize images to a common size
        size = (min(image1.size[0],
                    image2.size[0]), min(image1.size[1], image2.size[1]))
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

        result = combined
        result = result.convert('RGB')

        # Convert the resulting image to bytes and send it to the destination object
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
        if user1 is not None:
            m1 = re.match(user_regex, user1)
            if m1 is not None:
                user1 = ctx.guild.get_member(int(user1[2:-1]))
        if user2 is not None:
            m1 = re.match(user_regex, user2)
            if m1 is not None:
                user2 = ctx.guid.get_member(int(user2[2:-1]))

        if user1 is None:
            user1 = ctx.author
        elif user1 is not None and user2 is None:
            user2 = user1
            user1 = ctx.author
        if user2 is None:
            guild = ctx.guild
            user2 = random.choice(guild.members)

        def hash_comp(a="Ram", b="Shyam"):
            h1 = int(hashlib.md5(a.encode()).hexdigest(), 16)
            h2 = int(hashlib.md5(b.encode()).hexdigest(), 16)

            total = h1 + h2
            percentage = total % 101

            return percentage

        if not isinstance(user1, str):
            if user1.nick is None:
                u1 = user1.name
            else:
                u1 = user1.nick
        else:
            u1 = user1
        if not isinstance(user2, str):
            if user2.nick is None:
                u2 = user2.name
            else:
                u2 = user2.nick
        else:
            u2 = user2
        score = hash_comp(u1, u2)
        
        if score >= 50:
            heart = True
        else:
            heart = False
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
        combined_name = ":butterfly: " + u1[:len(u1) // 2] + u2[len(u2) // 2:]
        names = f":maple_leaf:`{u1}`\n:maple_leaf:`{u2}`" + "\n"
        desc = str(
            int(score)) + "% " + int(round(score, -1) / 10) * filled[int(
                round(score, -1) / 10)] + int(round(
                    (100 - score),
                    -1) / 10) * empty + f" {words[int(round(score, -1)/10)]}"
        if not isinstance(user1, str) and not isinstance(user2, str):
            file = await self.avatar_concatenation(user1, user2, heart=heart)
            emb = discord.Embed(title=combined_name, description=desc)
            emb.set_image(url='attachment://avatar.jpg')
            view = ShipView(self.bot, ctx)
            msg = await ctx.send(names, embed=emb, file=file, view=view)
            view.out = msg

        else:
            emb = discord.Embed(title=combined_name, description=desc)
            await ctx.send(names, embed=emb)

    @commands.hybrid_command(name="laser")
    async def laser(self, ctx, user: discord.Member = None):
        mo = "<:modiji:1011452564195246120>"
        las = "<:l1:1011452560147746939>"
        mol = "<:m1:1011452558444871731>"
        explode = "<a:explode:1011458958046793740>"

        if user is None:
            user = ctx.author

        text = f"{user.mention}" + ' ' * (30) + mo
        msg = await ctx.reply(text)

        for i in range(0, 6):
            await asyncio.sleep(1.5)
            text = f"{user.mention}" + ' ' * ((6 - i - 1) * 6) + las * i + mol
            await msg.edit(content=text)
        text = f"{explode}" + ' ' * ((6 - i - 1) * 6) + las * i + mol
        await msg.edit(content=text)
        await asyncio.sleep(1.5)
        text = f"{explode}" + ' ' * (30) + mo +f"\n{ctx.author.mention} annihilated {user.mention}"
        await msg.edit(content=text)

    @commands.cooldown(1, 3, commands.BucketType.user)
    @commands.hybrid_command(name="cartoon")
    async def cartoon(self, ctx):
        """Gets a random cartoon image"""

        car = random.choice(self.bot.cartoon_characters)

        emb = discord.Embed(title=f"**{car['character_name']}** from **{car['show_name']}**")
        emb.set_image(url=car['image_link'])
        await ctx.reply(embed=emb)

    @commands.hybrid_command(name="cartoonme")
    async def cartoonme(self, ctx, user: discord.Member=None):
        """Which cartoon character are you?"""

        def generate_random_number(user_id, n):
            random.seed(user_id)  # Set the seed based on the user ID
            return random.randint(0, n)  # Generate a random number between 0 and n

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

        emb = discord.Embed(title=f"{user.name} is **{character['character_name']}** from {character['show_name']}")
        emb.set_image(url=character['image_link'])
        await ctx.reply(embed=emb)

    @commands.hybrid_command(name="8ball")
    async def _8ball(self, ctx, question):
        """Want to know your fate?"""
        await ctx.reply(random.choice(["Yes", "No", "Maybe"]))

    @commands.hybrid_command(name="onewordstory") 
    async def onewordstory(self, ctx):
        """Make stories with your friends by writing one word each."""

        # Send an embed with the instructions
        def instruction_embed():
            emb = discord.Embed(title="One Word Story", description="""This'll contain the description.""")
            return emb

        def check(message):
            return message.channel == ctx.channel and len(message.content.split(" "))==1 

        await ctx.reply(embed=instruction_embed())

        timeout = 60
        para = ""

        # Loop to check for one word with a 60 sec timeout.
        while True:
            try:
                msg = await self.bot.wait_for('message',
                                              check=check,
                                              timeout=timeout)
                prefix = await self.bot.get_prefixx(self.bot, ctx.message)
                if msg.content==f"{prefix}end":
                    break
                para+=f" {msg.content}"
                await msg.add_reaction("\U0001F39F")
            except asyncio.exceptions.TimeoutError:
                await ctx.send("Looks like you didn't wanna play...")
                break

        # The final paragraph
        await ctx.channel.send(embed=discord.Embed(title="The final paragraph", description=para))

    @commands.hybrid_command(name="flames")
    async def flames(self, ctx, user1=None, user2=None):
        """Remember the Flames from your school days?"""
        user_regex = r'<@!?(\d+)>'
        if user1 is not None:
            m1 = re.match(user_regex, user1)
            if m1 is not None:
                user1 = ctx.guild.get_member(int(user1[2:-1]))
        if user2 is not None:
            m1 = re.match(user_regex, user2)
            if m1 is not None:
                user2 = ctx.guid.get_member(int(user2[2:-1]))

        if user1 is None:
            user1 = ctx.author
        elif user1 is not None and user2 is None:
            user2 = user1
            user1 = ctx.author
        if user2 is None:
            guild = ctx.guild
            user2 = random.choice(guild.members)

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
            while len(flames) > 1:
                index = (count - 1) % len(flames)
                flames = flames[:index] + flames[index+1:]

            #options = {"F":"Friends", "L":"Lovers", "A":"Affectionate", "M":"Marriage", "E":"Enemies", "S":"Siblings"}
            options = {"F": "👫 Friends", "L": "❤️ Lovers", "A": "😊 Affectionate", "M": "💍 Marriage", "E": "😡 Enemies", "S": "👦👧 Siblings"}

            return options[flames], flames

        def get_img_url(letter):
            options = {"F":"https://media.discordapp.net/attachments/1092244601525510154/1142797002778869910/F.png?width=400&height=300",
                       "L":"https://media.discordapp.net/attachments/1092244601525510154/1142797004469174292/L.png?width=400&height=300",
                       "A":"https://media.discordapp.net/attachments/1092244601525510154/1142797003345121350/A.png?width=400&height=300",
                       "M":"https://media.discordapp.net/attachments/1092244601525510154/1142797003630313502/M.png?width=400&height=300",
                       "E":"https://media.discordapp.net/attachments/1092244601525510154/1142797003928129626/E.png?width=400&height=300",
                       "S":"https://media.discordapp.net/attachments/1092244601525510154/1142797004154609774/S.png?width=400&height=300"}
            return options[letter]

        def return_embed(name1, name2):
            relation, letter = calculate_flames(name1, name2)
            emb = discord.Embed(title="Flames", description=f"**{relation}**")
            emb.set_image(url=get_img_url(letter))
            return emb

        name1 = user1.name
        name2 = user2.name
        relation, letter = calculate_flames(name1, name2)
        names = f":maple_leaf:`{name1}`\n:maple_leaf:`{name2}`" + "\n"
        await ctx.reply(names,embed=return_embed(user1.name, user2.name))

    @commands.hybrid_command(name="what", aliases=["define", "ub", "urban_dictionary", "urban"])
    async def meaning(self, ctx, query):
        """
        Querys Urban dictionary to get the meaning of the word.
        syntax: $what {word}
        """
        def getMeaning(word):
            response = requests.get(
                f"http://api.urbandictionary.com/v0/define?term={word}")
            res = response.json()['list']
            return res
        word = query
        res = getMeaning(word)
        toSend = "Data from Urban Dictionary"
        j = 1
        for i in res:
            defn = i['definition']
            if len(defn) <= 600:
                toSend += f"```{j}. {defn}```\n"
                j += 1
            if j == 4:
                break
        await ctx.reply(toSend)


async def setup(bot):
    await bot.add_cog(Fun(bot))

