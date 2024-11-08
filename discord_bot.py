import os

import discord
from discord import app_commands

from CouponCodeScraper import CouponCodeScraper
from Logger import Logger
from dotenv import load_dotenv
from discord.ext import tasks
from DatabaseManager import DatabaseManager
from utils import get_current_time, notify_users

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


@client.tree.command(name="sb-get-unused-coupon-codes", description="Get a list of unused coupon codes")
async def get_unused_coupon_codes(interaction: discord.Interaction, total_codes: int):
    Logger.info("Received request to get unused coupon codes")
    await interaction.response.defer(thinking=True)

    try:
        codes = client.db.get_unused_coupon_codes(total_codes)
        if codes:
            # Prepare the coupon codes to be sent in DM
            coupon_codes_text = '\n'.join([code.code for code in codes])
            coupon_codes_length = len(codes)

            # Send the coupon codes in a DM
            await interaction.user.send(
                f"Here are **{coupon_codes_length}** unused coupon codes:\n```\n{coupon_codes_text}\n```")

            embed = discord.Embed(
                title="🎟️ Unused Coupon Codes",
                description=f"I've sent you {coupon_codes_length} unused coupon codes via DM.",
                color=0x00ccff
            )
        else:
            embed = discord.Embed(
                title="🎟️ Unused Coupon Codes",
                description="There are no unused coupon codes available at the moment.",
                color=0xffcc00
            )
    except Exception as e:
        Logger.error('Error getting unused coupon codes:', e)
        embed = discord.Embed(
            title="❌ Error",
            description=f"An error occurred while fetching the unused coupon codes.\n{str(e)}",
            color=0xff0000
        )

    await interaction.followup.send(embed=embed)


@client.tree.command(name="sb-coupon-codes-count", description="Get the count of unused coupon codes")
async def coupon_codes_count(interaction: discord.Interaction):
    Logger.info("Received coupon codes count request")
    await interaction.response.defer(thinking=True)

    try:
        unused_count = client.db.get_unused_coupon_codes_count()
        embed = discord.Embed(
            title="🎟️ Coupon Codes Count",
            description=f"**Unused Coupon Codes:** {unused_count}",
            color=0x00ccff
        )
    except Exception as e:
        Logger.error('Error getting coupon codes count:', e)
        embed = discord.Embed(
            title="❌ Error",
            description=f"An error occurred while getting the coupon codes count.\n{str(e)}",
            color=0xff0000
        )

    await interaction.followup.send(embed=embed)


@tasks.loop(seconds=cron_interval)
async def cron_job():
    Logger.info("Starting scheduled stock check")
    scraper = CouponCodeScraper()
    await scraper.start()
    unused_count = client.db.get_unused_coupon_codes_count()
    embed = discord.Embed(
        title="Scheduled Stock Check Complete",
        color=discord.Color.green()
    )
    embed.add_field(name="Total Unused Coupon Codes", value=str(unused_count), inline=False)
    embed.set_footer(text=f"Completed on {get_current_time()} (UK Time)")
    await notify_users(
        client=client,
        message=f"Stock check completed",
        embed=embed
    )
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
