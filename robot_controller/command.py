from pydantic import BaseModel
from typing import Tuple


class Command(BaseModel):
    function_name: str
    position: Tuple[float, float, float]
