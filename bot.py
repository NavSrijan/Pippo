"""Pippo's Discord entry point. Run from the repository root."""

import asyncio
import logging
import os
import random

import asyncpg
import discord
from discord.ext import commands

from config import database_options, env, production
from database import DB

log = logging.getLogger(__name__)
cogs = ['greetings', 'bollywood', 'play', 'settings', 'help', 'info', 'fun', 'animals', 'actions', 'economy', 'shop']


async def get_prefix(bot, message):
    if message.guild is None:
        return "."
    try:
        return await bot.db.servers.fetch_prefix(message.guild.id) or "."
    except Exception:
        log.warning("Could not read guild prefix; using default")
        return "."


async def load_cogs(bot, extensions):
    for extension in extensions:
        # Fail startup rather than syncing a partially loaded command tree.
        await bot.load_extension('cogs.' + extension)
        log.info("Loaded %s", extension)


class PippoBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        super().__init__(
            command_prefix=get_prefix,
            case_insensitive=True,
            intents=intents,
            activity=discord.Activity(type=discord.ActivityType.listening, name="Maithili Thakur"),
            help_command=None,
            allowed_mentions=discord.AllowedMentions(everyone=False, roles=False, replied_user=False),
        )
        self.prefix = "."
        self.get_prefixx = get_prefix
        self.production = production()
        self.THEWHISTLER = int(env("BOT_OWNER_ID", default="302253506947973130"))
        self.owner_id = self.THEWHISTLER
        self.start_time = discord.utils.utcnow()
        self.pool = None
        self.topggpy = None
        self.pfp_url = ""

    async def setup_hook(self):
        self.pool = await asyncpg.create_pool(**database_options())
        self.db = DB(self.pool)
        await load_cogs(self, cogs)
        await self.tree.sync()
        self.pfp_url = self.user.display_avatar.url if self.user else ""
        topgg_token = env("TOPGG_TOKEN", "topgg")
        if self.production and topgg_token:
            import topgg
            self.topggpy = topgg.DBLClient(self, topgg_token, autopost=True, post_shard_count=False)

    async def close(self):
        try:
            if self.topggpy is not None:
                await self.topggpy.close()
                self.topggpy = None
        finally:
            try:
                await super().close()
            finally:
                if self.pool is not None:
                    await self.pool.close()
                    self.pool = None


bot = PippoBot()


@bot.before_invoke
async def acknowledge_slash_command(ctx):
    # Suggestion without text must open a modal as its first response.
    if ctx.interaction and ctx.command.name != "suggest":
        await ctx.defer()


@bot.event
async def on_ready():
    log.info("Logged in as %s", bot.user)


@bot.event
async def on_command_completion(ctx):
    """Reward successful commands consistently for prefix, slash, and menu calls."""
    if not getattr(bot, "db", None):
        return
    try:
        guild_id = ctx.guild.id if ctx.guild else None
        await bot.db.analytics.insert_command(ctx.command.qualified_name, guild_id, ctx.author.id)
        await bot.db.coins.add_coins(ctx.author.id, command_name=ctx.command.name)
        reward = bot.db.coins.commands_dict.get(ctx.command.name, {}).get('coins', 0)
        if reward and random.random() < 0.30:
            await ctx.send(f"You earned **{reward}** coins.")
    except Exception:
        log.exception("Could not record completed command")


async def main():
    token = env("DISCORD_TOKEN", "tc_token")
    if not token:
        raise RuntimeError("Set DISCORD_TOKEN (or the legacy tc_token) before starting Pippo")
    async with bot:
        await bot.start(token)


if __name__ == "__main__":
    logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
    asyncio.run(main())
