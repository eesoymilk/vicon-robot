import time
import json
import logging
import logging.config
from pathlib import Path

from command import Command
from redis_client import RedisClient
from robot_controller import RobotController

SCRIPT_DIR = Path(__file__).resolve().parent
LOG_DIR = SCRIPT_DIR.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

logger = logging.getLogger(__name__)


def setup_logging():
    config_file = SCRIPT_DIR.parent / "logging_config.json"
    with open(config_file, "r") as f:
        logging_config = json.load(f)
    logging.config.dictConfig(logging_config)


def command_robot(controller: RobotController, command: Command):
    logger.info(f"Function: {command.function_name}, Pos: {command.position}")
    if command.function_name == "grab_object":
        controller.grab_object(command.position)


def main():
    setup_logging()

    channel = "robot_command_channel"
    redis_client = RedisClient()
    robot_controller = RobotController()
    robot_controller.initialize_robot()

    time.sleep(1)

    def pubsub_handler(message):
        if not message:
            return

        logger.info(f"Received message: {message}")
        if message["type"] == "message":
            data = message["data"]
            command = Command(**json.loads(data))
            command_robot(robot_controller, command)

    try:
        logger.info("Listening for robot commands...")
        pubsub = redis_client.subscribe(channel, pubsub_handler)
        pubsub_thread = pubsub.run_in_thread(sleep_time=0.001)
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Stopping listener...")

    logger.info("Closing connection...")
    pubsub_thread.stop()


if __name__ == "__main__":
    main()
