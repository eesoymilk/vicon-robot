from dotenv import load_dotenv
from openai import OpenAI


def prompt_robot_action(
    client: OpenAI,
    system_message: list[str],
    user_messages: list[str],
    tools: list[dict],
) -> None:
    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_message},
            *[{"role": "user", "content": message} for message in user_messages],
        ],
        tools=tools,
    )

    print(f"Prompt: {user_messages[0]}\nResponse:")
    for tool_call in completion.choices[0].message.tool_calls:
        print(f"  - {tool_call.function.name}({tool_call.function.arguments})")


def main() -> None:
    load_dotenv()
    client = OpenAI()

    system_message = """
        You are a robotic arm assistant. You are tasked with picking up objects and placing them in a specific location. You are to understand the user's needs from a high-level description and execute the necessary actions. You have access to the following information:
        ```
        VICON Information:
        Objects: [{
            name: "apple",
            inrange: True,
        },
        {
            name: "banana",
            inrange: False,
        },
        {
            name: "orange",
            inrange: True,
        }]
        User: {
            palm_up: True,
        }
        ```
    """

    tools = [
        {
            "type": "function",
            "function": {
                "name": "grab_object",
                "description": "Grabs the object by its name. You can only grab objects that are in the provide VICON information and you have to make sure it is in range.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "The name of the object to grab.",
                        }
                    },
                    "additionalProperties": False,
                    "required": ["name"],
                },
                "strict": True,
            },
        },
        {
            "type": "function",
            "function": {
                "name": "noop",
                "description": "When the desired object is not in range, you should not do anything.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "additionalProperties": False,
                },
                "strict": True,
            },
        },
    ]

    test_prompts = [
        "I want to eat an apple.",
        "I am hungry, Can you grab me something to eat?",
        "I want to eat a banana.",
    ]

    print(f"System Message:\n{system_message}")

    for prompt in test_prompts:
        prompt_robot_action(
            client,
            system_message,
            [prompt],
            tools,
        )


if __name__ == "__main__":
    main()
