import logging

import redis

logger = logging.getLogger(__name__)


class RedisClient:
    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        decode_responses: bool = True,
    ):
        self._redis = redis.Redis(host, port, decode_responses=decode_responses)

    def publish(self, channel: str, message):
        self._redis.publish(channel, message)

    def get_value(self, key: str) -> str:
        return self._redis.get(key)
