import time
import json
import logging
import logging.config
from pathlib import Path

import numpy as np

from command import Command
from redis_client import RedisClient
from robot_controller import RobotController

SCRIPT_DIR = Path(__file__).resolve().parent
LOG_DIR = SCRIPT_DIR.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

REDIS_SUB_CHANNEL = "robot_command_channel"

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


def get_base(redis_client: RedisClient):
    while True:
        raw_vicon_info = json.loads(redis_client.get_value("vicon_subjects"))
        base_markers = raw_vicon_info["Base"]

        if all([coord == 0 for coord in base_markers["XYPlane1"][0]]):
            continue

        robot_base_planes = [
            np.array(base_markers[f"XYPlane{i}"][0]) for i in range(1, 5)
        ]
        robot_base = np.mean(robot_base_planes, axis=0)
        robot_base[2] = base_markers["Zbase"][0][2]
        return robot_base


def main():
    setup_logging()
    redis_client = RedisClient()
    robot_controller = RobotController()

    robot_controller.initialize_robot()
    time.sleep(1)

    base = get_base(redis_client)
    logger.warning(f"=== Robot base: {base} ===")
    return

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
        pubsub = redis_client.subscribe(REDIS_SUB_CHANNEL, pubsub_handler)
        pubsub_thread = pubsub.run_in_thread(sleep_time=0.001)
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Stopping listener...")

    logger.info("Closing connection...")
    pubsub_thread.stop()


if __name__ == "__main__":
    main()
