"""
AtlasServiceBus extends the core EventBus with typed channels and shared state.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import logging
from threading import RLock
from typing import Any, Callable, Iterable
import uuid

from atlas.core.analytics.artifacts import Artifact, utc_now
from atlas.core.engine.artifact_registry import ArtifactRegistry
from atlas.core.engine.event_bus import EventBus

logger = logging.getLogger("atlas.simulation.service_bus")


class BusChannel(str, Enum):
    MARKET_DATA = "MARKET_DATA"
    SIGNALS = "SIGNALS"
    RISK = "RISK"
    NEWS = "NEWS"
    MACRO = "MACRO"
    ORDERS = "ORDERS"


def coerce_bus_channel(value: BusChannel | str) -> BusChannel:
    if isinstance(value, BusChannel):
        return value
    return BusChannel(str(value).strip().upper())


@dataclass(frozen=True)
class ChannelMessage:
    channel: BusChannel
    payload: Any
    published_by: str
    created_at: datetime = field(default_factory=utc_now)
    metadata: dict[str, Any] = field(default_factory=dict)
    sequence: int | None = None


@dataclass(frozen=True)
class StateChange:
    key: str
    value: Any
    previous_value: Any
    published_by: str
    created_at: datetime = field(default_factory=utc_now)
    metadata: dict[str, Any] = field(default_factory=dict)
    sequence: int | None = None


@dataclass(frozen=True)
class _ChannelBinding:
    callback: Callable[[ChannelMessage], None]
    channels: set[BusChannel] | None


@dataclass(frozen=True)
class _StateBinding:
    callback: Callable[[StateChange], None]
    keys: set[str] | None


class AtlasServiceBus(EventBus):
    """
    EventBus with typed channels and a small shared state store.

    Artifacts continue to flow through the underlying EventBus / ArtifactRegistry.
    Channels and state are handled locally so modules can coordinate without
    losing the existing artifact pipeline.
    """

    def __init__(
        self,
        registry: ArtifactRegistry | None = None,
        *,
        channel_history_size: int = 1000,
        state_history_size: int = 1000,
    ) -> None:
        super().__init__(registry=registry or ArtifactRegistry())
        if channel_history_size <= 0:
            raise ValueError("channel_history_size must be > 0")
        if state_history_size <= 0:
            raise ValueError("state_history_size must be > 0")

        self._service_lock = RLock()
        self._sequence = 0
        self._channel_subscribers: dict[str, _ChannelBinding] = {}
        self._state_observers: dict[str, _StateBinding] = {}
        self._channel_history: deque[ChannelMessage] = deque(maxlen=channel_history_size)
        self._state_history: deque[StateChange] = deque(maxlen=state_history_size)
        self._state: dict[str, Any] = {}

    def publish(self, artifact: Artifact) -> Artifact:
        return super().publish(artifact)

    def publish_channel(
        self,
        channel: BusChannel | str,
        payload: Any,
        *,
        published_by: str = "service_bus",
        metadata: dict[str, Any] | None = None,
    ) -> ChannelMessage:
        channel_enum = coerce_bus_channel(channel)
        metadata = dict(metadata or {})

        with self._service_lock:
            sequence = self._next_sequence_locked()
            message = ChannelMessage(
                channel=channel_enum,
                payload=payload,
                published_by=published_by,
                metadata=metadata,
                sequence=sequence,
            )
            self._channel_history.append(message)
            subscribers = list(self._channel_subscribers.items())

        for token, binding in subscribers:
            if binding.channels is not None and channel_enum not in binding.channels:
                continue
            try:
                binding.callback(message)
            except Exception:
                logger.exception("Channel subscriber failed token=%s channel=%s", token, channel_enum.value)

        logger.info(
            "channel_published sequence=%s channel=%s published_by=%s",
            message.sequence,
            channel_enum.value,
            published_by,
        )
        return message

    def subscribe_channel(
        self,
        callback: Callable[[ChannelMessage], None],
        channels: BusChannel | str | Iterable[BusChannel | str] | None = None,
    ) -> str:
        token = uuid.uuid4().hex
        binding = _ChannelBinding(callback=callback, channels=self._normalize_channels(channels))
        with self._service_lock:
            self._channel_subscribers[token] = binding
        return token

    def unsubscribe_channel(self, token: str) -> bool:
        with self._service_lock:
            return self._channel_subscribers.pop(token, None) is not None

    def channel_subscriber_count(self) -> int:
        with self._service_lock:
            return len(self._channel_subscribers)

    def get_channel_history(
        self,
        channel: BusChannel | str | None = None,
        *,
        limit: int | None = None,
    ) -> list[ChannelMessage]:
        channel_enum = coerce_bus_channel(channel) if channel is not None else None
        with self._service_lock:
            history = list(self._channel_history)

        items = [message for message in history if channel_enum is None or message.channel == channel_enum]
        if limit is not None:
            if limit <= 0:
                return []
            items = items[-limit:]
        return items

    def latest_channel_message(self, channel: BusChannel | str) -> ChannelMessage | None:
        history = self.get_channel_history(channel=channel, limit=1)
        return history[-1] if history else None

    def set_state(
        self,
        key: str,
        value: Any,
        *,
        published_by: str = "service_bus",
        metadata: dict[str, Any] | None = None,
    ) -> StateChange:
        state_key = str(key).strip()
        if not state_key:
            raise ValueError("state key cannot be empty")

        metadata = dict(metadata or {})
        with self._service_lock:
            previous_value = self._state.get(state_key)
            self._state[state_key] = value
            sequence = self._next_sequence_locked()
            change = StateChange(
                key=state_key,
                value=value,
                previous_value=previous_value,
                published_by=published_by,
                metadata=metadata,
                sequence=sequence,
            )
            self._state_history.append(change)
            observers = list(self._state_observers.items())

        for token, binding in observers:
            if binding.keys is not None and state_key not in binding.keys:
                continue
            try:
                binding.callback(change)
            except Exception:
                logger.exception("State observer failed token=%s key=%s", token, state_key)

        logger.info("state_updated sequence=%s key=%s published_by=%s", change.sequence, state_key, published_by)
        return change

    def update_state(
        self,
        key: str,
        value: Any,
        *,
        published_by: str = "service_bus",
        metadata: dict[str, Any] | None = None,
    ) -> StateChange:
        return self.set_state(key, value, published_by=published_by, metadata=metadata)

    def get_state(self, key: str, default: Any = None) -> Any:
        with self._service_lock:
            return self._state.get(str(key).strip(), default)

    def get_state_snapshot(self) -> dict[str, Any]:
        with self._service_lock:
            return dict(self._state)

    def subscribe_state(
        self,
        callback: Callable[[StateChange], None],
        keys: str | Iterable[str] | None = None,
    ) -> str:
        token = uuid.uuid4().hex
        binding = _StateBinding(callback=callback, keys=self._normalize_keys(keys))
        with self._service_lock:
            self._state_observers[token] = binding
        return token

    def unsubscribe_state(self, token: str) -> bool:
        with self._service_lock:
            return self._state_observers.pop(token, None) is not None

    def state_observer_count(self) -> int:
        with self._service_lock:
            return len(self._state_observers)

    def get_state_history(self, key: str | None = None, *, limit: int | None = None) -> list[StateChange]:
        state_key = str(key).strip() if key is not None else None
        with self._service_lock:
            history = list(self._state_history)

        items = [change for change in history if state_key is None or change.key == state_key]
        if limit is not None:
            if limit <= 0:
                return []
            items = items[-limit:]
        return items

    def _next_sequence_locked(self) -> int:
        self._sequence += 1
        return self._sequence

    @staticmethod
    def _normalize_channels(
        channels: BusChannel | str | Iterable[BusChannel | str] | None,
    ) -> set[BusChannel] | None:
        if channels is None:
            return None
        if isinstance(channels, (BusChannel, str)):
            return {coerce_bus_channel(channels)}
        return {coerce_bus_channel(channel) for channel in channels}

    @staticmethod
    def _normalize_keys(keys: str | Iterable[str] | None) -> set[str] | None:
        if keys is None:
            return None
        if isinstance(keys, str):
            normalized = keys.strip()
            return {normalized} if normalized else set()
        return {str(key).strip() for key in keys if str(key).strip()}
