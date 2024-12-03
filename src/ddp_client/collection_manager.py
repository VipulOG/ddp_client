from pyee.asyncio import AsyncIOEventEmitter

from .message_router import MessageRouter
from .message_types import MessageType


class CollectionManager(AsyncIOEventEmitter):
    def __init__(self, message_router: MessageRouter):
        super().__init__()
        self._router = message_router
        self._router.on(MessageType.ADDED, self.handle_added)
        self._router.on(MessageType.CHANGED, self.handle_changed)
        self._router.on(MessageType.REMOVED, self.handle_removed)

    async def handle_added(self, data: dict) -> None:
        collection = data.get("collection")
        if collection:
            self.emit("added", collection, data)

    async def handle_changed(self, data: dict) -> None:
        collection = data.get("collection")
        if collection:
            self.emit("changed", collection, data)

    async def handle_removed(self, data: dict) -> None:
        collection = data.get("collection")
        if collection:
            self.emit("removed", collection, data)

    async def close(self) -> None:
        await self.wait_for_complete()
