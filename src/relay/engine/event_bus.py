"""Central asynchronous Publish/Subscribe Event Bus decoupling core engine from presentation surfaces."""

import asyncio
from typing import Awaitable, Callable
from relay.domain.events import BaseEvent

# Subscriber callback type definition
EventSubscriber = Callable[[BaseEvent], Awaitable[None] | None]


class EventBus:
    """Async Pub/Sub broker supporting exact match and wildcard (`*`) event topic subscriptions."""

    def __init__(self):
        self._subscribers: dict[str, list[EventSubscriber]] = {}
        self._lock = asyncio.Lock()

    async def subscribe(self, event_pattern: str, callback: EventSubscriber) -> None:
        """Register a callback for an event topic pattern (e.g., 'step.started', 'job.*', '*')."""
        async with self._lock:
            if event_pattern not in self._subscribers:
                self._subscribers[event_pattern] = []
            if callback not in self._subscribers[event_pattern]:
                self._subscribers[event_pattern].append(callback)

    async def unsubscribe(self, event_pattern: str, callback: EventSubscriber) -> bool:
        """Remove a previously registered callback."""
        async with self._lock:
            if event_pattern in self._subscribers and callback in self._subscribers[event_pattern]:
                self._subscribers[event_pattern].remove(callback)
                return True
        return False

    def _matches_pattern(self, pattern: str, event_type: str) -> bool:
        if pattern == "*" or pattern == event_type:
            return True
        if pattern.endswith(".*"):
            prefix = pattern[:-2]
            return event_type.startswith(prefix + ".")
        return False

    async def publish(self, event: BaseEvent) -> None:
        """Publish an event across all matching subscribers concurrently."""
        callbacks_to_invoke: list[EventSubscriber] = []
        async with self._lock:
            for pattern, callbacks in self._subscribers.items():
                if self._matches_pattern(pattern, event.event_type):
                    callbacks_to_invoke.extend(callbacks)

        if not callbacks_to_invoke:
            return

        tasks = []
        for cb in callbacks_to_invoke:
            res = cb(event)
            if asyncio.iscoroutine(res):
                tasks.append(res)

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
