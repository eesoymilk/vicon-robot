from pydantic import BaseModel


class Command(BaseModel):
    function_name: str
    position: tuple[float, float, float]
