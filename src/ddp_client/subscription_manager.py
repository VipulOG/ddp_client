import asyncio
from dataclasses import dataclass, field
from typing import Dict


@dataclass
class SubscriptionManager:
    _subscriptions: Dict[str, asyncio.Future] = field(default_factory=dict)

    def add_subscription(self, sub_id: str) -> asyncio.Future:
        future = asyncio.Future()
        self._subscriptions[sub_id] = future
        return future

    def remove_subscription(self, sub_id: str) -> None:
        future = self._subscriptions.pop(sub_id, None)
        if future and not future.done():
            future.cancel()

    def handle_ready(self, sub_ids: list) -> None:
        for sub_id in sub_ids:
            if sub_id in self._subscriptions:
                self._subscriptions[sub_id].set_result(True)

    def close(self) -> None:
        for sub_id, future in self._subscriptions.items():
            if not future.done():
                future.cancel()
        self._subscriptions.clear()
