import json
import time
import logging
import logging.config
from pathlib import Path

import numpy as np

from vicon_client import ViconClient
from redis_client import RedisClient

SCRIPT_DIR = Path(__file__).resolve().parent
LOG_DIR = SCRIPT_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

REDIS_KEY = "vicon_subjects"

logger = logging.getLogger(__name__)


def setup_logging():
    config_file = SCRIPT_DIR.parent / "logging_config.json"
    with open(config_file, "r") as f:
        logging_config = json.load(f)
    logging.config.dictConfig(logging_config)


def get_base(vicon_client: ViconClient):
    """
    This function gets the robot base coordinate from the vicon data.
    It is blocking and will keep running until the robot base is found.
    """
    while True:
        vicon_client.get_frame()
        vicon_subjects = vicon_client.get_all_subject_markers()
        logger.info(f"{vicon_subjects=}")
        base_markers = vicon_subjects["Base"]

        if all([coord == 0 for coord in base_markers["XYPlane1"][0]]):
            continue

        robot_base_planes = [
            np.array(base_markers[f"XYPlane{i}"][0]) for i in range(1, 5)
        ]
        robot_base = np.mean(robot_base_planes, axis=0)
        robot_base[2] = base_markers["ZBase1"][0][2]
        return robot_base


def main():
    setup_logging()
    vicon_client = ViconClient()
    redis_client = RedisClient()

    # We get the robot base coordinate from the vicon data once before the loop
    # TODO: Discuss whether this should be done in the main loop to get real-time updates
    robot_base = get_base(vicon_client)
    print(f"=== Robot base: {robot_base} ===")
    redis_client.set_value("robot_base", json.dumps(list(robot_base)))

    while True:
        vicon_client.get_frame()
        vicon_subjects = vicon_client.get_all_subject_markers()
        logger.info(f"{vicon_subjects=}")
        redis_client.set_value(REDIS_KEY, json.dumps(vicon_subjects))
        time.sleep(0.1)


if __name__ == "__main__":
    main()
