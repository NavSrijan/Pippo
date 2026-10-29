from runtime import http_session
from cogs.play import offer_game_mode
from runtime import react, run_blocking
from typing import Literal
import datetime
import time
import random
import hashlib
import re
import json
import asyncio
import html
import csv
import logging
from io import BytesIO
from urllib.parse import urlsplit
from PIL import Image, ImageDraw, ImageOps
import aiohttp

from discord.ext import commands
import discord
from views import (
    ShipView, FlamesView, OneWordStoryLobbyView, CartoonRouletteView, EightBallView,
    DefinitionBrowserView, onewordstory_art_file, ship_art_file,
    cartoon_art_file, eightball_art_file, what_art_file,
)

log = logging.getLogger(__name__)

def load_csv(filename):
    data = []
    with open(filename, 'r') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            data.append(dict(row))
    return data


def usable_cartoon_records(characters):
    """Return one usable image record for each character/show pair."""
    records = []
    seen = set()
    for character in characters:
        name = (character.get("character_name") or "").strip()
        show = (character.get("show_name") or "").strip()
        image_url = (character.get("image_link") or "").strip()
        parsed = urlsplit(image_url)
        key = (name.casefold(), show.casefold())
        if name and show and parsed.scheme in {"http", "https"} and parsed.netloc and key not in seen:
            records.append({**character, "character_name": name, "show_name": show, "image_link": image_url})
            seen.add(key)
    return records

