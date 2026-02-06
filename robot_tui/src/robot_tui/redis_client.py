"""Async Redis client for TUI operations."""

import json
from typing import Callable

import redis.asyncio as redis

REDIS_OBJECTS_KEY = "vicon_objects"
REDIS_COMMAND_CHANNEL = "robot_command_channel"


class AsyncRedisClient:
    """Async Redis client with auto-reconnect for TUI operations."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        on_connect: Callable[[], None] | None = None,
        on_disconnect: Callable[[], None] | None = None,
    ):
        self._host = host
        self._port = port
        self._redis: redis.Redis | None = None
        self._connected = False
        self._on_connect = on_connect
        self._on_disconnect = on_disconnect
        self._retry_delay = 1.0
        self._max_retry_delay = 30.0

    @property
    def connected(self) -> bool:
        """Return connection status."""
        return self._connected

    async def connect(self) -> bool:
        """Attempt to connect to Redis."""
        try:
            self._redis = redis.Redis(
                host=self._host,
                port=self._port,
                decode_responses=True,
            )
            # Test connection
            await self._redis.ping()
            self._connected = True
            self._retry_delay = 1.0  # Reset retry delay on success
            if self._on_connect:
                self._on_connect()
            return True
        except (redis.ConnectionError, redis.TimeoutError, OSError):
            self._connected = False
            if self._on_disconnect:
                self._on_disconnect()
            return False

    async def disconnect(self) -> None:
        """Disconnect from Redis."""
        if self._redis:
            await self._redis.close()
            self._redis = None
        self._connected = False

    async def get_objects(self) -> dict[str, tuple[float, float, float]]:
        """Get available objects from Redis, excluding Base and Board."""
        if not self._connected or not self._redis:
            return {}

        try:
            data = await self._redis.get(REDIS_OBJECTS_KEY)
            if not data:
                return {}

            objects = json.loads(data)
            # Filter out Base and Board objects
            return {
                name: tuple(obj["position"])
                for name, obj in objects.items()
                if name not in ("Base", "Board")
            }
        except (redis.ConnectionError, redis.TimeoutError, OSError):
            self._connected = False
            if self._on_disconnect:
                self._on_disconnect()
            return {}

    async def get_board_position(self) -> tuple[float, float, float] | None:
        """Get the Board position from Redis."""
        if not self._connected or not self._redis:
            return None

        try:
            data = await self._redis.get(REDIS_OBJECTS_KEY)
            if not data:
                return None

            objects = json.loads(data)
            if "Board" not in objects:
                return None

            return tuple(objects["Board"]["position"])
        except (redis.ConnectionError, redis.TimeoutError, OSError):
            self._connected = False
            if self._on_disconnect:
                self._on_disconnect()
            return None

    async def publish_command(self, command_json: str) -> bool:
        """Publish a command to the robot command channel."""
        if not self._connected or not self._redis:
            return False

        try:
            await self._redis.publish(REDIS_COMMAND_CHANNEL, command_json)
            return True
        except (redis.ConnectionError, redis.TimeoutError, OSError):
            self._connected = False
            if self._on_disconnect:
                self._on_disconnect()
            return False

    async def try_reconnect(self) -> bool:
        """Try to reconnect with exponential backoff."""
        success = await self.connect()
        if not success:
            # Increase retry delay with exponential backoff
            self._retry_delay = min(self._retry_delay * 1.5, self._max_retry_delay)
        return success

    def get_retry_delay(self) -> float:
        """Get current retry delay in seconds."""
        return self._retry_delay
