from enum import Enum


class MessageType(Enum):
    CONNECT = "connect"
    CONNECTED = "connected"
    FAILED = "failed"
    PING = "ping"
    PONG = "pong"
    ADDED = "added"
    CHANGED = "changed"
    REMOVED = "removed"
    RESULT = "result"
    READY = "ready"
    SUB = "sub"
    UNSUB = "unsub"
    METHOD = "method"
