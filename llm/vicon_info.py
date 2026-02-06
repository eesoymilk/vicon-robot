import json
import logging

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class ObjectInfo(BaseModel):
    name: str
    inrange: bool
    position: tuple[float, float, float]


class UserInfo(BaseModel):
    palm_up: bool
    inrange: bool
    hand_position: tuple[float, float, float]


class ViconInfo(BaseModel):
    objects: list[ObjectInfo]
    user: UserInfo

    @staticmethod
    def from_dict(vicon_info_dict: dict) -> "ViconInfo":
        objects = [ObjectInfo(**o) for o in vicon_info_dict["objects"]]
        user = UserInfo(**vicon_info_dict["user"])
        return ViconInfo(objects=objects, User=user)

    @staticmethod
    def from_redis_value(
        value: str,
        expected_objects: list[str],
    ) -> "ViconInfo":
        """
        Create ViconInfo from Redis value.
        Expects pre-processed object positions from vicon module.
        """
        value_dict = json.loads(value)
        objects = []

        for subject_name, data in value_dict.items():
            if subject_name not in expected_objects:
                continue

            objects.append(
                ObjectInfo(
                    name=subject_name,
                    inrange=data.get("inrange", True),
                    position=tuple(data["position"])
                )
            )

        user = UserInfo(palm_up=True, inrange=True, hand_position=(0, 0, 0))
        return ViconInfo(objects=objects, user=user)


# example_vicon_info = ViconInfo(
#     objects=[
#         ObjectInfo(
#             name="apple",
#             inrange=True,
#             position=(0.596527, 0.047547, 0.27),
#         ),
#         ObjectInfo(
#             name="banana",
#             inrange=False,
#             position=(0.596527, 0.047547, 0.27),
#         ),
#         ObjectInfo(
#             name="orange",
#             inrange=True,
#             position=(0.596527, 0.047547, 0.27),
#         ),
#     ],
#     User=UserInfo(palm_up=True),
# )
