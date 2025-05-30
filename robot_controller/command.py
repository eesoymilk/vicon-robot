from pydantic import BaseModel
from typing import Tuple


# class Command(BaseModel):
#     function_name: str
#     position: Tuple[float, float, float]

class ObjectInfo(BaseModel):
    name: str
    inrange: bool
    position: Tuple[float, float, float]


class Command(BaseModel):
    function_name: str
    object: ObjectInfo
    target: ObjectInfo

