import math
import time
import queue
import logging
import threading
import numpy as np
import libpyauboi5
from vicon_client import ViconClient
from aubo_robot.robot_control import (
    Auboi5Robot,
    RobotError,
    RobotErrorType,
    RobotStatus,
    logger_init,
)


logger = logging.getLogger("main.robot_controller")


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
        self.running = False
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

        joint_maxvelc = (20, 20, 20, 20, 20, 20)
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

            robot_base_xy1 = np.array(base_markers["XYPlane1"][0])
            robot_base_xy2 = np.array(base_markers["XYPlane2"][0])
            robot_base_xy3 = np.array(base_markers["XYPlane3"][0])
            robot_base_xy4 = np.array(base_markers["XYPlane4"][0])

            self.robot_base = (
                robot_base_xy1 + robot_base_xy2 + robot_base_xy3 + robot_base_xy4
            ) / 4
            self.robot_base[2] = base_markers["Zbase"][0][2]

            print(f"\n\nRobot base: {self.robot_base}\n")
            base_found = True

    def get_ik_result(self, pos, rpy_xyz):
        rpy_xyz = [i / 180.0 * pi for i in rpy_xyz]
        # 欧拉角转四元数
        ori = libpyauboi5.rpy_to_quaternion(self.rshd, rpy_xyz)

        # 逆运算得关节角
        joint_radian = libpyauboi5.get_current_waypoint(self.rshd)

        ik_result = libpyauboi5.inverse_kin(self.rshd, joint_radian['joint'], pos, ori)

        logging.info("ik_result====>{0}".format(ik_result))

    def vicon_reader(self):
        """Thread function to read Vicon coordinates and push them into the queue."""
        while self.running:
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
        while self.running:
            try:
                # Retrieve the latest target position
                target = self.vicon_queue.get(timeout=1)

                result = self.robot.move_to_target_in_cartesian(target, self.robot_init_rot)

                print(f"queue length: {self.vicon_queue.qsize()}")

                if result == RobotErrorType.RobotError_SUCC:
                    print(f"\n\n\n\n\n\n\nMoving to {target}")
                    delta = target - np.array(self.robot_init_pose)
                    print(f"Delta {delta}\n\n\n\n\n\n")

            except queue.Empty:
                continue  # Keep checking for new positions

    def start(self):
        """Start the Vicon reading and robot movement threads."""
        try:
            self.running = True
            self.initialize_robot()

            vicon_thread = threading.Thread(target=self.vicon_reader, daemon=True)
            robot_thread = threading.Thread(target=self.robot_mover, daemon=True)

            vicon_thread.start()
            robot_thread.start()

            while self.running:
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

    def stop(self):
        """Stop the robot controller."""
        self.running = False
        self.robot.move_stop()
        if self.robot.connected:
            self.robot.disconnect()
        Auboi5Robot.uninitialize()
        print("------------------------Run end-------------------------")


if __name__ == "__main__":
    controller = RobotController()
    controller.start()
