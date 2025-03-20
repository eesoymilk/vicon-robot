from pydantic import BaseModel


class ObjectInfo(BaseModel):
    name: str
    inrange: bool
    position: tuple[float, float, float]


class UserInfo(BaseModel):
    palm_up: bool


class ViconInfo(BaseModel):
    objects: list[ObjectInfo]
    User: UserInfo


example_vicon_info = ViconInfo(
    objects=[
        ObjectInfo(
            name="apple",
            inrange=True,
            position=(0.596527, 0.047547, 0.27),
        ),
        ObjectInfo(
            name="banana",
            inrange=False,
            position=(0.596527, 0.047547, 0.27),
        ),
        ObjectInfo(
            name="orange",
            inrange=True,
            position=(0.596527, 0.047547, 0.27),
        ),
    ],
    User=UserInfo(palm_up=True),
)
