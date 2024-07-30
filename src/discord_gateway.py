# src/gateway_protocols.py
"""
Extends the base Gateway class to handle Discord connection protocols, initiate handler
Explicitly handles all basic connection communications. All other messages go to handlers.
"""

import asyncio
import logging
import os
import sys
from dotenv import load_dotenv

from gateway import Gateway, GatewayMessage

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')

log = logging.getLogger(__name__)


class DiscordGateway(Gateway):
    """Extend DiscordGateway to handle discord interaction protocols"""
    _handlers: dict

    def __init__(self, token):
        self.log = logging.getLogger(f"{self.__module__}.{self.__class__.__name__}")
        self.log.debug("Initializing DiscordGateway.")
        super().__init__(token)
        self._handlers = {}
        engine = None
        self.zombie_countdown = None

    async def handle_message(self, msg: GatewayMessage):
        self.log.info(f"Handling discord gateway msg:")
        if isinstance(msg.data, dict):
            for k, v in msg.data.items():
                if isinstance(v, dict):
                    for key, val in v.items():
                        log.info(f"{key}: {val}")
                else:
                    log.info(f"{k}: {v}")
        '''
        handles basic connect/maintain messages with opcodes:
        op 1 = heartbeat, op 10 = hello, op 11 = ack
        '''

        if msg.op == 1:     # heartbeat
            hb = {"op": 1, "d": self._sequence}
            await self.send(hb)

        elif msg.op == 10:    # Hello

            # set heartbeat which runs in _ping_loop
            self._heartbeat = msg.data['heartbeat_interval'] / 1000
            self.log.debug(f"Set heartbeat to {self._heartbeat}")

            # create task to count down and reconnect if we don't receive op: 11 ack within hb*2
            self.zombie_countdown = asyncio.create_task(self.zombie_timer(self._heartbeat))

            id_json = {
                "op": 2,
                "d": {
                    "token": self._token,
                    "intents": 513,
                    "properties": {
                        "$os": sys.platform
                    },
                }
            }
            await self.send(id_json)

        elif msg.op == 11:    # if ack, cancel and restart zombie_countdown
            self.zombie_countdown.cancel()
            self.zombie_countdown = asyncio.create_task(self.zombie_timer(self._heartbeat))

        elif msg.op == 9:
            self.log.error("opcode 9 reconnect??")
            exit()

        # _handlers is a list of functions whose names are msg.name
        else:
            event = msg.name.lower()
            log.debug(f"Event: {event}")
            if event in self._handlers:
                await self._handlers[event](msg)
            else:
                log.debug(f'Unhandled event: {event}')

    def event(self, func):
        self.log.debug(f"Gateway_protocol adding function {func.__name__} to handlers.")
        self._handlers[func.__name__] = func


if __name__ == '__main__':

    g = DiscordGateway(BOT_TOKEN)

    @g.event
    async def ready(msg):
        print(f"session_id: {msg.data['session_id']}")
        print('ready')

    asyncio.run(g.run())
