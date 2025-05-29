import redis
import logging


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

    def get_value(self, key: str) -> str:
        """
        Get the value for the specified key from Redis.
        """
        return self._redis.get(key)

    def subscribe(
        self,
        channel: str,
        handler=None,
    ):
        pubsub = self._redis.pubsub()
        if handler:
            pubsub.subscribe(**{channel: handler} if handler else channel)
        else:
            pubsub.subscribe(channel)
        return pubsub
