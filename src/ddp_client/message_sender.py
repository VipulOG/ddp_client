from typing import Any, List, Optional

import ejson

from .message_types import MessageType
from .socket import Socket


class MessageSender:
    def __init__(self, socket: Socket) -> None:
        self._socket = socket

    async def send_connect(
        self, version: str, support: List[str], session_id: Optional[str] = None
    ) -> None:
        await self._send(
            {
                "version": version,
                "support": support,
                "session": session_id,
                "msg": MessageType.CONNECT.value,
            }
        )

    async def send_method_call(
        self, method_id: str, method: str, params: List[Any]
    ) -> None:
        await self._send(
            {
                "method": method,
                "params": params,
                "id": method_id,
                "msg": MessageType.METHOD.value,
            }
        )

    async def send_subscribe(self, sub_id: str, name: str, params: List[Any]) -> None:
        await self._send(
            {
                "name": name,
                "params": params,
                "id": sub_id,
                "msg": MessageType.SUB.value,
            }
        )

    async def send_unsubscribe(self, sub_id: str) -> None:
        await self._send(
            {
                "id": sub_id,
                "msg": MessageType.UNSUB.value,
            }
        )

    async def _send(self, message: dict) -> None:
        await self._socket.send(ejson.dumps(message))
