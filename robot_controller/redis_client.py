import logging
import threading
import time
from typing import Callable, Optional, Dict
import redis
from redis.client import PubSub


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
        handler = None,
    ):
        pubsub = self._redis.pubsub()
        if handler:
            pubsub.subscribe(**{channel: handler} if handler else channel)
        else:
            pubsub.subscribe(channel)
        return pubsub


def message_listener(pubsub: PubSub):
    logger.info("Listener thread started, waiting for messages...")
    while True:
        message = pubsub.get_message()
        if not message:
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
