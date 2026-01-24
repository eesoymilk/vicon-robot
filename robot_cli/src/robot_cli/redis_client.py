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
        """Get available objects from Redis, excluding Base and Board."""
        data = self._redis.get(REDIS_OBJECTS_KEY)
        if not data:
            return {}

        objects = json.loads(data)
        # Filter out Base and Board objects
        return {
            name: tuple(obj["position"])
            for name, obj in objects.items()
            if name not in ("Base", "Board")
        }

    def get_board_position(self) -> tuple[float, float, float] | None:
        """Get the Board position from Redis."""
        data = self._redis.get(REDIS_OBJECTS_KEY)
        if not data:
            return None

        objects = json.loads(data)
        if "Board" not in objects:
            return None

        return tuple(objects["Board"]["position"])

    def publish_command(self, command_json: str) -> None:
        """Publish a command to the robot command channel."""
        self._redis.publish(REDIS_COMMAND_CHANNEL, command_json)
