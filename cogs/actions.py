from runtime import run_blocking
import random

import discord
from discord.ext import commands

from views import KissConsentView, kiss_art_file


class Actions(commands.Cog):
    """Lightweight social actions."""

    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="kiss")
    async def kiss(self, ctx, user: discord.Member = None):
        """Send a recipient-controlled kiss request, or a friendly air-kiss."""
        actor = discord.utils.escape_markdown(ctx.author.display_name[:72]).replace("@", "@\u200b")
        if user is None:
            lines = (
                "blew a friendly air-kiss to the whole chat. 💌",
                "sent a tiny heart-shaped hello past the snack table. 💛",
                "launched a kiss into the chat; Pippo says catch it if you like. 🪽",
                "sent a friendly air-kiss with absolutely no pressure. 💋",
            )
            embed = discord.Embed(
                title="A little kiss for the chat",
                description=f"**{actor}** {random.choice(lines)}",
                color=discord.Color.fuchsia(),
            )
            artwork = await run_blocking(kiss_art_file, embed, "kiss-air")
            options = {"embed": embed, "allowed_mentions": discord.AllowedMentions.none()}
            if artwork:
                options["file"] = artwork
            await ctx.reply(**options)
            return

        if user.id == ctx.author.id:
            await ctx.reply(
                "A kiss request needs someone else to answer. Leave the target blank for a friendly air-kiss.",
                allowed_mentions=discord.AllowedMentions.none(),
            )
            return
        if user.bot:
            await ctx.reply(
                "Bots cannot answer a kiss request. Leave the target blank and Pippo will send an air-kiss instead.",
                allowed_mentions=discord.AllowedMentions.none(),
            )
            return

        recipient = discord.utils.escape_markdown(user.display_name[:72]).replace("@", "@\u200b")

        def render_result(decision):
            if decision == "accepted":
                title = "A friendly kiss was accepted 💛"
                description = f"**{recipient}** accepted **{actor}**'s little greeting. Pippo sends a heart-shaped hello."
            elif decision == "declined":
                title = "Request passed 🙌"
                description = f"**{recipient}** passed on **{actor}**'s greeting. Pippo sends a cheerful wave instead."
            elif decision == "expired":
                title = "The greeting request expired"
                description = f"**{recipient}** didn't answer in time, so the request closed quietly. No kiss was sent."
            else:
                title = "A little greeting request"
                description = f"**{actor}** would like to send **{recipient}** a friendly kiss. Only {recipient} can choose."
            embed = discord.Embed(title=title, description=description, color=discord.Color.fuchsia())
            artwork = kiss_art_file(embed, f"kiss-{decision}")
            return embed, artwork

        view = KissConsentView(user.id, render_result)
        embed, artwork = await run_blocking(render_result, "pending")
        options = {
            "embed": embed,
            "view": view,
            "allowed_mentions": discord.AllowedMentions.none(),
        }
        if artwork:
            options["file"] = artwork
        view.message = await ctx.reply(**options)


async def setup(bot):
    await bot.add_cog(Actions(bot))
