import logging
import time
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
        """
        Initializes the Redis client connection.
        :param host: Redis server host (default: localhost)
        :param port: Redis server port (default: 6379)
        :param decode_responses: If True, automatically decode bytes to str
        """
        self._redis = redis.Redis(
            host=host, port=port, decode_responses=decode_responses
        )

    def publish(self, channel: str, message):
        """
        Publish a message to a specific channel (for Pub/Sub).
        """
        self._redis.publish(channel, message)


def main():
    # Create a Redis client instance
    redis_client = RedisClient()

    for i in range(3):
        message = f"Message #{i}"
        redis_client.publish("example_channel", message)
        print(f"Published: {message}")
        time.sleep(1)


if __name__ == "__main__":
    main()
