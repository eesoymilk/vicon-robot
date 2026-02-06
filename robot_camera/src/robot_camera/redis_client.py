"""Synchronous Redis client for camera recorder."""

import json
import logging
from typing import Any, Callable

import redis

logger = logging.getLogger(__name__)

TRAJECTORY_EVENTS_CHANNEL = "trajectory_events"


class RedisSubscriber:
    """Subscribes to trajectory events from the robot controller."""

    def __init__(self, host: str = "localhost", port: int = 6379) -> None:
        self._redis = redis.Redis(host=host, port=port, decode_responses=True)
        self._pubsub = self._redis.pubsub()

    def listen(self, handler: Callable[[dict[str, Any]], None]) -> None:
        """Block and listen for trajectory events, calling handler for each.

        Args:
            handler: Called with parsed JSON dict for each event.
        """
        self._pubsub.subscribe(TRAJECTORY_EVENTS_CHANNEL)
        logger.info("Subscribed to %s", TRAJECTORY_EVENTS_CHANNEL)

        for message in self._pubsub.listen():
            if message["type"] != "message":
                continue
            try:
                event = json.loads(message["data"])
                handler(event)
            except (json.JSONDecodeError, KeyError):
                logger.warning("Invalid event: %s", message["data"])

    def close(self) -> None:
        self._pubsub.unsubscribe()
        self._redis.close()
