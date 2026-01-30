from pydantic import BaseModel
from typing import Optional, Tuple


class Command(BaseModel):
    """Command received from LLM or TUI.

    Fields match the pattern from llm package.
    return_position is optional for backwards compatibility.
    """
    function_name: str
    name: str
    position: Tuple[float, float, float]
    inrange: bool = True
    return_position: Optional[Tuple[float, float, float]] = None
