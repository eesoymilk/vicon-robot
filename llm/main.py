from dotenv import load_dotenv
from pydantic import BaseModel
from llm_client import LLMClient
from redis_client import RedisClient
import json


class ObjectInfo(BaseModel):
    name: str
    inrange: bool
    position: tuple[float, float, float]
    rotation: tuple[float, float, float]


class UserInfo(BaseModel):
    palm_up: bool


class ViconInfo(BaseModel):
    Objects: list[ObjectInfo]
    User: UserInfo


def get_system_message(vicon_info: ViconInfo) -> str:
    """
    Dynamically generate a system message string from the given ViconInfo instance.
    """
    # Build a snippet that mirrors your original system prompt structure:
    objects_str = ""
    for obj in vicon_info.Objects:
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


vicon_info_dict = {
    "Objects": [
        {
            "name": "apple",
            "inrange": True,
            "position": (0.596527, 0.047547, 0.27),
            "rotation": (178, -0.48, 86),
        },
        {
            "name": "banana",
            "inrange": False,
            "position": (0.596527, 0.047547, 0.27),
            "rotation": (178, -0.48, 86),
        },
        {
            "name": "orange",
            "inrange": True,
            "position": (0.596527, 0.047547, 0.27),
            "rotation": (178, -0.48, 86),
        },
    ],
    "User": {
        "palm_up": True,
    },
}


def main() -> None:
    load_dotenv()
    llm_client = LLMClient()
    redis_client = RedisClient()

    vicon_info = ViconInfo(**vicon_info_dict)
    system_message = get_system_message(vicon_info)
    user_message = "Grab the apple"

    function_calls = llm_client.prompt_robot_action(system_message, [user_message])
    assert function_calls is not None, "Function calls returned None"
    func = function_calls[0].function
    print(f"Publishing function call: {func}")

    channel = "robot_command_channel"
    object_name = json.loads(func.arguments)["name"]
    vicon_object = next((d for d in vicon_info_dict["Objects"] if d["name"] == object_name), None)
    assert vicon_object is not None

    vicon_object["function_name"] = func.name
    print(f"{vicon_object=}")
    redis_client.publish(channel, json.dumps(vicon_object))


if __name__ == "__main__":
    main()
