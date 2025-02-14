import queue
import logging
import threading
import numpy as np
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
    robot_init_rot = (179.99847, -0.000170, 84.27533)
    robot_ip = "192.168.0.246"
    robot_port = 8899

    def __init__(self):
        """Initialize the robot controller with Vicon and robot interfaces."""
        logger_init()
        self.vicon_queue = queue.Queue()
        self.vicon_client = ViconClient()
        self.robot = Auboi5Robot()

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
        joint_maxacc = tuple(17.308779 / 2.5 for _ in range(6))
        self.robot.set_joint_maxacc(joint_maxacc)
        self.robot.set_joint_maxvelc(joint_maxvelc)

        # Move robot to initial position
        self.robot.move_to_target_in_cartesian(
            self.robot_init_pose, self.robot_init_rot
        )

    def vicon_reader(self):
        """Thread function to read Vicon coordinates and push them into the queue."""
        while True:
            self.vicon_client.get_frame()
            hand_markers = self.vicon_client.get_vicon_subject_markers("Hand")

            # Get the center marker and convert to meters
            target = np.array(hand_markers["Center"][0]) / 1000

            # Ignore invalid target positions
            if np.all(target == 0):
                continue

            self.vicon_queue.put(target)

    def robot_mover(self):
        """Thread function to retrieve targets from queue and move the robot."""
        while True:
            try:
                # Retrieve the latest target position
                target = self.vicon_queue.get(timeout=1)

                if self.robot.get_robot_state() == RobotStatus.Running:
                    print(f"Robot is running, skipping target {target}")
                    continue

                print(f"Moving to {target}")
                delta = target - np.array(self.robot_init_pose)
                print(f"Delta {delta}")

                self.robot.move_to_target_in_cartesian(target, self.robot_init_rot)

            except queue.Empty:
                continue  # Keep checking for new positions

    def start(self):
        """Start the Vicon reading and robot movement threads."""
        try:
            self.initialize_robot()

            vicon_thread = threading.Thread(target=self.vicon_reader, daemon=True)
            robot_thread = threading.Thread(target=self.robot_mover, daemon=True)

            vicon_thread.start()
            robot_thread.start()

            # Keep the main thread alive
            vicon_thread.join()
            robot_thread.join()

        except KeyboardInterrupt:
            logger.info("Stopping robot...")
            self.robot.move_stop()

        except RobotError as e:
            logger.error(f"Robot Event: {e}")

        if self.robot.connected:
            self.robot.disconnect()
        Auboi5Robot.uninitialize()
        print("------------------------Run end-------------------------")


if __name__ == "__main__":
    controller = RobotController()
    controller.start()
