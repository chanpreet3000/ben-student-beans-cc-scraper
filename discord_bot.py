import os
from datetime import datetime

import discord
from discord import app_commands

from CouponCodeScraper import CouponCodeScraper
from Logger import Logger
from dotenv import load_dotenv
from discord.ext import tasks
from DatabaseManager import DatabaseManager

load_dotenv()

cron_interval = int(os.getenv('CRON_INTERVAL', 60 * 60))  # 1 hour


class Bot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)
        self.db = DatabaseManager()

    async def setup_hook(self):
        await self.tree.sync()
        Logger.info("Command tree synced")


client = Bot()


@client.tree.command(name="sb-add-channel", description="Add a notification channel")
@app_commands.checks.has_permissions(administrator=True)
async def add_channel(interaction: discord.Interaction, channel: discord.TextChannel):
    Logger.info(f"Received add channel request for channel ID: {channel.id}")
    await interaction.response.defer(thinking=True)

    try:
        if client.db.add_discord_channel(str(channel.id)):
            embed = discord.Embed(
                title="✅ Channel Added",
                description=f"Added {channel.mention} to notification channels.",
                color=0x00ff00
            )
        else:
            embed = discord.Embed(
                title="⚠️ Already Added",
                description=f"{channel.mention} is already a notification channel.",
                color=0xffcc00
            )
    except Exception as e:
        Logger.error('Error adding channel:', e)
        embed = discord.Embed(
            title="❌ Error",
            description=f"An error occurred while adding the channel.\n{str(e)}",
            color=0xff0000
        )

    await interaction.followup.send(embed=embed)


@client.tree.command(name="sb-remove-channel", description="Remove a notification channel")
@app_commands.checks.has_permissions(administrator=True)
async def remove_channel(interaction: discord.Interaction, channel: discord.TextChannel):
    Logger.info(f"Received remove channel request for channel ID: {channel.id}")
    await interaction.response.defer(thinking=True)

    try:
        if client.db.remove_discord_channel(str(channel.id)):
            embed = discord.Embed(
                title="✅ Channel Removed",
                description=f"Removed {channel.mention} from notification channels.",
                color=0x00ff00
            )
        else:
            embed = discord.Embed(
                title="⚠️ Not Found",
                description=f"{channel.mention} was not a notification channel.",
                color=0xffcc00
            )
    except Exception as e:
        Logger.error('Error removing channel:', e)
        embed = discord.Embed(
            title="❌ Error",
            description=f"An error occurred while removing the channel.\n{str(e)}",
            color=0xff0000
        )

    await interaction.followup.send(embed=embed)


@client.tree.command(name="sb-list-channels", description="Show all notification channels")
async def list_channels(interaction: discord.Interaction):
    Logger.info("Received list channels request")
    await interaction.response.defer(thinking=True)

    try:
        channels = client.db.get_all_notification_channels()
        if channels:
            channel_mentions = []
            for channel_id in channels:
                channel = client.get_channel(int(channel_id))
                if channel:
                    channel_mentions.append(f"• {channel.mention}")
                else:
                    channel_mentions.append(f"• Unknown Channel (ID: {channel_id})")

            embed = discord.Embed(
                title="📋 Notification Channels",
                description="\n".join(channel_mentions),
                color=0x00ccff
            )
        else:
            embed = discord.Embed(
                title="📋 Notification Channels",
                description="No notification channels are configured.",
                color=0xffcc00
            )
    except Exception as e:
        Logger.error('Error listing channels:', e)
        embed = discord.Embed(
            title="❌ Error",
            description=f"An error occurred while fetching the channel list.\n{str(e)}",
            color=0xff0000
        )

    await interaction.followup.send(embed=embed)


@client.tree.command(name="sb-list-codes", description="Show all unique & unexpired coupon codes")
async def list_codes(interaction: discord.Interaction):
    Logger.info("Received list codes request")
    await interaction.response.defer(thinking=True)

    try:
        codes = client.db.get_valid_coupon_codes()
        if codes:
            # Sort codes by expiry date
            sorted_codes = sorted(codes, key=lambda x: x.expiry)

            embed = discord.Embed(
                title="🎟️ Valid Coupon Codes",
                description="Here are the unique and unexpired coupon codes:",
                color=0x00ccff
            )

            for code in sorted_codes:
                # Convert expiry to human-readable format
                expiry_dt = datetime.fromisoformat(code.expiry)
                expiry_str = expiry_dt.strftime("%Y-%m-%d %H:%M:%S %Z")

                embed.add_field(
                    name=f"Code: {code.code}",
                    value=f"Expires: {expiry_str} (UTC)",
                    inline=False
                )

            embed.set_footer(text="All times are in UTC")
        else:
            embed = discord.Embed(
                title="🎟️ Valid Coupon Codes",
                description="There are no valid coupon codes at the moment.",
                color=0xffcc00
            )
    except Exception as e:
        Logger.error('Error listing codes:', e)
        embed = discord.Embed(
            title="❌ Error",
            description=f"An error occurred while fetching the coupon codes list.\n{str(e)}",
            color=0xff0000
        )

    await interaction.followup.send(embed=embed)


@tasks.loop(seconds=cron_interval)
async def cron_job():
    Logger.info("Starting scheduled stock check")
    scraper = CouponCodeScraper()
    await scraper.start()
    Logger.info(f"Scheduled stock check completed. Next run in {cron_interval} seconds.")


@client.event
async def on_ready():
    Logger.info(f"Bot is ready and logged in as {client.user}")
    cron_job.start()


def run_bot():
    token = os.getenv('DISCORD_BOT_TOKEN')
    if not token:
        raise ValueError("Discord bot token not found in environment variables")

    Logger.info("Starting bot...")
    client.run(token)
