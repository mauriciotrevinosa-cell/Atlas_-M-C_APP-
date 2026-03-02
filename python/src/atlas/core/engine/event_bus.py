"""
Event bus for real-time artifact publish/subscribe.
"""

from __future__ import annotations

from dataclasses import dataclass
import logging
from threading import RLock
from typing import Callable
import uuid

from atlas.core.analytics.artifacts import Artifact, ArtifactFilter
from atlas.core.engine.artifact_registry import ArtifactRegistry

logger = logging.getLogger("atlas.simulation.event_bus")

Subscriber = Callable[[Artifact], None]


@dataclass(frozen=True)
class _SubscriberBinding:
    callback: Subscriber
    filters: ArtifactFilter | None


class EventBus:
    def __init__(self, registry: ArtifactRegistry) -> None:
        self._registry = registry
        self._subscribers: dict[str, _SubscriberBinding] = {}
        self._lock = RLock()

    @property
    def registry(self) -> ArtifactRegistry:
        return self._registry

    def publish(self, artifact: Artifact) -> Artifact:
        published = self._registry.publish(artifact)

        with self._lock:
            subscribers = list(self._subscribers.items())

        for token, binding in subscribers:
            if binding.filters and not binding.filters.matches(published):
                continue
            try:
                binding.callback(published)
            except Exception:
                logger.exception("Subscriber callback failed token=%s", token)

        return published

    def subscribe(self, callback: Subscriber, filters: ArtifactFilter | None = None) -> str:
        token = uuid.uuid4().hex
        with self._lock:
            self._subscribers[token] = _SubscriberBinding(callback=callback, filters=filters)
        return token

    def unsubscribe(self, token: str) -> bool:
        with self._lock:
            return self._subscribers.pop(token, None) is not None

    def subscriber_count(self) -> int:
        with self._lock:
            return len(self._subscribers)

