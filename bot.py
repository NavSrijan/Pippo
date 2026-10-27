import asyncio
import asyncpg
import os
import datetime
import time
import random

import discord
from discord.ext import commands
import topgg
import json

from database import DB

#MY_GUILD = discord.Object(id=864085584691593216)
cogs = ['greetings', 'bollywood', 'settings', 'help', 'info', 'fun', 'animals', 'actions', 'economy', 'shop']


async def get_prefix(bot, message):
    """Returns the specific guild prefix"""
    if message.guild is None:
        return "."
    try:
        prefix = await bot.db.servers.fetch_prefix(message.guild.id)
        return prefix or "."
    except Exception:
        return "."

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
activity = discord.Activity(type=discord.ActivityType.listening, name=f"Maithili Thakur")
prefix = "."
bot = commands.Bot(command_prefix=get_prefix,
                   case_insensitive=True,
                   intents=intents,
                   status=discord.Status.online,
                   activity=activity,
                   help_command=None)

bot.prefix = prefix
bot.get_prefixx = get_prefix
bot.production = str(os.environ.get('production', 'False')).lower() in ('true', '1')

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
    try:
        thewhistler = bot.get_user(THEWHISTLER) or await bot.fetch_user(THEWHISTLER)
        if thewhistler:
            await thewhistler.send("Pippo Online")
    except Exception as e:
        print(f"Could not notify owner on ready: {e}")

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

creds = {
    'username': os.environ.get('database_username', ''),
    'password': os.environ.get('database_password', ''),
    'host': os.environ.get('db_host', '')
}
async def create_db_pool():
    #Remove max_size=1
    try:
        bot.pool = await asyncpg.create_pool(database="pippobot_db", user=creds['username'], password=creds['password'], host=creds['host'], max_size=1, min_size=1)
    except Exception as e:
        print(f"Database connection error: {e}")
        bot.pool = None


async def store_command(message):
    ctx = await bot.get_context(message)
    if ctx.invoked_with and ctx.command and getattr(bot, 'db', None):
        anal = bot.db.analytics
        guild_id = ctx.message.guild.id if ctx.message.guild else None
        await anal.insert_command(ctx.command.name, guild_id, ctx.message.author.id) 
        await bot.db.coins.add_coins(ctx.author.id, command_name=ctx.command.name)
        reward = bot.db.coins.commands_dict.get(ctx.command.name, {}).get('coins', 0)
        if random.random() < 0.30 and reward != 0:
            await ctx.reply(f"You can get coins upon using commands now!\nYou got **{reward}** coins.")

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
async def on_interaction(interaction: discord.Interaction):
    if interaction.type == discord.InteractionType.application_command and interaction.data and 'name' in interaction.data:
        guild_id = interaction.guild.id if interaction.guild else None
        try:
            if getattr(bot, 'db', None):
                await bot.db.analytics.insert_command(interaction.data['name'], guild_id, interaction.user.id)
        except Exception:
            pass

@bot.event
async def setup_hook():
    await create_db_pool()
    if bot.pool:
        bot.db = DB(bot.pool)
    await load_cogs(bot, cogs)
    await bot.tree.sync()
    bot.pfp_url = bot.user.display_avatar.url if bot.user else ""
    if bot.production is True and 'topgg' in os.environ: 
        bot.topggpy = topgg.DBLClient(bot, os.environ['topgg'], autopost=True, post_shard_count=False)


async def main():
    async with bot:
        await bot.start(os.environ["tc_token"])


if __name__ == "__main__":
    asyncio.run(main())
