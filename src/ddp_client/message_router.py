import ejson
from pyee.asyncio import AsyncIOEventEmitter

from ddp_client.message_types import MessageType

from .socket import Socket


class MessageRouter(AsyncIOEventEmitter):
    def __init__(self, socket: Socket):
        super().__init__()
        self._socket = socket
        self._socket.on("message", self._handle_message)

    async def _handle_message(self, message: str):
        data: dict = ejson.loads(message)
        msg = data.get("msg")
        if not msg or msg not in MessageType._value2member_map_:
            return
        msg_type = MessageType(msg)
        self.emit(msg_type, data)

    async def close(self) -> None:
        await self.wait_for_complete()
