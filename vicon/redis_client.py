import logging
import redis


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
        self._redis = redis.Redis(host, port, decode_responses=decode_responses)

    def set_value(self, key: str, value: str):
        self._redis.set(key, value)

    def get_value(self, key: str) -> str:
        return self._redis.get(key)
