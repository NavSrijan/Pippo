import logging

from discord.ext import commands
from views import HelpView
import discord

class Help(commands.Cog):
    """Help"""

    def __init__(self, bot):
        self.bot = bot

    async def main_help_message(self, ctx):
        """Interactive category-based modern help message"""
        if ctx.message:
            try:
                prefix = await self.bot.get_prefixx(self.bot, ctx.message)
            except Exception:
                prefix = getattr(self.bot, 'prefix', '.')
        else:
            prefix = getattr(self.bot, 'prefix', '.')

        view = HelpView(bot=self.bot, author_id=ctx.author.id, prefix=prefix)
        emb = view.generate_embed("home")

        pfp = getattr(self.bot, 'pfp_url', None)
        if not pfp and self.bot.user:
            pfp = self.bot.user.display_avatar.url
        if pfp:
            emb.set_thumbnail(url=pfp)

        msg = await ctx.send(embed=emb, view=view)
        view.message = msg

    async def help_for_command(self, ctx, command):
        """Help for a particular command"""
        cmd = self.bot.get_command(command)
        if cmd is None:
            cmd = next(
                (candidate for candidate in self.bot.walk_commands()
                 if command.lower() in {candidate.name.lower(), *(alias.lower() for alias in candidate.aliases)}),
                None,
            )

        if cmd is None:
            emb = discord.Embed(title="Command Not Found",
                                description=f"Could not find a command named `{command}`.",
                                color=discord.Color.red())
        else:
            prefix = getattr(ctx, "prefix", None) or getattr(self.bot, "prefix", ".")
            suffix = f" {cmd.signature}" if cmd.signature else ""
            usage = f"`{prefix}{cmd.qualified_name}{suffix}`"
            emb = discord.Embed(
                title=f"/{cmd.qualified_name} · {prefix}{cmd.qualified_name}",
                description=cmd.help or "No description provided.",
                color=discord.Color.green(),
            )
            emb.add_field(name="Usage", value=usage, inline=False)
            aliases = getattr(cmd, "aliases", [])
            if aliases:
                emb.add_field(name="Aliases", value=", ".join(f"`{alias}`" for alias in aliases), inline=False)

        try:
            prefix = await self.bot.get_prefixx(self.bot, ctx.message) if ctx.message else getattr(self.bot, "prefix", ".")
        except Exception:
            prefix = getattr(self.bot, "prefix", ".")
        await ctx.send(embed=emb, view=HelpView(bot=self.bot, author_id=ctx.author.id, prefix=prefix))

    @commands.hybrid_command(name="help")
    async def help(self, ctx, command: str = None):
        """Interactive help menu or details for a specific command"""
        if command is None:
            await self.main_help_message(ctx)
        else:
            await self.help_for_command(ctx, command)

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if ctx.command and ctx.command.has_error_handler():
            return
        if isinstance(error, commands.CommandNotFound):
            return
        if isinstance(error, commands.MaxConcurrencyReached):
            await ctx.send("A game is already running in this channel. Wait for it to finish or try again later.", view=HelpView(bot=self.bot, author_id=ctx.author.id, prefix=getattr(ctx, "prefix", ".")))
        elif isinstance(error, (commands.MissingRequiredArgument, commands.BadArgument, commands.TooManyArguments)):
            command_name = ctx.command.qualified_name if ctx.command else "command"
            prefix = getattr(ctx, "prefix", ".")
            await ctx.send(f"I couldn't read those options. Use `{prefix}help {command_name}` or `/help {command_name}` to see the correct format.")
        elif isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"Please try again in {error.retry_after:.1f} seconds.")
        elif isinstance(error, commands.CheckFailure):
            await ctx.send("You cannot use this command here.")
        else:
            original = getattr(error, "original", error)
            logging.getLogger(__name__).error("Command failed", exc_info=(type(original), original, original.__traceback__))
            await ctx.send("Something went wrong. Please try again later.")


async def setup(bot):
    await bot.add_cog(Help(bot))
