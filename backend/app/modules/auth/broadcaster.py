from __future__ import annotations

import asyncio
import json
import logging
from collections import defaultdict
from typing import Any
from uuid import UUID

logger = logging.getLogger(__name__)


class NotificationBroadcaster:
    """
    In-memory pub/sub broker for user-scoped Server-Sent Events (SSE).
    Maps each user_id to a set of active asyncio.Queue instances.
    Thread-safe and async-safe across concurrent connections.
    """

    def __init__(self) -> None:
        # user_id -> set of asyncio.Queue
        self._subscribers: dict[UUID, set[asyncio.Queue[dict[str, Any]]]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def subscribe(self, user_id: UUID) -> asyncio.Queue[dict[str, Any]]:
        """Registers a new listener queue for a connected client session."""
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=100)
        async with self._lock:
            self._subscribers[user_id].add(queue)
        logger.debug("User %s subscribed to SSE. Total queues for user: %d", user_id, len(self._subscribers[user_id]))
        return queue

    async def unsubscribe(self, user_id: UUID, queue: asyncio.Queue[dict[str, Any]]) -> None:
        """Removes a listener queue when client disconnects."""
        async with self._lock:
            if user_id in self._subscribers:
                self._subscribers[user_id].discard(queue)
                if not self._subscribers[user_id]:
                    del self._subscribers[user_id]
        logger.debug("User %s unsubscribed from SSE.", user_id)

    async def publish(self, user_id: UUID, data: dict[str, Any]) -> None:
        """Pushes a notification payload to all active client queues registered to user_id."""
        async with self._lock:
            queues = list(self._subscribers.get(user_id, set()))

        for q in queues:
            try:
                q.put_nowait(data)
            except asyncio.QueueFull:
                logger.warning("Queue full for user %s, dropping event.", user_id)
            except Exception as exc:
                logger.error("Error publishing to queue: %s", exc)


# Global singleton instance
broadcaster = NotificationBroadcaster()

