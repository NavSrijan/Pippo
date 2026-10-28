import datetime
import io
import platform
import discord
from discord.ext import commands


def is_bot_owner():
    """Ensure only the configured bot owner can execute admin/analytics commands."""
    async def predicate(ctx):
        whistler_id = getattr(ctx.bot, "THEWHISTLER", None)
        if whistler_id and ctx.author.id == whistler_id:
            return True
        try:
            return await ctx.bot.is_owner(ctx.author)
        except Exception:
            return False
    return commands.check(predicate)


class Info(commands.Cog):
    """Commands for analytics, server tracking, and bot diagnostics."""

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        try:
            thewhistler = self.bot.get_user(self.bot.THEWHISTLER) or await self.bot.fetch_user(self.bot.THEWHISTLER)
            if thewhistler:
                await thewhistler.send(f"Pippo joined server: **{guild.name}** (`{guild.id}`)")
        except Exception as e:
            print(f"Could not notify owner of guild join: {e}")

        try:
            if hasattr(self.bot, "db") and hasattr(self.bot.db, "servers"):
                prefix = getattr(self.bot, "prefix", ".")
                if hasattr(self.bot.db.servers, "ensure_server"):
                    await self.bot.db.servers.ensure_server(guild.id, prefix)
                else:
                    await self.bot.db.servers.prefix_add(guild.id, prefix)
        except Exception as e:
            print(f"Could not register prefix for new guild: {e}")

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        """Silently ignore unauthorized usage of hidden owner commands."""
        if ctx.cog is not self:
            return
        if isinstance(error, (commands.NotOwner, commands.CheckFailure)):
            return

    # -------------------------------------------------------------------------
    # 1. Server List & Export
    # -------------------------------------------------------------------------
    @commands.command(name="servers", aliases=["guilds", "serverlist"], hidden=True)
    @is_bot_owner()
    async def servers(self, ctx):
        """Owner command: Generates a complete report of all connected servers and DMs it."""
        guilds = sorted(self.bot.guilds, key=lambda g: g.member_count or 0, reverse=True)
        total_guilds = len(guilds)
        total_members = sum(g.member_count or 0 for g in guilds)
        avg_members = round(total_members / total_guilds, 1) if total_guilds else 0

        now_utc = discord.utils.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        report_lines = [
            "=" * 90,
            "PIPPO CONNECTED SERVERS REPORT",
            f"Generated: {now_utc}",
            f"Total Servers: {total_guilds} | Total Cached Members: {total_members:,} | Avg Members/Server: {avg_members}",
            "=" * 90,
            "",
            f"{'#':<4} {'Members':<9} {'Server ID':<20} {'Server Name':<34} {'Owner'}",
            "-" * 90,
        ]

        for idx, g in enumerate(guilds, 1):
            owner_info = f"{g.owner} ({g.owner_id})" if g.owner else str(g.owner_id)
            report_lines.append(f"{idx:<4} {g.member_count or 0:<9} {g.id:<20} {g.name[:32]:<34} {owner_info}")

        report_content = "\n".join(report_lines)
        file = discord.File(
            io.StringIO(report_content),
            filename=f"pippo_servers_{datetime.date.today()}.txt"
        )

        embed = discord.Embed(
            title="🌐 Connected Servers Summary",
            description=f"Pippo is currently connected to **{total_guilds}** servers with **{total_members:,}** total members.",
            color=discord.Color.blue(),
            timestamp=discord.utils.utcnow(),
        )
        if guilds:
            largest = guilds[0]
            embed.add_field(
                name="Largest Server",
                value=f"**{largest.name}**\n`{largest.member_count:,}` members",
                inline=True
            )
            smallest = guilds[-1]
            embed.add_field(
                name="Smallest Server",
                value=f"**{smallest.name}**\n`{smallest.member_count:,}` members",
                inline=True
            )
            embed.add_field(
                name="Average Server Size",
                value=f"`{avg_members}` members",
                inline=True
            )
        embed.set_footer(text="Complete breakdown attached as servers.txt")

        try:
            await ctx.author.send(embed=embed, file=file)
            if ctx.guild:
                try:
                    await ctx.message.add_reaction("📬")
                except Exception:
                    pass
        except discord.Forbidden:
            await ctx.reply("⚠️ Could not DM you (DMs are closed). Sending here instead:", embed=embed, file=file)

    # -------------------------------------------------------------------------
    # 2. Analytics & Bot Metrics
    # -------------------------------------------------------------------------
    @commands.command(name="analytics", aliases=["stats", "botstats", "botanalytics"], hidden=True)
    @is_bot_owner()
    async def analytics(self, ctx):
        """Owner command: View overall bot usage and system statistics."""
        summary = {}
        top_commands = []
        if hasattr(self.bot, "db") and hasattr(self.bot.db, "analytics"):
            try:
                summary = await self.bot.db.analytics.get_summary_stats()
                top_commands = await self.bot.db.analytics.get_top_commands(limit=5)
            except Exception as e:
                print(f"Error fetching analytics: {e}")

        # Calculate Uptime
        start_time = getattr(self.bot, "start_time", None)
        if start_time:
            uptime_delta = discord.utils.utcnow() - start_time
            days = uptime_delta.days
            hours, remainder = divmod(uptime_delta.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            uptime_str = f"{days}d {hours}h {minutes}m {seconds}s"
        else:
            uptime_str = "Unknown"

        total_guilds = len(self.bot.guilds)
        total_members = sum(g.member_count or 0 for g in self.bot.guilds)
        latency_ms = round(self.bot.latency * 1000, 1)

        embed = discord.Embed(
            title="📊 Pippo Analytics & Overview",
            color=discord.Color.green(),
            timestamp=discord.utils.utcnow()
        )

        tot_cmds = summary.get("total_commands", 0)
        c24h = summary.get("commands_24h", 0)
        c7d = summary.get("commands_7d", 0)
        dms = summary.get("dm_commands", 0)
        embed.add_field(
            name="📈 Command Activity",
            value=(
                f"• **All-time:** `{tot_cmds:,}` commands\n"
                f"• **Last 24h:** `{c24h:,}`\n"
                f"• **Last 7d:** `{c7d:,}`\n"
                f"• **Direct Messages:** `{dms:,}`"
            ),
            inline=True,
        )

        unique_users = summary.get("unique_users", 0)
        db_servers = summary.get("unique_servers", 0)
        embed.add_field(
            name="👥 Reach & Database",
            value=(
                f"• **Live Guilds:** `{total_guilds}`\n"
                f"• **Cached Members:** `{total_members:,}`\n"
                f"• **Active Users (DB):** `{unique_users:,}`\n"
                f"• **Active Servers (DB):** `{db_servers:,}`"
            ),
            inline=True,
        )

        if top_commands:
            top_str = "\n".join(
                f"`{idx}.` **{cmd[0] if isinstance(cmd, (tuple, list)) else cmd['command']}**: "
                f"`{cmd[1] if isinstance(cmd, (tuple, list)) else cmd['count']:,}`"
                for idx, cmd in enumerate(top_commands, 1)
            )
        else:
            top_str = "No command data logged yet."
        embed.add_field(name="🔥 Top 5 Commands", value=top_str, inline=False)

        embed.add_field(
            name="⚙️ System & Runtime",
            value=(
                f"• **Ping:** `{latency_ms} ms`\n"
                f"• **Uptime:** `{uptime_str}`\n"
                f"• **discord.py:** `v{discord.__version__}`\n"
                f"• **Python:** `v{platform.python_version()}`"
            ),
            inline=False,
        )

        await ctx.send(embed=embed)

    # -------------------------------------------------------------------------
    # 3. Top Commands Breakdown
    # -------------------------------------------------------------------------
    @commands.command(name="topcommands", aliases=["topcmd"], hidden=True)
    @is_bot_owner()
    async def topcommands(self, ctx, days: int = None, limit: int = 10):
        """Owner command: View top commands executed overall or in the last N days."""
        if not hasattr(self.bot, "db") or not hasattr(self.bot.db, "analytics"):
            await ctx.send("Database analytics are not available.")
            return

        limit = max(1, min(limit, 25))
        top = await self.bot.db.analytics.get_top_commands(limit=limit, days=days)
        if not top:
            time_msg = f" in the last {days} days" if days else ""
            await ctx.send(f"No command usage records found{time_msg}.")
            return

        total_in_sample = sum(cmd[1] if isinstance(cmd, (tuple, list)) else cmd["count"] for cmd in top)
        timeframe = f"Last {days} Days" if days else "All Time"

        lines = []
        for idx, record in enumerate(top, 1):
            name = record[0] if isinstance(record, (tuple, list)) else record["command"]
            count = record[1] if isinstance(record, (tuple, list)) else record["count"]
            pct = (count / total_in_sample * 100) if total_in_sample else 0
            lines.append(f"`{idx:2d}.` **{name}**: `{count:,}` ({pct:.1f}%)")

        embed = discord.Embed(
            title=f"🏆 Top {len(top)} Commands ({timeframe})",
            description="\n".join(lines),
            color=discord.Color.gold(),
            timestamp=discord.utils.utcnow()
        )
        await ctx.send(embed=embed)

    # -------------------------------------------------------------------------
    # 4. Server Details & Stats
    # -------------------------------------------------------------------------
    @commands.command(name="serverinfo", aliases=["guildinfo"], hidden=True)
    @is_bot_owner()
    async def serverinfo(self, ctx, guild_id: int = None):
        """Owner command: Inspect details and analytics for a specific server."""
        target_id = guild_id or (ctx.guild.id if ctx.guild else None)
        if not target_id:
            await ctx.send("Please provide a server ID (e.g. `.serverinfo 123456789`).")
            return

        guild = self.bot.get_guild(target_id)
        if guild is None:
            try:
                guild = await self.bot.fetch_guild(target_id)
            except Exception:
                guild = None

        if guild is None:
            await ctx.send(f"Could not find guild with ID `{target_id}` in bot cache or via API.")
            return

        prefix = "."
        if hasattr(self.bot, "db") and hasattr(self.bot.db, "servers"):
            try:
                prefix = await self.bot.db.servers.fetch_prefix(guild.id)
            except Exception:
                pass

        server_stats = {"total_commands": 0, "top_commands": []}
        if hasattr(self.bot, "db") and hasattr(self.bot.db, "analytics"):
            try:
                server_stats = await self.bot.db.analytics.get_server_stats(guild.id)
            except Exception:
                pass

        embed = discord.Embed(
            title=f"Server Details: {guild.name}",
            color=discord.Color.purple(),
            timestamp=discord.utils.utcnow()
        )
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)

        owner_str = f"{guild.owner} (`{guild.owner_id}`)" if guild.owner else str(guild.owner_id)
        created_at = guild.created_at.strftime("%Y-%m-%d") if hasattr(guild, "created_at") and guild.created_at else "Unknown"

        embed.add_field(name="Server ID", value=f"`{guild.id}`", inline=True)
        embed.add_field(name="Owner", value=owner_str, inline=True)
        embed.add_field(name="Created", value=created_at, inline=True)
        embed.add_field(name="Members", value=f"`{guild.member_count or 'Unknown':,}`" if isinstance(guild.member_count, int) else "Unknown", inline=True)
        embed.add_field(name="Prefix in DB", value=f"`{prefix}`", inline=True)
        embed.add_field(name="Commands Executed", value=f"`{server_stats['total_commands']:,}`", inline=True)

        if server_stats["top_commands"]:
            top_cmds = "\n".join(
                f"• **{r[0] if isinstance(r, (tuple, list)) else r['command']}**: "
                f"`{r[1] if isinstance(r, (tuple, list)) else r['count']:,}`"
                for r in server_stats["top_commands"]
            )
            embed.add_field(name="Top Commands in Server", value=top_cmds, inline=False)

        await ctx.send(embed=embed)

    # -------------------------------------------------------------------------
    # 5. Database Sync
    # -------------------------------------------------------------------------
    @commands.command(name="syncservers", hidden=True)
    @is_bot_owner()
    async def syncservers(self, ctx):
        """Owner command: Syncs all currently connected Discord guilds into the database."""
        if not hasattr(self.bot, "db") or not hasattr(self.bot.db, "servers"):
            await ctx.send("Database servers table is not accessible.")
            return

        existing = set()
        try:
            all_servers = await self.bot.db.servers.get_all_servers()
            existing = {r["server_id"] if hasattr(r, "get") else r[0] for r in all_servers}
        except Exception as e:
            print(f"Could not read existing servers: {e}")

        added_count = 0
        default_prefix = getattr(self.bot, "prefix", ".")
        for guild in self.bot.guilds:
            if guild.id not in existing:
                try:
                    await self.bot.db.servers.ensure_server(guild.id, default_prefix)
                    added_count += 1
                except Exception as e:
                    print(f"Error syncing guild {guild.id}: {e}")

        await ctx.send(
            f"✅ **Server Sync Complete!**\n"
            f"• Connected Discord Guilds: **{len(self.bot.guilds)}**\n"
            f"• Previously in Database: **{len(existing)}**\n"
            f"• Newly Added: **{added_count}**\n"
            f"• Total Now in Database: **{len(existing) + added_count}**"
        )


async def setup(bot):
    await bot.add_cog(Info(bot))