class Fun(commands.Cog):
    """Fun commands"""

    def __init__(self, bot):
        self.bot = bot
        self.bot.cartoon_characters = load_csv("data/cartoons/character_dataset.csv")

    async def avatar_concatenation(self,
                                   user1,
                                   user2,
                                   heart=True) -> discord.File:
        bytes1, bytes2 = await asyncio.gather(
            user1.display_avatar.read(), user2.display_avatar.read()
        )
        return await run_blocking(self._render_avatars, bytes1, bytes2, heart)

    @staticmethod
    def _render_avatars(bytes1, bytes2, heart):
        image1 = Image.open(BytesIO(bytes1)).convert('RGBA')
        image2 = Image.open(BytesIO(bytes2)).convert('RGBA')

        if heart:
            heart_path = "imgs/heart.webp"
        else:
            heart_path = "imgs/bheart.png"
        heart = Image.open(heart_path).convert('RGBA')

        size = 512
        image1 = ImageOps.fit(image1, (size, size), method=Image.Resampling.LANCZOS)
        image2 = ImageOps.fit(image2, (size, size), method=Image.Resampling.LANCZOS)
        mask = Image.new('L', (size, size), 0)
        ImageDraw.Draw(mask).ellipse((4, 4, size - 4, size - 4), fill=255)
        image1.putalpha(mask)
        image2.putalpha(mask)

        heart_size = (176, 176)
        heart = ImageOps.contain(heart, heart_size, method=Image.Resampling.LANCZOS)
        heart_position = (size - heart.width // 2, (size - heart.height) // 2)
        combined = Image.new('RGBA', (size * 2, size), (30, 25, 58, 255))
        combined.paste(image1, (0, 0), image1)
        combined.paste(image2, (size, 0), image2)
        combined.alpha_composite(heart, heart_position)

        result = combined.convert('RGB')

        output = BytesIO()
        result.save(output, format='JPEG', quality=88, optimize=True, progressive=True)
        output.seek(0)
        return discord.File(output, filename='avatar.jpg')

    @staticmethod
    def _ship_label(target):
        value = getattr(target, 'display_name', str(target)).strip() or "Mystery"
        return discord.utils.escape_markdown(value[:72]).replace("@", "@\u200b")

    @staticmethod
    def _ship_identity(target):
        user_id = getattr(target, "id", None)
        if user_id is not None:
            return f"id:{user_id}"
        return f"name:{str(target).strip().casefold()}"

    @classmethod
    def _ship_score(cls, first, second, *, reroll=0):
        """Give each pair a repeatable score, with fresh readings on reroll."""
        pair = sorted((cls._ship_identity(first), cls._ship_identity(second)))
        seed = "\0".join((*pair, f"reroll:{reroll}")).encode("utf-8")
        digest = hashlib.blake2s(seed, digest_size=8, person=b"pipposhp").digest()
        return int.from_bytes(digest, "big") % 101

    async def make_ship_result(self, first, second, *, reroll=0):
        score = self._ship_score(first, second, reroll=reroll)
        tiers = (
            (20, "Chaotic besties", "A legendary duo for snacks, schemes, and questionable plans."),
            (40, "Friendly sparks", "This pairing has a cozy sitcom energy."),
            (60, "Cute chemistry", "A little spark is there. Pippo recommends sharing fries."),
            (80, "Rom-com material", "Someone cue the accidental umbrella scene."),
            (95, "Power couple", "Matching jackets would be a reasonable next step."),
            (101, "Pippo-approved soulmates", "The universe made room for one more adorable duo."),
        )
        mood, verdict = next((mood, text) for ceiling, mood, text in tiers if score < ceiling)
        filled = round(score / 10)
        bar = "💗" * filled + "🤍" * (10 - filled)
        first_label, second_label = self._ship_label(first), self._ship_label(second)
        left = first_label[:max(1, (len(first_label) + 1) // 2)]
        right = second_label[len(second_label) // 2:]
        ship_name = (left + right).strip() or "A cute duo"
        embed = discord.Embed(
            title=f"💘 {ship_name[:120]}",
            description=(
                f"{bar}\n**{score}% · {mood}**\n\n{verdict}\n\n"
                f"{first_label} + {second_label}"
            ),
            color=discord.Color.magenta(),
        )
        embed.set_footer(text="For fun only · no compatibility science involved" + (f" · reading {reroll + 1}" if reroll else ""))

        files = []
        artwork = await run_blocking(ship_art_file, embed, f"ship_scene_{reroll + 1}")
        if artwork:
            files.append(artwork)
        if hasattr(first, "display_avatar") and hasattr(second, "display_avatar"):
            try:
                avatar_art = await self.avatar_concatenation(first, second, heart=score >= 50)
                embed.set_image(url="attachment://avatar.jpg")
                files.append(avatar_art)
            except Exception:
                log.exception("Could not compose ship avatars")
        return embed, files

    @commands.cooldown(1, 3, commands.BucketType.user)
    @commands.hybrid_command(name="ship")
    async def ship(self,
                   ctx,
                   user1 = None,
                   user2 = None):
        """Get a playful compatibility reading for two names or members."""
        supplied_first = user1 is not None
        user_regex = re.compile(r"<@!?(\d+)>")

        async def resolve_target(value):
            if not isinstance(value, str):
                return value
            value = value.strip()
            match = user_regex.fullmatch(value)
            if match and ctx.guild:
                member = ctx.guild.get_member(int(match.group(1)))
                if member:
                    return member
                try:
                    return await self.bot.fetch_user(int(match.group(1)))
                except (discord.NotFound, discord.HTTPException):
                    return value[:72]
            return value[:72] or "Mystery"

        user1 = await resolve_target(user1)
        user2 = await resolve_target(user2)
        if user1 is None:
            user1 = ctx.author
        if user2 is None and supplied_first:
            user2, user1 = user1, ctx.author
        elif user2 is None:
            members = [member for member in getattr(ctx.guild, "members", []) if not member.bot and member.id != getattr(user1, "id", None)]
            user2 = random.choice(members) if members else "Pippo"

        embed, files = await self.make_ship_result(user1, user2)
        view = ShipView(self, ctx, user1, user2)
        options = {"embed": embed, "view": view, "allowed_mentions": discord.AllowedMentions.none()}
        if files:
            options["files"] = files
        view.out = await ctx.send(**options)

    @commands.hybrid_command(name="laser")
    @commands.max_concurrency(1, per=commands.BucketType.member, wait=False)
    async def laser(self, ctx, user: discord.Member = None):
        """Watch a slow emoji laser strike reveal through edits to one message."""
        mo = str(self.bot.get_emoji(1011452564195246120) or "🛰️")
        las = str(self.bot.get_emoji(1011452560147746939) or "🔴")
        mol = str(self.bot.get_emoji(1011452558444871731) or "⚡")
        explode = str(self.bot.get_emoji(1011458958046793740) or "💥")
        user = user or ctx.author
        msg = await ctx.reply(user.mention + " " * 30 + mo, allowed_mentions=discord.AllowedMentions.none())
        try:
            for step in range(6):
                await asyncio.sleep(1.5)
                await msg.edit(
                    content=user.mention + " " * ((5 - step) * 6) + las * step + mol,
                    allowed_mentions=discord.AllowedMentions.none(),
                )
            await msg.edit(content=explode + las * 5 + mol, allowed_mentions=discord.AllowedMentions.none())
            await asyncio.sleep(1.5)
            await msg.edit(
                content=explode + " " * 30 + mo + f"\n{ctx.author.mention} annihilated {user.mention}",
                allowed_mentions=discord.AllowedMentions.none(),
            )
        except discord.NotFound:
            # The animation message was deleted; don't recreate it or keep editing.
            return

    @commands.cooldown(1, 3, commands.BucketType.user)
    @commands.hybrid_command(name="cartoon")
    async def cartoon(self, ctx):
        """Draw a random cartoon character and spin the roulette for more."""
        if not hasattr(self.bot, 'cartoon_characters') or not self.bot.cartoon_characters:
            self.bot.cartoon_characters = load_csv("data/cartoons/character_dataset.csv")

        characters = usable_cartoon_records(self.bot.cartoon_characters)

        if not characters:
            await ctx.reply("I couldn't find any cartoon characters with usable images right now. Try again later.")
            return

        def render_card(character, draw_number):
            embed = discord.Embed(
                title=f"Cartoon Roulette · Draw {draw_number}/6",
                description=f"**{character['character_name']}** from **{character['show_name']}**",
                color=discord.Color.dark_purple(),
            )
            embed.set_image(url=character["image_link"])
            embed.set_footer(text="Spin again for another character · Only you can use this roulette")
            artwork = cartoon_art_file(embed, f"cartoon_draw_{draw_number}")
            return embed, artwork

        first = random.choice(characters)
        embed, artwork = await run_blocking(render_card, first, 1)
        view = CartoonRouletteView(ctx.author.id, characters, render_card, first)
        options = {"embed": embed, "view": view, "allowed_mentions": discord.AllowedMentions.none()}
        if artwork:
            options["file"] = artwork
        view.message = await ctx.reply(**options)

    @commands.hybrid_command(name="cartoonme")
    async def cartoonme(self, ctx, user: discord.Member=None):
        """See your saved cartoon alter ego or check a friend."""
        if not hasattr(self.bot, 'cartoon_characters') or not self.bot.cartoon_characters:
            self.bot.cartoon_characters = load_csv("data/cartoons/character_dataset.csv")

        characters = usable_cartoon_records(self.bot.cartoon_characters)
        if not characters:
            await ctx.reply("I couldn't find any cartoon characters with usable images right now. Try again later.")
            return

        def default_character(user_id):
            return characters[random.Random(user_id).randrange(len(characters))]

        if user is None:
            user = ctx.author

        character_name = await self.bot.db.characters.get_character(user.id)
        if character_name is None:
            character = default_character(user.id)
        else:
            saved_name = (character_name["cartoon_character"] or "").strip().casefold()
            saved_show = (character_name["show_name"] or "").strip().casefold()
            matches = [
                record for record in characters
                if record["character_name"].casefold() == saved_name
                and (not saved_show or record["show_name"].casefold() == saved_show)
            ]
            character = matches[0] if matches else default_character(user.id)

        name = discord.utils.escape_markdown(user.display_name)
        character_name = discord.utils.escape_markdown(character["character_name"])
        show_name = discord.utils.escape_markdown(character["show_name"])
        emb = discord.Embed(
            title="Cartoon alter ego",
            description=f"**{name}** is **{character_name}** from **{show_name}**.",
            color=discord.Color.gold(),
        )
        emb.set_image(url=character["image_link"])
        emb.set_footer(text="Choose another identity from `/shop character` for 1,000 coins.")
        artwork = await run_blocking(cartoon_art_file, emb, "cartoonme")
        options = {"embed": emb, "allowed_mentions": discord.AllowedMentions.none()}
        if artwork:
            options["file"] = artwork
        await ctx.reply(**options)

    @commands.cooldown(1, 3, commands.BucketType.user)
    @commands.hybrid_command(name="8ball")
    async def _8ball(self, ctx, *, question: str):
        """Ask Pippo's 8-ball a question, then shake it up to three more times."""
        responses = [
            "It is certain.", "It is decidedly so.", "Without a doubt.",
            "Yes definitely.", "You may rely on it.", "As I see it, yes.",
            "Most likely.", "Outlook good.", "Yes.", "Signs point to yes.",
            "Reply hazy, try again.", "Ask again later.", "Better not tell you now.",
            "Cannot predict now.", "Concentrate and ask again.",
            "Don't count on it.", "My reply is no.", "My sources say no.",
            "Outlook not so good.", "Very doubtful."
        ]
        question = question.strip()
        if not question:
            await ctx.reply("Ask Pippo's 8-ball a question first.")
            return

        def render_reading(answer, reading):
            safe_question = discord.utils.escape_markdown(question[:500])
            embed = discord.Embed(
                title="Pippo's Magic 8-Ball",
                description=f"**You asked:** {safe_question}\n\n🔮 **{answer}**",
                color=discord.Color.from_rgb(83, 57, 151),
            )
            embed.set_footer(text=f"Reading {reading}/4 · Just for fun")
            artwork = eightball_art_file(embed, f"8ball_reading_{reading}")
            return embed, artwork

        first_answer = random.choice(responses)
        embed, artwork = await run_blocking(render_reading, first_answer, 1)
        view = EightBallView(ctx.author.id, question, responses, render_reading, first_answer)
        options = {"embed": embed, "view": view, "allowed_mentions": discord.AllowedMentions.none()}
        if artwork:
            options["file"] = artwork
        view.message = await ctx.reply(**options)

    @commands.hybrid_command(name="onewordstory")
    @commands.max_concurrency(1, per=commands.BucketType.channel, wait=False)
    async def onewordstory(self, ctx):
        """Create a story in rotating one-word turns, with solo and twist modes."""
        if await offer_game_mode(ctx, "onewordstory"):
            return
        solo = ctx._pippo_play_mode
        prefix = ctx.prefix or "."
        if ctx.message is not None:
            try:
                prefix = await self.bot.get_prefixx(self.bot, ctx.message) or prefix
            except Exception:
                pass
        elif ctx.guild is not None and getattr(self.bot, "db", None):
            try:
                prefix = await self.bot.db.servers.fetch_prefix(ctx.guild.id) or prefix
            except Exception:
                pass
        end_command = f"{prefix}end".casefold()
        player_ids = [ctx.author.id]

        if not solo:
            lobby = OneWordStoryLobbyView(ctx.author.id, ctx.author.display_name, "One Word Story", max_players=6)
            lobby.message = await ctx.send(lobby.render(), view=lobby)
            await lobby.wait()
            if not lobby.started:
                return
            player_ids = list(lobby.joined_ids)

        target_words = 8 if solo else len(player_ids) * 4
        turn_seconds = 30 if solo else 20
        host_id = ctx.author.id
        words = []
        scores = {user_id: 0 for user_id in player_ids}
        passes = 0
        common_letters = "AEBCDFGHLMPRST"
        end_note = f"<@{host_id}> can type `{prefix}end` to wrap early."

        await ctx.send(
            f"📖 **One Word Story is live!** {target_words} turns · one word each · "
            f"{turn_seconds}s per turn. {end_note}",
            allowed_mentions=discord.AllowedMentions.none(),
        )

        for turn in range(target_words):
            user_id = player_ids[turn % len(player_ids)]
            round_number = turn // len(player_ids) + 1
            constraint = None
            letter = None
            if turn > 0 and len(words) and len(words) % 4 == 0:
                constraint = random.choice(("letter", "long", "y"))
                if constraint == "letter":
                    letter = random.choice(common_letters)
            prompt = {
                "letter": f" Twist card: start with **{letter}** for **+2 Story Points**.",
                "long": " Twist card: use **6+ letters** for **+2 Story Points**.",
                "y": " Twist card: end with **Y** for **+2 Story Points**.",
            }.get(constraint, "")
            await ctx.send(
                f"🗣️ <@{user_id}> — Round **{round_number}**, your word.{prompt}",
                allowed_mentions=discord.AllowedMentions(users=True, everyone=False, roles=False, replied_user=False),
            )
            if words and turn % len(player_ids) == 0:
                preview = discord.utils.escape_markdown(" ".join(words[-8:])).replace("@", "@\u200b")
                await ctx.send(f"📖 Story so far: `{preview}`", allowed_mentions=discord.AllowedMentions.none())

            def check(message):
                if message.channel != ctx.channel or message.author.bot:
                    return False
                content = message.content.strip()
                if message.author.id == host_id and content.casefold() == end_command:
                    return True
                if message.author.id != user_id or content.startswith(prefix):
                    return False
                return len(content.split()) == 1 and len(content) <= 32

            deadline = time.monotonic() + turn_seconds
            accepted_word = None
            ended_early = False
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    break
                try:
                    msg = await self.bot.wait_for("message", check=check, timeout=remaining)
                except asyncio.TimeoutError:
                    break
                if msg.author.id == host_id and msg.content.strip().casefold() == end_command:
                    ended_early = True
                    break

                word = msg.content.strip()
                lower_word = word.casefold()
                letters_in_word = "".join(character for character in lower_word if character.isalpha())
                meets_twist = (
                    constraint is None
                    or (constraint == "letter" and letters_in_word.startswith(letter.casefold()))
                    or (constraint == "long" and len(letters_in_word) >= 6)
                    or (constraint == "y" and letters_in_word.endswith("y"))
                )
                if not meets_twist:
                    hint = {
                        "letter": f"Your twist card needs a word starting with **{letter}**. Try again before the timer ends.",
                        "long": "Your twist card needs at least **6 letters**. Try again before the timer ends.",
                        "y": "Your twist card needs to end with **Y**. Try again before the timer ends.",
                    }[constraint]
                    await react(msg, "❔")
                    continue
                accepted_word = word
                try:
                    await react(msg, "✍️")
                except discord.HTTPException:
                    pass
                break

            if ended_early:
                break
            if accepted_word is None:
                passes += 1
                await ctx.send(f"⏱️ <@{user_id}> missed the turn. ({passes}/{len(player_ids)} consecutive passes.)", allowed_mentions=discord.AllowedMentions.none())
                if passes >= len(player_ids):
                    await ctx.send("The story pauses here: everyone missed a turn in a row.")
                    break
                continue

            passes = 0
            words.append(accepted_word)
            scores[user_id] += 1
            if constraint:
                scores[user_id] += 2

        if words:
            final_text = " ".join(words)
            if final_text[-1] not in ".!?…":
                final_text += "."
            final_text = discord.utils.escape_markdown(final_text).replace("@", "@\u200b")
        else:
            final_text = "No words made it into the story this time."

        result = discord.Embed(title="📖 The story you made", description=final_text[:4000], color=discord.Color.green())
        if scores:
            ranking = sorted(scores, key=lambda uid: scores[uid], reverse=True)
            result.add_field(
                name="Story Points",
                value="\n".join(f"<@{uid}> · **{scores[uid]}**" for uid in ranking),
                inline=False,
            )
            best = scores[ranking[0]]
            stars = [uid for uid in ranking if scores[uid] == best]
            result.set_footer(text=f"Story MVP: {', '.join(f'<@{uid}>' for uid in stars)} · twist cards were worth +2 points")
        artwork = await run_blocking(onewordstory_art_file, result, "onewordstory_final")
        if artwork:
            await ctx.send(embed=result, file=artwork, allowed_mentions=discord.AllowedMentions.none())
        else:
            await ctx.send(embed=result, allowed_mentions=discord.AllowedMentions.none())

    @commands.hybrid_command(name="flames")
    async def flames(self, ctx, user1=None, user2=None):
        """Reveal the classic FLAMES result one burn at a time."""
        supplied_first = user1 is not None
        mention_pattern = re.compile(r"<@!?(\d+)>")

        async def resolve_target(value):
            if not isinstance(value, str):
                return value
            value = value.strip()
            match = mention_pattern.fullmatch(value)
            if match and ctx.guild:
                member = ctx.guild.get_member(int(match.group(1)))
                if member:
                    return member
                try:
                    return await self.bot.fetch_user(int(match.group(1)))
                except (discord.NotFound, discord.HTTPException):
                    return value[:72]
            return value[:72] or "Mystery"

        user1 = await resolve_target(user1)
        user2 = await resolve_target(user2)
        if user1 is None:
            user1 = ctx.author
        if user2 is None and supplied_first:
            user2, user1 = user1, ctx.author
        elif user2 is None:
            members = [member for member in getattr(ctx.guild, "members", []) if not member.bot and member.id != getattr(user1, "id", None)]
            user2 = random.choice(members) if members else "Pippo"

        first_name = (getattr(user1, "display_name", str(user1)).strip() or "Mystery")[:72]
        second_name = (getattr(user2, "display_name", str(user2)).strip() or "Mystery")[:72]
        first_letters = [character.casefold() for character in first_name if character.isalpha()]
        remaining_second = [character.casefold() for character in second_name if character.isalpha()]
        unmatched_first = []
        for character in first_letters:
            try:
                remaining_second.remove(character)
            except ValueError:
                unmatched_first.append(character)
        count = max(1, len(unmatched_first) + len(remaining_second))

        active = list("FLAMES")
        cursor = 0
        steps = []
        while len(active) > 1:
            cursor = (cursor + count - 1) % len(active)
            removed = active.pop(cursor)
            steps.append((removed, "".join(active)))
            if active:
                cursor %= len(active)

        outcomes = {
            "F": "👫 Friends",
            "L": "❤️ Lovers",
            "A": "😊 Affection",
            "M": "💍 Marriage",
            "E": "😅 Enemies",
            "S": "🧑‍🤝‍🧑 Siblings",
        }
        outcome = active[0]
        view = FlamesView(ctx.author.id, first_name, second_name, count, steps, outcomes[outcome], outcome)
        embed = await run_blocking(view.make_embed)
        options = {"embed": embed, "view": view, "allowed_mentions": discord.AllowedMentions.none()}
        files = [art for art in (view._pending_art, view._outcome_art) if art is not None]
        if files:
            options["files"] = files
        view.message = await ctx.reply(**options)

    @commands.hybrid_command(name="what", aliases=["define", "ub", "urban_dictionary", "urban"])
    async def meaning(self, ctx, *, query: str):
        """
        Browse community-written Urban Dictionary definitions for a word or phrase.
        syntax: .what {word or phrase}
        """
        query = " ".join(query.split())[:80]
        if not query:
            await ctx.reply("Give me a word or phrase to decode.", allowed_mentions=discord.AllowedMentions.none())
            return

        try:
            async with http_session(self.bot, timeout=aiohttp.ClientTimeout(total=8)) as session:
                async with session.get("https://api.urbandictionary.com/v0/define", params={"term": query}) as resp:
                    if resp.status != 200:
                        raise aiohttp.ClientResponseError(
                            resp.request_info, resp.history, status=resp.status, message="Urban Dictionary request failed"
                        )
                    data = await resp.json(content_type=None)
                    results = data.get("list", []) if isinstance(data, dict) else []
        except (aiohttp.ClientError, asyncio.TimeoutError, ValueError):
            await ctx.reply(
                "Could not reach Urban Dictionary right now. Give it another try in a moment.",
                allowed_mentions=discord.AllowedMentions.none(),
            )
            return

        def clean_text(value, limit):
            value = html.unescape(str(value or "")).replace("[", "").replace("]", "")
            value = " ".join(value.split())
            return discord.utils.escape_markdown(value, as_needed=False)[:limit]

        entries = []
        seen_definitions = set()
        for result in results:
            if not isinstance(result, dict):
                continue
            definition = clean_text(result.get("definition"), 3600)
            if not definition or definition.casefold() in seen_definitions:
                continue
            seen_definitions.add(definition.casefold())
            entries.append({
                "definition": definition,
                "example": clean_text(result.get("example"), 900),
                "author": clean_text(result.get("author"), 80),
                "thumbs_up": result.get("thumbs_up", 0),
                "thumbs_down": result.get("thumbs_down", 0),
            })
            if len(entries) == 12:
                break

        safe_query = clean_text(query, 120)
        if not entries:
            await ctx.reply(
                f"No definitions found for **{safe_query}** on Urban Dictionary.",
                allowed_mentions=discord.AllowedMentions.none(),
            )
            return

        def render_card(entry, page, total):
            embed = discord.Embed(
                title=f"📖 Urban Dictionary: {safe_query}"[:256],
                description=entry["definition"],
                color=discord.Color.from_rgb(255, 190, 76),
            )
            if entry["example"]:
                embed.add_field(name="In the wild", value=entry["example"], inline=False)
            author = entry["author"] or "Community contributor"
            embed.set_author(name=f"Definition {page} of {total} · by {author}"[:256])
            try:
                upvotes = max(0, int(entry["thumbs_up"]))
                downvotes = max(0, int(entry["thumbs_down"]))
            except (TypeError, ValueError):
                upvotes, downvotes = 0, 0
            embed.set_footer(text=f"👍 {upvotes:,}   👎 {downvotes:,} · Community-written; tone and accuracy vary")
            artwork = what_art_file(embed, f"what-{page}")
            return embed, artwork

        view = DefinitionBrowserView(ctx.author.id, entries, query, render_card)
        embed, artwork = await run_blocking(render_card, entries[0], 1, len(entries))
        options = {
            "embed": embed,
            "view": view,
            "allowed_mentions": discord.AllowedMentions.none(),
        }
        if artwork:
            options["file"] = artwork
        view.message = await ctx.reply(**options)


async def setup(bot):
    await bot.add_cog(Fun(bot))
