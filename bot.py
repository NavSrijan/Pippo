import asyncio
import asyncpg
import os
import datetime
import time
import random
import ipdb

import discord
from discord.ext import commands
import topgg
import json

from database import DB

#MY_GUILD = discord.Object(id=864085584691593216)
cogs = ['greetings', 'bollywood', 'settings', 'help', 'info', 'fun', 'animals', 'actions', 'economy', 'shop']


async def get_prefix(bot, message):
    """Returns the specific guild prefix"""
    #return "."
    prefix = await bot.db.servers.fetch_prefix(message.guild.id)
    return prefix

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
activity = discord.Activity(type=discord.ActivityType.listening, name=f"Maithili Thakur")
prefix = "."
bot = commands.Bot(command_prefix=get_prefix,
                   case_insensitive=True,
                   intents=intents,
                   status=discord.Status.online,
                   activity=activity)

bot.prefix = prefix
bot.get_prefixx = get_prefix
bot.production = os.environ['production']

bot.THEWHISTLER = 302253506947973130

async def load_cogs(bot, cogs):
    for extension in cogs:
        try:
            await bot.load_extension('cogs.' + extension)
            print(f"Loaded {extension}")
        except Exception as e:
            print(f"Error loading {extension}")
            print(e)


@bot.event
async def on_ready():
    print("Logged in as {0.user}".format(bot))
    THEWHISTLER = bot.THEWHISTLER
    thewhistler = bot.get_user(THEWHISTLER)
    await thewhistler.send("Pippo Online")

    def generate_command_list():
        # Generating a command list
        def get_command_info(command):
            return {
                'name': command.name,
                'aliases': command.aliases,
                'help': command.help,
                'coins': 0,
            }

        commands_info = []
        for command in bot.commands:
            command_info = get_command_info(command)
            commands_info.append(command_info)

        with open('commands.json', 'w') as file:
            json.dump(commands_info, file, indent=4)

creds = {'username': os.environ['database_username'], 'password': os.environ['database_password'], 'host': os.environ['db_host']}
async def create_db_pool():
    #Remove max_size=1
    bot.pool = await asyncpg.create_pool(database="pippobot_db", user=creds['username'], password=creds['password'], host=creds['host'], max_size=1, min_size=1)


async def store_command(message):
    ctx = await bot.get_context(message)
    if ctx.invoked_with:
        anal = bot.db.analytics
        await anal.insert_command(ctx.command.name, ctx.message.guild.id, ctx.message.author.id) 
        await bot.db.coins.add_coins(ctx.author.id, command_name=ctx.command.name)
        if random.random() < 0.30 and bot.db.coins.commands_dict[ctx.command.name]['coins']!=0:
            await ctx.reply(f"You can get coins upon using commands now!\nYou got **{bot.db.coins.commands_dict[ctx.command.name]['coins']}** coins.")

@bot.event
async def on_message(message: discord.Message):
    if message.author == bot.user or message.author.bot:
        return
    try:
        await store_command(message)
    except:
        pass
    await bot.process_commands(message)


@bot.event
async def on_interaction(interaction):
    await bot.db.analytics.insert_command(interaction.data['name'], interaction.guild.id, interaction.user.id)

@bot.event
async def setup_hook():
    await load_cogs(bot, cogs)
    await bot.tree.sync()
    bot.pfp_url = bot.user.avatar.url
    await create_db_pool()
    if bot.production is True: 
        bot.topggpy = topgg.DBLClient(bot, os.environ['topgg'], autopost=True, post_shard_count=False)
    bot.db = DB(bot.pool)


async def main():
    async with bot:
        await bot.start(os.environ["tc_token"])


bot.remove_command('help')

asyncio.run(main())
