import random
import json
import asyncio
import aiohttp

from discord.ext import commands
import discord

from views import BreedGuessView

class Animals(commands.Cog):
    """Animal related commands"""

    def __init__(self, bot):
        self.bot = bot

    async def _get_json(self, url: str):
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=8)) as session:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        return await resp.json()
        except Exception as e:
            print(f"Error fetching {url}: {e}")
        return None

    @commands.cooldown(1, 10, commands.BucketType.user)
    @commands.hybrid_command(name="dog")
    async def dog(self, ctx):
        """Gets a random dog image"""
        data = await self._get_json("https://api.thedogapi.com/v1/images/search")
        dog_url = data[0]['url'] if (data and isinstance(data, list) and len(data) > 0 and 'url' in data[0]) else "https://images.dog.ceo/breeds/retriever-golden/n02099233_100.jpg"

        cute_lines = [
            "Just sending a dose of canine cuteness to brighten your day!",
            "Woof-tastic moments are best shared! Enjoy this adorable doggy pic!",
            "Prepare for an overload of cuteness! Here's a precious little pup for you.",
            "Sending you a little box of wagging tails and puppy kisses to brighten your day!",
            "Get ready for a mega dose of adorable! Here's an extra cute doggy pic just for you.",
            "Prepare yourself for maximum cuteness overload! Enjoy this sweet little furball.",
            "Dog-titude and cuteness collide! Enjoy this delightful canine friend in all its adorable glory.",
            "Warming your heart with a virtual cuddle! Here's an image of an incredibly cute dog.",
            "Sending a burst of happiness with this paw-somely adorable picture. It's guaranteed to make you smile!",
            "Pause everything and behold the cuteness! Enjoy this precious little ball of fluff.",
            "Hope this adorable dog brings a moment of sheer joy and sweetness to your day!",
            "Unlocking the magical world of adorable dogs! Here's a picture to make your heart melt.",
            "Woof-massive cuteness alert! Brace yourself for an overwhelmingly cute dog picture.",
            "Sending you a virtual hug from this super cute pup! Let the cuddliness embrace you.",
            "Prepare for your heart to be stolen! Here's an irresistibly cute dog pic just for you.",
            "Cuteness level: off the charts! Enjoy this delightful little canine that will melt your heart.",
            "Feeling down? Take a look at this charming doggy and feel the instant mood lift!",
            "May your day be filled with as much sweetness as this adorable dog brings!",
            "Here's a little dose of canine enchantment to brighten your day. Enjoy this adorable pup!",
            "The world needs more smiles, so here's an impossibly cute dog picture to make you grin.",
            "Sending you a virtual high-five from this adorable canine companion. Enjoy the cuteness!",
            "Dogs have mastered the art of capturing hearts. Allow this cute pup to capture yours!",
            "Unlocking the secret to happiness: an image of a ridiculously cute dog. Enjoy the instant joy!",
            "Get ready for your heart to melt into a puddle of adorableness! Here's an incredibly cute dog for you.",
            "Sending a little ray of sunshine in the form of an adorable dog picture. Let it brighten your day!",
            "Take a break and indulge in the fluffiest cuteness therapy. Here's an adorable pup for you.",
            "Ready for a cuteness explosion? Brace yourself for this unbelievably cute dog image!",
            "Feeling stressed? Here's a prescription for instant relaxation: an image of an incredibly cute dog!",
            "Happiness is just a wag away! Enjoy this sweet little ball of fur that will melt your heart.",
            "Wishing you a day filled with as much joy as this charming dog picture brings!",
            "Sending you a virtual smooch from this adorable canine friend. Prepare for maximum cuteness!",
            "May your day be as delightful as this picture of a precious little pup. Enjoy the cuteness!",
            "Pause. Breathe. Smile. Let this unbelievably cute dog image bring a moment of pure happiness.",
            "Sending you a fluffy bundle of joy wrapped in cuteness. Enjoy this adorable doggy pic!",
            "Dogs have a way of making everything better. Here's an image to brighten your day!",
            "Feeling blue? Allow this adorable dog to wag its way into your heart and turn your day around.",
            "Sending you a virtual tail wag and a whole lot of cuteness to make your day extra special.",
            "Just a friendly reminder that doggy love is the best kind of love. Enjoy this adorable picture!",
            "In a world full of chaos, let the pure innocence of this cute doggy bring you peace and happiness.",
            "Get ready for your heart to melt with this paw-sitively adorable dog picture. Enjoy the cuteness!",
            "Take a moment to appreciate the simple joys in life, like this adorable dog bringing you happiness.",
            "Sending you a virtual bundle of joy and wet nose kisses. Enjoy the cuteness overload!",
            "Unleash the power of cuteness! Here's an adorable doggy pic that will brighten your day.",
            "Feeling stressed? Let this adorable pup melt away your worries and bring a smile to your face.",
            "Wishing you a day filled with as much love and joy as this sweet doggy brings!",
            "Sending you a virtual cuddle session with this incredibly cute dog. Let the warmth embrace you.",
            "Need a pick-me-up? This super cute dog picture is here to bring a big smile to your face!",
            "Unlocking the secret to happiness: an image of an incredibly adorable dog. Enjoy the instant joy!",
            "Get ready for a cuteness explosion! Brace yourself for this unbelievably cute dog image!",
            "Feeling tired? Let this adorable pup brighten your day and fill it with pure happiness.",
            "Sending you a virtual bundle of wagging tails and wet nose boops. Enjoy the cuteness overload!"
        ]

        emb = discord.Embed(title=random.choice(cute_lines), color=discord.Color.gold())
        emb.set_image(url=dog_url)
        await ctx.reply(embed=emb)

    @commands.cooldown(1, 10, commands.BucketType.user)
    @commands.hybrid_command(name="cat")
    async def cat(self, ctx):
        """Gets a random cat image"""
        data = await self._get_json("https://api.thecatapi.com/v1/images/search")
        cat_url = data[0]['url'] if (data and isinstance(data, list) and len(data) > 0 and 'url' in data[0]) else "https://cdn.pixabay.com/photo/2022/02/18/14/30/cat-7020828_640.jpg"

        cute_lines = [
            "Just sending a dose of feline cuteness to brighten your day!",
            "Meow-gical moments are best shared! Enjoy this adorable kitty pic!",
            "Prepare for an overload of cuteness! Here's a precious little kitty for you.",
            "Sending you a little box of feline cuteness to brighten your day!",
            "Get ready for a mega dose of adorable! Here's an extra cute kitty pic just for you.",
            "Prepare yourself for maximum cuteness overload! Enjoy this sweet little furball.",
            "Cat-titude and cuteness collide! Enjoy this delightful feline friend in all its adorable glory.",
            "Warming your heart with a virtual cuddle! Here's an image of an incredibly cute cat.",
            "Sending a burst of happiness with this purr-fectly adorable picture. It's guaranteed to make you smile!",
            "Pause everything and behold the cuteness! Enjoy this precious little ball of fur.",
            "Hope this adorable cat brings a moment of sheer joy and sweetness to your day!",
            "Unlocking the magical world of adorable cats! Here's a picture to make your heart melt.",
            "Meow-sive cuteness alert! Brace yourself for an overwhelmingly cute cat picture.",
            "Sending you a virtual hug from this super cute kitty! Let the cuddliness embrace you.",
            "Prepare for your heart to be stolen! Here's an irresistibly cute cat pic just for you.",
            "Cuteness level: off the charts! Enjoy this delightful little feline that will melt your heart.",
            "Feeling down? Take a look at this charming kitty and feel the instant mood lift!",
            "May your day be filled with as much sweetness as this adorable cat brings!",
            "Here's a little dose of feline enchantment to brighten your day. Enjoy this adorable kitty!",
            "The world needs more smiles, so here's an impossibly cute cat picture to make you grin.",
            "Sending you a virtual high-five from this adorable feline companion. Enjoy the cuteness!",
            "Cats have mastered the art of capturing hearts. Allow this cute kitty to capture yours!",
            "Unlocking the secret to happiness: an image of a ridiculously cute cat. Enjoy the instant joy!",
            "Get ready for your heart to melt into a puddle of adorableness! Here's an incredibly cute cat for you.",
            "Sending a little ray of sunshine in the form of an adorable cat picture. Let it brighten your day!",
            "Take a break and indulge in the fluffiest cuteness therapy. Here's an adorable kitty for you.",
            "Ready for a cuteness explosion? Brace yourself for this unbelievably cute cat image!",
            "Feeling stressed? Here's a prescription for instant relaxation: an image of an incredibly cute cat!",
            "Happiness is just a whisker away! Enjoy this sweet little ball of fur that will melt your heart.",
            "Wishing you a day filled with as much joy as this charming cat picture brings!",
            "Sending you a virtual smooch from this adorable feline friend. Prepare for maximum cuteness!",
            "May your day be as delightful as this picture of a precious little kitty. Enjoy the cuteness!",
            "Pause. Breathe. Smile. Let this unbelievably cute cat image bring a moment of pure happiness.",
            "Sending you a fluffy bundle of joy wrapped in cuteness. Enjoy this adorable cat pic!",
            "Cats have a way of making everything better. Here's an image to brighten your day!",
            "Feeling blue? Look at this ridiculously cute cat and let the cheerfulness wash over you.",
            "Sending a little love and a whole lot of cuteness your way with this adorable kitty picture.",
            "Allow this charming cat to sprinkle a dash of magic and cuteness into your day.",
            "Cuteness alert! Brace yourself for a heartwarming image of the most adorable cat.",
            "Need an instant mood boost? Look no further! This cute cat picture is guaranteed to make you smile.",
            "Unlocking the door to happiness with a tiny paw and a lot of cuteness. Enjoy this delightful kitty!",
            "Sending you a virtual cuddle session with this super cute cat. Let the warm fuzzies begin!",
            "Ready for a cuteness infusion? Here's an adorable kitty pic that will melt even the coldest of hearts.",
            "Feeling overwhelmed? Take a moment to appreciate this ridiculously cute cat and let the stress melt away.",
            "Wishing you a day filled with as much sweetness as this charming cat brings. Enjoy the cuteness!",
            "Just a friendly reminder that the world is a better place with cute cats in it. Enjoy this adorable picture!",
            "Sending you a little ball of fur and a whole lot of cuteness to make your day extra special.",
            "In a world where you can be anything, be like this incredibly cute cat. Embrace the cuteness and be happy!",
            "Here's an image of pure kitty enchantment to brighten your day. Allow the cuteness to sweep you off your feet!",
            "Pause for a moment and let this adorable cat picture bring a smile to your face. Cutest therapy ever!",
            "Sending you a virtual treasure chest filled with cat cuddles and adorable moments. Enjoy the cuteness overload!"
        ]

        emb = discord.Embed(title=random.choice(cute_lines), color=discord.Color.teal())
        emb.set_image(url=cat_url)
        await ctx.reply(embed=emb)

    @commands.hybrid_command(name="meow")
    async def meow(self, ctx):
        """Guess the breed of a cat"""
        with open('data/breeds/catBreeds.json', 'r') as f:
            breeds_data = json.load(f)

        breed_names = {x['name']: x['id'] for x in breeds_data}
        sample_breeds = random.sample(list(breed_names.keys()), 4)
        answer = random.choice(sample_breeds)

        url = f"https://api.thecatapi.com/v1/images/search?breed_ids={breed_names[answer]}"
        data = await self._get_json(url)
        img_url = data[0]['url'] if (data and isinstance(data, list) and len(data) > 0 and 'url' in data[0]) else None
        if not img_url:
            data = await self._get_json("https://api.thecatapi.com/v1/images/search")
            img_url = data[0]['url'] if (data and isinstance(data, list) and len(data) > 0 and 'url' in data[0]) else "https://cdn.pixabay.com/photo/2022/02/18/14/30/cat-7020828_640.jpg"

        emb = discord.Embed(title="Can you guess the breed?", color=discord.Color.blue())
        emb.set_image(url=img_url)

        view = BreedGuessView(answer, sample_breeds)
        out = await ctx.reply(embed=emb, view=view)
        view.out = out

    @commands.hybrid_command(name="woof")
    async def woof(self, ctx):
        """Guess the breed of a dog"""
        with open('data/breeds/dogBreeds.json', 'r') as f:
            breeds_data = json.load(f)

        breed_names = {x['name']: x['id'] for x in breeds_data}
        sample_breeds = random.sample(list(breed_names.keys()), 4)
        answer = random.choice(sample_breeds)

        url = f"https://api.thedogapi.com/v1/images/search?breed_ids={breed_names[answer]}"
        data = await self._get_json(url)
        img_url = data[0]['url'] if (data and isinstance(data, list) and len(data) > 0 and 'url' in data[0]) else None
        if not img_url:
            data = await self._get_json("https://api.thedogapi.com/v1/images/search")
            img_url = data[0]['url'] if (data and isinstance(data, list) and len(data) > 0 and 'url' in data[0]) else "https://images.dog.ceo/breeds/retriever-golden/n02099233_100.jpg"

        emb = discord.Embed(title="Can you guess the breed?", color=discord.Color.blue())
        emb.set_image(url=img_url)

        view = BreedGuessView(answer, sample_breeds)
        out = await ctx.reply(embed=emb, view=view)
        view.out = out

    @commands.hybrid_command(name="breedme")
    async def breedme(self, ctx, user: discord.Member = None):
        """Which breed of dog are you?"""
        def generate_random_number(user_id, n):
            random.seed(user_id)
            return random.randint(0, n)

        def dog_age_to_human_age(dog_age):
            if dog_age <= 0:
                return "Invalid age."
            elif dog_age == 1:
                return 15
            elif dog_age == 2:
                return 24
            elif dog_age <= 20:
                return 24 + (dog_age - 2) * 5
            elif dog_age <= 50:
                return 24 + 18 + (dog_age - 20) * 5
            elif dog_age <= 90:
                return 24 + 18 + 30 + (dog_age - 50) * 6
            else:
                return 24 + 18 + 30 + 40 + (dog_age - 90) * 8

        if user is None:
            user = ctx.author

        with open('data/breeds/dogBreeds.json', 'r') as f:
            breeds = json.load(f)

        idd = user.id
        number = generate_random_number(idd, len(breeds) - 1)
        if idd == 1095818778446667838:
            number = 146
        breed = breeds[number]

        try:
            das = breed.get('life_span', '').split(" ")
            dog_age = (int(das[0]) + int(das[2])) // 2
            expected_age = dog_age_to_human_age(dog_age)
        except Exception:
            expected_age = "Couldn't determine"

        bg = breed.get('breed_group', 'Companion / Working')
        temperament = breed.get('temperament', 'friendly, energetic, and loyal')
        img_url = breed.get('image', {}).get('url') if isinstance(breed.get('image'), dict) else "https://images.dog.ceo/breeds/retriever-golden/n02099233_100.jpg"

        emb = discord.Embed(title=f"{user.display_name} is a {breed['name']}", color=discord.Color.orange())
        if img_url:
            emb.set_image(url=img_url)
        emb.set_footer(text="This is obviously random.")
        emb.description = f"{user.mention} is **{temperament}**.\nBelongs to the group **{bg}**.\n\nExpected life span is **{expected_age}**."
        await ctx.reply(embed=emb)

    @commands.hybrid_command(name="meowme")
    async def meowme(self, ctx, user: discord.Member = None):
        """Which breed of cat are you?"""
        def generate_random_number(user_id, n):
            random.seed(user_id)
            return random.randint(0, n)

        def dog_age_to_human_age(dog_age):
            if dog_age <= 0:
                return "Invalid age."
            elif dog_age == 1:
                return 15
            elif dog_age == 2:
                return 24
            elif dog_age <= 20:
                return 24 + (dog_age - 2) * 5
            elif dog_age <= 50:
                return 24 + 18 + (dog_age - 20) * 5
            elif dog_age <= 90:
                return 24 + 18 + 30 + (dog_age - 50) * 6
            else:
                return 24 + 18 + 30 + 40 + (dog_age - 90) * 8

        if user is None:
            user = ctx.author

        with open('data/breeds/catBreeds.json', 'r') as f:
            breeds = json.load(f)

        idd = user.id
        number = generate_random_number(idd, len(breeds) - 1)
        if idd == 585878983980089354:
            number = 14
        breed = breeds[number]

        try:
            das = breed.get('life_span', '').split(" ")
            dog_age = (int(das[0]) + int(das[2])) // 2
            expected_age = dog_age_to_human_age(dog_age)
        except Exception:
            expected_age = "Couldn't determine"

        temperament = breed.get('temperament', 'curious, intelligent, and playful')
        refn_id = breed.get('reference_image_id')
        img = None
        if refn_id:
            img_data = await self._get_json(f"https://api.thecatapi.com/v1/images/{refn_id}")
            if isinstance(img_data, dict) and 'url' in img_data:
                img = img_data['url']
        if not img:
            img = "https://cdn.pixabay.com/photo/2022/02/18/14/30/cat-7020828_640.jpg"

        if idd == 585878983980089354:
            img = "https://cdn.pixabay.com/photo/2022/02/18/14/30/cat-7020828_640.jpg"

        emb = discord.Embed(title=f"{user.display_name} is a {breed['name']}", color=discord.Color.purple())
        emb.set_image(url=img)
        emb.set_footer(text="This is obviously random.")
        emb.description = f"{user.mention} is **{temperament}**.\n\nExpected life span is **{expected_age}**."
        await ctx.reply(embed=emb)

async def setup(bot):
    await bot.add_cog(Animals(bot))

