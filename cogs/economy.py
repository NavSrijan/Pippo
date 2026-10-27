from discord.ext import commands
import discord

class Economy(commands.Cog):
    """Economy commands"""

    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="balance", aliases=["bal", "khazana", "money", "cash", "paisa", "rupya"])
    async def balance(self, ctx):
        """How many coins do you have?"""
        bal = await self.bot.db.coins.get_amount_coins(ctx.author.id)
        coins = bal.get('coins', 0) if isinstance(bal, dict) else (bal['coins'] if hasattr(bal, '__getitem__') else 0)
        await ctx.reply(f"You have **{coins}** coins.")

    @commands.hybrid_command(name="add_coins", hidden=True)
    async def add_coins(self, ctx, user: discord.Member, coins: int = 0):
        """Add coins to a user (Owner only)"""
        if ctx.author.id == self.bot.THEWHISTLER:
            await self.bot.db.coins.add_coins(user.id, coins=coins)
            await ctx.reply(f"{coins} coins added to {user.mention}")
        else:
            await ctx.reply("You are not authorized to use this command.", ephemeral=True)

    @commands.hybrid_command(name="send_coins")
    async def send_coins(self, ctx, user: discord.Member, coins: int = 0):
        """Send coins to another user"""
        if coins <= 0:
            await ctx.reply("You must send at least 1 coin.")
            return
        if ctx.author.id == user.id:
            await ctx.reply("You cannot send coins to yourself.")
            return
        if user.bot:
            await ctx.reply("You cannot send coins to a bot.")
            return

        bal = await self.bot.db.coins.get_amount_coins(ctx.author.id)
        user_coins = bal.get('coins', 0) if isinstance(bal, dict) else bal['coins']
        if user_coins < coins:
            await ctx.reply(f"You don't have enough coins! You currently have **{user_coins}** coins.")
            return

        await self.bot.db.coins.deduct_coins(ctx.author.id, coins=coins)
        await self.bot.db.coins.add_coins(user.id, coins=coins)
        await ctx.reply(f"{ctx.author.mention} sent **{coins}** coins to {user.mention}!")


async def setup(bot):
    await bot.add_cog(Economy(bot))

