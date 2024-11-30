import asyncio
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class MethodManager:
    _method_calls: Dict[str, asyncio.Future] = field(default_factory=dict)

    def add_method_call(self, method_id: str) -> asyncio.Future:
        future = asyncio.Future()
        self._method_calls[method_id] = future
        return future

    def remove_method_call(self, method_id: str) -> None:
        future = self._method_calls.pop(method_id, None)
        if future and not future.done():
            future.cancel()

    def handle_result(
        self, method_id: str, result: Any, error: Optional[dict] = None
    ) -> None:
        if method_id in self._method_calls:
            if error:
                self._method_calls[method_id].set_exception(Exception(error))
            else:
                self._method_calls[method_id].set_result(result)

    def close(self) -> None:
        for method_id, future in self._method_calls.items():
            if not future.done():
                future.cancel()
        self._method_calls.clear()
