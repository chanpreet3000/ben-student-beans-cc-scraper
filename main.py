import asyncio

from DatabaseManager import DatabaseManager
from discord_bot import run_bot
from Logger import Logger


async def main():
    db = DatabaseManager()
    try:
        run_bot()
    except Exception as e:
        Logger.critical("Fatal error", e)
    finally:
        db.close()
        Logger.info("Exiting...")


if __name__ == '__main__':
    asyncio.run(main())
