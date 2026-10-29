from discord.ext import commands
from discord import app_commands
import discord

class Economy(commands.Cog):
    """Economy commands"""

    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="balance", aliases=["bal", "khazana", "money", "cash", "paisa", "rupya"])
    async def balance(self, ctx):
        """Check your coin balance in the treasury"""
        bal = await self.bot.db.coins.get_amount_coins(ctx.author.id)
        coins = bal.get('coins', 0) if isinstance(bal, dict) else (bal['coins'] if hasattr(bal, '__getitem__') else 0)
        emb = discord.Embed(
            title="🪙 Pippo Treasury",
            description=f"{ctx.author.mention}, you currently have **{coins:,}** coins.",
            color=discord.Color.gold()
        )
        emb.set_thumbnail(url=ctx.author.display_avatar.url)
        await ctx.reply(embed=emb)

    @commands.hybrid_command(name="add_coins", hidden=True)
    async def add_coins(self, ctx, user: discord.Member, coins: int = 0):
        """Add coins to a user (Owner only)"""
        if ctx.author.id == self.bot.THEWHISTLER:
            await self.bot.db.coins.add_coins(user.id, coins=coins)
            await ctx.reply(f"Added **{coins:,}** coins to {user.mention}.", ephemeral=True)
        else:
            await ctx.reply("You are not authorized to use this command.", ephemeral=True)

    @app_commands.describe(user="The member to send coins to", coins="Amount of coins to transfer")
    @commands.hybrid_command(name="send_coins")
    async def send_coins(self, ctx, user: discord.Member, coins: int = 0):
        """Transfer virtual Pippo coins to another member"""
        if coins <= 0:
            await ctx.reply("You must send at least 1 coin.", ephemeral=True)
            return
        if coins > 2_147_483_647:
            await ctx.reply("A single transfer cannot exceed 2,147,483,647 coins.", ephemeral=True)
            return
        if ctx.author.id == user.id:
            await ctx.reply("You cannot send coins to yourself.", ephemeral=True)
            return
        if user.bot:
            await ctx.reply("You cannot send coins to a bot.", ephemeral=True)
            return

        if not await self.bot.db.coins.transfer(ctx.author.id, user.id, coins):
            await ctx.reply("You don't have enough coins for that transfer.", ephemeral=True)
            return

        emb = discord.Embed(
            title="🪙 Transfer Successful",
            description=f"{ctx.author.mention} transferred **{coins:,}** coins to {user.mention}!",
            color=discord.Color.green()
        )
        await ctx.reply(embed=emb)


async def setup(bot):
    await bot.add_cog(Economy(bot))
