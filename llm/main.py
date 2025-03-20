import json
import logging
from pathlib import Path

from dotenv import load_dotenv
from openai.types.chat.chat_completion_message_tool_call import Function

from vicon_info import ViconInfo
from agent import Agent
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

    user_str = f"{{ palm_up: {str(vicon_info.User.palm_up).lower()} }}"

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


def get_vicon_info(redis_client: RedisClient) -> ViconInfo:
    raw_vicon_info = redis_client.get("vicon_info")
    vicon_info_dict = json.loads(raw_vicon_info)
    return ViconInfo(**vicon_info_dict)


def prompt_robot_action(
    agent: Agent,
    system_message: str,
    user_messages: list[str],
):
    function_calls = agent.prompt_robot_action(system_message, user_messages)
    func = function_calls[0].function
    logger.info(f"Publishing function call: {func}")
    return func


def get_command(vicon_info: ViconInfo, function_call: Function):
    object_name = json.loads(function_call.arguments)["name"]
    command_dict = next((o for o in vicon_info.objects if o.name == object_name), None)
    assert command_dict is not None, f"Object {object_name} not found in ViconInfo"
    command_dict["function_name"] = function_call.name
    return json.dumps(command_dict)


def main() -> None:
    load_dotenv()
    agent = Agent()
    redis_client = RedisClient()
    redis_pub_channel = "robot_command_channel"

    while True:
        user_prompt = agent.listen_user_prompt()  # blocking call
        vicon_info = get_vicon_info(redis_client)
        system_message = get_system_message(vicon_info)
        function_call = prompt_robot_action(agent, system_message, [user_prompt])
        command = get_command(vicon_info, function_call)
        redis_client.publish(redis_pub_channel, command)


if __name__ == "__main__":
    main()
