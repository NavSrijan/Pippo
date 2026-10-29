import argparse
import asyncio
import discord
from discord.ext import commands
import os

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
prefix = "."
bot = commands.Bot(command_prefix=prefix, case_insensitive=True, intents=intents)

async def print_context_messages(guild_id: int, limit: int = 10):
    guild = bot.get_guild(guild_id)
    if not guild:
        print("Guild not found or bot is not in the guild.")
        return
    for channel in guild.text_channels:
        print(f"Channel: {channel.name}")
        try:
            messages = [msg async for msg in channel.history(limit=limit)]
        except Exception as e:
            print(f"  Could not read history: {e}")
            continue
        if not messages:
            print("  No messages found.")
            continue
        for msg in reversed(messages):
            author = getattr(msg.author, 'display_name', msg.author)
            print(f"  {author}: {msg.content}")
        print("---")

@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user}')
    import ipdb; ipdb.set_trace()
    guild_id = 1226237063050035250
    ids = [
    1133407839768027279,
    1077709130615246898,
    1150064766287626342,
    1070771954300235796,
     971097946772869171,
    1096008223569489980,
     528622324384137216,
    1100823244057104441,
     333949691962195969,
     959672696931762216,
    1106977812243554456,
    1022047444466417715,
    1083303088540098680,
    1106003373527945366,
     864085584691593216,
     715115710548017203,
    1226237063050035250
]

    # Print members
    for x in ids:
        guild = bot.get_guild(x)
        print(guild)

    exit()
    # if guild:
    #     print(f"Members in {guild.name}:")
    #     for member in guild.members:
    #         print(f"- {member.display_name} (ID: {member.id})")
    # else:
    #     print("Guild not found or bot is not in the guild.")
    await print_context_messages(guild_id, 300)

async def main():
    await bot.login(os.environ["pippo_token"])
    await bot.connect()

if __name__ == "__main__":
    asyncio.run(main())
