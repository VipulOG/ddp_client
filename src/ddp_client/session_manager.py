import asyncio
from typing import Optional

from pyee.asyncio import AsyncIOEventEmitter

from .constants import DDP_SUPPORTED_VERSIONS
from .message_router import MessageRouter
from .message_sender import MessageSender
from .message_types import MessageType
from .socket import Socket


class SessionManager(AsyncIOEventEmitter):
    def __init__(
        self,
        socket: Socket,
        message_sender: MessageSender,
        message_router: MessageRouter,
    ):
        super().__init__()
        self._socket = socket
        self._sender = message_sender
        self._router = message_router
        self._version = DDP_SUPPORTED_VERSIONS[0]
        self._session_id: Optional[str] = None
        self._connect_future: Optional[asyncio.Future] = None

        self._socket.on("connection", self._handle_socket_connection_change)
        self._router.on(MessageType.CONNECTED, self._handle_connected)
        self._router.on(MessageType.FAILED, self._handle_failed)
        self._router.on(MessageType.PING, self._handle_ping)

    async def connect(self, session_id: str = None, timeout: float = 10.0) -> str:
        self._connect_future = asyncio.Future()
        try:
            await self._socket.connect()
            await self._sender.send_connect(
                version=self._version,
                support=DDP_SUPPORTED_VERSIONS,
                session_id=session_id or self._session_id,
            )
            return await asyncio.wait_for(self._connect_future, timeout)
        except asyncio.TimeoutError:
            self._connect_future.cancel()
            self._connect_future = None
            raise

    async def close(self) -> None:
        await self.wait_for_complete()

    async def _handle_socket_connection_change(self, connected: bool) -> None:
        if not connected:
            self.emit("disconnected")

    async def _handle_connected(self, data: dict) -> None:
        self._session_id = data.get("session")
        if self._connect_future is not None:
            self._connect_future.set_result(self._session_id)
            self.emit("connected")

    async def _handle_failed(self, data: dict) -> None:
        version = data.get("version")
        if version and version in DDP_SUPPORTED_VERSIONS:
            self._version = version
            await self.connect()
        else:
            raise ConnectionError("Version negotiation failed: Unsupported version")

    async def _handle_ping(self, data: dict) -> None:
        await self._sender.send_pong()
