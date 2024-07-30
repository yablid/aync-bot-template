# src/gateway.py
"""Base gateway class to connect to websocket and establish async recv, send, ping loops"""

import aiohttp
import asyncio
import json
import logging
import os
from dotenv import load_dotenv

from dataclasses import dataclass
from cfg.cfg import CFG

load_dotenv()
URL = CFG['apis']['discord']

BOT_TOKEN = os.getenv('BOT_TOKEN')
APP_ID = os.getenv('APP_ID')

log = logging.getLogger(__name__)


@dataclass
class GatewayMessage:
    op: int
    data: dict
    sequence: int
    session_id: str = ''
    name: str = ''


async def parse_msg(msg: aiohttp.WSMessage) -> GatewayMessage:
    """Convert incoming message into GatewayMessage dataclass
    :param: incoming message
    """
    obj = json.loads(msg.data)
    op = obj['op']
    data = obj['d']
    sequence = obj['s']
    session_id = obj['session_id'] if 'session_id' in obj.keys() else ''
    name = obj['t'] if 't' in obj.keys() else ''

    return GatewayMessage(op, data, sequence, session_id, name)


class Gateway:
    """
    Base class for Discord Api: send, recieve, ping loops.
    Zombie timer can be invoked to fire an inactivity timer.
    Reconnect protocol (invoked by ping loop if zombie timer expires).
    """
    _token: str
    _q: asyncio.Queue
    _heartbeat: int
    _session_id: str
    _sequence: int or None
    gw_url: str
    _zombie: asyncio.Event

    def __init__(self, token):
        self.log = logging.getLogger(f"{self.__module__}.{self.__class__.__name__}")
        self.log.debug(f"Initializing Gateway with token {token[:5]}...")
        self._token = token
        self._q = asyncio.Queue()
        self._heartbeat = 60
        self._session_id = ''
        self._sequence = None
        self.gw_url = ''
        self._zombies = asyncio.Event()   # this is my zombie timer if connection stays open but is not active

    async def run(self):
        self.log.debug("Connect gateway...")
        await self._connect()

    async def _connect(self):
        """Creates aiohttp session context manager, creates task for each loop"""
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{URL}/gateway") as response:
                try:
                    assert 200 == response.status, response.reason
                    _r = await response.json()
                    self.gw_url = _r['url'] + "/?v=9&encoding=json"
                except Exception as e:
                    log.error("gateway response error: {e}")

            self.log.debug("Opened aiohttp ClientSession - creating discord send/recv/ping loops.")
            async with session.ws_connect(self.gw_url) as ws:
                recv = asyncio.create_task(self._recv_loop(ws))
                send = asyncio.create_task(self._send_loop(ws))
                ping = asyncio.create_task(self._ping_loop(ws))
                await ping
                await send
                await recv
            
    async def _recv_loop(self, ws):
        """Handle received messages"""
        async for msg in ws:
            decoded = await parse_msg(msg)
            self.log.debug(
                f"Op {decoded.op}, s: {decoded.sequence}, name: {decoded.name}. session_id: {decoded.session_id}\n"
            )
            try:
                self._sequence = decoded.sequence
                await self.handle_message(decoded)
            except Exception as e:
                # handle exception
                self.log.error(f"Exception in recv loop. {e}")

    async def _send_loop(self, ws):
        """Sends any messages found in send queue"""
        while True:
            try:
                msg = await self._q.get()
                self.log.debug(f"_send_loop sending: {msg}")
                await ws.send_json(msg)

            except Exception as e:
                self.log.debug(f"Exception in _send_loop: {e}")
                exit()

    async def _ping_loop(self, ws):
        """Send heartbeats, check if connection closes"""
        while True:
            # if websocket is closed or _zombie (ack timer) has triggered
            if ws.closed or self._zombies.is_set():
                if ws.closed:
                    self.log.error("Websocket closed.")
                elif self._zombies.is_set():
                    self.log.error("Zombies is set")

                for attempt in range(3):
                    try:
                        await self.reconnect(ws)
                    except Exception as e:
                        self.log.error(f"Error reconnecting. {e}")
                        await asyncio.sleep(3)
                        continue
                    else:
                        self._zombie.clear()
                        break
                else:
                    self.log.error("Error reconnecting in three tries.")

            wait = self._heartbeat
            self.log.debug(f"Waiting for hb: {wait}")
            await asyncio.sleep(wait)
            ack = {"op": 1, "d": self._sequence}
            await self.send(ack)

    async def handle_message(self, msg) -> None:
        pass

    async def send(self, msg) -> None:
        await self._q.put(msg)

    async def zombie_timer(self, interval: int) -> None:
        """Check for zombie connection"""
        self.log.debug(f"Zombie counting down from {(interval*2)}...")
        await asyncio.sleep((interval*2))
        self._zombies.set()

    async def reconnect(self, ws) -> None:
        """Close connection, reconnect, and send gateway resume to discord"""
        log.warning("Reconnecting...")
        await ws.close()
        await self._connect()
        gateway_resume = {
                    "op": 6,
                    "d": {
                        "token": self._token,
                        "session_id": self._session_id,
                        "seq": self._sequence
                    }
                }
        await self.send(gateway_resume)


if __name__ == '__main__':
    con = Gateway("stuff")
    asyncio.run(con.run())
