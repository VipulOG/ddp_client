from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Set


@dataclass
class CollectionManager:
    _collections: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    _handlers: Dict[str, Set[Callable]] = field(
        default_factory=lambda: {"added": set(), "changed": set(), "removed": set()}
    )

    def handle_added(self, collection: str, id: str, fields: dict) -> None:
        if collection not in self._collections:
            self._collections[collection] = {}
        self._collections[collection][id] = fields
        for handler in self._handlers["added"]:
            handler(collection, id, fields)

    def handle_changed(self, collection: str, id: str, fields: dict) -> None:
        if collection in self._collections and id in self._collections[collection]:
            self._collections[collection][id].update(fields)
            for handler in self._handlers["changed"]:
                handler(collection, id, fields)

    def handle_removed(self, collection: str, id: str) -> None:
        if collection in self._collections and id in self._collections[collection]:
            del self._collections[collection][id]
            for handler in self._handlers["removed"]:
                handler(collection, id)

    def add_handler(self, event_type: str, callback: Callable) -> None:
        if event_type in self._handlers:
            self._handlers[event_type].add(callback)

    def remove_handler(self, event_type: str, callback: Callable) -> None:
        if event_type in self._handlers:
            self._handlers[event_type].discard(callback)

    def clear(self) -> None:
        self._collections.clear()

    def close(self) -> None:
        self.clear()
