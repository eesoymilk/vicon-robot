import logging
from openai import OpenAI

logger = logging.getLogger(__name__)


class Agent:
    def __init__(self, test_mode: bool = False) -> None:
        self.test_mode = test_mode

        if not self.test_mode:
            self.client = OpenAI()

        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": "grab_object",
                    "description": (
                        "Grabs the object by its name. You can only grab objects "
                        "that are in the provided VICON information, and you must "
                        "ensure it is in range."
                        "If the user's palm is up, you should place the object at the location of the 'Palm' object."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            # "name": {
                            #     "type": "string",
                            #     "description": "The name of the object to grab and place.",
                            # }
                            "object": {
                                "type": "string",
                                "description": (
                                    "The name of the object to grab and place. "
                                    "This should match an object in the VICON information."
                                ),
                            },
                            "target": {
                                "type": "string",
                                "description": (
                                    "The name of the target object where the grabbed object "
                                    "should be placed. (eg. 'Palm' for the user's hand)"
                                ),
                            }
                        },
                        "additionalProperties": False,
                        "required": ["object", "target"],
                        "examples": [
                            {
                                "object": "Cube",
                                "target": "Palm",
                            },
                            {
                                "object": "Apple",
                                "target": "Palm",
                            },
                        ],
                    },
                    "strict": True,
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "noop",
                    "description": (
                        "When the desired object is either not in range or not recognized, "
                        "you should not do anything."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "additionalProperties": False,
                    },
                    "strict": True,
                },
            },
        ]

    def prompt_robot_action(
        self,
        system_message: str,
        user_messages: list[str],
        model: str = "gpt-4o-mini"
    ):
        if self.test_mode:
            from openai.types.chat.chat_completion_message_tool_call import (
                Function,
            )

            return Function(
                arguments='{"name": "Cube"}',
                name="grab_object",
            )

        completion = self.client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_message},
                *[{"role": "user", "content": msg} for msg in user_messages],
            ],
            tools=self.tools,
        )

        tool_calls = completion.choices[0].message.tool_calls
        if not tool_calls:
            print("No tool calls found in the response.")
            print("Response:", completion.choices[0].message.content)
            return None

        # Display the model's response details (which tools/functions it wants to call) in debug logs
        logger.debug(f"Prompt: {user_messages[0]}\nResponse:")
        for tool_call in tool_calls:
            func_name = tool_call.function.name
            func_args = tool_call.function.arguments
            logger.debug(f"  - {func_name}({func_args})")

        return tool_calls[0].function

    def listen_user_prompt(self):
        return input("User Prompt: ").strip()

    def test_run(self) -> None:
        test_prompts = [
            "I want to eat an apple.",
            "I am hungry, Can you grab me something to eat?",
            "I want to eat a banana.",
        ]

        logger.info(f"System Message:\n{self.system_message}")
        for prompt in test_prompts:
            self.prompt_robot_action([prompt])


def main() -> None:
    """
    Create and run an instance of the RobotArmChatApp.
    """
    app = Agent()
    app.test_run()


if __name__ == "__main__":
    main()
