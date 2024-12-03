from typing import Any, List

from pyee.asyncio import AsyncIOEventEmitter

from .collection_manager import CollectionManager
from .message_router import MessageRouter
from .message_sender import MessageSender
from .method_manager import MethodManager
from .session_manager import SessionManager
from .socket import Socket
from .subscription_manager import SubscriptionManager


class DDPClient(AsyncIOEventEmitter):
    def __init__(self, server_url: str):
        super().__init__()
        self._socket = Socket(server_url=server_url)
        self._sender = MessageSender(socket=self._socket)
        self._router = MessageRouter(socket=self._socket)
        self._session_manager = SessionManager(self._socket, self._sender, self._router)
        self._method_manager = MethodManager(self._sender, self._router)
        self._subscription_manager = SubscriptionManager(self._sender, self._router)
        self._collection_manager = CollectionManager(self._router)

        self._collection_manager.on("added", self._handle_collection_added)
        self._collection_manager.on("changed", self._handle_collection_changed)
        self._collection_manager.on("removed", self._handle_collection_removed)

    async def connect(self, timeout: float = 10.0) -> None:
        await self._session_manager.connect(timeout=timeout)

    async def subscribe(self, name: str, params: List[Any] | None = None) -> str:
        return await self._subscription_manager.subscribe(name, params)

    async def unsubscribe(self, sub_id: str) -> None:
        await self._subscription_manager.unsubscribe(sub_id)

    async def call_method(self, method: str, params: List[Any] | None = None) -> Any:
        return await self._method_manager.call_method(method, params)

    async def close(self) -> None:
        await self.wait_for_complete()
        await self._collection_manager.close()
        await self._subscription_manager.close()
        await self._method_manager.close()
        await self._session_manager.close()
        await self._router.close()
        await self._socket.close()

    async def _handle_collection_added(self, collection: str, data: dict) -> None:
        self.emit("collection_added", collection, data)
        self.emit(f"collection:{collection}:added", data)

    async def _handle_collection_changed(self, collection: str, data: dict) -> None:
        self.emit("collection_changed", collection, data)
        self.emit(f"collection:{collection}:changed", data)

    async def _handle_collection_removed(self, collection: str, data: dict) -> None:
        self.emit("collection_removed", collection, data)
        self.emit(f"collection:{collection}:removed", data)
