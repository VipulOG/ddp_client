import asyncio
import uuid
from functools import wraps
from typing import Any, Callable, List, Optional

import ejson

from .collection_manager import CollectionManager
from .message_types import MessageType
from .method_manager import MethodManager
from .socket import Socket
from .subscription_manager import SubscriptionManager


def _ensure_connected(func):
    @wraps(func)
    def wrapper(self: "DDPClient", *args, **kwargs):
        if not self._socket.connected:
            raise ConnectionError("Not connected to server")
        return func(self, *args, **kwargs)

    return wrapper


class DDPClient:
    DDP_VERSIONS = ["1", "pre2", "pre1"]

    def __init__(self, server_url: str):
        self._version = self.DDP_VERSIONS[0]
        self._session_id: Optional[str] = None

        self._collection_manager = CollectionManager()
        self._subscription_manager = SubscriptionManager()
        self._method_manager = MethodManager()

        self._socket = Socket(
            server_url=server_url,
            on_message=self._handle_message,
            on_reconnect=self._handle_socket_reconnect,
        )

        self._connect_future: Optional[asyncio.Future] = None

    async def connect(self) -> None:
        self._connect_future = asyncio.Future()
        await self._socket.connect()
        await self._send_connect()
        await self._connect_future

    @_ensure_connected
    async def call(
        self, method: str, params: List[Any] = None, timeout: float = 10.0
    ) -> Any:
        try:
            method_id = str(uuid.uuid4())
            future = self._method_manager.add_method_call(method_id)
            await self._send(
                {
                    "msg": MessageType.METHOD.value,
                    "method": method,
                    "params": params or [],
                    "id": method_id,
                }
            )
            result = await asyncio.wait_for(future, timeout)
            return result
        finally:
            self._method_manager.remove_method_call(method_id)

    @_ensure_connected
    async def subscribe(
        self, name: str, params: List[Any] = None, timeout: float = 10.0
    ) -> str:
        try:
            sub_id = str(uuid.uuid4())
            future = self._subscription_manager.add_subscription(sub_id)
            await self._send(
                {
                    "msg": MessageType.SUB.value,
                    "name": name,
                    "params": params or [],
                    "id": sub_id,
                }
            )
            await asyncio.wait_for(future, timeout)
            return sub_id
        except asyncio.TimeoutError:
            await self.unsubscribe(sub_id)

    @_ensure_connected
    async def unsubscribe(self, sub_id: str) -> None:
        await self._send({"msg": MessageType.UNSUB.value, "id": sub_id})
        self._subscription_manager.remove_subscription(sub_id)

    def on(self, event_type: str, callback: Callable) -> None:
        self._collection_manager.add_handler(event_type, callback)

    def off(self, event_type: str, callback: Callable) -> None:
        self._collection_manager.remove_handler(event_type, callback)

    async def close(self) -> None:
        self._session_id = None
        await self._socket.close()
        self._subscription_manager.close()
        self._method_manager.close()
        self._collection_manager.close()

    async def _send_connect(self) -> None:
        msg = {
            "msg": MessageType.CONNECT.value,
            "version": self._version,
            "support": self.DDP_VERSIONS,
        }
        if self._session_id:
            msg["session"] = self._session_id

        await self._send(msg)

    async def _send(self, msg: dict) -> None:
        await self._socket.send(ejson.dumps(msg))

    async def _handle_message(self, message: str) -> None:
        data: dict = ejson.loads(message)
        msg = data.get("msg")

        if not msg or msg not in MessageType._value2member_map_:
            return

        handlers = {
            MessageType.CONNECTED: self._handle_connected,
            MessageType.FAILED: self._handle_failed,
            MessageType.PING: self._handle_ping,
            MessageType.ADDED: self._handle_added,
            MessageType.CHANGED: self._handle_changed,
            MessageType.REMOVED: self._handle_removed,
            MessageType.RESULT: self._handle_result,
            MessageType.READY: self._handle_ready,
        }

        msg_type = MessageType(msg)
        handler = handlers.get(msg_type)
        await handler(data)

    async def _handle_connected(self, data: dict) -> None:
        self._session_id = data.get("session")
        if self._connect_future:
            self._connect_future.set_result(None)
            self._connect_future = None

    async def _handle_socket_reconnect(self) -> None:
        await self._send_connect()

    async def _handle_failed(self, data: dict) -> None:
        version = data.get("version")
        if version and version in self.DDP_VERSIONS:
            self._version = version
            await self._send_connect()
        else:
            raise ConnectionError("Version negotiation failed")

    async def _handle_ping(self, data: dict) -> None:
        await self._send({"msg": MessageType.PONG.value, "id": data.get("id")})

    async def _handle_added(self, data: dict) -> None:
        self._collection_manager.handle_added(
            data.get("collection"), data["id"], data.get("fields", {})
        )

    async def _handle_changed(self, data: dict) -> None:
        self._collection_manager.handle_changed(
            data.get("collection"), data["id"], data.get("fields", {})
        )

    async def _handle_removed(self, data: dict) -> None:
        self._collection_manager.handle_removed(data.get("collection"), data["id"])

    async def _handle_result(self, data: dict) -> None:
        self._method_manager.handle_result(
            data["id"], data.get("result"), data.get("error")
        )

    async def _handle_ready(self, data: dict) -> None:
        self._subscription_manager.handle_ready(data.get("subs", []))
