from typing import Literal
from enum import Enum
import datetime

from discord.ext import commands, tasks
from views import HelpView
import discord

from utils.bollywood_utils import game_start_embed, pixelate_game_start_embed, plotster_game_start_embed, create_instructions_embed

class Help(commands.Cog):
    """Help"""

    def __init__(self, bot):
        self.bot = bot

    async def main_help_message(self,
                                ctx,
                                cogs_to_show_help_for=['settings', 'games', 'fun', 'greetings', 'help', 'actions', 'animals', 'economy', 'shop']):
        """Main help"""
        desc = ""
        emb = discord.Embed(title="Help",
                            description=desc,
                            color=discord.Color.gold())
        for cog in self.bot.cogs:
            fill = ""
            if cog.lower() in cogs_to_show_help_for:
                cog_obj = self.bot.get_cog(cog)
                if cog_obj:
                    for cmd in cog_obj.get_commands():
                        if not cmd.hidden:
                            fill += "`" + cmd.name + "` "
                    if fill:
                        fill = fill.strip() + "\n"
                        emb.add_field(name=cog, value=fill, inline=False)
        if ctx.message:
            try:
                prefix = await self.bot.get_prefixx(self.bot, ctx.message)
            except Exception:
                prefix = getattr(self.bot, 'prefix', '.')
        else:
            prefix = getattr(self.bot, 'prefix', '.')

        desc += f"\nFor more info about a command use `{prefix}help <command>`."
        emb.description = desc
        emb.set_footer(text="~TheWhistler")
        pfp = getattr(self.bot, 'pfp_url', None)
        if not pfp and self.bot.user:
            pfp = self.bot.user.display_avatar.url
        if pfp:
            emb.set_thumbnail(url=pfp)
        await ctx.send(embed=emb, view=HelpView())

    def embed_for_commands(self, command):
        """Embed for a particular command"""
        name = command.name
        if name == "bollywood":
            return game_start_embed("bollywood", help_mode=True)
        elif name == "hollywood":
            return game_start_embed("hollywood", help_mode=True)
        elif name == "plotster":
            return plotster_game_start_embed(help_mode=True)
        elif name == "quizster":
            return create_instructions_embed(help_mode=True)
        elif name == "poster":
            return pixelate_game_start_embed(help_mode=True)

        return None


    async def help_for_command(self, ctx, command):
        """Help for a particular command"""
        emb = None
        for cmd in self.bot.commands:
            if command == cmd.name or command in cmd.aliases:
                emb = self.embed_for_commands(cmd)
                if emb is None:
                    emb = discord.Embed(title=cmd.name,
                                        description=cmd.help or "No description provided.",
                                        color=discord.Color.green())
                break

        if emb is None:
            emb = discord.Embed(title="Command Not Found",
                                description=f"Could not find a command named `{command}`.",
                                color=discord.Color.red())

        await ctx.send(embed=emb, view=HelpView())

    @commands.hybrid_command(name="help")
    async def help(self, ctx, command=None):
        """Shows help"""

        if command is None:
            await self.main_help_message(ctx)
        elif command.lower() in [word.lower() for word in self.bot.cogs]:
            await self.main_help_message(
                ctx, cogs_to_show_help_for=[command.lower()])
        else:
            await self.help_for_command(ctx, command)

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.MaxConcurrencyReached):
            await ctx.send("An instance is already running.", view=HelpView())


async def setup(bot):
    await bot.add_cog(Help(bot))
