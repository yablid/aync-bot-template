"""entry point"""
import asyncio
import logging
import os
import sys

from dotenv import load_dotenv

import interactions
from discord_gateway import DiscordGateway
from discord_api import DiscordApi

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')

log = logging.getLogger(__name__)

# log to stdout
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logging.getLogger().addHandler(handler)
logging.getLogger().setLevel(logging.DEBUG)


class Bot:
    gateway: DiscordGateway
    discord_api: DiscordApi

    def __init__(self, token=BOT_TOKEN):
        self.log = logging.getLogger(f"{self.__module__}.{self.__class__.__name__}")
        self.log.info("Initializing bot.")
        self.gateway = DiscordGateway(token)
        self.discord_api = DiscordApi(BOT_TOKEN)

    async def run_gateway(self):
        """Set up aiohttp and queues via gateway class and discord_gateway class extension"""
        await self.gateway.run()

    def discord_event(self, func):
        """Wrapper to add functions to DiscordGateway for handling interactions"""
        self.log.debug(f"Wrapping DiscordGateway event handler. func.__name__: {func.__name__}")
        return self.gateway.event(func)


async def start_bot(token):
    bot = Bot(token)

    @bot.discord_event
    async def ready(msg):
        bot.gateway._session_id = msg.data['session_id']
        bot.log.debug("Received READY from Discord")

    @bot.discord_event
    async def message_create(msg):
        log.debug(f"Read message with id {msg.data['channel_id']} and content {msg.data['content']}.")

    @bot.discord_event
    async def interaction_create(msg):
        await interactions.interact(bot.discord_api, msg)

    log.debug("Calling run_gateway...")
    await asyncio.gather(bot.run_gateway())


if __name__ == '__main__':
    print("Starting bot...")
    asyncio.run(start_bot(BOT_TOKEN))
