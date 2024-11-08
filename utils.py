import discord
import pytz

from datetime import datetime
from DatabaseManager import DatabaseManager
from Logger import Logger

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 OPR/108.0.0.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Vivaldi/6.5.3206.63',
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 11.0; Win64; x64) Gecko/20100101 Firefox/109.0",
    "Mozilla/5.0 (Windows NT 10.0; WOW64) Gecko/20100101 Firefox/110.0",
    "Mozilla/5.0 (Windows NT 11.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.1587.57 Safari/537.36 Edg/110.0.1587.57",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.1661.54 Safari/537.36 Edg/111.0.1661.54"
]


def get_current_time():
    uk_tz = pytz.timezone('Europe/London')
    return datetime.now(uk_tz).strftime('%d %B %Y, %I:%M:%S %p %Z')


async def notify_users(client: discord.Client, message: str, embed: discord.Embed = None):
    try:
        Logger.info("Sending notifications to all channels")
        db_manager = DatabaseManager()
        channel_ids = db_manager.get_all_notification_channels()

        if not channel_ids:
            Logger.warn("No notification channels configured")
            return

        Logger.info(f"Attempting to send notifications to {len(channel_ids)} channels")

        for channel_id in channel_ids:
            try:
                channel = client.get_channel(int(channel_id))

                if not channel:
                    Logger.error(f"Could not find Discord channel with ID: {channel_id}")
                    continue

                Logger.info(f"Sending notification to channel {channel_id}")
                Logger.debug(f"Message content: {message[:100]}...")

                await channel.send(
                    content=message,
                    embed=embed if embed else None
                )
                Logger.info(f"Successfully sent notification to channel {channel_id}")
            except Exception as e:
                Logger.error(f"Error sending notification to channel {channel_id}", e)

        Logger.info("Finished sending notifications")
    except Exception as e:
        Logger.error("Critical error in notify_users", e)
        raise e
