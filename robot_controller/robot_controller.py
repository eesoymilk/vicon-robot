import math
import time
import logging
from pathlib import Path
from typing import Optional, Tuple

import numpy as np
from aubo_robot.auboi5_robot import (
    Auboi5Robot,
    RobotError,
    RobotErrorType,
)
from pyDHgripper import AG95 as Gripper
from trajectory_logger import TrajectoryLogger

logger = logging.getLogger(__name__)


class RobotController:
    robot_init_pose = (0.410444, 0.080962, 0.547597)
    robot_return_pose = (0, 0.6, 0.25)
    robot_init_pose_np = np.array(robot_init_pose)
    robot_init_rot = (179.99847, -0.000170, 84.27533)
    robot_ip = "192.168.0.246"
    robot_port = 8899

    def __init__(self):
        """Initialize the robot controller with Vicon and robot interfaces."""
        self.robot = Auboi5Robot()
        self.gripper = Gripper(port="COM4")
        self.controller_running = False
        self.trajectory_logger: Optional[TrajectoryLogger] = None

    def enable_trajectory_logging(
        self,
        output_dir: Path = None,
        poll_rate_hz: float = 20.0,
    ):
        """Enable trajectory logging for grab operations."""
        self.trajectory_logger = TrajectoryLogger(
            robot=self.robot,
            output_dir=output_dir,
            poll_rate_hz=poll_rate_hz,
        )
        logger.info(f"Trajectory logging enabled at {poll_rate_hz}Hz")

    def initialize_robot(self):
        """Initialize and connect to the robot arm."""
        Auboi5Robot.initialize()
        handle = self.robot.create_context()
        logger.info(f"robot.rshd={handle}")

        result = self.robot.connect(self.robot_ip, self.robot_port)
        if result != RobotErrorType.RobotError_SUCC:
            raise RobotError(
                result,
                error_msg=f"Connect server {self.robot_ip}:{self.robot_port} failed.",
            )

        self.robot.enable_robot_event()
        self.robot.init_profile()

        joint_maxvelc = (10, 10, 10, 10, 10, 10)
        joint_maxacc = tuple([17.308779 / 2.5 for _ in range(6)])
        self.robot.set_joint_maxacc(joint_maxacc)
        self.robot.set_joint_maxvelc(joint_maxvelc)
        # self.robot.set_arrival_ahead_time(0.5)
        # self.robot.set_arrival_ahead_blend(0.05) # try arrival ahead time (0.5)


    def get_ik_result(self, target, rotation):
        ori = self.robot.rpy_to_quaternion([math.radians(i) for i in rotation])
        joint_radian = self.robot.get_current_waypoint()
        ik_result = self.robot.inverse_kin(joint_radian["joint"], target, ori)
        if ik_result is None:
            raise RuntimeError(f"IK solver failed for target={target}, rotation={rotation}")
        return ik_result

    def grab_object(
        self,
        target_pos: Tuple[float, float, float] = (0.596527, 0.047547, 0.27),
        target_rot: Tuple[float, float, float] = (178, -0.48, 86),
        return_pos: Tuple[float, float, float] = None,
        object_name: Optional[str] = None,
    ):
        """
        Grasp sequence that moves the robot to grab an object and return it.

        Args:
            target_pos: Position to grab object from
            target_rot: Rotation at target position
            return_pos: Position to drop object at (defaults to robot_return_pose)
            object_name: Name of the object being grabbed (for trajectory logging)
        """
        if return_pos is None:
            return_pos = self.robot_return_pose

        # Start trajectory logging if enabled
        tl = self.trajectory_logger
        if tl:
            tl.start_trajectory(target_pos, target_rot, return_pos, object_name)

        try:
            # Phase 1: Approach with open gripper, close after arrival
            time.sleep(1)
            ik_result = self.get_ik_result(target_pos, target_rot)
            if tl:
                tl.record_movement(ik_result["joint"], "move_to_grab", gripper_position=900)
            else:
                self.robot.move_joint(ik_result["joint"])
            self.gripper.set_pos(20)

            # Phase 2: Lift with closed gripper
            time.sleep(1)
            lifted_pos = list(target_pos)
            lifted_pos[2] = lifted_pos[2] + 0.1
            ik_result = self.get_ik_result(lifted_pos, target_rot)
            if tl:
                tl.record_movement(ik_result["joint"], "lift_object", gripper_position=20)
            else:
                self.robot.move_joint(ik_result["joint"])

            # Phase 3: Move to return with closed gripper, open after arrival
            time.sleep(1)
            ik_result = self.get_ik_result(return_pos, self.robot_init_rot)
            if tl:
                tl.record_movement(ik_result["joint"], "move_to_return", gripper_position=20)
            else:
                self.robot.move_joint(ik_result["joint"])
            self.gripper.set_pos(900)

            # Phase 4: Return home with open gripper
            time.sleep(1)
            ik_result = self.get_ik_result(self.robot_init_pose, self.robot_init_rot)
            if tl:
                tl.record_movement(ik_result["joint"], "return_home", gripper_position=900)
            else:
                self.robot.move_joint(ik_result["joint"])

            if tl:
                tl.end_trajectory(success=True)

        except Exception as e:
            if tl:
                tl.end_trajectory(success=False, error_message=str(e))
            raise

    def stop(self):
        """Stop the robot controller."""
        self.controller_running = False
        self.robot.move_stop()
        if self.robot.connected:
            self.robot.disconnect()
        Auboi5Robot.uninitialize()
        logger.info("------------------------Run end-------------------------")


if __name__ == "__main__":
    controller = RobotController()
    controller.initialize_robot()
