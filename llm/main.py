import json
import logging
import logging.config
from pathlib import Path

import numpy as np
from dotenv import load_dotenv
from openai.types.chat.chat_completion_message_tool_call import Function

from vicon_info import ViconInfo
from agent import Agent
from redis_client import RedisClient

SCRIPT_DIR = Path(__file__).resolve().parent
LOG_DIR = SCRIPT_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

TEST_MODE=False
REDIS_KEY = "vicon_subjects"
REDIS_PUB_CHANNEL = "robot_command_channel"
# TODO: Use the actual robot base coordinate
ROBOT_BASE_COORDINATE = np.array((-0.60834328463, -0.05565796363, 0.03369949684))
EXPECTED_OBJECTS = ["Cube"]

logger = logging.getLogger(__name__)


def setup_logging():
    config_file = SCRIPT_DIR.parent / "logging_config.json"
    with open(config_file, "r") as f:
        logging_config = json.load(f)
    logging.config.dictConfig(logging_config)


def get_system_message(vicon_info: ViconInfo) -> str:
    """
    Dynamically generate a system message string from the given ViconInfo instance.
    """
    # Build a snippet that mirrors your original system prompt structure:
    objects_str = ""
    for obj in vicon_info.objects:
        objects_str += f"""
    {{
        name: "{obj.name}",
        inrange: {str(obj.inrange).lower()},
    }},"""
    objects_str = objects_str.strip().rstrip(",")

    user_str = f"{{ palm_up: {str(vicon_info.user.palm_up).lower()} }}"

    system_message = f"""
    You are a robotic arm assistant. You are tasked with picking up objects
    and placing them in a specific location. You are to understand the user's
    needs from a high-level description and execute the necessary actions.
    You have access to the following information:
    ```
    VICON Information:
    Objects: [{objects_str}]
    User: {user_str}
    ```
    """
    return system_message


def get_command(vicon_info: ViconInfo, function_call: Function):
    object_name = json.loads(function_call.arguments)["name"]
    object_info = next((o for o in vicon_info.objects if o.name == object_name), None)
    assert object_info is not None, f"Object {object_name} not found in ViconInfo"
    command_dict = {"function_name": function_call.name, **object_info.model_dump() }
    return json.dumps(command_dict)


def main() -> None:
    load_dotenv()
    setup_logging()
    agent = Agent(test_mode=TEST_MODE)
    redis_client = RedisClient()

    while True:
        user_prompt = agent.listen_user_prompt()  # blocking call
        redis_value = redis_client.get_value(REDIS_KEY)
        vicon_info = ViconInfo.from_redis_value(
            redis_value,
            robot_base_coordinate=ROBOT_BASE_COORDINATE,
            expected_objects=EXPECTED_OBJECTS,
        )
        system_message = get_system_message(vicon_info)
        function_call = agent.prompt_robot_action(
            system_message,
            [user_prompt],
            model="gpt-4o-mini"
        )
        if function_call.name == "noop":
            print("No action taken: object not in range or not recognized.")
            continue
        elif function_call.name == "grab_object":
            args = json.loads(function_call.arguments)
            print(f"Function call: {function_call.name} with args: {args}")

        command = get_command(vicon_info, function_call)
        logger.info(f"{command=}")
        redis_client.publish(REDIS_PUB_CHANNEL, command)


if __name__ == "__main__":
    main()
