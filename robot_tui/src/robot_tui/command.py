from pydantic import BaseModel


class Command(BaseModel):
    """Command to send to the robot controller.

    Mimics the pattern from llm package - includes object info
    plus optional return_position for drop location.
    """
    function_name: str
    name: str
    position: tuple[float, float, float]
    inrange: bool = True
    return_position: tuple[float, float, float] | None = None
