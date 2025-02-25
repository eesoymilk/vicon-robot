import math
import time
import queue
import logging
import threading
import numpy as np
from vicon.vicon_client import ViconClient
from aubo_robot.auboi5_robot import (
    Auboi5Robot,
    RobotError,
    RobotErrorType,
    RobotStatus,
    logger_init,
)
from pyDHgripper import AG95 as Gripper

# gripper = Gripper(port='COM4')
logger = logging.getLogger("robot_controller")
# gripper_close = False

class RobotController:
    robot_init_pose = (0.410444, 0.080962, 0.547597)
    robot_init_pose_np = np.array(robot_init_pose)
    robot_init_rot = (179.99847, -0.000170, 84.27533)
    robot_ip = "192.168.0.246"
    robot_port = 8899

    def __init__(self):
        """Initialize the robot controller with Vicon and robot interfaces."""
        logger_init()
        self.vicon_queue = queue.Queue()
        self.vicon_client = ViconClient()
        self.robot = Auboi5Robot()
        self.controller_running = False
        self.robot_moving = False

    @property
    def robot_running(self):
        return self.robot.get_robot_state() == RobotStatus.Running

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

        # Move robot to initial position
        self.robot.move_to_target_in_cartesian(
            self.robot_init_pose, self.robot_init_rot
        )

        base_found = False
        while not base_found:
            self.vicon_client.get_frame()
            base_markers = self.vicon_client.get_vicon_subject_markers("Base")

            if all([coord == 0 for coord in base_markers["XYPlane1"][0]]):
                continue

            robot_base_planes = [
                np.array(base_markers[f"XYPlane{i}"][0]) for i in range(1, 5)
            ]
            self.robot_base = np.mean(robot_base_planes, axis=0)
            self.robot_base[2] = base_markers["Zbase"][0][2]

            print(f"\n\nRobot base: {self.robot_base}\n")
            base_found = True

    def get_ik_result(self, target, rotation):
        ori = self.robot.rpy_to_quaternion([math.radians(i) for i in rotation])
        joint_radian = self.robot.get_current_waypoint()
        ik_result = self.robot.inverse_kin(joint_radian["joint"], target, ori)
        return ik_result

    def vicon_reader(self):
        """Thread function to read Vicon coordinates and push them into the queue."""
        while self.controller_running:
            if self.robot_moving:
                print("\n\n\nRobot is running, skipping points\n\n")
                continue

            self.vicon_client.get_frame()
            hand_markers = self.vicon_client.get_vicon_subject_markers("Hand")
            hand_center = np.array(hand_markers["Center"][0])

            if np.all(hand_center == 0):
                continue

            # Get the center marker and convert to meters
            target = (hand_center - self.robot_base) / 1000
            self.vicon_queue.put(target)

    def robot_mover(self):
        """Thread function to retrieve targets from queue and move the robot."""
        while self.controller_running:
            try:
                # Retrieve the latest target position
                target = self.vicon_queue.get(timeout=1)
                ik_result = self.get_ik_result(target, self.robot_init_rot)

                if ik_result is None:
                    continue

                self.robot_moving = True
                self.robot.move_joint(ik_result["joint"])
                self.robot_moving = False

            except queue.Empty:
                pass

    def start(self):
        """Start the Vicon reading and robot movement threads."""
        try:
            self.controller_running = True
            self.initialize_robot()

            vicon_thread = threading.Thread(target=self.vicon_reader, daemon=True)
            robot_thread = threading.Thread(target=self.robot_mover, daemon=True)

            vicon_thread.start()
            robot_thread.start()

            while self.controller_running:
                print(f"Robot State: {self.robot.get_robot_state()}")
                time.sleep(0.1)

        except KeyboardInterrupt:
            logger.info("Stopping robot...")
            self.stop()
        except RobotError as e:
            logger.error(f"Robot Event: {e}")
            self.stop()
        except ValueError as e:
            logger.error(f"{e}")
            self.stop()
        finally:
            self.stop()

    def hard_coded_grasp(self):
        self.initialize_robot()
        # Move robot to initial position
        self.robot.move_to_target_in_cartesian(
            self.robot_init_pose, self.robot_init_rot
        )
        time.sleep(5)
        hard_coded_start_pose = (0.596527, 0.047547, 0.27)
        hard_coded_start_rot = (178, -0.48, 86)
        hard_coded_target_pose = (0., 0.100962, 0.2)
        self.robot.move_to_target_in_cartesian(
            hard_coded_start_pose, hard_coded_start_rot
        )
        gripper.set_pos(20)
        time.sleep(0.3)
        self.robot.move_to_target_in_cartesian(
            hard_coded_target_pose, self.robot_init_rot
        )
        gripper.set_pos(900)
        time.sleep(0.3)

    def stop(self):
        """Stop the robot controller."""
        self.controller_running = False
        self.robot.move_stop()
        if self.robot.connected:
            self.robot.disconnect()
        Auboi5Robot.uninitialize()
        print("------------------------Run end-------------------------")


if __name__ == "__main__":
    controller = RobotController()
    controller.start()
