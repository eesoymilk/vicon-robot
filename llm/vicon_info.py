import json
import logging

import numpy as np
import numpy.typing as npt
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class ObjectInfo(BaseModel):
    name: str
    inrange: bool
    position: tuple[float, float, float]


class UserInfo(BaseModel):
    palm_up: bool
    # inrange: bool
    # hand_position: tuple[float, float, float]


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
        robot_base_coordinate: npt.ArrayLike,
        expected_objects: list[str],
    ) -> "ViconInfo":
        value_dict = json.loads(value)
        objects = []

        flange_offset = 0.2
        for subject_name, markers in value_dict.items():
            if subject_name not in expected_objects:
                continue
            logger.info(f"markers {markers}")
            position = np.mean([pos for pos, _ in (markers.values())], axis=0) / 1000
            offset_position = position - robot_base_coordinate
            logger.info(f"ori position {offset_position}")
            offset_position[2] = offset_position[2] + flange_offset
            logger.info(f"position {offset_position}")

            objects.append(
                ObjectInfo(
                    name=subject_name,
                    inrange=True,
                    position=tuple(offset_position)
                )
            )

        palm_present = any(object.name.lower() == "palm" for object in objects)
        user = UserInfo(palm_up=palm_present)
        return ViconInfo(objects=objects, user=user)
