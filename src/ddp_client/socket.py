import asyncio
from typing import Callable, Optional

import websockets
from websockets.asyncio.client import ClientConnection
from websockets.exceptions import ConnectionClosed


class Socket:
    def __init__(
        self,
        server_url: str,
        on_message: Callable,
        on_reconnect: Callable = None,
        max_reconnect_attempts: int = 3,
    ):
        self.connected = False
        self.stopping = False
        self.closed = False

        self._server_url = server_url
        self._websocket: Optional[ClientConnection] = None
        self._on_message = on_message
        self._on_reconnect = on_reconnect
        self._reconnect_attempt = 0
        self._max_reconnect_attempts = max_reconnect_attempts

    async def connect(self) -> None:
        try:
            self._websocket = await websockets.connect(self._server_url)
            self.connected = True
            asyncio.create_task(self._message_handler())
            self._reconnect_attempt = 0
            # logger.info("Connected to server")
        except Exception:
            # logger.error(f"Failed to connect: {e}")
            await self._handle_connection_failure()

    async def _handle_connection_failure(self) -> None:
        if self._reconnect_attempt < self._max_reconnect_attempts:
            self._reconnect_attempt += 1
            wait_time = min(2**self._reconnect_attempt, 30)
            # logger.info(f"Reconnecting in {wait_time} seconds...")
            await asyncio.sleep(wait_time)
            await self.connect()
            if self._on_reconnect:
                await self._on_reconnect()
        else:
            # logger.error("Max reconnection attempts reached")
            self.closed = True
            raise ConnectionError("Failed to connect to server")

    async def _message_handler(self) -> None:
        while not self.stopping and not self.closed and self._websocket:
            try:
                message = await self._websocket.recv()
                await self._on_message(message)
            except ConnectionClosed:
                # logger.warning("Connection closed unexpectedly")
                self.connected = False
                await self._handle_connection_failure()
                break
            except Exception:
                # logger.error(f"Error handling message: {e}")
                pass

    async def send(self, message: str) -> None:
        if self._websocket:
            await self._websocket.send(message)
        else:
            raise ConnectionError("Not connected to server")

    async def close(self) -> None:
        self.stopping = True
        if self._websocket:
            await self._websocket.close()
        self.connected = False
        self.closed = True
        self.stopping = False
