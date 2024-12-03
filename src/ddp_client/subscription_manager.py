import asyncio
import uuid
from typing import Any, Dict, List

from pyee.asyncio import AsyncIOEventEmitter

from .message_router import MessageRouter
from .message_sender import MessageSender
from .message_types import MessageType


class SubscriptionManager(AsyncIOEventEmitter):
    def __init__(self, message_sender: MessageSender, message_router: MessageRouter):
        super().__init__()
        self._sender = message_sender
        self._router = message_router
        self._subscriptions: Dict[str, asyncio.Future] = {}
        self._router.on(MessageType.READY, self._handle_subscription_ready)

    async def subscribe(
        self, name: str, params: List[Any] | None = None, timeout: float = 10.0
    ) -> str:
        try:
            sub_id = str(uuid.uuid4())
            future = self._add_subscription(sub_id)
            await self._sender.send_subscribe(sub_id, name, params or [])
            await asyncio.wait_for(future, timeout)
            return sub_id
        except asyncio.TimeoutError:
            await self.unsubscribe(sub_id)

    async def unsubscribe(self, sub_id: str) -> None:
        await self._sender.send_unsubscribe(sub_id)
        self._remove_subscription(sub_id)

    async def close(self) -> None:
        await self.wait_for_complete()
        for sub_id, future in self._subscriptions.items():
            if not future.done():
                future.cancel()
        self._subscriptions.clear()

    def _add_subscription(self, sub_id: str) -> asyncio.Future:
        future = asyncio.Future()
        self._subscriptions[sub_id] = future
        return future

    def _remove_subscription(self, sub_id: str) -> None:
        future = self._subscriptions.pop(sub_id, None)
        if future and not future.done():
            future.cancel()

    def _handle_subscription_ready(self, data: dict) -> None:
        sub_ids = data.get("subs", [])
        for sub_id in sub_ids:
            if sub_id in self._subscriptions:
                self._subscriptions[sub_id].set_result(True)
        self.emit("ready", sub_ids)
