from dotenv import load_dotenv
from openai import OpenAI


class LLMClient:
    """
    A class-based application to handle interactions with an OpenAI model.
    This app simulates a robotic arm assistant that can grab objects based
    on user prompts, using Redis for possible expansions or other tools if needed.
    """

    def __init__(self) -> None:
        """
        Initialize the application by loading environment variables and creating
        an OpenAI client instance. Define the system message and the tool set.
        """
        load_dotenv()
        self.client = OpenAI()

        # Set up your system prompt
        self.system_message = """
            You are a robotic arm assistant. You are tasked with picking up objects 
            and placing them in a specific location. You are to understand the user's 
            needs from a high-level description and execute the necessary actions. 
            You have access to the following information:
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

        # Define the set of tools (functions) the model can use
        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": "grab_object",
                    "description": (
                        "Grabs the object by its name. You can only grab objects "
                        "that are in the provided VICON information, and you must "
                        "ensure it is in range."
                    ),
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
                    "description": (
                        "When the desired object is not in range, you should "
                        "not do anything."
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
    ):
        """
        Sends a prompt to the OpenAI model, including the system message
        and any user messages, along with defined tools. Prints out the tool calls
        that the model requests.
        """
        from openai.types.chat.chat_completion_message_tool_call import (
            ChatCompletionMessageToolCall,
            Function,
        )

        return [
            ChatCompletionMessageToolCall(
                id="1",
                function=Function(
                    arguments='{"name": "apple"}',
                    name="grab_object",
                ),
                type="function",
            )
        ]
        completion = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_message},
                *[{"role": "user", "content": msg} for msg in user_messages],
            ],
            tools=self.tools,
        )

        # Display the model's response details (which tools/functions it wants to call)
        print(f"Prompt: {user_messages[0]}\nResponse:")
        tool_calls = completion.choices[0].message.tool_calls

        if not tool_calls:
            print("  - No tool calls.")
        else:
            for tool_call in tool_calls:
                func_name = tool_call.function.name
                func_args = tool_call.function.arguments
                print(f"  - {func_name}({func_args})")
            return tool_calls

    def test_run(self) -> None:
        test_prompts = [
            "I want to eat an apple.",
            "I am hungry, Can you grab me something to eat?",
            "I want to eat a banana.",
        ]

        print(f"System Message:\n{self.system_message}")
        for prompt in test_prompts:
            self.prompt_robot_action([prompt])


def main() -> None:
    """
    Create and run an instance of the RobotArmChatApp.
    """
    app = LLMClient()
    app.test_run()


if __name__ == "__main__":
    main()
