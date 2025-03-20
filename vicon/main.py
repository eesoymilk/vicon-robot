import json
import time
import logging
from pathlib import Path

from vicon_client import ViconClient
from redis_client import RedisClient

SCRIPT_DIR = Path(__file__).resolve().parent
LOG_DIR = SCRIPT_DIR.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

logger = logging.getLogger(__name__)


def setup_logging():
    config_file = SCRIPT_DIR.parent / "logging_config.json"
    with open(config_file, "r") as f:
        logging_config = json.load(f)
    logging.config.dictConfig(logging_config)


def main():
    vicon_client = ViconClient()
    redis_client = RedisClient()

    while True:
        vicon_client.get_frame()
        vicon_subject_info = vicon_client.get_all_subject_markers()
        redis_client.set_value("vicon_info", json.dumps(vicon_subject_info))
        time.sleep(0.1)


if __name__ == "__main__":
    main()
