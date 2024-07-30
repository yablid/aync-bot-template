# src/discord_api.py

"""
gateway.py handles send, receive, and ping loops
discord_gateway.py handles connection protocols (heartbeat, pings, etc.) - basic opcodes
discord_api.py holds the methods for all the rest - fetching_msgs, dms, etc.
"""

import asyncio
import logging.config
import os
import requests
import time
from dotenv import load_dotenv

from pprint import pformat
from typing import List

from cfg.cfg import CFG

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
APP_ID = os.getenv("APP_ID")
DISCORD_API = CFG['apis']['discord']

log = logging.getLogger(__name__)


def handle_api_response(resp: requests.Response):
    """Checks response status, returns body as json."""
    log.debug(f"Handling discord api response...{resp} of type: {type(resp)}")

    if resp.status_code == 204:
        log.debug("Discord api returned 204 - all good, no content.")
        return
    try:
        log.debug(f"Response: {resp}")
        body = resp.json()
        if "errors" in body:
            raise Exception(f"{body}")
        if "message" in body:
            log.debug(f"Message: {body}")
        return body
    except Exception as e:
        log.error(f"Error of type {type(e)} handling Discord api response. {e}")
        return resp.text


class DiscordApi:
    """Handles all user commands from discord (i.e. not heartbeack, ack, etc)"""

    def __init__(self, token):
        self.log = logging.getLogger(f"{self.__module__}.{self.__class__.__name__}")
        self.log.info("Initializing DiscordApi.")
        self._token = token

    async def run(self, method: str, endpoint: str, _json=None):
        """Will receive 40060 from discord (interaction already acknowledged)
        If running both locally and remote
        """

        url = f"{DISCORD_API}/{endpoint}"

        headers = {"Authorization": f"Bot {self._token}"}

        # GET, POST, PATCH, DELETE
        try:
            self.log.debug(f"Sending {method} request to url {url}. _json: {_json}")
            # verbose logging - can remove or keep for debugging
            if _json:
                for key, val in _json.items():
                    log.debug(f"{key}: {val}")
            resp = getattr(requests, method.lower())(url, json=_json, headers=headers)

        except Exception as e:
            self.log.error(f"Exception in discord_api.run: {e}")
            self.log.error(f"Method: {method}, json: {_json}")
            raise

        return handle_api_response(resp)

    async def fetch_msgs_from_channel(
            self,
            channel_id: int,
            limit: int = None,
            before: str = None
    ) -> list:
        """
        Fetches messages from discord channel
        :param channel_id: channel to query
        :param limit: limit to receive (queries from now backwards)
        :param before: message id to get messages before
        :return:
        """
        endpoint = f"channels/{channel_id}/messages"

        # grab last message
        if limit:
            endpoint = endpoint + f"?limit={int(limit)}"

        if before:
            if '?limit' in endpoint:
                endpoint = endpoint + f"&before={before}"
            else:
                endpoint = endpoint + f"?before={before}"

        for i in range(10):

            r = await self.run("GET", endpoint)

            if isinstance(r, list):
                return r

            elif isinstance(r, dict):
                if 'message' in r.keys() and r['message'] == 'You are being rate limited.':
                    log.warning("Rate limited...")
                    rate_limit = r['retry_after']
                    time.sleep(rate_limit)
                    continue

        return []

    async def send_msg_to_channel(
            self,
            channel_id: int,
            content: str = None,
            embeds: List[dict] = None,
            components: List[dict] = None
    ):
        """Sends message to a discord channel"""
        endpoint = f"channels/{channel_id}/messages"
        _json = {"content": content, "embeds": embeds, "components": components}
        _json = {k: v for k, v in _json.items() if v is not None}
        self.log.debug(f"discord_api creating new message to channel: {endpoint}\n    JSON: {pformat(_json)}")
        r = await self.run("POST", endpoint, _json=_json)
        self.log.debug(f"send_msg_to_channel should return a message object...returning:\n    {r if r else 'nothing'}")
        return r

    async def edit_msg(self, channel_id, msg_id, content=None, embeds=None):
        """edit previously sent message"""

        if embeds is None:
            embeds = []
        elif isinstance(embeds, dict):
            embeds = [embeds]
        _json = {}
        if content:
            _json['content'] = content
        if embeds:
            _json['embeds'] = embeds
        endpoint = f'channels/{channel_id}/messages/{msg_id}'
        r = await self.run("PATCH", endpoint, _json=_json)
        return r

    async def answer_interaction_in_channel(self, endpoint, content='', embeds=None):
        """answer interaction directly in channel where received"""

        if embeds is None:
            embeds = []
        elif isinstance(embeds, dict):
            embeds = [embeds]

        _json = {
            "type": 4,
            "data": {
                "content": content,
                "embeds": embeds
            }
        }

        self.log.debug(f"Attempting to answer ix in channel with _json: {_json}")
        r = await self.run("POST", endpoint, _json=_json)

    async def ack_interaction(self, interaction):
        """Acknowledge interaction with type 5 deferred response"""
        _json = {"type": 5}
        r = await self.run("POST", interaction.endpoint, _json=_json)
        return r

    async def edit_interaction_response(self, interaction, content, embeds=None):
        """edit original response to interaction"""
        if embeds is None:
            embeds = []
        elif isinstance(embeds, dict):
            embeds = [embeds]

        endpoint = f"webhooks/{APP_ID}/{interaction.token}/messages/@original"

        _json = {"content": content, "embeds": embeds}  # up to 10 embeds
        r = await self.run("PATCH", endpoint, _json=_json)
        return r

    async def delete_msg(self, channel_id, msg_id):

        endpoint = f'channels/{channel_id}/messages/{msg_id}'

        r = await self.run("DELETE", endpoint)
        log.info(f"Attempted delete of msg_id: {msg_id}. Returned status_code {r.status_code}")


if __name__ == '__main__':
    api = DiscordApi(BOT_TOKEN)
    print(api._token)
    v = asyncio.run(api.run("GET", "/users/@me"))
    print(v)