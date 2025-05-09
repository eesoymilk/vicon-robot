import logging
import logging.config
from pathlib import Path
import time
import json

from redis_client import RedisClient
from robot_controller import RobotController

SCRIPT_DIR = Path(__file__).resolve().parent
LOG_DIR = SCRIPT_DIR.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

logger = logging.getLogger(__name__)

logging_config = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {"format": "%(levelname)s: %(message)s"},
        "detailed": {
            "format": "[%(levelname)s|%(module)s|L%(lineno)d] %(asctime)s: %(message)s",
            "datefmt": "%Y-%m-%dT%H:%M:%S%z",
        },
    },
    "handlers": {
        "stderr": {
            "class": "logging.StreamHandler",
            "level": "WARNING",
            "formatter": "simple",
            "stream": "ext://sys.stderr",
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "DEBUG",
            "formatter": "detailed",
            "filename": "logs/main.log",
            "maxBytes": 50_000_000,
            "backupCount": 3,
        },
    },
    "loggers": {"root": {"level": "DEBUG", "handlers": ["stderr", "file"]}},
}


def setup_logging():
    LOG_DIR.mkdir(exist_ok=True)
    logging.config.dictConfig(logging_config)


def main():
    try:
        setup_logging()
        redis_client = RedisClient()
        robot_controller = RobotController()

        robot_controller.initialize_robot()
        time.sleep(1)

        def pubsub_handler(message):
            if not message:
                return
            print(f"Received message: {message}")
            if message["type"] == "message":
                data = message["data"]
                print(f"data={data}")
                data = json.loads(data)
                print(f"parsed data = {data}")
                function_name, pos, rot = data["function_name"], data["position"], data["rotation"]
                print(f"Function: {function_name}, Pos: {pos}, Rot: {rot}")
                if function_name == "grab_object":
                    robot_controller.grab_object(pos, rot)

        # Subscribe to a channel
        print("listening...")
        channel = "robot_command_channel"
        pubsub = redis_client.subscribe(channel, pubsub_handler)
        pubsub_thread = pubsub.run_in_thread(sleep_time=0.001)

        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("Stopping listener...")
        pubsub_thread.stop()
    finally:
        print("Closing connection...")


if __name__ == "__main__":
    main()
