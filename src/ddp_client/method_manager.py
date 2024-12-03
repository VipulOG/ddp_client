import asyncio
import uuid
from typing import Any, Dict, List

from pyee.asyncio import AsyncIOEventEmitter

from .message_router import MessageRouter
from .message_sender import MessageSender
from .message_types import MessageType


class MethodManager(AsyncIOEventEmitter):
    def __init__(self, message_sender: MessageSender, message_router: MessageRouter):
        super().__init__()
        self._sender = message_sender
        self._router = message_router
        self._method_calls: Dict[str, asyncio.Future] = {}
        self._router.on(MessageType.RESULT, self._handle_method_result)

    async def call_method(
        self, method: str, params: List[Any] = None, timeout: float = 10.0
    ) -> Any:
        try:
            method_id = str(uuid.uuid4())
            future = self._add_method_call(method_id)
            await self._sender.send_method_call(method_id, method, params or [])
            result = await asyncio.wait_for(future, timeout)
            return result
        finally:
            self._remove_method_call(method_id)

    async def close(self) -> None:
        await self.wait_for_complete()
        for method_id, future in self._method_calls.items():
            if not future.done():
                future.cancel()
        self._method_calls.clear()

    def _add_method_call(self, method_id: str) -> asyncio.Future:
        future = asyncio.Future()
        self._method_calls[method_id] = future
        return future

    def _remove_method_call(self, method_id: str) -> None:
        future = self._method_calls.pop(method_id, None)
        if future and not future.done():
            future.cancel()

    def _handle_method_result(self, data: dict) -> None:
        method_id, result, error = data.get("id"), data.get("result"), data.get("error")
        if method_id in self._method_calls:
            if error:
                self._method_calls[method_id].set_exception(Exception(error))
                self.emit("error", error)
            else:
                self._method_calls[method_id].set_result(result)
                self.emit("result", result)
