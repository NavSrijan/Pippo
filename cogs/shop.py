import csv
from discord.ext import commands
import discord

def load_csv(filename):
    data = []
    with open(filename, 'r') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            data.append(dict(row))
    return data

class ShowDropdown(discord.ui.Select):
    def __init__(self, show_names, data):
        options = []
        self.data = data
        for show in show_names:
            options.append(discord.SelectOption(label=show))

        super().__init__(placeholder='Choose which show you want your character from.', min_values=1, max_values=1, options=options)

    def change_options(self, show_names):
        options = []
        for show in show_names:
            options.append(discord.SelectOption(label=show))

        self.options = options

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.view.author_id:
            await interaction.response.send_message("This shop session is not for you. Open your own using `/shop character`.", ephemeral=True)
            return
        await interaction.response.defer()
        view2 = CharacterView(self.view.bot, self.values[0], self.data, author_id=self.view.author_id)
        await self.view.out.edit(view=view2)
        view2.out = self.view.out
        
class ShowNavButton(discord.ui.Button):

    def __init__(self, label:str, forward=True):
        super().__init__(style=discord.ButtonStyle.blurple, label=label)
        self.label = label
        self.forward = forward 
        if self.forward is False:
            self.disabled=True

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.view.author_id:
            await interaction.response.send_message("This shop session is not for you.", ephemeral=True)
            return
        await interaction.response.defer()
        if self.forward is True:
            self.view.current_page+=1
        else:
            self.view.current_page-=1

        if self.view.current_page >= self.view.max_page-1:
            self.view.children[2].disabled=True
        else:
            self.view.children[2].disabled=False
        if self.view.current_page <= 0:
            self.view.children[1].disabled=True
        else:
            self.view.children[1].disabled=False

        self.view.children[0].change_options(self.view.show_names[self.view.current_page])

        await self.view.out.edit(view=self.view)

class ShowView(discord.ui.View):

    def __init__(self, bot, show_names, data, author_id=None):
        super().__init__(timeout=60)

        self.bot = bot
        self.author_id = author_id
        self.show_names = self.split_list(show_names)
        self.data = data

        self.max_page = len(self.show_names)
        self.current_page = 0

        self.add_item(ShowDropdown(self.show_names[self.current_page], self.data))
        self.add_item(ShowNavButton("<", forward=False))
        self.add_item(ShowNavButton(">", forward=True))

    def split_list(self, lst):
        sublists = []
        sublist = []
        for item in lst:
            sublist.append(item)
            if len(sublist) == 25:
                sublists.append(sublist)
                sublist = []
        if sublist:
            sublists.append(sublist)
        return sublists

class CharacterDropdown(discord.ui.Select):
    def __init__(self, character_names):
        options = []
        for character in character_names:
            options.append(discord.SelectOption(label=character))

        super().__init__(placeholder='Choose your preferred character.', min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.view.author_id:
            await interaction.response.send_message("This shop session is not for you.", ephemeral=True)
            return
        await interaction.response.defer()
        cost = 1000
        coins_data = await self.view.bot.db.coins.get_amount_coins(interaction.user.id)
        coins = coins_data.get('coins', 0) if isinstance(coins_data, dict) else coins_data['coins']
        if coins>=cost:
            await self.view.bot.db.coins.deduct_coins(interaction.user.id, cost)
            await self.view.bot.db.characters.insert_character(interaction.user.id, self.view.show_name, self.values[0])
            await self.view.out.edit(content=f"Your character has been changed to **{self.values[0]}**!", view=None)
        else:
            await self.view.out.edit(content="You sadly don't have enough coins. You need 1000 coins.", view=None)

class CharacterView(discord.ui.View):

    def __init__(self, bot, show_name, data, author_id=None):
        super().__init__(timeout=60)

        self.bot = bot
        self.author_id = author_id
        self.show_name = show_name
        self.data = data
        self.character_names = self.fetch_characters_by_show()

        self.add_item(CharacterDropdown(self.character_names))

    def fetch_characters_by_show(self):
        characters = []
        for entry in self.data:
            if entry['show_name'] == self.show_name:
                characters.append(entry['character_name'])
        return characters


class Shop(commands.Cog):
    """Shop commands"""

    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_group(name="shop")
    async def shop(self, ctx):
        """Buy things using coins!"""
        if ctx.invoked_subcommand is None:
            await ctx.send("Available shop subcommands: `character` (e.g. `.shop character`)")

    @shop.command(name="character")
    async def character_shop(self, ctx):
        """Buy a character of your choice"""
        if not hasattr(self.bot, 'cartoon_characters') or not self.bot.cartoon_characters:
            self.bot.cartoon_characters = load_csv("data/cartoons/character_dataset.csv")

        # Sort the list of shows into alphabetical order
        show_names = list(set([x['show_name'] for x in self.bot.cartoon_characters]))
        show_names.sort()

        # The main view, which allows to select the show, it goes deeper into multiple views.
        view = ShowView(self.bot, show_names, self.bot.cartoon_characters, author_id=ctx.author.id)
        msg = await ctx.reply(view=view)
        view.out = msg


async def setup(bot):
    await bot.add_cog(Shop(bot))

