import json
import time
import logging
import logging.config
from pathlib import Path

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


def main():
    setup_logging()
    vicon_client = ViconClient()
    redis_client = RedisClient()

    while True:
        vicon_client.get_frame()
        vicon_subjects = vicon_client.get_all_subject_markers()
        logger.info(f"{vicon_subjects=}")
        redis_client.set_value(REDIS_KEY, json.dumps(vicon_subjects))
        time.sleep(0.1)


if __name__ == "__main__":
    main()
