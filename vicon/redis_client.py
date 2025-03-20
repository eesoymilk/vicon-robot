import logging
import redis
import redis.client


logger = logging.getLogger(__name__)


class RedisClient:
    """
    A simple class to encapsulate common Redis operations (set/get, publish/subscribe).
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        decode_responses: bool = True,
    ):
        """
        Initializes the Redis client connection.
        :param host: Redis server host (default: localhost)
        :param port: Redis server port (default: 6379)
        :param decode_responses: If True, automatically decode bytes to str
        """
        self._redis = redis.Redis(
            host=host, port=port, decode_responses=decode_responses
        )

    def set_value(self, key: str, value: str) -> None:
        """
        Set a value in Redis under the specified key.
        """
        self._redis.set(key, value)

    def get_value(self, key: str) -> str:
        """
        Get the value for the specified key from Redis.
        """
        return self._redis.get(key)
