from runtime import http_session, read_limited
from cogs.play import offer_game_mode
from runtime import run_blocking
import random
import json
from functools import lru_cache
from pathlib import Path
import asyncio
import aiohttp
from io import BytesIO
from urllib.parse import urlsplit
from PIL import Image

from discord.ext import commands
import discord

from functions import write_caption_on_image
from views import BreedGuessView, AnimalPhotoView, animal_art_file

@lru_cache(maxsize=4)
def _breed_rows(filename, modified_ns):
    with open(filename, encoding="utf-8") as source:
        return json.load(source)


def load_breeds(species):
    path = Path(__file__).resolve().parents[1] / "data" / "breeds" / f"{species}Breeds.json"
    return [dict(breed) for breed in _breed_rows(str(path), path.stat().st_mtime_ns)]


class Animals(commands.Cog):
    """Animal related commands"""

    def __init__(self, bot):
        self.bot = bot

    async def _get_json(self, url: str):
        try:
            async with http_session(self.bot, timeout=aiohttp.ClientTimeout(total=8)) as session:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        return await resp.json()
        except Exception as e:
            print(f"Error fetching {url}: {e}")
        return None

    @staticmethod
    def _trusted_animal_image_url(url, species):
        parsed = urlsplit(url or "")
        host = (parsed.hostname or "").casefold()
        domain = f"the{species}api.com"
        return parsed.scheme == "https" and (host == domain or host.endswith(f".{domain}"))

    @staticmethod
    def _validate_photo(image_bytes):
        with Image.open(BytesIO(image_bytes)) as photo:
            if photo.format not in {"JPEG", "PNG", "WEBP"} or photo.width * photo.height > 20_000_000:
                raise ValueError("Unsupported image dimensions or format")
            photo.verify()

    async def fetch_animal_photo(
        self,
        species,
        number,
        seen_urls,
        breed_id=None,
        fallback_url=None,
        caption_title=None,
        caption_description=None,
        art_folder=None,
    ):
        """Fetch, validate, caption, and return a unique animal photo."""
        if species not in {"dog", "cat"}:
            return None
        api_url = f"https://api.the{species}api.com/v1/images/search"
        parade = "Pup Parade" if species == "dog" else "Cat Parade"
        timeout = aiohttp.ClientTimeout(total=10, connect=4)
        try:
            async with http_session(self.bot, timeout=timeout) as session:
                for attempt in range(4):
                    params = {"breed_ids": str(breed_id)} if breed_id is not None else None
                    try:
                        async with session.get(api_url, params=params, timeout=timeout) as response:
                            data = await response.json(content_type=None) if response.status == 200 else None
                    except (aiohttp.ClientError, asyncio.TimeoutError, ValueError):
                        data = None
                    photo_url = (
                        data[0].get("url", "")
                        if isinstance(data, list) and data and isinstance(data[0], dict)
                        else fallback_url or ""
                    )
                    if attempt == 3 and fallback_url:
                        photo_url = fallback_url
                    if (
                        not isinstance(photo_url, str)
                        or not self._trusted_animal_image_url(photo_url, species)
                        or photo_url in seen_urls
                    ):
                        photo_url = fallback_url
                    if (
                        not isinstance(photo_url, str)
                        or not self._trusted_animal_image_url(photo_url, species)
                        or photo_url in seen_urls
                    ):
                        continue
                    try:
                        async with session.get(photo_url, allow_redirects=False, timeout=timeout) as image_response:
                            if image_response.status != 200:
                                continue
                            mime_type = image_response.headers.get("Content-Type", "").split(";", 1)[0]
                            if not mime_type.startswith("image/"):
                                continue
                            image_bytes = await read_limited(image_response, 8 * 1024 * 1024)
                        await run_blocking(self._validate_photo, image_bytes)
                    except (aiohttp.ClientError, asyncio.TimeoutError, ValueError, OSError, Image.DecompressionBombError):
                        continue

                    if species == "dog":
                        description = random.choice((
                            "Today's guest is an excellent dog. Tap for another pup!",
                            "Pippo's dog-park report: tail-wagging levels are off the charts.",
                            "A very good dog has entered the chat. This parade has four photos.",
                            "New pup, new serotonin. Browse three more in this parade.",
                            "Pippo checked the ears, paws, and vibes: top marks all around.",
                            "Today's assignment: admire this dog, then choose if you want another.",
                        ))
                        color = discord.Color.gold()
                    else:
                        description = random.choice((
                            "Today's guest is an excellent cat. Tap for another kitty!",
                            "Pippo's cat report: whisker confidence is looking excellent.",
                            "A very good cat has entered the chat. This parade has four photos.",
                            "New kitty, new serotonin. Browse three more in this parade.",
                            "Pippo checked the ears, paws, and vibes: top marks all around.",
                            "Today's assignment: admire this cat, then choose if you want another.",
                        ))
                        color = discord.Color.teal()
                    if breed_id is not None:
                        title = caption_title or "Name that breed"
                        description = caption_description or f"One {species}, four choices. Which breed do you think it is?"
                    else:
                        title = f"{parade} · photo {number}/4"
                    embed = discord.Embed(title=title, description=description, color=color)
                    embed.set_image(url=f"attachment://{species}.jpg")
                    thumbnail = await run_blocking(animal_art_file,
                        embed,
                        species,
                        f"pippo-{species}-{number}",
                        folder=art_folder or (("woof" if species == "dog" else "meow") if breed_id is not None else None),
                    )
                    photo_file = await run_blocking(write_caption_on_image,
                        BytesIO(image_bytes), embed.title, description, filename=f"{species}.jpg"
                    )
                    return embed, photo_file, thumbnail, photo_url
        except (aiohttp.ClientError, asyncio.TimeoutError, ValueError, OSError, Image.DecompressionBombError):
            return None
        return None

    async def start_breed_quiz(self, ctx, species, *, solo):
        try:
            breeds_data = await run_blocking(load_breeds, species)
        except (OSError, json.JSONDecodeError):
            label = "cat" if species == "cat" else "dog"
            await ctx.reply(f"The {label}-breed list is unavailable right now. Please try again later.")
            return

        breeds = [
            breed for breed in breeds_data
            if isinstance(breed, dict) and breed.get("name") and breed.get("id") is not None
        ]
        if len(breeds) < 4:
            await ctx.reply(f"There aren't enough {species} breeds available to start a quiz right now.")
            return

        seen_breed_ids = set()
        seen_photo_urls = set()

        async def next_round():
            round_number = len(seen_breed_ids) + 1
            if round_number > 5:
                return None
            available = [breed for breed in breeds if breed["id"] not in seen_breed_ids]
            if len(available) < 4:
                return None
            choices = random.sample(available, 4)
            answer = random.choice(choices)
            result = await self.fetch_animal_photo(
                species,
                round_number,
                seen_photo_urls,
                breed_id=answer["id"],
                fallback_url=(answer.get("image") or {}).get("url"),
                caption_title=f"Round {round_number}/5 · Name that breed",
                caption_description=(
                    f"Choose the {species} breed from four options. "
                    + (
                        "You get one attempt per round; each correct answer earns a point."
                        if solo else "Everyone can guess once each round; correct answers earn a point."
                    )
                ),
            )
            if result is None:
                return None
            embed, photo, thumbnail, photo_url = result
            seen_breed_ids.add(answer["id"])
            seen_photo_urls.add(photo_url)
            return {
                "answer": answer["name"],
                "breeds": [breed["name"] for breed in choices],
                "embed": embed,
                "files": [photo] + ([thumbnail] if thumbnail else []),
            }

        question = await next_round()
        if question is None:
            await ctx.reply(f"I couldn't load a photo for this {species} breed quiz. Please try again.")
            return

        view = BreedGuessView(
            question["answer"],
            question["breeds"],
            timeout=75,
            author_id=ctx.author.id if solo else None,
            embed=question["embed"],
            total_rounds=5,
            next_round=next_round,
        )
        view.out = await ctx.reply(
            embed=question["embed"],
            view=view,
            files=question["files"],
            allowed_mentions=discord.AllowedMentions.none(),
        )

    @commands.cooldown(1, 10, commands.BucketType.user)
    @commands.hybrid_command(name="dog")
    async def dog(self, ctx):
        """Browse four captioned dog photos in an invoker-only Pup Parade."""
        result = await self.fetch_animal_photo("dog", 1, set())
        if result is None:
            await ctx.reply(
                "The dog-photo feed is taking a break. Try `/dog` again in a moment.",
                allowed_mentions=discord.AllowedMentions.none(),
            )
            return
        embed, photo, thumbnail, photo_url = result
        view = AnimalPhotoView(ctx.author.id, lambda number, seen: self.fetch_animal_photo("dog", number, seen), photo_url, "dog")
        options = {
            "embed": embed,
            "view": view,
            "allowed_mentions": discord.AllowedMentions.none(),
            "files": [photo] + ([thumbnail] if thumbnail else []),
        }
        view.message = await ctx.reply(**options)

    @commands.cooldown(1, 10, commands.BucketType.user)
    @commands.hybrid_command(name="cat")
    async def cat(self, ctx):
        """Browse four captioned cat photos in an invoker-only Cat Parade."""
        result = await self.fetch_animal_photo("cat", 1, set())
        if result is None:
            await ctx.reply(
                "The cat-photo feed is taking a break. Try `/cat` again in a moment.",
                allowed_mentions=discord.AllowedMentions.none(),
            )
            return
        embed, photo, thumbnail, photo_url = result
        view = AnimalPhotoView(ctx.author.id, lambda number, seen: self.fetch_animal_photo("cat", number, seen), photo_url, "cat")
        options = {
            "embed": embed,
            "view": view,
            "allowed_mentions": discord.AllowedMentions.none(),
            "files": [photo] + ([thumbnail] if thumbnail else []),
        }
        view.message = await ctx.reply(**options)

    @commands.hybrid_command(name="meow")
    async def meow(self, ctx):
        """Play five cat-breed photo rounds solo or with chat, and build a score."""
        if await offer_game_mode(ctx, "meow"):
            return
        await self.start_breed_quiz(ctx, "cat", solo=ctx._pippo_play_mode)

    @commands.hybrid_command(name="woof")
    async def woof(self, ctx):
        """Play five dog-breed photo rounds solo or with chat, and build a score."""
        if await offer_game_mode(ctx, "woof"):
            return
        await self.start_breed_quiz(ctx, "dog", solo=ctx._pippo_play_mode)

    @commands.hybrid_command(name="breedme")
    async def breedme(self, ctx, user: discord.Member = None):
        """Which breed of dog are you?"""
        if user is None:
            user = ctx.author

        try:
            raw_breeds = await run_blocking(load_breeds, "dog")
        except (OSError, json.JSONDecodeError):
            await ctx.reply("The dog-breed list is unavailable right now. Please try again later.")
            return

        breeds = [
            breed for breed in raw_breeds
            if isinstance(breed, dict) and breed.get("name") and breed.get("id") is not None
        ]
        if not breeds:
            await ctx.reply("There aren't any dog breeds available for a match right now.")
            return

        number = random.Random(user.id).randrange(len(breeds))
        if user.id == 1095818778446667838 and len(breeds) > 146:
            number = 146
        breed = breeds[number]
        breed_name = breed["name"]
        temperament = breed.get("temperament") or "friendly, energetic, and loyal"
        breed_group = breed.get("breed_group") or "Companion / Working"
        lifespan = breed.get("life_span") or "not listed"
        image = breed.get("image")
        fallback_url = image.get("url") if isinstance(image, dict) else None

        title = f"{user.display_name}'s Pippo breed match: {breed_name}"
        caption = f"Temperament: {temperament}. Typical lifespan: {lifespan}."
        result = await self.fetch_animal_photo(
            "dog",
            1,
            set(),
            breed_id=breed["id"],
            fallback_url=fallback_url,
            caption_title=title,
            caption_description=caption,
            art_folder="dog",
        )
        emb = discord.Embed(
            title=title,
            description=(
                f"{user.mention} gets Pippo's playful breed match.\n\n"
                f"**Temperament:** {temperament}\n"
                f"**Breed group:** {breed_group}\n"
                f"**Typical lifespan:** {lifespan}"
            ),
            color=discord.Color.orange(),
        )
        emb.set_footer(text="This playful match stays the same for this Discord profile.")
        files = []
        if result is not None:
            _photo_embed, photo, thumbnail, _photo_url = result
            emb.set_image(url="attachment://dog.jpg")
            if thumbnail is not None:
                emb.set_thumbnail(url=f"attachment://{thumbnail.filename}")
            files = [photo] + ([thumbnail] if thumbnail else [])
        await ctx.reply(
            embed=emb,
            files=files,
            allowed_mentions=discord.AllowedMentions.none(),
        )

    @commands.hybrid_command(name="meowme")
    async def meowme(self, ctx, user: discord.Member = None):
        """Which breed of cat are you?"""
        if user is None:
            user = ctx.author

        try:
            raw_breeds = await run_blocking(load_breeds, "cat")
        except (OSError, json.JSONDecodeError):
            await ctx.reply("The cat-breed list is unavailable right now. Please try again later.")
            return

        breeds = [
            breed for breed in raw_breeds
            if isinstance(breed, dict) and breed.get("name") and breed.get("id") is not None
        ]
        if not breeds:
            await ctx.reply("There aren't any cat breeds available for a match right now.")
            return

        number = random.Random(user.id).randrange(len(breeds))
        if user.id == 585878983980089354 and len(breeds) > 14:
            number = 14
        breed = breeds[number]
        breed_name = breed["name"]
        temperament = breed.get("temperament") or "curious, intelligent, and playful"
        lifespan = breed.get("life_span") or "not listed"
        image = breed.get("image")
        fallback_url = image.get("url") if isinstance(image, dict) else None

        title = f"{user.display_name}'s Pippo cat match: {breed_name}"
        caption = f"Temperament: {temperament}. Typical lifespan: {lifespan}."
        result = await self.fetch_animal_photo(
            "cat",
            1,
            set(),
            breed_id=breed["id"],
            fallback_url=fallback_url,
            caption_title=title,
            caption_description=caption,
            art_folder="cat",
        )
        emb = discord.Embed(
            title=title,
            description=(
                f"{user.mention} gets Pippo's playful cat-breed match.\n\n"
                f"**Temperament:** {temperament}\n"
                f"**Typical lifespan:** {lifespan}"
            ),
            color=discord.Color.purple(),
        )
        emb.set_footer(text="This playful match stays the same for this Discord profile.")
        files = []
        if result is not None:
            _photo_embed, photo, thumbnail, _photo_url = result
            emb.set_image(url="attachment://cat.jpg")
            if thumbnail is not None:
                emb.set_thumbnail(url=f"attachment://{thumbnail.filename}")
            files = [photo] + ([thumbnail] if thumbnail else [])
        await ctx.reply(
            embed=emb,
            files=files,
            allowed_mentions=discord.AllowedMentions.none(),
        )

async def setup(bot):
    await bot.add_cog(Animals(bot))
