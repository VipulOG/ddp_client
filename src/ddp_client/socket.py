import asyncio
from enum import Enum
from typing import Optional

import websockets
from pyee.asyncio import AsyncIOEventEmitter
from websockets.asyncio.client import ClientConnection


class ConnectionState(Enum):
    DISCONNECTED = "disconnected"
    CONNECTED = "connected"


class Socket(AsyncIOEventEmitter):
    def __init__(self, server_url: str):
        super().__init__()
        self._server_url = server_url
        self._websocket: Optional[ClientConnection] = None
        self._message_handler_task: Optional[asyncio.Task] = None
        self._state = ConnectionState.DISCONNECTED

    async def connect(self) -> None:
        if self._state == ConnectionState.CONNECTED:
            return
        try:
            self._websocket = await websockets.connect(self._server_url)
            self._message_handler_task = asyncio.create_task(self._message_handler())
            self._set_state(ConnectionState.CONNECTED)
        except Exception as e:
            raise ConnectionError(f"Failed to connect: {str(e)}")

    async def send(self, message: str) -> None:
        if self._state != ConnectionState.CONNECTED:
            raise ConnectionError("Not connected to server")
        try:
            await self._websocket.send(message)
        except Exception as e:
            raise ConnectionError(f"Failed to send message: {e}")

    async def disconnect(self) -> None:
        if self._state == ConnectionState.DISCONNECTED:
            return
        if self._message_handler_task:
            self._message_handler_task.cancel()
            try:
                await self._message_handler_task
            except asyncio.CancelledError:
                pass
        if self._websocket:
            await self._websocket.close()
        self._set_state(ConnectionState.DISCONNECTED)

    async def close(self) -> None:
        await self.wait_for_complete()
        await self.disconnect()

    async def _message_handler(self) -> None:
        while self._state == ConnectionState.CONNECTED:
            try:
                message = await self._websocket.recv()
                self.emit("message", message)
            except websockets.ConnectionClosed:
                self.disconnect()

    def _set_state(self, new_state: ConnectionState) -> None:
        self._state = new_state
        self.emit("connection", new_state)
