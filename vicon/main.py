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
REDIS_OBJECTS_KEY = "vicon_objects"
FLANGE_OFFSET = 0.2  # meters

logger = logging.getLogger(__name__)


def calculate_object_positions(vicon_subjects: dict, robot_base: np.ndarray) -> dict:
    """
    Calculate object positions relative to robot base.

    Args:
        vicon_subjects: Raw marker data from Vicon {subject: {marker: (x,y,z,occluded)}}
        robot_base: Robot base coordinate in mm

    Returns:
        Dict of {subject_name: {"position": [x, y, z], "inrange": bool}}
        Positions are in meters, relative to robot base
    """
    objects = {}
    for subject_name, markers in vicon_subjects.items():
        if subject_name == "Base":
            continue  # Skip the base subject

        # Handle Board specially: calculate center from Board1-4 markers
        if subject_name == "Board":
            board_marker_names = ["Board1", "Board2", "Board3", "Board4"]
            board_positions = []
            for marker_name in board_marker_names:
                if marker_name in markers:
                    pos, _ = markers[marker_name]
                    board_positions.append(pos)
            if len(board_positions) != 4:
                continue  # Skip if not all Board markers are present
            position_mm = np.mean(board_positions, axis=0)
        else:
            # Average all marker positions for this subject
            positions = [pos for pos, _ in markers.values()]
            if not positions:
                continue
            position_mm = np.mean(positions, axis=0)

        # Convert mm to m and subtract base
        position_m = position_mm / 1000
        base_m = robot_base / 1000
        offset_position = position_m - base_m

        # Add flange offset to Z (only for grab targets, not Board)
        if subject_name != "Board":
            offset_position[2] += FLANGE_OFFSET

        objects[subject_name] = {
            "position": list(offset_position),
            "inrange": True  # Could add range check logic here
        }

    return objects


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
    print(f"=== Robot base (mm): {robot_base} ===")
    redis_client.set_value("robot_base", json.dumps(list(robot_base)))

    while True:
        vicon_client.get_frame()
        vicon_subjects = vicon_client.get_all_subject_markers()
        logger.info(f"{vicon_subjects=}")

        # Calculate offset positions
        object_positions = calculate_object_positions(vicon_subjects, robot_base)

        # Publish both raw and processed data
        redis_client.set_value(REDIS_KEY, json.dumps(vicon_subjects))  # raw
        redis_client.set_value(REDIS_OBJECTS_KEY, json.dumps(object_positions))  # processed

        time.sleep(0.1)


if __name__ == "__main__":
    main()
