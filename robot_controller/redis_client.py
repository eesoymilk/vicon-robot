import logging
import threading
import time
from typing import Callable, Optional
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

    def subscribe(
        self,
        channel: str,
        handler: Optional[Callable[[str], None]] = None,
    ):
        """
        Return a PubSub object subscribed to the specified channel.
        You can then iterate over its messages in a separate loop.
        """
        pubsub = self._redis.pubsub()
        if handler:
            pubsub.subscribe(**{channel: handler})
        else:
            pubsub.subscribe(channel)
        return pubsub


def message_listener(pubsub: redis.client.PubSub):
    logger.info("Listener thread started, waiting for messages...")
    while True:
        if not (message := pubsub.get_message()):
            time.sleep(1)
        print(f"Received message: {message}")


def main():
    try:
        # Create a Redis client instance
        redis_client = RedisClient()

        # Subscribe to a channel
        pubsub = redis_client.subscribe("example_channel")

        # Start a listener thread
        listener_thread = threading.Thread(
            target=message_listener,
            args=(pubsub,),
        )
        listener_thread.start()

    except KeyboardInterrupt:
        print("Stopping listener...")


if __name__ == "__main__":
    main()
