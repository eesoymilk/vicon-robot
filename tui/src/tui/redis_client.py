import json
import redis

REDIS_OBJECTS_KEY = "vicon_objects"
REDIS_COMMAND_CHANNEL = "robot_command_channel"


class RedisClient:
    """Redis client for TUI operations."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
    ):
        self._redis = redis.Redis(host, port, decode_responses=True)

    def get_objects(self) -> dict[str, tuple[float, float, float]]:
        """Get available objects from Redis, excluding Base."""
        data = self._redis.get(REDIS_OBJECTS_KEY)
        if not data:
            return {}

        objects = json.loads(data)
        # Filter out Base object
        return {
            name: tuple(pos)
            for name, pos in objects.items()
            if name != "Base"
        }

    def publish_command(self, command_json: str) -> None:
        """Publish a command to the robot command channel."""
        self._redis.publish(REDIS_COMMAND_CHANNEL, command_json)
