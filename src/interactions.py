# src/interactions.py
"""Interactions class and interaction handler functions"""

import logging.config
import os

from dotenv import load_dotenv
from pprint import pformat

from gateway import GatewayMessage
from discord_api import DiscordApi

load_dotenv()

log = logging.getLogger(__name__)

APP_ID = os.getenv('APP_ID')

MAX_LEN_EMBED_FIELD_VAL = 1024

class Interaction:
    """Discord interactions class"""
    name: str
    id: str
    token: str
    discord_id: str
    discord_name: str
    guild_id: str
    endpoint: str
    options: dict

    def __init__(self, msg: GatewayMessage):
        self.log = logging.getLogger(f"{self.__module__}.{self.__class__.__name__}")
        self.log.debug("Initializing Interaction.")
        self.name = msg.data['data']['name']
        self.id = msg.data['id']
        self.token = msg.data['token']
        self.discord_id = msg.data['member']['user']['id']
        self.discord_name = msg.data['member']['user']['username']
        self.guild_id = msg.data['guild_id']

        # interaction response endpoint
        self.endpoint = f"interactions/{self.id}/{self.token}/callback"

        # add user inputs from slash command
        self.options = {}
        if 'options' in msg.data['data'].keys():
            for d in msg.data['data']['options']:
                self.options[d['name']] = d['value']


async def interact(discord_api: DiscordApi, msg: GatewayMessage) -> str:
    """Redirects discord interactions to call appropriate function. Returns function name."""
    log.debug(f"Interact redirecting msg: {pformat(msg)}")

    ix = Interaction(msg)

    await discord_api.ack_interaction(ix)  # acknowledge interaction with deferred response
    await discord_api.edit_interaction_response(ix, 'Responding...')

    return ix.name
